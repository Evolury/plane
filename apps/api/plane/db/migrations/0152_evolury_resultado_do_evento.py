# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Evolury: o evento do Asaas passa a dizer o que aconteceu com ele (ADR 0021).
#
# `aplicado`, `ignorado` ou `erro`. O terceiro estado é o que motiva o campo:
# a conta do Asaas da Evolury atende outros negócios — medido em 21/08/2026,
# eram 9 assinaturas, 25 clientes e 259 cobranças que não têm nada a ver com o
# QooWork —, e o webhook recebe tudo. Ignorar é normal; sem um campo dizendo
# isso, um painel de erros mostraria centenas de linhas saudáveis e ninguém
# olharia para ele.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('db', '0151_evolury_faturamento'),
    ]

    operations = [
        migrations.AddField(
            model_name='eventoasaas',
            name='resultado',
            field=models.CharField(blank=True, db_index=True, default='', max_length=16),
        ),
    ]
