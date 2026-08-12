# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Evolury: o fuso do usuário passa a aceitar só as zonas do Brasil (ADR 0006).
# A normalização vem ANTES do AlterField de propósito: com choices restritas,
# um perfil que ficasse em "UTC" falharia na validação do DRF no primeiro
# PATCH, e o usuário não teria como consertar — o seletor não ofereceria mais
# o valor antigo.
#
# Quem já está numa zona brasileira é preservado: só cai para São Paulo quem
# está fora da lista (inclusive o "UTC" que o upstream usava como padrão, três
# horas à frente de Brasília).

from django.db import migrations, models

BRAZIL_TIMEZONES = [
    "America/Noronha",
    "America/Sao_Paulo",
    "America/Bahia",
    "America/Fortaleza",
    "America/Recife",
    "America/Maceio",
    "America/Belem",
    "America/Santarem",
    "America/Araguaina",
    "America/Manaus",
    "America/Cuiaba",
    "America/Campo_Grande",
    "America/Porto_Velho",
    "America/Boa_Vista",
    "America/Rio_Branco",
    "America/Eirunepe",
]

DEFAULT_TIMEZONE = "America/Sao_Paulo"


def normalize_timezone(apps, schema_editor):
    User = apps.get_model("db", "User")
    User.objects.exclude(user_timezone__in=BRAZIL_TIMEZONES).update(user_timezone=DEFAULT_TIMEZONE)


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0129_evolury_start_of_week_sunday"),
    ]

    operations = [
        migrations.RunPython(normalize_timezone, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="user",
            name="user_timezone",
            field=models.CharField(
                choices=[(tz, tz) for tz in BRAZIL_TIMEZONES],
                default=DEFAULT_TIMEZONE,
                max_length=255,
            ),
        ),
    ]
