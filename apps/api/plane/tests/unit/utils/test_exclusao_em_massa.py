# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""As regras da exclusão em massa que não precisam de banco (ADR 0018).

A travessia é DESCOBERTA no modelo, e não escrita à mão. É o que garante que a
próxima relação criada neste fork — a sétima — caia junto sem que ninguém tenha
de lembrar de vir aqui. Estes testes vigiam os dois lados da descoberta: o que
ela precisa alcançar e o que ela não pode arrastar.
"""

import types

import pytest

from plane.db.models import Issue, IssueActivity, IssueComment, IssueSequence
from plane.utils.exclusao_em_massa import (
    modelos_alcancaveis,
    relacoes_em_cascata,
    separar_por_permissao,
)


def _modelos(relacoes):
    return {modelo for modelo, _ in relacoes}


@pytest.mark.unit
class TestOQueCaiJunto:
    def test_sub_items_fall_with_the_parent(self):
        """A relação de `Issue` consigo mesma é `CASCADE`: subtarefa morre com o
        pai. Era o buraco do endpoint antigo."""
        assert Issue in _modelos(relacoes_em_cascata(Issue))

    def test_comments_fall_with_the_work_item(self):
        assert IssueComment in _modelos(relacoes_em_cascata(Issue))

    def test_history_does_not_fall(self):
        """`IssueActivity` é `DO_NOTHING`: o histórico sobrevive à exclusão — e
        precisa sobreviver, senão o desfazer devolveria a tarefa sem passado."""
        assert IssueActivity not in _modelos(relacoes_em_cascata(Issue))

    def test_set_null_relations_are_left_alone(self):
        """`IssueSequence.issue` é `SET_NULL`. Anular seria perda que nenhum
        desfazer traz de volta."""
        assert IssueSequence not in _modelos(relacoes_em_cascata(Issue))

    def test_the_walk_goes_deeper_than_one_level(self):
        """O desfazer procura por instante em cada modelo alcançável; se a
        varredura parasse no primeiro nível, a reação de um comentário voltaria
        excluída."""
        alcancaveis = modelos_alcancaveis(Issue)
        assert Issue in alcancaveis
        assert IssueComment in alcancaveis
        assert len(alcancaveis) > len(_modelos(relacoes_em_cascata(Issue)))


@pytest.mark.unit
class TestQuemPodeExcluir:
    def _tarefa(self, autor):
        return types.SimpleNamespace(created_by_id=autor)

    def test_an_admin_may_delete_everything(self):
        tarefas = [self._tarefa("alguem"), self._tarefa("outro")]
        permitidas, negadas = separar_por_permissao(tarefas, actor_id="admin", e_admin=True)
        assert permitidas == tarefas
        assert negadas == []

    def test_a_member_may_delete_only_what_they_created(self):
        minha = self._tarefa("eu")
        alheia = self._tarefa("outro")
        permitidas, negadas = separar_por_permissao([minha, alheia], actor_id="eu", e_admin=False)
        assert permitidas == [minha]
        assert negadas == [alheia]

    def test_the_comparison_survives_uuid_versus_text(self):
        """O ator vem do pedido e o autor vem do banco: um é `UUID`, o outro
        vira texto no caminho. Comparar sem normalizar diria "não é sua" para
        toda tarefa."""
        from uuid import uuid4

        pessoa = uuid4()
        permitidas, negadas = separar_por_permissao([self._tarefa(pessoa)], actor_id=str(pessoa), e_admin=False)
        assert len(permitidas) == 1
        assert negadas == []
