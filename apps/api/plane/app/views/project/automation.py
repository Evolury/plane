# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Evolury: endpoints das automações personalizadas (ADR 0012, F1).
#
# Porta de admin, inteira — ler inclusive. Uma regra descreve o processo do
# time e às vezes contém decisão de gestão ("quando marcar como bloqueado,
# avisar a diretoria"); e o registro de execuções mostra quem mexeu em quê.
# É a mesma porta das automações fixas ao lado das quais ela mora.

# Third party imports
from rest_framework import status
from rest_framework.response import Response

# Module imports
from plane.app.permissions import ROLE, allow_permission
from plane.app.serializers.automation import AutomationRunSerializer, AutomationSerializer
from plane.app.views.base import BaseViewSet
from plane.db.models import Automation, Workspace
from plane.utils.automacoes.agenda import reagendar
from plane.utils.automacoes.condicao import CondicaoInvalida, tarefas_que_casam

#: Teto da leitura do log. O registro é grande por natureza — uma regra ativa
#: escreve uma linha por evento — e a tela mostra as últimas, não todas.
PAGINA_DO_LOG = 50


class AutomationViewSet(BaseViewSet):
    serializer_class = AutomationSerializer
    model = Automation

    def get_queryset(self):
        return Automation.objects.filter(
            workspace__slug=self.kwargs.get("slug"), project_id=self.kwargs.get("project_id")
        ).select_related("project")

    def get_serializer_context(self):
        contexto = super().get_serializer_context()
        contexto["project_id"] = self.kwargs.get("project_id")
        return contexto

    @allow_permission(allowed_roles=[ROLE.ADMIN], level="PROJECT")
    def list(self, request, slug, project_id):
        regras = self.get_queryset()
        return Response(AutomationSerializer(regras, many=True).data, status=status.HTTP_200_OK)

    @allow_permission(allowed_roles=[ROLE.ADMIN], level="PROJECT")
    def create(self, request, slug, project_id):
        serializer = AutomationSerializer(data=request.data, context={"project_id": project_id})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        regra = serializer.save(
            project_id=project_id,
            workspace_id=Workspace.objects.values_list("id", flat=True).get(slug=slug),
        )
        # Sem isto a regra agendada nasce sem relógio, e o job — que varre por
        # `next_run_at` — nunca a enxerga. Mesma armadilha das recorrentes.
        reagendar(regra)
        return Response(AutomationSerializer(regra).data, status=status.HTTP_201_CREATED)

    @allow_permission(allowed_roles=[ROLE.ADMIN], level="PROJECT")
    def partial_update(self, request, slug, project_id, pk):
        regra = self.get_queryset().filter(pk=pk).first()
        if regra is None:
            return Response({"error": "Automação não encontrada."}, status=status.HTTP_404_NOT_FOUND)
        serializer = AutomationSerializer(
            regra, data=request.data, partial=True, context={"project_id": project_id}
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        regra = serializer.save()
        # A agenda pode ter mudado — ou a regra pode ter deixado de ser
        # agendada, e aí o relógio antigo precisa sumir para o job não a pegar.
        if {"trigger_type", "trigger_config"} & set(request.data):
            reagendar(regra)
        return Response(AutomationSerializer(regra).data, status=status.HTTP_200_OK)

    @allow_permission(allowed_roles=[ROLE.ADMIN], level="PROJECT")
    def destroy(self, request, slug, project_id, pk):
        regra = self.get_queryset().filter(pk=pk).first()
        if regra is None:
            return Response({"error": "Automação não encontrada."}, status=status.HTTP_404_NOT_FOUND)
        regra.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @allow_permission(allowed_roles=[ROLE.ADMIN], level="PROJECT")
    def runs(self, request, slug, project_id, pk):
        """O registro de execuções da regra — a resposta a "por que não rodou?"."""
        regra = self.get_queryset().filter(pk=pk).first()
        if regra is None:
            return Response({"error": "Automação não encontrada."}, status=status.HTTP_404_NOT_FOUND)
        execucoes = regra.runs.select_related("issue").order_by("-created_at")[:PAGINA_DO_LOG]
        return Response(AutomationRunSerializer(execucoes, many=True).data, status=status.HTTP_200_OK)

    @allow_permission(allowed_roles=[ROLE.ADMIN], level="PROJECT")
    def simular(self, request, slug, project_id):
        """Quantas tarefas do projeto casam com esta condição AGORA.

        Não executa nada e não grava nada: é a resposta honesta a "essa regra
        vai pegar o quê?", feita antes de ligar a regra. Sem isso, a única
        forma de descobrir o alcance de uma condição é ligá-la e olhar o
        estrago.
        """
        try:
            casam = tarefas_que_casam(project_id, request.data.get("condition"))
        except CondicaoInvalida as erro:
            return Response({"condition": str(erro)}, status=status.HTTP_400_BAD_REQUEST)

        amostra = casam.values("id", "name", "sequence_id")[:5]
        return Response(
            {
                "total": casam.count(),
                "amostra": [
                    {"id": str(item["id"]), "name": item["name"], "sequence_id": item["sequence_id"]}
                    for item in amostra
                ],
            },
            status=status.HTTP_200_OK,
        )
