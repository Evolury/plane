# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""O "se" da automação (ADR 0012).

A condição é a MESMA árvore JSON que o quadro manda no parâmetro `filters`. No
quadro ela pergunta "quais tarefas mostrar?"; aqui pergunta "esta tarefa se
encaixa?". É o mesmo predicado com aridade diferente — e é por isso que este
arquivo é curto: não existe avaliador de condição próprio, existe o filtro do
produto aplicado a um conjunto de uma tarefa só.

O que se ganha com isso, e que um avaliador próprio custaria a manter em dia:
os quinze campos do produto, os seis tipos de propriedade personalizada, os
operadores de negação, os intervalos de data, a exclusão lógica das relações —
tudo já resolvido em `FiltroComPropriedades`, e resolvido do mesmo jeito nos
dois lugares. Filtro e automação não podem divergir sobre o que "prioridade é
urgente" quer dizer.
"""

# Python imports
from types import SimpleNamespace

# Third party imports
from rest_framework.exceptions import ValidationError as DRFValidationError

# Module imports
from plane.db.models import Issue
from plane.utils.filters.filterset import IssueFilterSet
from plane.utils.filters.propriedades import FiltroComPropriedades

#: O backend só olha `filterset_class` (e, opcionalmente, a profundidade
#: máxima) do objeto de view. Não há pedido HTTP aqui, e forjar um seria pior
#: do que dizer com clareza que só isto é usado.
_VIEW = SimpleNamespace(filterset_class=IssueFilterSet)

_BACKEND = FiltroComPropriedades()


class CondicaoInvalida(Exception):
    """A árvore gravada não passa mais na validação do filtro."""


def aplicar(queryset, condicao):
    """Filtra `queryset` pela árvore. Árvore vazia não filtra nada.

    Levanta `CondicaoInvalida` quando a árvore não é aceitável — o que acontece
    de verdade quando alguém remove um campo que a regra usava. É erro da regra,
    não da tarefa, e o motor precisa saber a diferença para registrar a falha
    no lugar certo.
    """
    if not condicao:
        return queryset
    try:
        return _BACKEND.filter_queryset(request=None, queryset=queryset, view=_VIEW, filter_data=condicao)
    except DRFValidationError as erro:
        raise CondicaoInvalida(str(erro.detail)) from erro


def casa(issue_id, condicao) -> bool:
    """A tarefa se encaixa na condição?

    Parte de `Issue.objects` (com exclusão lógica), e não de `issue_objects`,
    porque a automação também vale para rascunho e arquivada quando a regra
    pedir — quem restringe isso é a própria condição, não uma escolha muda aqui.
    """
    if not condicao:
        return True
    return aplicar(Issue.objects.filter(pk=issue_id), condicao).exists()


def tarefas_que_casam(project_id, condicao):
    """As tarefas do projeto que se encaixam — a leitura da regra agendada.

    `issue_objects` já tira rascunho, arquivada, triagem e projeto arquivado, que
    é exatamente o recorte certo aqui: uma regra que roda toda manhã sobre "tudo
    que vence amanhã" não deve mexer no que ainda nem foi publicado nem no que
    alguém guardou. No gatilho de evento a decisão é a mesma, e está em
    `gatilhos.py`.
    """
    return aplicar(Issue.issue_objects.filter(project_id=project_id), condicao)
