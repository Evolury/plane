# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Evolury: a semana começa sempre no domingo (ADR 0005), convenção de
# calendário no Brasil. O default do campo já era domingo; aqui os perfis que
# ficaram com outro dia (de quem trocou enquanto havia seletor) são
# normalizados — senão o valor sobreviveria sem nenhuma tela capaz de
# corrigi-lo. A coluna continua existindo: voltar a oferecer a escolha é
# reverter o commit, sem migração de esquema.

from django.db import migrations

SUNDAY = 0


def normalize_start_of_week(apps, schema_editor):
    Profile = apps.get_model("db", "Profile")
    Profile.objects.exclude(start_of_the_week=SUNDAY).update(start_of_the_week=SUNDAY)


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0128_evolury_profile_language_pt_br"),
    ]

    operations = [
        # Sem reversão: não há como saber qual dia cada perfil usava.
        migrations.RunPython(normalize_start_of_week, migrations.RunPython.noop),
    ]
