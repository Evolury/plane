# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Filtro por propriedade personalizada dentro da árvore de filtros ricos.

A tela não manda mais um parâmetro por filtro: manda a árvore inteira em
`filters`, como JSON, e o `ComplexFilterBackend` a valida contra o FilterSet
antes de virar `Q`. Uma propriedade personalizada não cabe nesse FilterSet —
o "campo" é um id que só existe em tempo de execução, e declarar um filtro por
propriedade seria declarar um filtro por linha de tabela.

O upstream deixou dois ganchos exatamente para isso
(`_transform_field_name_for_validation` e `_preprocess_leaf_conditions`).
Usamos o primeiro para a validação e trocamos o segundo por `_build_leaf_q`,
que é onde a condição precisa nascer: como `Q(pk__in=…)`, e não como join.

A prova que o campo não faz pela allowlist ele faz aqui, e é a mesma do
`group_by` (ADR 0011): o que vem de quem chama tem de ser um UUID e tem de
existir como propriedade. Nada do nome do campo chega ao ORM como caminho.
"""

import uuid as _uuid

from django.db.models import Q

from plane.utils.filters.filter_backend import ComplexFilterBackend
from plane.utils.issue_properties import (
    OPERADORES_POR_TIPO,
    PREFIXO_DE_FILTRO,
    propriedades_por_id,
    q_de_propriedade,
)

#: O campo-sentinela declarado no `IssueFilterSet`.
#:
#: A validação do upstream compara o nome do campo com `base_filters`. Toda
#: chave de propriedade é traduzida para este nome antes dessa comparação —
#: depois de provado que é um UUID. Assim a allowlist continua sendo uma
#: allowlist: o que passa é um nome fixo, e não o texto que veio do pedido.
CAMPO_SENTINELA = "custom_property"

#: Os sufixos que a árvore de filtros usa, e o operador interno de cada um.
LOOKUPS = {
    "in": "in",
    "contains": "in",
    "gte": "gte",
    "lte": "lte",
    # `exact` só vira "in" nos tipos de lista e texto; nos demais é igualdade
    # de verdade, e quem decide é `q_de_propriedade`, que conhece o tipo.
    "exact": "exact",
    "range": "range",
}


def partes_da_chave(nome):
    """`property_<uuid>__<lookup>` → `(id, lookup)`, ou `None`.

    Devolve `None` para qualquer coisa que não seja exatamente isso — chave
    de outro filtro, id malformado, sufixo que não declaramos.
    """
    if not isinstance(nome, str) or not nome.startswith(PREFIXO_DE_FILTRO):
        return None
    resto = nome[len(PREFIXO_DE_FILTRO) :]
    lookup = "in"
    if "__" in resto:
        resto, sufixo = resto.rsplit("__", 1)
        lookup = LOOKUPS.get(sufixo)
        if lookup is None:
            return None
    try:
        _uuid.UUID(resto)
    except (ValueError, AttributeError, TypeError):
        return None
    return resto, lookup


class FiltroComPropriedades(ComplexFilterBackend):
    """O backend do upstream, mais as propriedades personalizadas."""

    def _transform_field_name_for_validation(self, field_name):
        # Um id não cabe numa allowlist de nomes. O que a allowlist recebe é
        # o sentinela — e só depois de o id ter passado pela prova de forma.
        if partes_da_chave(field_name) is not None:
            return CAMPO_SENTINELA
        return field_name

    def _build_leaf_q(self, leaf_conditions, view, queryset):
        if not leaf_conditions:
            return Q()

        propriedades, restantes = {}, {}
        for chave, valor in leaf_conditions.items():
            partes = partes_da_chave(chave)
            if partes is None:
                restantes[chave] = valor
                continue
            propriedade_id, lookup = partes
            propriedades.setdefault(propriedade_id, {})[lookup] = valor

        if not propriedades:
            return super()._build_leaf_q(leaf_conditions, view, queryset)

        # O resto da folha continua sendo problema do upstream: só o que é
        # nosso sai da folha antes de ela seguir o caminho normal.
        condicao = super()._build_leaf_q(restantes, view, queryset) if restantes else Q()

        por_id = propriedades_por_id(propriedades.keys())
        for propriedade_id, operadores in propriedades.items():
            propriedade = por_id.get(propriedade_id)
            if propriedade is None or not propriedade.is_active:
                # Propriedade apagada ou desligada não filtra nada — e também
                # não derruba a tela de quem tinha a visão salva com ela.
                continue
            permitidos = OPERADORES_POR_TIPO.get(propriedade.property_type, ())
            usados = {k: v for k, v in operadores.items() if k in permitidos}
            if not usados:
                continue
            parcial = q_de_propriedade(propriedade, usados)
            if parcial is not None:
                condicao &= parcial

        return condicao
