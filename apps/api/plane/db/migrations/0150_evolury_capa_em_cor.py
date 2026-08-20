# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Evolury: a capa passa a poder ser uma cor.
#
# Campo novo, e não reaproveitamento: `cover_image` do usuário é um `URLField`,
# e a API recusa `#0C91EB` com "Enter a valid URL." — medido contra o servidor,
# não deduzido. No projeto o campo é `TextField` e aceitaria, mas guardar cor
# num campo que o resto do código lê como endereço de arquivo é o tipo de
# ambiguidade que cobra juros depois.
#
# Nasce vazio em todas as linhas, e é o certo: quem já tem capa continua com a
# capa que escolheu, e quem não tem continua no azul da marca que a tela pinta.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0149_evolury_atividade_de_propriedade"),
    ]

    operations = [
        migrations.AddField(
            model_name="project",
            name="cover_color",
            field=models.CharField(blank=True, max_length=7, null=True),
        ),
        migrations.AddField(
            model_name="user",
            name="cover_color",
            field=models.CharField(blank=True, max_length=7, null=True),
        ),
    ]
