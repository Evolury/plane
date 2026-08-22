# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Evolury: os dados de cobrança do contrato (ADR 0021).
#
# CPF ou CNPJ é exigência do Asaas para criar o cliente, e não existia em lugar
# nenhum do produto — nem no usuário, nem no espaço de trabalho. Nascem vazios,
# e é o certo: espaço em cortesia não tem contrato para preencher.
#
# Ficam na assinatura, e não no espaço, porque são do contrato: quem paga pode
# não ser quem administra, e trocar de responsável financeiro não pode mexer no
# nome do espaço de trabalho.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('db', '0152_evolury_resultado_do_evento'),
    ]

    operations = [
        migrations.AddField(
            model_name='assinatura',
            name='cpf_cnpj',
            field=models.CharField(blank=True, default='', max_length=14),
        ),
        migrations.AddField(
            model_name='assinatura',
            name='email_de_cobranca',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='assinatura',
            name='nome_de_cobranca',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='assinatura',
            name='telefone_de_cobranca',
            field=models.CharField(blank=True, default='', max_length=20),
        ),
    ]
