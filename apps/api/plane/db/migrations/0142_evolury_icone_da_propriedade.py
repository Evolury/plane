# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Evolury: o ícone escolhido para a propriedade (ADR 0011).
#
# Vazio quer dizer "o padrão do tipo", e não "sem ícone". Assim a propriedade
# que já existe continua funcionando sem nenhuma escrita, e mudar o padrão de um
# tipo alcança quem nunca escolheu — sem migração de dado.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("db", "0141_evolury_propriedades_personalizadas")]

    operations = [
        migrations.AddField(
            model_name="issueproperty",
            name="icon",
            field=models.CharField(blank=True, default="", max_length=32),
        )
    ]
