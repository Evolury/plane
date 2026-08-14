# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Evolury: endpoints das tarefas recorrentes (ADR 0010, revisão 13/08/2026).
#
# Escrever é porta de admin — a regra cria trabalho para os outros sem pedir
# licença. Ler é de todos: o selo no cartão, a seção "Repetir" desabilitada e o
# rastro da tarefa gerada são informação, não poder.

# Python imports
from collections import defaultdict

# Django imports
from django.db import transaction
from django.utils import timezone

# Third party imports
from rest_framework import status
from rest_framework.response import Response

# Module imports
from plane.app.permissions import ROLE, allow_permission
from plane.app.serializers.recurring_work_item import RecurringWorkItemSerializer
from plane.app.views.base import BaseViewSet
from plane.bgtasks.recurring_work_item_task import agendar_proxima_data
from plane.db.models import IssueAssignee, ProjectMember, RecurringWorkItem, RecurringWorkItemOccurrence
from plane.utils.recurrence import proximas_datas


class RecurringWorkItemViewSet(BaseViewSet):
    serializer_class = RecurringWorkItemSerializer
    model = RecurringWorkItem

    def get_queryset(self):
        return (
            RecurringWorkItem.objects.filter(
                workspace__slug=self.kwargs.get("slug"), project_id=self.kwargs.get("project_id")
            )
            # Origem excluída leva a regra junto; até o job passar, a lista
            # não pode mostrar uma regra apontando para o nada.
            .filter(source_issue__deleted_at__isnull=True)
            .select_related("project", "initial_state", "source_issue", "source_issue__state")
        )

    def _contexto_de_responsaveis(self, regras, project_id):
        """Os dois conjuntos que o serializer precisaria consultar por regra.

        O selo do quadro chama esta lista a cada render; sem isto seriam duas
        consultas por regra para responder a mesma pergunta sobre o mesmo
        projeto.
        """
        ativos = set(
            ProjectMember.objects.filter(project_id=project_id, is_active=True).values_list(
                "member_id", flat=True
            )
        )
        por_tarefa = defaultdict(list)
        origens = [regra.source_issue_id for regra in regras]
        for vinculo in IssueAssignee.objects.filter(issue_id__in=origens).select_related("assignee"):
            por_tarefa[vinculo.issue_id].append(vinculo)
        return {"membros_ativos": ativos, "responsaveis_por_tarefa": por_tarefa}

    @allow_permission(allowed_roles=[ROLE.ADMIN, ROLE.MEMBER, ROLE.GUEST], level="PROJECT")
    def list(self, request, slug, project_id):
        regras = list(self.get_queryset())
        serializer = RecurringWorkItemSerializer(
            regras, many=True, context=self._contexto_de_responsaveis(regras, project_id)
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    @allow_permission(allowed_roles=[ROLE.ADMIN, ROLE.MEMBER, ROLE.GUEST], level="PROJECT")
    def for_issue(self, request, slug, project_id, issue_id):
        """O papel de uma tarefa na recorrência: origem, gerada, ou nenhum.

        É o que alimenta a seção "Repetir" do cartão — inclusive o rastro
        "gerada pela recorrência de X", que vem da trava.
        """
        regra = self.get_queryset().filter(source_issue_id=issue_id).first()
        if regra is not None:
            return Response(
                {"role": "source", "rule": RecurringWorkItemSerializer(regra).data},
                status=status.HTTP_200_OK,
            )

        ocorrencia = (
            RecurringWorkItemOccurrence.objects.filter(issue_id=issue_id, issue__project_id=project_id)
            .select_related(
                "recurring_work_item",
                "recurring_work_item__source_issue",
                "recurring_work_item__source_issue__state",
                "recurring_work_item__initial_state",
                "recurring_work_item__project",
            )
            .order_by("-scheduled_for")
            .first()
        )
        if ocorrencia is not None:
            return Response(
                {
                    "role": "occurrence",
                    "rule": RecurringWorkItemSerializer(ocorrencia.recurring_work_item).data,
                    "scheduled_for": ocorrencia.scheduled_for,
                },
                status=status.HTTP_200_OK,
            )
        return Response({"role": None, "rule": None}, status=status.HTTP_200_OK)

    @allow_permission(allowed_roles=[ROLE.ADMIN], level="PROJECT")
    def create(self, request, slug, project_id):
        serializer = RecurringWorkItemSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        origem = serializer.validated_data.get("source_issue")
        if origem is None or str(origem.project_id) != str(project_id):
            return Response(
                {"source_issue": "A tarefa de origem precisa ser deste projeto."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        regra = serializer.save(project_id=project_id, workspace_id=self.workspace_id_from_slug(slug))
        # Sem isto a regra nasce sem relógio e o job nunca a enxerga.
        agendar_proxima_data(regra)
        return Response(RecurringWorkItemSerializer(regra).data, status=status.HTTP_201_CREATED)

    @allow_permission(allowed_roles=[ROLE.ADMIN], level="PROJECT")
    def partial_update(self, request, slug, project_id, pk):
        regra = self.get_queryset().filter(pk=pk).first()
        if regra is None:
            return Response({"error": "Tarefa recorrente não encontrada."}, status=status.HTTP_404_NOT_FOUND)

        serializer = RecurringWorkItemSerializer(regra, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        regra = serializer.save()
        # A agenda pode ter mudado; o relógio antigo não vale mais. Trocar de
        # modo zera o relógio: uma data de calendário não sobrevive à mudança
        # para "após a conclusão".
        if "generation_mode" in request.data:
            RecurringWorkItem.objects.filter(pk=regra.pk).update(next_run_at=None)
            regra.next_run_at = None
        agendar_proxima_data(regra)
        return Response(RecurringWorkItemSerializer(regra).data, status=status.HTTP_200_OK)

    @allow_permission(allowed_roles=[ROLE.ADMIN], level="PROJECT")
    def destroy(self, request, slug, project_id, pk):
        regra = self.get_queryset().filter(pk=pk).first()
        if regra is None:
            return Response({"error": "Tarefa recorrente não encontrada."}, status=status.HTTP_404_NOT_FOUND)
        # As tarefas já geradas ficam: elas são trabalho, não histórico da regra.
        regra.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @allow_permission(allowed_roles=[ROLE.ADMIN], level="PROJECT")
    def for_member(self, request, slug, project_id, user_id):
        """As recorrentes em que alguém é responsável.

        Alimenta a confirmação de remoção do membro: o ato não é travado, mas
        deixa de ser silencioso (ADR 0010).
        """
        regras = list(self.get_queryset().filter(source_issue__assignees__id=user_id).distinct())
        serializer = RecurringWorkItemSerializer(
            regras, many=True, context=self._contexto_de_responsaveis(regras, project_id)
        )
        return Response({"count": len(regras), "rules": serializer.data}, status=status.HTTP_200_OK)

    @allow_permission(allowed_roles=[ROLE.ADMIN], level="PROJECT")
    def transfer_assignee(self, request, slug, project_id):
        """Troca o responsável nas tarefas de origem, de uma vez.

        `to_user` vazio apenas remove — é o conserto inline do painel, quando
        já não há para quem transferir.
        """
        de = request.data.get("from_user")
        para = request.data.get("to_user")
        if not de:
            return Response({"from_user": "Informe quem sai."}, status=status.HTTP_400_BAD_REQUEST)

        origens = list(
            self.get_queryset()
            .filter(source_issue__assignees__id=de)
            .values_list("source_issue_id", flat=True)
            .distinct()
        )
        if not origens:
            return Response({"transferred": 0}, status=status.HTTP_200_OK)

        with transaction.atomic():
            IssueAssignee.objects.filter(issue_id__in=origens, assignee_id=de).delete()
            if para:
                # `ignore_conflicts` porque a pessoa de destino pode já ser
                # responsável em parte das origens.
                IssueAssignee.objects.bulk_create(
                    [
                        IssueAssignee(
                            issue_id=origem,
                            assignee_id=para,
                            project_id=project_id,
                            workspace_id=self.workspace_id_from_slug(slug),
                        )
                        for origem in origens
                    ],
                    batch_size=100,
                    ignore_conflicts=True,
                )

        return Response({"transferred": len(origens)}, status=status.HTTP_200_OK)

    @allow_permission(allowed_roles=[ROLE.ADMIN], level="PROJECT")
    def preview(self, request, slug, project_id):
        """As próximas datas de uma agenda que ainda não foi salva.

        É o que torna uma regra complexa confiável: em vez de decifrar
        "mensal, última sexta", a pessoa lê 28/08, 25/09, 30/10.

        `partial=True` porque a pré-visualização é da AGENDA: a origem não
        entra no cálculo, e exigi-la aqui rejeitaria a edição de uma regra
        existente ("esta tarefa já tem recorrência").
        """
        dados = {campo: valor for campo, valor in request.data.items() if campo != "source_issue"}
        serializer = RecurringWorkItemSerializer(data=dados, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        for obrigatorio in ("frequency", "time_of_day", "start_date"):
            if serializer.validated_data.get(obrigatorio) is None:
                return Response(
                    {obrigatorio: "Sem este campo não há agenda para calcular."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        rascunho = RecurringWorkItem(**serializer.validated_data)
        rascunho.project_id = project_id
        datas = proximas_datas(rascunho, timezone.now(), quantidade=5)
        return Response({"next_occurrences": [data.isoformat() for data in datas]}, status=status.HTTP_200_OK)

    def workspace_id_from_slug(self, slug):
        from plane.db.models import Workspace

        return Workspace.objects.values_list("id", flat=True).get(slug=slug)
