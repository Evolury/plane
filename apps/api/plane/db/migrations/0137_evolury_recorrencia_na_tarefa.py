# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Evolury: a recorrência passa a morar na tarefa (ADR 0010, revisão de
# 13/08/2026). O molde embutido na regra vira uma tarefa de verdade, que passa
# a ser a origem. Havia regra em produção quando isto foi escrito — a conversão
# abaixo é migração de dados, não só de esquema.

import uuid

import django.db.models.deletion
from django.db import migrations, models
from django.db.models import Max, Q
from django.utils import timezone
from django.utils.html import strip_tags


def _molde_vira_tarefa(apps, schema_editor):
    """Cada regra viva ganha uma tarefa de origem criada a partir do molde.

    Regras já excluídas logicamente são removidas de vez: não faz sentido criar
    tarefa para molde que ninguém vê, e a coluna nova é obrigatória.
    """
    RecurringWorkItem = apps.get_model("db", "RecurringWorkItem")
    Issue = apps.get_model("db", "Issue")
    IssueSequence = apps.get_model("db", "IssueSequence")
    IssueAssignee = apps.get_model("db", "IssueAssignee")
    IssueLabel = apps.get_model("db", "IssueLabel")
    State = apps.get_model("db", "State")

    RecurringWorkItem._default_manager.filter(deleted_at__isnull=False).delete()

    # Só quem ainda não tem origem: torna a conversão retomável se a migração
    # for interrompida no meio (ela roda fora de transação — ver atomic).
    for regra in RecurringWorkItem._default_manager.filter(source_issue__isnull=True).select_related("project"):
        estado = regra.initial_state
        if estado is None or estado.deleted_at is not None or estado.project_id != regra.project_id:
            estado = State._default_manager.filter(
                ~Q(is_triage=True), project_id=regra.project_id, default=True, deleted_at__isnull=True
            ).first()

        # O modelo histórico não roda o save() customizado: sequência, ordem e
        # texto sem tags entram à mão, do mesmo jeito que o save() faria.
        ultima_sequencia = IssueSequence._default_manager.filter(project_id=regra.project_id).aggregate(
            largest=Max("sequence")
        )["largest"]
        maior_ordem = Issue._default_manager.filter(project_id=regra.project_id, state=estado).aggregate(
            largest=Max("sort_order")
        )["largest"]
        descricao = regra.template_description_html or "<p></p>"

        tarefa = Issue._default_manager.create(
            id=uuid.uuid4(),
            project_id=regra.project_id,
            workspace_id=regra.workspace_id,
            name=regra.name,
            description_html=descricao,
            description_stripped=strip_tags(descricao),
            priority=regra.template_priority or "none",
            state=estado,
            type=regra.template_type,
            estimate_point=regra.template_estimate_point,
            sequence_id=(ultima_sequencia or 0) + 1,
            sort_order=(maior_ordem + 10000) if maior_ordem is not None else 65535,
            created_by_id=regra.created_by_id,
            updated_by_id=regra.created_by_id,
            created_at=timezone.now(),
            updated_at=timezone.now(),
        )
        IssueSequence._default_manager.create(
            id=uuid.uuid4(),
            issue=tarefa,
            sequence=tarefa.sequence_id,
            project_id=regra.project_id,
            workspace_id=regra.workspace_id,
            created_at=timezone.now(),
            updated_at=timezone.now(),
        )
        IssueAssignee._default_manager.bulk_create(
            [
                IssueAssignee(
                    id=uuid.uuid4(),
                    issue=tarefa,
                    assignee=responsavel,
                    project_id=regra.project_id,
                    workspace_id=regra.workspace_id,
                    created_at=timezone.now(),
                    updated_at=timezone.now(),
                )
                for responsavel in regra.template_assignees.all()
            ]
        )
        IssueLabel._default_manager.bulk_create(
            [
                IssueLabel(
                    id=uuid.uuid4(),
                    issue=tarefa,
                    label=etiqueta,
                    project_id=regra.project_id,
                    workspace_id=regra.workspace_id,
                    created_at=timezone.now(),
                    updated_at=timezone.now(),
                )
                for etiqueta in regra.template_labels.all()
            ]
        )

        regra.source_issue = tarefa
        regra.save(update_fields=["source_issue"])


class Migration(migrations.Migration):
    # Fora de transação: a conversão insere tarefas (gatilhos de FK adiados) e
    # o aperto do NOT NULL vem logo depois — juntos na mesma transação, o
    # Postgres recusa com "pending trigger events". Cada operação comita a sua,
    # e a conversão acima é retomável por construção.
    atomic = False

    dependencies = [
        ("db", "0136_evolury_recurring_last_day"),
    ]

    operations = [
        # O estado do molde já era, na prática, a etapa onde a ocorrência
        # nasce — o nome novo diz isso.
        migrations.RenameField(
            model_name="recurringworkitem",
            old_name="template_state",
            new_name="initial_state",
        ),
        migrations.AddField(
            model_name="recurringworkitem",
            name="source_issue",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="recurrence_rules",
                to="db.issue",
            ),
        ),
        migrations.AddField(
            model_name="recurringworkitem",
            name="lead_time_days",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.RunPython(_molde_vira_tarefa, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="recurringworkitem",
            name="source_issue",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="recurrence_rules",
                to="db.issue",
            ),
        ),
        migrations.RemoveField(model_name="recurringworkitem", name="name"),
        migrations.RemoveField(model_name="recurringworkitem", name="template_description_html"),
        migrations.RemoveField(model_name="recurringworkitem", name="template_priority"),
        migrations.RemoveField(model_name="recurringworkitem", name="template_assignees"),
        migrations.RemoveField(model_name="recurringworkitem", name="template_labels"),
        migrations.RemoveField(model_name="recurringworkitem", name="template_estimate_point"),
        migrations.RemoveField(model_name="recurringworkitem", name="template_type"),
        migrations.AddConstraint(
            model_name="recurringworkitem",
            constraint=models.UniqueConstraint(
                condition=models.Q(("deleted_at__isnull", True)),
                fields=("source_issue",),
                name="recurring_work_item_unique_source_when_deleted_at_null",
            ),
        ),
    ]
