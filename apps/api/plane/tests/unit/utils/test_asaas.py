# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""O cliente do Asaas, na parte que não precisa de rede (ADR 0021).

Dois assuntos, e os dois já mordem em produção quando saem errado: **dinheiro**,
onde o Asaas fala em reais com casa decimal e nós guardamos centavos inteiros, e
**identidade**, que é como sabemos que uma cobrança é nossa numa conta que
atende outros negócios da Evolury.
"""

from datetime import date

import pytest

from plane.utils import asaas
from plane.utils.planos import CICLO_ANUAL, CICLO_MENSAL, fim_do_ciclo


@pytest.mark.unit
class TestDinheiro:
    @pytest.mark.parametrize(
        "reais,esperado",
        [
            # Os três valores vieram da conta real, em 21/08/2026.
            (2000.0, 200000),
            (10000.0, 1000000),
            (10.0, 1000),
            (0.1, 10),
            (1939.71, 193971),
            (0, 0),
            (None, 0),
        ],
    )
    def test_reais_para_centavos(self, reais, esperado):
        assert asaas.centavos(reais) == esperado

    def test_o_centavo_nao_se_perde_no_caminho(self):
        """`19.99 * 100` em ponto flutuante dá 1998.9999… — daí o Decimal."""
        assert asaas.centavos(19.99) == 1999
        assert asaas.centavos("19.99") == 1999

    def test_centavos_para_reais(self):
        assert asaas.reais(29000) == 290.0
        assert asaas.reais(1999) == 19.99

    def test_ida_e_volta(self):
        for valor in (29000, 69000, 159000, 1, 999999):
            assert asaas.centavos(asaas.reais(valor)) == valor


@pytest.mark.unit
class TestIdentidade:
    def test_a_referencia_leva_o_espaco(self):
        assert asaas.referencia_de("abc-123") == "qoowork:abc-123"

    def test_a_volta_devolve_o_espaco(self):
        assert asaas.espaco_da_referencia("qoowork:abc-123") == "abc-123"

    def test_referencia_de_outro_sistema_nao_e_nossa(self):
        """Medido na conta real: há assinatura com UUID puro, de outro negócio."""
        assert asaas.espaco_da_referencia("7dcf92dd-3b07-4107-a524-938b4b618353") is None

    def test_sem_referencia_nao_e_nossa(self):
        assert asaas.espaco_da_referencia(None) is None
        assert asaas.espaco_da_referencia("") is None


@pytest.mark.unit
class TestAmbiente:
    def test_producao_e_o_padrao(self):
        assert asaas.base_da_api("producao") == "https://api.asaas.com/v3"
        assert asaas.base_da_api("qualquer-outra-coisa") == "https://api.asaas.com/v3"

    def test_sandbox_quando_pedido(self):
        assert asaas.base_da_api("sandbox") == "https://api-sandbox.asaas.com/v3"


@pytest.mark.unit
class TestFimDoCiclo:
    def test_mensal(self):
        assert fim_do_ciclo(date(2026, 8, 22), CICLO_MENSAL) == date(2026, 9, 22)

    def test_anual(self):
        assert fim_do_ciclo(date(2026, 8, 22), CICLO_ANUAL) == date(2027, 8, 22)

    def test_trinta_e_um_de_janeiro_nao_vira_tres_de_marco(self):
        """Somar trinta dias faria a cobrança andar no calendário a cada mês."""
        assert fim_do_ciclo(date(2026, 1, 31), CICLO_MENSAL) == date(2026, 2, 28)

    def test_ano_bissexto(self):
        assert fim_do_ciclo(date(2028, 1, 31), CICLO_MENSAL) == date(2028, 2, 29)
        assert fim_do_ciclo(date(2028, 2, 29), CICLO_ANUAL) == date(2029, 2, 28)

    def test_ciclo_desconhecido_e_erro(self):
        with pytest.raises(ValueError, match="Ciclo desconhecido"):
            fim_do_ciclo(date(2026, 8, 22), "quinzenal")
