# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Evolury: automações personalizadas — quando / se / então (ADR 0012, F1).
#
# Duas tabelas: a regra e o registro de execuções. O registro nasce junto, e
# não depois, porque "por que não rodou?" é a pergunta número um desse tipo de
# recurso — e uma condição que não casa para em silêncio por definição.

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("db", "0142_evolury_icone_da_propriedade")]

    operations = [
        migrations.CreateModel(
            name="Automation",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Created At")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Last Modified At")),
                ("deleted_at", models.DateTimeField(blank=True, null=True, verbose_name="Deleted At")),
                (
                    "id",
                    models.UUIDField(
                        db_index=True,
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True, default="")),
                ("is_active", models.BooleanField(default=True)),
                (
                    "trigger_type",
                    models.CharField(
                        choices=[
                            ("work_item_created", "Tarefa criada"),
                            ("field_changed", "Campo alterado"),
                            ("comment_added", "Comentário adicionado"),
                            ("scheduled", "Em um horário"),
                        ],
                        max_length=32,
                    ),
                ),
                ("trigger_config", models.JSONField(blank=True, default=dict)),
                ("condition", models.JSONField(blank=True, null=True)),
                ("actions", models.JSONField(blank=True, default=list)),
                ("next_run_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("last_run_at", models.DateTimeField(blank=True, null=True)),
                ("run_count", models.PositiveIntegerField(default=0)),
                ("error_count", models.PositiveIntegerField(default=0)),
                ("disabled_reason", models.TextField(blank=True, default="")),
                (
                    "created_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_created_by",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Created By",
                    ),
                ),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="project_%(class)s",
                        to="db.project",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_updated_by",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Last Modified By",
                    ),
                ),
                (
                    "workspace",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="workspace_%(class)s",
                        to="db.workspace",
                    ),
                ),
            ],
            options={
                "verbose_name": "Automation",
                "verbose_name_plural": "Automations",
                "db_table": "automations",
                "ordering": ("-created_at",),
            },
        ),
        migrations.CreateModel(
            name="AutomationRun",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Created At")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Last Modified At")),
                ("deleted_at", models.DateTimeField(blank=True, null=True, verbose_name="Deleted At")),
                (
                    "id",
                    models.UUIDField(
                        db_index=True,
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("matched", "Executada"),
                            ("skipped", "Condição não casou"),
                            ("failed", "Falhou"),
                        ],
                        max_length=16,
                    ),
                ),
                ("trigger_summary", models.JSONField(blank=True, default=dict)),
                ("actions_result", models.JSONField(blank=True, default=list)),
                ("error", models.TextField(blank=True, default="")),
                ("duration_ms", models.PositiveIntegerField(default=0)),
                ("depth", models.PositiveSmallIntegerField(default=0)),
                (
                    "automation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name="runs", to="db.automation"
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_created_by",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Created By",
                    ),
                ),
                (
                    "issue",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="automation_runs",
                        to="db.issue",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(class)s_updated_by",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Last Modified By",
                    ),
                ),
                (
                    "workspace",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="automation_runs",
                        to="db.workspace",
                    ),
                ),
            ],
            options={
                "verbose_name": "Automation Run",
                "verbose_name_plural": "Automation Runs",
                "db_table": "automation_runs",
                "ordering": ("-created_at",),
            },
        ),
        migrations.AddIndex(
            model_name="automation",
            index=models.Index(
                fields=["project", "trigger_type", "is_active"], name="automation_despacho_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="automationrun",
            index=models.Index(fields=["automation", "-created_at"], name="automation_run_historico_idx"),
        ),
    ]
