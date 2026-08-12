# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Evolury: as preferências de tema passam a ter só preferência do sistema,
# claro e escuro (ADR 0007). Quem estivesse em alto contraste ou no tema
# personalizado ficaria com um valor que o seletor não oferece mais e que o
# next-themes não reconhece — a tela cairia no tema padrão sem explicar por
# quê, e o valor seguiria no banco.
#
# Cada tema removido cai no equivalente de mesma luminosidade: os de alto
# contraste viram claro/escuro, e o personalizado segue o `darkPalette` que
# o próprio usuário tinha escolhido. As chaves de cor do tema personalizado
# são descartadas junto, já que nada mais as lê.

from django.db import migrations

FALLBACK = {"light-contrast": "light", "dark-contrast": "dark"}
COR_KEYS = ("primary", "background", "darkPalette", "sidebarBackground", "sidebarText", "text", "palette")


def normalize_theme(apps, schema_editor):
    Profile = apps.get_model("db", "Profile")

    alterados = []
    for profile in Profile.objects.exclude(theme={}):
        theme = profile.theme or {}
        atual = theme.get("theme")
        if atual not in FALLBACK and atual != "custom":
            continue

        if atual == "custom":
            theme["theme"] = "dark" if theme.get("darkPalette") else "light"
        else:
            theme["theme"] = FALLBACK[atual]

        for chave in COR_KEYS:
            theme.pop(chave, None)

        profile.theme = theme
        alterados.append(profile)

    Profile.objects.bulk_update(alterados, ["theme"], batch_size=200)


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0131_evolury_one_timezone_per_offset"),
    ]

    operations = [
        # Sem reversão: as cores do tema personalizado não são recuperáveis.
        migrations.RunPython(normalize_theme, migrations.RunPython.noop),
    ]
