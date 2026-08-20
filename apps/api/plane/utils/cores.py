# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""A cor de capa, e o que conta como uma.

A capa de um projeto ou de um perfil pode ser uma imagem OU uma cor. A cor não
cabia no campo que existia: `cover_image` do usuário é um `URLField`, e uma
medição contra a API devolveu `{"cover_image": ["Enter a valid URL."]}` para
`#0C91EB`. Daí o campo próprio — `cover_color` —, em vez de enfiar o que não é
URL num campo que o resto do código trata como URL.

O valor termina desenhado num `style` do navegador. Aceitar "qualquer coisa que
comece com #" deixaria passar `#fff);background-image:url(…` e transformaria um
campo de cor em injeção de CSS. Por isso a forma é exata, e é aqui — no
servidor — que ela é cobrada; o front tem a mesma regra, mas o front é sugestão.
"""

import re

# `#RRGGBB`. Sem forma curta (`#FFF`), sem `rgb()`, sem nome de cor: um formato
# só é um formato que não precisa ser adivinhado na hora de desenhar.
FORMATO_DE_COR = re.compile(r"^#[0-9a-fA-F]{6}$")


def normalizar_cor_de_capa(valor):
    """Devolve `#RRGGBB` em maiúsculas, ou `None` quando não há cor.

    Levanta `ValueError` para qualquer outra coisa. Maiúsculas para que
    `#0c91eb` e `#0C91EB` não vivam no banco como se fossem cores diferentes —
    o que quebraria "esta é a cor selecionada" na hora de marcar a escolhida.
    """
    if valor is None:
        return None

    if not isinstance(valor, str):
        raise ValueError("COVER_COLOR_INVALID")

    valor = valor.strip()
    if valor == "":
        return None

    if not FORMATO_DE_COR.match(valor):
        raise ValueError("COVER_COLOR_INVALID")

    return valor.upper()
