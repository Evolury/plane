# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""A árvore de subtarefas de uma tarefa, em largura e com teto (ADR 0010, F8).

Em largura por correção, não por gosto: **filha de quem não foi copiado não
pode ser copiada**. Percorrer nível a nível e cortar na fronteira do nível
garante isso sozinho — em profundidade, o teto cairia no meio de um ramo e
deixaria netas sem pai na ocorrência.

O teto conta a **árvore inteira**, não os filhos diretos. É a escolha do
ClickUp, que soma as aninhadas no limite dele; sem ela, "50 subtarefas" viraria
50 × 50 × 50 no dia em que o aninhamento entrasse. E é o que mantém o custo da
geração igual ao de antes: o mesmo número de nós, distribuídos de outro jeito.

O conjunto de visitados fecha a porta do ciclo. `parent` é um ponteiro comum e
nada no banco impede A → B → A; uma travessia ingênua rodaria para sempre
dentro de um job de fundo, que é onde ninguém está olhando.
"""

# Python imports
from collections import defaultdict

# Module imports
from plane.db.models import Issue

# Teto de subtarefas copiadas por ocorrência, contando todos os níveis. Acima
# disso a ocorrência é um projeto disfarçado. A tela avisa ao configurar, e
# aqui o corte é silencioso de propósito: a regra de ninguém é desligada por
# causa do teto — que é o que o ClickUp faz ao passar de 500.
TETO_DE_SUBTAREFAS = 50


def ids_da_arvore(raiz_id, teto=TETO_DE_SUBTAREFAS):
    """Os ids dos descendentes de `raiz_id`, em ordem de cópia.

    Ordem de cópia = pai sempre antes das filhas, e irmãs juntas na ordem em
    que aparecem no cartão. Devolve ids, e não objetos, porque quem só quer
    saber o tamanho da árvore — o aviso de teto na tela — não precisa carregar
    tarefa nenhuma.

    Uma consulta por nível. Uma tarefa comum tem um ou dois; o teto limita o
    resto, porque cada volta do laço coleta ao menos um nó ou termina.
    """
    coletados = []
    visitados = {raiz_id}
    fronteira = [raiz_id]

    while fronteira and len(coletados) < teto:
        por_pai = defaultdict(list)
        for filha_id, pai_id in (
            Issue.issue_objects.filter(parent_id__in=fronteira)
            .order_by("sort_order", "created_at")
            .values_list("id", "parent_id")
        ):
            por_pai[pai_id].append(filha_id)

        # A fronteira já está em ordem de cópia; percorrê-la nesta ordem é o
        # que mantém as irmãs contíguas em vez de intercaladas com as primas.
        proxima = []
        for pai_id in fronteira:
            for filha_id in por_pai[pai_id]:
                if filha_id in visitados:
                    continue
                visitados.add(filha_id)
                coletados.append(filha_id)
                proxima.append(filha_id)
                if len(coletados) == teto:
                    return coletados
        fronteira = proxima

    return coletados


def excede_o_teto(raiz_id, teto=TETO_DE_SUBTAREFAS):
    """A árvore é maior que o teto — o que a tela avisa antes de a regra rodar."""
    return len(ids_da_arvore(raiz_id, teto=teto + 1)) > teto


def dentro_da_arvore(raiz_id, subtarefa_id, teto=TETO_DE_SUBTAREFAS):
    """`subtarefa_id` é descendente de `raiz_id` e cabe na cópia.

    A pergunta que a API faz ao aceitar um vencimento relativo: agendar uma
    subtarefa que a ocorrência nunca vai criar seria configurar o vazio.
    """
    return subtarefa_id in set(ids_da_arvore(raiz_id, teto=teto))
