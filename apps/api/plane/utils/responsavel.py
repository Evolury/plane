# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Evolury — uma tarefa tem um responsável, e nunca mais de um (ADR 0016).

A garantia de verdade é o índice único parcial em `issue_assignees(issue_id)`:
o Postgres torna dois responsáveis **impossíveis**, valha o pedido pela tela,
pela API, por importação ou por SQL direto.

Esta função existe para que a rede embaixo não precise ser usada. Toda porta de
escrita normaliza antes de gravar, e o que chega com mais de um vira o
**último** — decisão do Tássio em 19/08/2026, contra a recomendação de recusar
com 400. O risco de perder gente em silêncio fica mitigado pela resposta, que
devolve o `assignee_ids` efetivo: quem comparar o que enviou com o que voltou
enxerga a diferença.
"""


def apenas_um(responsaveis):
    """Devolve `[]` ou uma lista com o último responsável pedido.

    Aceita `None` (nada foi pedido) devolvendo `None`, para que quem chama
    consiga distinguir "não mexeu" de "esvaziou" — a diferença entre não tocar
    no campo e tirar o responsável.
    """
    if responsaveis is None:
        return None
    lista = list(responsaveis)
    return lista[-1:] if lista else []


def excedentes(linhas):
    """Quais atribuições saem quando uma tarefa tem mais de um responsável.

    `linhas` é uma sequência de `(id, dono, created_at)`. Sobrevive a **mais
    recente** de cada dono — a mesma regra do `apenas_um`, para que a migração e
    as portas de escrita não divirjam.

    O desempate por `id` não é preciosismo: sem ele, duas linhas gravadas no
    mesmo instante escolheriam sobrevivente diferente a cada execução, e a
    migração deixaria de ser determinística.
    """
    visto = set()
    fora = []
    for identificador, dono, _ in sorted(linhas, key=lambda linha: (linha[2], linha[0]), reverse=True):
        if dono in visto:
            fora.append(identificador)
        else:
            visto.add(dono)
    return fora
