# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Evolury: agrupar por propriedade vira escolha da definição (ADR 0011).
#
# O padrão `True` não é só o padrão do campo novo: é o que o Django grava em
# TODAS as linhas existentes ao adicionar a coluna. É de propósito — antes
# desta migração toda propriedade de seleção única já aparecia em "agrupar
# por", e nascer desligada faria sumir do menu um agrupamento que alguém pode
# estar usando agora.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0147_evolury_um_responsavel"),
    ]

    operations = [
        migrations.AddField(
            model_name="issueproperty",
            name="show_in_grouping",
            field=models.BooleanField(default=True),
        ),
    ]
