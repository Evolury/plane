# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Evolury: tarefas recorrentes (ADR 0010).
#
# Uma regra é um par AGENDA + MOLDE: quando gerar, e o que gerar. A agenda vive
# em campos legíveis — frequência, intervalo, dias, horário — e vira `rrule` só
# na hora de calcular; guardar RRULE cru economizaria código e custaria a tela.
#
# Especificação e decisões em docs/evolury/funcionalidades/tarefa-recorrente/.

# Django imports
from django.conf import settings
from django.db import models
from django.db.models import Q

# Module imports
from .base import BaseModel
from .project import ProjectBaseModel


class RecurrenceFrequency(models.TextChoices):
    DAILY = "daily", "Diária"
    WEEKLY = "weekly", "Semanal"
    MONTHLY = "monthly", "Mensal"
    YEARLY = "yearly", "Anual"


class MonthlyMode(models.TextChoices):
    """Como o mês escolhe o dia."""

    DAY_OF_MONTH = "day_of_month", "Dia do mês"
    # Existe como opção própria, e não como "dia 31", porque ninguém pensa
    # "dia 31" quando quer dizer "fecha o mês" — e o Asana, que é a referência
    # aqui, também tem a opção separada.
    LAST_DAY = "last_day", "Último dia do mês"
    WEEKDAY_OF_MONTH = "weekday_of_month", "Dia da semana do mês"


class GenerationMode(models.TextChoices):
    SCHEDULE = "schedule", "Por agenda"
    AFTER_COMPLETION = "after_completion", "Após a conclusão"


class RecurrenceEndMode(models.TextChoices):
    NEVER = "never", "Nunca"
    ON_DATE = "on_date", "Em uma data"
    AFTER_COUNT = "after_count", "Após N ocorrências"


class RecurringWorkItem(ProjectBaseModel):
    """Regra de recorrência de um projeto."""

    # --- identificação ---
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    # --- agenda ---
    frequency = models.CharField(max_length=20, choices=RecurrenceFrequency.choices)
    # "a cada N" — 1 = todo dia/semana/mês/ano
    interval = models.PositiveIntegerField(default=1)
    # Semanal: dias escolhidos, 0=domingo (como Date.getDay e como o produto,
    # cuja semana começa no domingo — ADR 0005).
    weekdays = models.JSONField(default=list, blank=True)
    # Mensal e anual: dia do mês. 31 em fevereiro vira o último dia do mês —
    # a RFC 5545 mandaria PULAR, o que some com a tarefa por cinco meses no ano
    # sem ninguém relacionar à causa (ADR 0010).
    monthly_mode = models.CharField(max_length=20, choices=MonthlyMode.choices, null=True, blank=True)
    day_of_month = models.PositiveSmallIntegerField(null=True, blank=True)
    # Mensal por dia da semana: 1ª a 4ª, ou -1 para a última.
    week_of_month = models.SmallIntegerField(null=True, blank=True)
    weekday_of_month = models.PositiveSmallIntegerField(null=True, blank=True)
    # Anual: mês (1-12).
    month_of_year = models.PositiveSmallIntegerField(null=True, blank=True)
    # Horário local da geração (fuso do produto — ADR 0006).
    time_of_day = models.TimeField()
    start_date = models.DateField()

    # --- fim da recorrência ---
    end_mode = models.CharField(max_length=20, choices=RecurrenceEndMode.choices, default=RecurrenceEndMode.NEVER)
    end_date = models.DateField(null=True, blank=True)
    end_after_count = models.PositiveIntegerField(null=True, blank=True)

    # --- geração ---
    generation_mode = models.CharField(
        max_length=20, choices=GenerationMode.choices, default=GenerationMode.SCHEDULE
    )
    # "Após a conclusão": quantos dias depois de concluída a anterior.
    days_after_completion = models.PositiveIntegerField(null=True, blank=True)
    # Resposta ao problema número um de recorrência em ferramenta de trabalho:
    # o quadro entupido de cópias da mesma coisa.
    skip_while_previous_open = models.BooleanField(default=True)
    # Desnormalizado para o job não varrer todas as regras a cada rodada.
    next_run_at = models.DateTimeField(null=True, blank=True, db_index=True)
    occurrences_created = models.PositiveIntegerField(default=0)

    # --- molde ---
    template_description_html = models.TextField(blank=True, default="<p></p>")
    template_priority = models.CharField(max_length=30, default="none")
    template_state = models.ForeignKey(
        "db.State", on_delete=models.SET_NULL, null=True, blank=True, related_name="recurring_work_items"
    )
    template_assignees = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="recurring_work_items_assigned"
    )
    template_labels = models.ManyToManyField("db.Label", blank=True, related_name="recurring_work_items")
    template_estimate_point = models.ForeignKey(
        "db.EstimatePoint", on_delete=models.SET_NULL, null=True, blank=True, related_name="recurring_work_items"
    )
    template_type = models.ForeignKey(
        "db.IssueType", on_delete=models.SET_NULL, null=True, blank=True, related_name="recurring_work_items"
    )

    class Meta:
        verbose_name = "Recurring Work Item"
        verbose_name_plural = "Recurring Work Items"
        db_table = "recurring_work_items"
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.name} <{self.project.name}>"


class RecurringWorkItemOccurrence(BaseModel):
    """Registro de que uma data prevista já virou tarefa.

    É o que garante idempotência — rodar o job duas vezes não cria duas tarefas
    para a mesma data — e o que vai permitir, depois, pular uma ocorrência sem
    mexer na série.
    """

    recurring_work_item = models.ForeignKey(
        RecurringWorkItem, on_delete=models.CASCADE, related_name="occurrences"
    )
    workspace = models.ForeignKey("db.Workspace", on_delete=models.CASCADE, related_name="recurring_occurrences")
    # A data/hora que a agenda previu, não a que o job rodou.
    scheduled_for = models.DateTimeField()
    issue = models.ForeignKey(
        "db.Issue", on_delete=models.SET_NULL, null=True, blank=True, related_name="recurring_occurrences"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["recurring_work_item", "scheduled_for"],
                condition=Q(deleted_at__isnull=True),
                name="recurring_occurrence_unique_schedule_when_deleted_at_null",
            )
        ]
        verbose_name = "Recurring Work Item Occurrence"
        verbose_name_plural = "Recurring Work Item Occurrences"
        db_table = "recurring_work_item_occurrences"
        ordering = ("-scheduled_for",)

    def __str__(self):
        return f"{self.recurring_work_item_id} @ {self.scheduled_for}"
