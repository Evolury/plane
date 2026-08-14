# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Evolury: antecedência em horas, além de dias (ADR 0010, revisão). Dias
# resolvem a véspera; horas resolvem o preparo — a pauta que chega duas horas
# antes da reunião.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0137_evolury_recorrencia_na_tarefa"),
    ]

    operations = [
        migrations.AddField(
            model_name="recurringworkitem",
            name="lead_time_hours",
            field=models.PositiveIntegerField(default=0),
        ),
    ]
