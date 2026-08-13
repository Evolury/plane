# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Evolury: serializer das tarefas recorrentes (ADR 0010).
#
# A validação por frequência mora aqui porque é a fronteira: uma regra semanal
# sem dias escolhidos ou uma mensal sem modo geram datas silenciosamente
# erradas, e "silenciosamente" é o problema.

# Third party imports
from rest_framework import serializers

# Module imports
from plane.db.models import RecurrenceEndMode, RecurrenceFrequency, RecurringWorkItem
from plane.db.models.recurring_work_item import GenerationMode, MonthlyMode

from .base import BaseSerializer


class RecurringWorkItemSerializer(BaseSerializer):
    next_occurrences = serializers.SerializerMethodField()

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

        return data
