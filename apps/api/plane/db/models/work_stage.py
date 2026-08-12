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
DEFAULT_WORK_STAGES = [
    {
        "name": "Recém-atribuídas",
        "color": "#3F76FF",
        "sort_order": 15000,
        "group": StateGroup.UNSTARTED.value,
        "is_default": True,
    },
    {
        "name": "Hoje",
        "color": "#F59E0B",
        "sort_order": 25000,
        "group": StateGroup.STARTED.value,
        "is_default": False,
    },
    {
        "name": "Em breve",
        "color": "#60646C",
        "sort_order": 35000,
        "group": StateGroup.UNSTARTED.value,
        "is_default": False,
    },
    {
        "name": "Depois",
        "color": "#91959E",
        "sort_order": 45000,
        "group": StateGroup.BACKLOG.value,
        "is_default": False,
    },
    {
        "name": "Concluídas",
        "color": "#46A758",
        "sort_order": 55000,
        "group": StateGroup.COMPLETED.value,
        "is_default": False,
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
