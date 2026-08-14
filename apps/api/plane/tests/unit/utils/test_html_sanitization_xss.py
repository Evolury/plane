# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Regressão de GHSA-rwjc-xhh3-m9m9 — XSS armazenado em `description_html`.

O ataque é gravar HTML malicioso pela API e ele executar quando outra pessoa
abre a tarefa. A defesa é sanitizar **na escrita**, com lista de permissão:
`nh3.clean` roda nos serializers do app e da API pública antes de qualquer
coisa chegar ao banco.

Este teste ataca o sanitizador direto, com os vetores clássicos. Ele existe
porque a lista de permissão é editada quando o editor ganha um nó novo — e uma
tag executável entrando ali passaria despercebida sem alguém tentando explorá-la.

Verificado na triagem de 14/08/2026
(docs/evolury/processos/historico-de-revisoes.md).
"""

import pytest

from plane.utils.content_validator import validate_html_content

# Vetor, e o que não pode sobreviver a ele.
VETORES = [
    ("<script>alert(1)</script>", "script"),
    ("<img src=x onerror=alert(1)>", "onerror"),
    ('<a href="javascript:alert(1)">clique</a>', "javascript:"),
    ('<iframe src="https://evil.example"></iframe>', "iframe"),
    ("<svg onload=alert(1)>", "onload"),
    ('<p onclick="alert(1)">texto</p>', "onclick"),
    ('<body background="javascript:alert(1)">', "javascript:"),
    ('<object data="data:text/html;base64,PHNjcmlwdD4="></object>', "object"),
]


@pytest.mark.unit
@pytest.mark.parametrize("html,proibido", VETORES)
def test_dangerous_markup_never_survives(html, proibido):
    valido, erro, limpo = validate_html_content(html)

    assert valido is True, erro
    assert proibido not in (limpo or "").lower()


@pytest.mark.unit
def test_legitimate_formatting_survives():
    """A sanitização não pode custar o texto: quem escreve em negrito continua."""
    html = '<p>Relatório <strong>mensal</strong> — <a href="https://evolury.com.br">aqui</a></p>'

    _, _, limpo = validate_html_content(html)

    assert "<strong>mensal</strong>" in limpo
    assert 'href="https://evolury.com.br"' in limpo


@pytest.mark.unit
def test_editor_nodes_survive():
    """As tags do nosso editor estão na lista de permissão de propósito."""
    html = '<mention-component entity_identifier="abc"></mention-component>'

    _, _, limpo = validate_html_content(html)

    assert "mention-component" in limpo
