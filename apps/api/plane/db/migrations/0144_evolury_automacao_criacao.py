# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Evolury: criação de tarefa por automação (ADR 0012, F3).
#
# Duas mudanças, e as duas separam automação de recorrência:
#
# `include_recurring` desliga, por padrão, o disparo de regra de "tarefa criada"
# quando quem criou foi a recorrência — a mesma separação que Notion e ClickUp
# fazem explicitamente. Fica desligado porque a tarefa de origem de uma
# recorrência já é um molde preenchido, e uma regra de nascimento brigaria com
# ele a cada ocorrência.
#
# `AutomationCreation` é a idempotência da criação. O defeito número um desse
# recurso, nos produtos que o têm, não é laço infinito — é duplicata: checklist
# criado em dobro quando a regra dispara duas vezes. A garantia mora no banco,
# como já mora na recorrência.

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("db", "0143_evolury_automacoes")]

    operations = [
        migrations.AddField(
            model_name="automation",
            name="include_recurring",
            field=models.BooleanField(default=False),
        ),
        migrations.CreateModel(
            name="AutomationCreation",
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
                ("chave", models.CharField(blank=True, default="", max_length=255)),
                (
                    "automation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name="creations", to="db.automation"
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
                        related_name="automation_creations",
                        to="db.issue",
                    ),
                ),
                (
                    "source_issue",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="automation_creations_as_source",
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
                        related_name="automation_creations",
                        to="db.workspace",
                    ),
                ),
            ],
            options={
                "verbose_name": "Automation Creation",
                "verbose_name_plural": "Automation Creations",
                "db_table": "automation_creations",
                "ordering": ("-created_at",),
            },
        ),
        migrations.AddConstraint(
            model_name="automationcreation",
            constraint=models.UniqueConstraint(
                condition=models.Q(("deleted_at__isnull", True)),
                fields=("automation", "source_issue", "chave"),
                name="automation_creation_unique_when_deleted_at_null",
            ),
        ),
    ]
