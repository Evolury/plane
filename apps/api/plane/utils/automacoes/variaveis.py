# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""As variáveis do texto de comentário e notificação (ADR 0012, F2).

**Lista fechada, e não linguagem.** O Jira resolve isto com *smart values*, que
são expressões com funções, aninhamento e um modo de depuração próprio — a
ponto de a documentação deles ensinar a envolver um valor em `debug` para
descobrir por que a regra escreveu a coisa errada. Uma linguagem dentro de uma
caixa de texto é uma linguagem que alguém vai ter de manter, documentar e
depurar; e o texto de um comentário automático não justifica isso.

Aqui há cinco nomes. O que não estiver na lista fica **literal** na tela, e não
vira erro: quem escreveu `{{orçamento}}` sem querer vê o que escreveu, em vez
de ver um comentário que sumiu ou uma regra que falhou.
"""

# Python imports
import re

#: `{{nome}}` — as chaves duplas, e não `$nome` ou `%nome%`, porque é a forma
#: que a maioria das ferramentas do gênero usa e que as pessoas já reconhecem.
PADRAO = re.compile(r"\{\{\s*([a-zà-ú_]+)\s*\}\}", re.IGNORECASE)

VAZIO = "—"


def _nome(usuario):
    if usuario is None:
        return VAZIO
    return usuario.display_name or usuario.email or VAZIO


def valores(tarefa, contexto):
    """O dicionário de substituição desta execução."""
    from plane.db.models import User

    quem_disparou = (contexto.get("evento") or {}).get("actor_id")
    disparador = User.objects.filter(pk=quem_disparou).first() if quem_disparou else None

    # Evolury: a tarefa tem um responsável (ADR 0016) — a variável deixou de
    # juntar nomes. O `first()` não é chute: o índice único do banco garante que
    # não há um segundo.
    atribuicao = (
        tarefa.issue_assignee.filter(deleted_at__isnull=True).select_related("assignee").first()
    )
    responsavel = _nome(atribuicao.assignee) if atribuicao else VAZIO

    return {
        "tarefa": tarefa.name,
        "responsável": responsavel,
        # Sem acento também, porque quem digita a variável na caixa nem sempre
        # acentua — e uma variável que "não funciona" por causa de um acento é
        # um defeito que a pessoa não tem como diagnosticar.
        "responsavel": responsavel,
        "quem_disparou": _nome(disparador),
        "estado": tarefa.state.name if tarefa.state_id else VAZIO,
        "vencimento": tarefa.target_date.isoformat() if tarefa.target_date else VAZIO,
    }


def aplicar(texto, tarefa, contexto):
    """Troca as variáveis conhecidas. As demais ficam como estão."""
    if not texto:
        return ""
    tabela = valores(tarefa, contexto)
    return PADRAO.sub(lambda achado: tabela.get(achado.group(1).lower(), achado.group(0)), texto)
