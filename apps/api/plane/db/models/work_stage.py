# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Evolury: etapas pessoais de "Minhas tarefas".
#
# Organização por usuário e workspace, em cima dos grupos globais de estado —
# um overlay que nunca toca o estado real do work item. Especificação e
# decisões em docs/evolury/funcionalidades/minhas-tarefas/ (ADRs 0001 e 0002).

# Django imports
from django.conf import settings
from django.db import models
from django.db.models import Q

# Module imports
from .base import BaseModel
from .state import StateGroup

# Triage é interno do intake; etapa pessoal usa só os cinco grupos visíveis.
WORK_STAGE_GROUP_CHOICES = [(choice.value, choice.label) for choice in StateGroup if choice != StateGroup.TRIAGE]

# Seed criado no primeiro acesso do usuário ao workspace. Ponto de partida
# editável, não imposição — ver especificacao.md ("Seed inicial").
#
# As marcações vêm junto (ADR 0014): conta nova já nasce com a varredura diária
# funcionando, sem ninguém precisar configurar nada. `is_default` continua sendo
# a única obrigatória; as quatro de vencimento são opcionais e estão aqui porque
# este é o arranjo que o produto recomenda, não porque o modelo as exija.
DEFAULT_WORK_STAGES = [
    {
        "name": "Recentes",
        "color": "#3F76FF",
        "sort_order": 15000,
        "group": StateGroup.UNSTARTED.value,
        "is_default": True,
        # Recentes é onde se toma conhecimento do que chegou. Esvaziá-la toda
        # madrugada a impediria de cumprir esse papel — ver ADR 0014.
        "automation_disabled": True,
    },
    {
        "name": "Em Andamento",
        "color": "#F59E0B",
        "sort_order": 25000,
        "group": StateGroup.STARTED.value,
    },
    {
        "name": "Para Hoje (fila)",
        "color": "#F59E0B",
        "sort_order": 35000,
        "group": StateGroup.STARTED.value,
        "is_due_today": True,
    },
    {
        "name": "Pendências",
        "color": "#DC2626",
        "sort_order": 45000,
        "group": StateGroup.BACKLOG.value,
        "is_overdue": True,
        # A pessoa põe aqui, à mão, coisa que quer manter à vista mesmo com
        # vencimento futuro. Travada de saída; continua recebendo as vencidas.
        "automation_disabled": True,
    },
    {
        "name": "Para amanhã",
        "color": "#60646C",
        "sort_order": 55000,
        "group": StateGroup.BACKLOG.value,
        "is_due_tomorrow": True,
    },
    {
        "name": "Para Depois",
        "color": "#91959E",
        "sort_order": 65000,
        "group": StateGroup.BACKLOG.value,
        "is_due_later": True,
    },
    {
        "name": "Concluídas",
        "color": "#46A758",
        "sort_order": 75000,
        "group": StateGroup.COMPLETED.value,
        "is_completion": True,
    },
    {
        "name": "Cancelado",
        "color": "#DC2626",
        "sort_order": 85000,
        "group": StateGroup.CANCELLED.value,
    },
]


class WorkStage(BaseModel):
    workspace = models.ForeignKey("db.Workspace", on_delete=models.CASCADE, related_name="work_stages")
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="work_stages")
    name = models.CharField(max_length=255)
    color = models.CharField(max_length=255)
    group = models.CharField(max_length=20, choices=WORK_STAGE_GROUP_CHOICES, default=StateGroup.BACKLOG.value)
    sort_order = models.FloatField(default=65535)
    # A etapa padrão é a "primeira etapa": todo item atribuído sem associação
    # pertence a ela implicitamente. Exatamente uma por usuário/workspace.
    is_default = models.BooleanField(default=False)
    # Destino da tarefa concluída, entre as etapas do grupo concluído — a
    # mesma pergunta que `Project.completion_state` responde do lado do
    # projeto. Sem marcação, vale a primeira do grupo por `sort_order`.
    is_completion = models.BooleanField(default=False)

    # Evolury: para onde a varredura diária manda cada balde de vencimento
    # (ADR 0014). Mesmo molde de `is_default`/`is_completion`, com UMA
    # diferença que importa: a etapa padrão é obrigatória — item sem associação
    # precisa pertencer a algum lugar —, e estas quatro são OPCIONAIS. Balde
    # sem etapa marcada simplesmente não move ninguém, e quem não quiser a
    # separação por amanhã não marca.
    #
    # A constraint que sustenta as duas coisas é a mesma: ela impede DUAS
    # etapas para o mesmo papel, e não exige uma. Uma etapa pode acumular
    # vários papéis — "Futuro" sendo amanhã e depois é escolha legítima.
    is_due_today = models.BooleanField(default=False)
    is_due_tomorrow = models.BooleanField(default=False)
    is_due_later = models.BooleanField(default=False)
    is_overdue = models.BooleanField(default=False)

    # Evolury: a varredura não TIRA tarefa desta etapa (ADR 0014).
    #
    # De SAÍDA, nunca de chegada — e isto é o que se implementa ao contrário com
    # facilidade. A etapa de vencidas é o exemplo que prova: ela é destino das
    # vencidas E a que mais se quer travar, porque a pessoa põe ali, à mão,
    # coisa que não quer ver saindo sozinha. Se bloqueasse a chegada, nunca
    # receberia nada e ninguém entenderia por quê.
    #
    # Sem constraint: quantas etapas a pessoa quiser.
    automation_disabled = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "owner", "name"],
                condition=Q(deleted_at__isnull=True),
                name="work_stage_unique_name_per_owner_when_deleted_at_null",
            ),
            models.UniqueConstraint(
                fields=["workspace", "owner"],
                condition=Q(is_default=True, deleted_at__isnull=True),
                name="work_stage_single_default_per_owner_when_deleted_at_null",
            ),
            models.UniqueConstraint(
                fields=["workspace", "owner"],
                condition=Q(is_completion=True, deleted_at__isnull=True),
                name="work_stage_single_completion_per_owner_when_deleted_at_null",
            ),
            # Evolury: no máximo uma etapa por balde de vencimento (ADR 0014).
            # "No máximo", e não "exatamente": é a mesma constraint do padrão, e
            # é ela que deixa a marcação ser opcional.
            models.UniqueConstraint(
                fields=["workspace", "owner"],
                condition=Q(is_due_today=True, deleted_at__isnull=True),
                name="work_stage_single_due_today_per_owner_when_deleted_at_null",
            ),
            models.UniqueConstraint(
                fields=["workspace", "owner"],
                condition=Q(is_due_tomorrow=True, deleted_at__isnull=True),
                name="work_stage_single_due_tomorrow_per_owner_when_deleted_at_null",
            ),
            models.UniqueConstraint(
                fields=["workspace", "owner"],
                condition=Q(is_due_later=True, deleted_at__isnull=True),
                name="work_stage_single_due_later_per_owner_when_deleted_at_null",
            ),
            models.UniqueConstraint(
                fields=["workspace", "owner"],
                condition=Q(is_overdue=True, deleted_at__isnull=True),
                name="work_stage_single_overdue_per_owner_when_deleted_at_null",
            ),
        ]
        verbose_name = "Work Stage"
        verbose_name_plural = "Work Stages"
        db_table = "work_stages"
        ordering = ("sort_order",)

    def save(self, *args, **kwargs):
        if self._state.adding:
            # Etapa nova entra no fim da lista do usuário — mesmo passo de
            # sequência dos estados de projeto (State.save). O seed usa
            # bulk_create, que não passa por aqui, e preserva as ordens
            # explícitas; reordenação posterior é update, também fora deste
            # ramo.
            last_sort_order = WorkStage.objects.filter(workspace=self.workspace, owner=self.owner).aggregate(
                largest=models.Max("sort_order")
            )["largest"]
            if last_sort_order is not None:
                self.sort_order = last_sort_order + 15000

        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} <{self.owner.email}>"


class WorkStageIssue(BaseModel):
    """Associação item ↔ etapa pessoal.

    Só existe depois do primeiro movimento: item atribuído sem linha aqui
    pertence implicitamente à etapa padrão. A linha sobrevive à desatribuição
    de propósito — se o item voltar a ser atribuído, reaparece na etapa em que
    estava (especificacao.md).
    """

    workspace = models.ForeignKey("db.Workspace", on_delete=models.CASCADE, related_name="work_stage_issues")
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="work_stage_issues")
    stage = models.ForeignKey(WorkStage, on_delete=models.CASCADE, related_name="stage_issues")
    issue = models.ForeignKey("db.Issue", on_delete=models.CASCADE, related_name="work_stage_issues")
    sort_order = models.FloatField(default=65535)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "issue"],
                condition=Q(deleted_at__isnull=True),
                name="work_stage_issue_unique_owner_issue_when_deleted_at_null",
            )
        ]
        verbose_name = "Work Stage Issue"
        verbose_name_plural = "Work Stage Issues"
        db_table = "work_stage_issues"
        ordering = ("sort_order",)

    def __str__(self):
        return f"{self.issue_id} → {self.stage_id}"


class WorkStageSweep(BaseModel):
    """Quando a varredura diária passou por esta pessoa, neste workspace.

    Evolury: ADR 0014.

    **Não existe para evitar repetição.** A varredura é idempotente — ela
    recalcula onde cada tarefa deveria estar, então rodar duas vezes no mesmo
    dia não muda nada. Existe para ela **se recuperar sozinha**: worker fora do
    ar às 00h05 não pode custar o dia inteiro de organização de alguém. Guardando
    o último dia varrido, a execução seguinte percebe o atraso e cobre.

    A data é a LOCAL da pessoa, e não a do servidor: meia-noite não é um
    instante, é um instante por fuso.
    """

    workspace = models.ForeignKey("db.Workspace", on_delete=models.CASCADE, related_name="work_stage_sweeps")
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="work_stage_sweeps")
    ran_on = models.DateField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "owner"],
                condition=Q(deleted_at__isnull=True),
                name="work_stage_sweep_unique_per_owner_when_deleted_at_null",
            )
        ]
        verbose_name = "Work Stage Sweep"
        verbose_name_plural = "Work Stage Sweeps"
        db_table = "work_stage_sweeps"
        ordering = ("-ran_on",)

    def __str__(self):
        return f"{self.owner.email} @ {self.ran_on}"
