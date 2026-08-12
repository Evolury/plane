# Evolury: cria as tabelas de "Minhas tarefas" — etapas pessoais (WorkStage) e
# a associação item↔etapa (WorkStageIssue). Aditiva: nenhuma tabela herdada é
# tocada. Modelo e regras em docs/evolury/funcionalidades/minhas-tarefas/.
#
# O seed das etapas padrão NÃO acontece aqui: ele é por usuário, no primeiro
# acesso à página (ensure_default_work_stages) — uma migration não conhece os
# usuários futuros.

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0124_evolury_default_timezone_sao_paulo"),
    ]

    operations = [
        migrations.CreateModel(
            name="WorkStage",
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
                ("color", models.CharField(max_length=255)),
                (
                    "group",
                    models.CharField(
                        choices=[
                            ("backlog", "Backlog"),
                            ("unstarted", "Unstarted"),
                            ("started", "Started"),
                            ("completed", "Completed"),
                            ("cancelled", "Cancelled"),
                        ],
                        default="backlog",
                        max_length=20,
                    ),
                ),
                ("sort_order", models.FloatField(default=65535)),
                ("is_default", models.BooleanField(default=False)),
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
                    "owner",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="work_stages",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "workspace",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name="work_stages", to="db.workspace"
                    ),
                ),
            ],
            options={
                "verbose_name": "Work Stage",
                "verbose_name_plural": "Work Stages",
                "db_table": "work_stages",
                "ordering": ("sort_order",),
            },
        ),
        migrations.CreateModel(
            name="WorkStageIssue",
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
                ("sort_order", models.FloatField(default=65535)),
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
                    "issue",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name="work_stage_issues", to="db.issue"
                    ),
                ),
                (
                    "owner",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="work_stage_issues",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "stage",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name="stage_issues", to="db.workstage"
                    ),
                ),
                (
                    "workspace",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name="work_stage_issues", to="db.workspace"
                    ),
                ),
            ],
            options={
                "verbose_name": "Work Stage Issue",
                "verbose_name_plural": "Work Stage Issues",
                "db_table": "work_stage_issues",
                "ordering": ("sort_order",),
            },
        ),
        migrations.AddConstraint(
            model_name="workstage",
            constraint=models.UniqueConstraint(
                condition=models.Q(("deleted_at__isnull", True)),
                fields=("workspace", "owner", "name"),
                name="work_stage_unique_name_per_owner_when_deleted_at_null",
            ),
        ),
        migrations.AddConstraint(
            model_name="workstage",
            constraint=models.UniqueConstraint(
                condition=models.Q(("deleted_at__isnull", True), ("is_default", True)),
                fields=("workspace", "owner"),
                name="work_stage_single_default_per_owner_when_deleted_at_null",
            ),
        ),
        migrations.AddConstraint(
            model_name="workstageissue",
            constraint=models.UniqueConstraint(
                condition=models.Q(("deleted_at__isnull", True)),
                fields=("owner", "issue"),
                name="work_stage_issue_unique_owner_issue_when_deleted_at_null",
            ),
        ),
    ]
