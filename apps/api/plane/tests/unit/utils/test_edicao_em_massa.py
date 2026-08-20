# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""As contas do preenchimento em massa (ADR 0019).

`aplicar_modo` é a função que decide se uma etiqueta some ou fica, e é onde o
erro mais caro deste recurso mora: substituir quando se quis somar apaga o
trabalho de outras pessoas sem avisar. Foi o que aconteceu no Jira por anos
(JRA-30729) e é o motivo de o padrão aqui ser somar.
"""

import types

import pytest

from plane.utils.edicao_em_massa import MODO_PADRAO, aplicar_modo, erro_de_data, modo_de


@pytest.mark.unit
class TestAplicarModo:
    def test_add_keeps_what_was_there(self):
        assert aplicar_modo(["a", "b"], ["c"], "add") == ["a", "b", "c"]

    def test_add_does_not_duplicate(self):
        assert aplicar_modo(["a"], ["a", "b"], "add") == ["a", "b"]

    def test_remove_takes_only_what_was_asked(self):
        assert aplicar_modo(["a", "b", "c"], ["b"], "remove") == ["a", "c"]

    def test_remove_ignores_what_is_not_there(self):
        assert aplicar_modo(["a"], ["z"], "remove") == ["a"]

    def test_replace_replaces_everything(self):
        assert aplicar_modo(["a", "b"], ["c"], "replace") == ["c"]

    def test_replace_with_nothing_clears(self):
        assert aplicar_modo(["a", "b"], [], "replace") == []

    def test_the_order_is_stable(self):
        """Ordem instável faria o histórico registrar mudança onde não houve."""
        assert aplicar_modo(["b", "a"], [], "add") == ["b", "a"]

    def test_uuids_and_text_compare_the_same(self):
        from uuid import uuid4

        um = uuid4()
        assert aplicar_modo([um], [str(um)], "add") == [str(um)]


@pytest.mark.unit
class TestModoDe:
    def test_the_default_is_to_add(self):
        assert modo_de({}, "label_ids") == "add"
        assert MODO_PADRAO == "add"

    def test_an_unknown_mode_falls_back_to_the_default(self):
        """Modo desconhecido não pode virar "substituir" por acidente."""
        assert modo_de({"label_ids": "apagar-tudo"}, "label_ids") == "add"

    def test_it_reads_the_asked_mode(self):
        assert modo_de({"label_ids": "replace"}, "label_ids") == "replace"


@pytest.mark.unit
class TestErroDeData:
    def _tarefa(self, inicio=None, vencimento=None):
        return types.SimpleNamespace(start_date=inicio, target_date=vencimento)

    def test_it_compares_against_what_the_work_item_already_has(self):
        """O ponto: só o início foi pedido, e ele passa o vencimento que
        ninguém tocou. Validar contra o vazio deixaria isso entrar."""
        tarefa = self._tarefa(vencimento="2026-08-10")
        assert erro_de_data(tarefa, {"start_date": "2026-08-20"}) == "start_date"

    def test_the_target_date_is_named_when_it_is_the_one_asked(self):
        tarefa = self._tarefa(inicio="2026-08-20")
        assert erro_de_data(tarefa, {"target_date": "2026-08-10"}) == "target_date"

    def test_coherent_dates_pass(self):
        tarefa = self._tarefa(inicio="2026-08-01")
        assert erro_de_data(tarefa, {"target_date": "2026-08-10"}) is None

    def test_same_day_passes(self):
        tarefa = self._tarefa(vencimento="2026-08-10")
        assert erro_de_data(tarefa, {"start_date": "2026-08-10"}) is None

    def test_a_work_item_without_dates_never_breaks(self):
        assert erro_de_data(self._tarefa(), {"start_date": "2026-08-20"}) is None
