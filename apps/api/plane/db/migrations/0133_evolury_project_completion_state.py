# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Evolury: destino do botão de concluir tarefa (ADR 0009). Nulo significa
# "resolver automaticamente" — nenhum projeto precisa ser configurado para o
# botão funcionar, então a migração não preenche nada.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0132_evolury_basic_themes_only"),
    ]

    operations = [
        migrations.AddField(
            model_name="project",
            name="completion_state",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="completion_state",
                to="db.state",
            ),
        ),
    ]
