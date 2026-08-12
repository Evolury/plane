# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Evolury: a lista de fusos passa a ter uma entrada por offset (ADR 0006).
# As zonas removidas só diferem das que ficaram em regras de horário de verão
# anteriores a 2019, quando o Brasil o aboliu — de lá para cá o offset é o
# mesmo, então remapear não muda hora nenhuma para datas atuais.
#
# Cada zona removida vai para a que sobreviveu no MESMO offset; assim ninguém
# muda de hora. A normalização vem antes do AlterField pelo mesmo motivo da
# 0130: com choices restritas, um valor fora da lista travaria o próximo PATCH
# do perfil sem que o usuário tivesse como corrigir.

from django.db import migrations, models

BRAZIL_TIMEZONES = [
    "America/Noronha",
    "America/Sao_Paulo",
    "America/Manaus",
    "America/Rio_Branco",
]

DEFAULT_TIMEZONE = "America/Sao_Paulo"

# zona removida -> zona que ficou, sempre no mesmo offset
REMAPPING = {
    # UTC-03:00
    "America/Bahia": "America/Sao_Paulo",
    "America/Fortaleza": "America/Sao_Paulo",
    "America/Recife": "America/Sao_Paulo",
    "America/Maceio": "America/Sao_Paulo",
    "America/Belem": "America/Sao_Paulo",
    "America/Santarem": "America/Sao_Paulo",
    "America/Araguaina": "America/Sao_Paulo",
    # UTC-04:00
    "America/Cuiaba": "America/Manaus",
    "America/Campo_Grande": "America/Manaus",
    "America/Porto_Velho": "America/Manaus",
    "America/Boa_Vista": "America/Manaus",
    # UTC-05:00
    "America/Eirunepe": "America/Rio_Branco",
}


def collapse_timezones(apps, schema_editor):
    User = apps.get_model("db", "User")

    for removida, mantida in REMAPPING.items():
        User.objects.filter(user_timezone=removida).update(user_timezone=mantida)

    # rede de segurança para qualquer valor que ainda esteja fora da lista
    User.objects.exclude(user_timezone__in=BRAZIL_TIMEZONES).update(user_timezone=DEFAULT_TIMEZONE)


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0130_evolury_user_timezone_brazil"),
    ]

    operations = [
        migrations.RunPython(collapse_timezones, migrations.RunPython.noop),
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
