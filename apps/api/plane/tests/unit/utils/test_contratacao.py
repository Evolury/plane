# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""As três contas da contratação (ADR 0021): documento, cupom e pró-rata.

Nenhuma delas precisa de banco nem de rede — e todas as três, erradas, custam
dinheiro ou confiança. Documento inválido vira erro de gateway três telas
depois; cupom sem fim vira assinatura grátis para sempre; pró-rata errado cobra
duas vezes pelos dias que o cliente já pagou.
"""

from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from plane.utils import cupons, documentos, proporcional
from plane.utils.planos import fim_do_ciclo

HOJE = date(2026, 8, 21)


def cupom(**campos):
    padrao = {
        "codigo": "TESTE",
        "tipo": cupons.PERCENTUAL,
        "valor": 20,
        "ciclos": 3,
        "validade": None,
        "usos_max": None,
        "usos": 0,
    }
    padrao.update(campos)
    return SimpleNamespace(**padrao)


@pytest.mark.unit
class TestDocumentos:
    @pytest.mark.parametrize("documento", ["11144477735", "111.444.777-35", " 111.444.777-35 "])
    def test_cpf_valido_em_qualquer_formato(self, documento):
        assert documentos.valido(documento)

    @pytest.mark.parametrize("documento", ["11222333000181", "11.222.333/0001-81"])
    def test_cnpj_valido_em_qualquer_formato(self, documento):
        assert documentos.valido(documento)

    @pytest.mark.parametrize(
        "documento", ["12345678900", "11111111111", "00000000000000", "123", "", None, "abcdefghijk"]
    )
    def test_o_que_nao_pode_existir(self, documento):
        assert not documentos.valido(documento)

    def test_guardar_e_so_digito_exibir_e_com_pontuacao(self):
        assert documentos.normalizar("111.444.777-35") == "11144477735"
        assert documentos.formatar("11144477735") == "111.444.777-35"
        assert documentos.formatar("11222333000181") == "11.222.333/0001-81"


@pytest.mark.unit
class TestCupons:
    def test_percentual_desconta_e_arredonda_para_baixo(self):
        # 20% de R$ 690,00 são R$ 138,00 — e o resto é do cliente.
        assert cupons.valor_com_desconto(cupom(valor=20), 69000) == 55200
        assert cupons.valor_com_desconto(cupom(valor=33), 29000) == 19430

    def test_cem_por_cento_zera(self):
        assert cupons.valor_com_desconto(cupom(valor=100), 69000) == 0

    def test_cortesia_zera_qualquer_valor(self):
        assert cupons.valor_com_desconto(cupom(tipo=cupons.CORTESIA, valor=30), 159000) == 0

    def test_sem_cupom_o_valor_e_o_valor(self):
        assert cupons.valor_com_desconto(None, 69000) == 69000

    def test_cortesia_empurra_a_primeira_cobranca(self):
        assert cupons.primeira_cobranca(cupom(tipo=cupons.CORTESIA, valor=30), HOJE) == HOJE + timedelta(days=30)

    def test_sem_cortesia_cobra_hoje(self):
        """Quem contrata, contrata pagando — não há teste grátis por autoatendimento."""
        assert cupons.primeira_cobranca(None, HOJE) == HOJE
        assert cupons.primeira_cobranca(cupom(valor=50), HOJE) == HOJE

    def test_toda_promocao_por_ciclos_tem_fim(self):
        assert cupons.fim_da_promocao(cupom(ciclos=3), HOJE, fim_do_ciclo, "mensal") == date(2026, 11, 21)

    def test_tres_ciclos_de_um_contrato_anual_sao_tres_anos(self):
        """Confundir ciclo com mês daria desconto por engano — e por muito tempo."""
        assert cupons.fim_da_promocao(cupom(ciclos=3), HOJE, fim_do_ciclo, "anual") == date(2029, 8, 21)

    def test_cortesia_termina_no_dia_marcado(self):
        assert cupons.fim_da_promocao(
            cupom(tipo=cupons.CORTESIA, valor=15), HOJE, fim_do_ciclo, "mensal"
        ) == date(2026, 9, 5)

    def test_permanente_e_a_unica_sem_data(self):
        """E é decisão, registrada pela ausência — não descuido."""
        assert cupons.fim_da_promocao(cupom(ciclos=None), HOJE, fim_do_ciclo, "mensal") is None

    def test_recusa_diz_o_motivo(self):
        with pytest.raises(cupons.CupomRecusado) as recusa:
            cupons.conferir(None, HOJE)
        assert recusa.value.motivo == cupons.INVALIDO

        with pytest.raises(cupons.CupomRecusado) as recusa:
            cupons.conferir(cupom(validade=HOJE - timedelta(days=1)), HOJE)
        assert recusa.value.motivo == cupons.VENCIDO

        with pytest.raises(cupons.CupomRecusado) as recusa:
            cupons.conferir(cupom(usos_max=5, usos=5), HOJE)
        assert recusa.value.motivo == cupons.ESGOTADO

    def test_vence_amanha_ainda_vale_hoje(self):
        assert cupons.conferir(cupom(validade=HOJE), HOJE) is not None


@pytest.mark.unit
class TestProporcional:
    def test_no_meio_do_ciclo_cobra_metade_da_diferenca(self):
        # Ciclo de 30 dias, 15 usados: metade da diferença entre 290 e 690.
        assert proporcional.diferenca_de_upgrade(
            valor_atual=29000,
            valor_novo=69000,
            hoje=date(2026, 8, 16),
            inicio=date(2026, 8, 1),
            fim=date(2026, 8, 31),
        ) == 20000

    def test_no_primeiro_dia_cobra_quase_tudo(self):
        assert proporcional.diferenca_de_upgrade(
            valor_atual=29000,
            valor_novo=69000,
            hoje=date(2026, 8, 1),
            inicio=date(2026, 8, 1),
            fim=date(2026, 8, 31),
        ) == 40000

    def test_no_ultimo_dia_nao_cobra(self):
        assert proporcional.diferenca_de_upgrade(
            valor_atual=29000,
            valor_novo=69000,
            hoje=date(2026, 8, 31),
            inicio=date(2026, 8, 1),
            fim=date(2026, 8, 31),
        ) == 0

    def test_descer_de_plano_nao_gera_credito(self):
        """Rebaixar no meio do ciclo e receber de volta seria arbitragem fácil."""
        assert proporcional.diferenca_de_upgrade(
            valor_atual=69000,
            valor_novo=29000,
            hoje=date(2026, 8, 16),
            inicio=date(2026, 8, 1),
            fim=date(2026, 8, 31),
        ) == 0

    def test_a_diferenca_e_sobre_a_diferenca_nao_sobre_o_plano_novo(self):
        """Cobrar o plano novo inteiro cobraria de novo os dias já pagos."""
        meio = proporcional.diferenca_de_upgrade(
            valor_atual=69000,
            valor_novo=159000,
            hoje=date(2026, 8, 16),
            inicio=date(2026, 8, 1),
            fim=date(2026, 8, 31),
        )
        assert meio == 45000
        assert meio < 159000 // 2

    def test_ciclo_sem_duracao_nao_cobra(self):
        assert proporcional.diferenca_de_upgrade(
            valor_atual=29000, valor_novo=69000, hoje=HOJE, inicio=HOJE, fim=HOJE
        ) == 0

    def test_dias_restantes_nunca_e_negativo(self):
        assert proporcional.dias_restantes(date(2026, 9, 1), date(2026, 8, 1)) == 0
