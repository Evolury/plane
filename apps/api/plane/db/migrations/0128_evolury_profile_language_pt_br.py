# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Evolury: o produto passou a ter idioma único pt-BR (ADR 0004). O default do
# campo já era "pt-BR"; aqui os perfis que ficaram com outro valor (criados
# antes da mudança, ou de quem trocou o idioma quando ainda havia seletor)
# são normalizados — senão o valor sobreviveria no banco sem nenhuma tela
# capaz de corrigi-lo.

from django.db import migrations


def normalize_language(apps, schema_editor):
    Profile = apps.get_model("db", "Profile")
    Profile.objects.exclude(language="pt-BR").update(language="pt-BR")


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0127_evolury_default_state_names_pt_br"),
    ]

    operations = [
        # Sem reversão: não há como saber qual era o idioma de cada perfil.
        migrations.RunPython(normalize_language, migrations.RunPython.noop),
    ]
