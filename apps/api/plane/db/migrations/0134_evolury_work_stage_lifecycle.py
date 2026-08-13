# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Ciclo completo da tarefa nas etapas pessoais (ADR 0009).

A etapa pessoal passa a acompanhar o ciclo inteiro — concluir, reabrir e
cancelar —, e para isso precisa de duas coisas que não existiam: uma marcação
de qual etapa do grupo concluído é o destino, e uma etapa no grupo cancelado.

Quem já tem etapas semeadas não é deixado para trás: a migração marca a
primeira etapa concluída de cada usuário e cria a de canceladas para quem não
tiver nenhuma.
"""

from django.db import migrations, models
from django.db.models import Q


def marcar_conclusao_e_criar_canceladas(apps, schema_editor):
    WorkStage = apps.get_model("db", "WorkStage")

    # Cada dupla (workspace, owner) tem seu próprio conjunto de etapas.
    donos = WorkStage.objects.filter(deleted_at__isnull=True).values_list("workspace_id", "owner_id").distinct()

    for workspace_id, owner_id in donos:
        etapas = WorkStage.objects.filter(workspace_id=workspace_id, owner_id=owner_id, deleted_at__isnull=True)

        if not etapas.filter(is_completion=True).exists():
            concluida = etapas.filter(group="completed").order_by("sort_order").first()
            if concluida is not None:
                concluida.is_completion = True
                concluida.save(update_fields=["is_completion"])

        if not etapas.filter(group="cancelled").exists():
            maior = etapas.order_by("-sort_order").values_list("sort_order", flat=True).first() or 0
            WorkStage.objects.create(
                workspace_id=workspace_id,
                owner_id=owner_id,
                name="Canceladas",
                color="#DC2626",
                group="cancelled",
                sort_order=maior + 15000,
                is_default=False,
            )


def reverter(apps, schema_editor):
    """A etapa criada não é removida: pode já ter tarefas associadas."""
    WorkStage = apps.get_model("db", "WorkStage")
    WorkStage.objects.filter(is_completion=True).update(is_completion=False)


class Migration(migrations.Migration):
    dependencies = [("db", "0133_evolury_project_completion_state")]

    operations = [
        migrations.AddField(
            model_name="workstage",
            name="is_completion",
            field=models.BooleanField(default=False),
        ),
        migrations.AddConstraint(
            model_name="workstage",
            constraint=models.UniqueConstraint(
                condition=Q(is_completion=True, deleted_at__isnull=True),
                fields=("workspace", "owner"),
                name="work_stage_single_completion_per_owner_when_deleted_at_null",
            ),
        ),
        migrations.RunPython(marcar_conclusao_e_criar_canceladas, reverter),
    ]
