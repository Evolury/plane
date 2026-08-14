# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Evolury: serializer das tarefas recorrentes (ADR 0010, revisão 13/08/2026).
#
# A validação por frequência mora aqui porque é a fronteira: uma regra semanal
# sem dias escolhidos ou uma mensal sem modo geram datas silenciosamente
# erradas, e "silenciosamente" é o problema. As travas da origem também: são
# elas que impedem a série de virar árvore.

# Third party imports
from rest_framework import serializers

# Module imports
from plane.db.models import (
    RecurrenceEndMode,
    RecurrenceFrequency,
    RecurringWorkItem,
    RecurringWorkItemOccurrence,
)
from plane.db.models.recurring_work_item import GenerationMode, MonthlyMode

from .base import BaseSerializer


class RecurringWorkItemSerializer(BaseSerializer):
    next_occurrences = serializers.SerializerMethodField()
    source_issue_detail = serializers.SerializerMethodField()
    inactive_assignees = serializers.SerializerMethodField()

    class Meta:
        model = RecurringWorkItem
        fields = "__all__"
        read_only_fields = [
            "workspace",
            "project",
            "next_run_at",
            "occurrences_created",
            "created_by",
            "updated_by",
            "deleted_at",
        ]

    def get_next_occurrences(self, obj):
        """As próximas datas previstas — o que torna a regra confiável na tela."""
        from django.utils import timezone

        from plane.utils.recurrence import proximas_datas

        return [data.isoformat() for data in proximas_datas(obj, timezone.now(), quantidade=3)]

    def get_source_issue_detail(self, obj):
        """O resumo da origem, para a lista não precisar de outra chamada."""
        origem = obj.source_issue
        if origem is None:
            return None
        return {
            "id": str(origem.id),
            "name": origem.name,
            "sequence_id": origem.sequence_id,
            "archived_at": origem.archived_at,
            "state_group": origem.state.group if origem.state else None,
        }

    def get_inactive_assignees(self, obj):
        """Responsáveis da origem que não são mais membros do projeto.

        A geração já os descarta; isto é o que torna o descarte visível para
        alguém consertar a raiz — corrigir em silêncio seria a outra armadilha.
        """
        from plane.db.models import IssueAssignee, ProjectMember

        ativos = set(
            ProjectMember.objects.filter(project_id=obj.project_id, is_active=True).values_list(
                "member_id", flat=True
            )
        )
        vinculos = IssueAssignee.objects.filter(issue_id=obj.source_issue_id).select_related("assignee")
        return [
            {
                "id": str(vinculo.assignee_id),
                "display_name": vinculo.assignee.display_name,
                "avatar_url": vinculo.assignee.avatar_url,
            }
            for vinculo in vinculos
            if vinculo.assignee_id not in ativos
        ]

    def validate_source_issue(self, origem):
        # A origem é escolhida no nascimento e não muda: trocar de tarefa é
        # excluir a regra e ligar outra.
        if self.instance is not None and origem.id != self.instance.source_issue_id:
            raise serializers.ValidationError("A tarefa de origem não pode ser trocada.")
        if self.instance is not None:
            return origem

        if origem.parent_id is not None:
            raise serializers.ValidationError("Subtarefa não pode ter recorrência própria.")
        if origem.archived_at is not None:
            raise serializers.ValidationError("Desarquive a tarefa antes de ativar a recorrência.")
        if origem.is_draft:
            raise serializers.ValidationError("Rascunho não pode ter recorrência.")
        # A trava que impede a série de virar árvore — e que dá o rastro:
        # tarefa gerada por recorrência não ativa recorrência própria.
        if RecurringWorkItemOccurrence.objects.filter(issue_id=origem.id).exists():
            raise serializers.ValidationError("Tarefa gerada por recorrência não pode ter recorrência própria.")
        if RecurringWorkItem.objects.filter(source_issue_id=origem.id).exists():
            raise serializers.ValidationError("Esta tarefa já tem uma recorrência.")
        return origem

    def validate(self, data):
        # Em PATCH parcial, o que não veio continua valendo.
        def campo(nome):
            if nome in data:
                return data[nome]
            return getattr(self.instance, nome, None)

        if (campo("interval") or 1) < 1:
            raise serializers.ValidationError({"interval": "O intervalo precisa ser pelo menos 1."})

        frequencia = campo("frequency")

        if frequencia == RecurrenceFrequency.WEEKLY:
            dias = campo("weekdays") or []
            if not dias:
                raise serializers.ValidationError({"weekdays": "Escolha pelo menos um dia da semana."})
            if any(dia not in range(7) for dia in dias):
                raise serializers.ValidationError({"weekdays": "Dia da semana inválido."})

        if frequencia == RecurrenceFrequency.MONTHLY:
            modo = campo("monthly_mode")
            if modo == MonthlyMode.WEEKDAY_OF_MONTH:
                if campo("week_of_month") is None or campo("weekday_of_month") is None:
                    raise serializers.ValidationError(
                        {"week_of_month": "Escolha a semana e o dia da semana do mês."}
                    )
            elif modo == MonthlyMode.LAST_DAY:
                pass  # não precisa de dia: é sempre o fim do mês
            elif not campo("day_of_month"):
                raise serializers.ValidationError({"day_of_month": "Escolha o dia do mês."})

        if frequencia == RecurrenceFrequency.YEARLY and (
            not campo("day_of_month") or not campo("month_of_year")
        ):
            raise serializers.ValidationError({"month_of_year": "Escolha o dia e o mês."})

        if campo("end_mode") == RecurrenceEndMode.ON_DATE and not campo("end_date"):
            raise serializers.ValidationError({"end_date": "Escolha a data de término."})
        if campo("end_mode") == RecurrenceEndMode.AFTER_COUNT and not campo("end_after_count"):
            raise serializers.ValidationError({"end_after_count": "Escolha quantas ocorrências."})

        if campo("generation_mode") == GenerationMode.AFTER_COMPLETION and not campo("days_after_completion"):
            raise serializers.ValidationError(
                {"days_after_completion": "Escolha quantos dias após a conclusão."}
            )

        # A representação canônica da antecedência: horas até 23, dias dali em
        # diante — "26 horas" e "1 dia e 2 horas" não podem ser duas regras.
        if (campo("lead_time_hours") or 0) > 23:
            raise serializers.ValidationError({"lead_time_hours": "A partir de 24 horas, use dias."})

        estado = campo("initial_state")
        origem = campo("source_issue")
        if estado is not None and origem is not None and estado.project_id != origem.project_id:
            raise serializers.ValidationError({"initial_state": "A etapa inicial precisa ser do mesmo projeto."})

        return data
