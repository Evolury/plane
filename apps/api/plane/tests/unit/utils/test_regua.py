# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""A régua da assinatura, dia a dia (ADR 0021).

O que estes testes protegem não é a aritmética: é a promessa. "Somente leitura
no sétimo dia" e "bloqueado no décimo quinto" são frases ditas ao cliente, e
uma frase dessas errada por um dia é cobrança indevida de acesso.

Nada aqui toca banco. A régua recebe datas e devolve uma palavra — e é isso que
permite percorrer sessenta dias de atraso num teste que roda em milissegundos.
"""

from datetime import date, timedelta

import pytest

from plane.utils import regua

HOJE = date(2026, 8, 21)


def vencido_ha(dias: int) -> date:
    """A data de `pago_ate` para quem está `dias` dias em atraso hoje."""
    return HOJE - timedelta(days=dias)


@pytest.mark.unit
class TestDiasDeAtraso:
    def test_em_dia_nao_tem_atraso(self):
        assert regua.dias_de_atraso(HOJE, HOJE) == 0
        assert regua.dias_de_atraso(HOJE + timedelta(days=10), HOJE) == 0

    def test_o_dia_seguinte_ao_vencimento_e_o_primeiro(self):
        assert regua.dias_de_atraso(vencido_ha(1), HOJE) == 1

    def test_sem_data_nao_ha_atraso_a_calcular(self):
        assert regua.dias_de_atraso(None, HOJE) == 0


@pytest.mark.unit
class TestAEscada:
    """Os degraus, exatamente onde foram prometidos."""

    @pytest.mark.parametrize(
        "atraso,esperado",
        [
            (0, regua.ATIVA),
            (1, regua.ATRASADA),
            (6, regua.ATRASADA),
            (7, regua.RESTRITA),
            (14, regua.RESTRITA),
            (15, regua.BLOQUEADA),
            (44, regua.BLOQUEADA),
            (45, regua.ENCERRADA),
        ],
    )
    def test_cada_degrau(self, atraso, esperado):
        assert (
            regua.estado_de_hoje(estado=regua.ATIVA, pago_ate=vencido_ha(atraso), hoje=HOJE) == esperado
        )

    def test_o_sexto_dia_ainda_escreve_e_o_setimo_nao(self):
        """A fronteira que o cliente sente — vale escrever nos dois lados."""
        assert regua.permite_escrita(regua.estado_de_hoje(estado=regua.ATIVA, pago_ate=vencido_ha(6), hoje=HOJE))
        assert not regua.permite_escrita(regua.estado_de_hoje(estado=regua.ATIVA, pago_ate=vencido_ha(7), hoje=HOJE))

    def test_o_atraso_recente_nao_restringe_nada(self):
        """O Asaas ainda está tentando o cartão: cinco vezes em ~3 dias."""
        for atraso in (1, 2, 3):
            estado = regua.estado_de_hoje(estado=regua.ATIVA, pago_ate=vencido_ha(atraso), hoje=HOJE)
            assert estado == regua.ATRASADA
            assert regua.permite_escrita(estado)

    def test_a_rotina_parada_uma_semana_nao_atrasa_a_regua(self):
        """Estado que depende de a rotina ter rodado todo dia mente quando ela falha."""
        assert (
            regua.estado_de_hoje(estado=regua.ATRASADA, pago_ate=vencido_ha(60), hoje=HOJE) == regua.ENCERRADA
        )
        assert (
            regua.estado_de_hoje(estado=regua.ATRASADA, pago_ate=vencido_ha(20), hoje=HOJE) == regua.BLOQUEADA
        )

    def test_pagar_devolve_o_acesso(self):
        """Pagou, `pago_ate` andou: a régua não guarda rancor."""
        futuro = HOJE + timedelta(days=30)
        for anterior in (regua.ATRASADA, regua.RESTRITA, regua.BLOQUEADA):
            assert regua.estado_de_hoje(estado=anterior, pago_ate=futuro, hoje=HOJE) == regua.ATIVA


@pytest.mark.unit
class TestCortesia:
    def test_cortesia_valida_continua_cortesia(self):
        """E não vira `ativa`: quem não pagou não passa a constar como pagante."""
        futuro = HOJE + timedelta(days=30)
        assert regua.estado_de_hoje(estado=regua.EM_CORTESIA, pago_ate=futuro, hoje=HOJE) == regua.EM_CORTESIA

    def test_cortesia_vencida_entra_na_mesma_escada(self):
        assert (
            regua.estado_de_hoje(estado=regua.EM_CORTESIA, pago_ate=vencido_ha(1), hoje=HOJE) == regua.ATRASADA
        )
        assert (
            regua.estado_de_hoje(estado=regua.EM_CORTESIA, pago_ate=vencido_ha(9), hoje=HOJE) == regua.RESTRITA
        )

    def test_a_cortesia_de_transicao_dura_noventa_dias(self):
        assert regua.DIAS_DE_CORTESIA_DE_TRANSICAO == 90
        assert regua.fim_da_cortesia_de_transicao(HOJE) == date(2026, 11, 19)


@pytest.mark.unit
class TestCancelamento:
    def test_cancelar_mantem_o_ciclo_pago(self):
        futuro = HOJE + timedelta(days=10)
        assert regua.estado_de_hoje(estado=regua.CANCELADA, pago_ate=futuro, hoje=HOJE) == regua.CANCELADA
        assert regua.permite_escrita(regua.CANCELADA)

    def test_no_ultimo_dia_do_ciclo_ainda_ha_acesso(self):
        assert regua.estado_de_hoje(estado=regua.CANCELADA, pago_ate=HOJE, hoje=HOJE) == regua.CANCELADA

    def test_passado_o_ciclo_encerra(self):
        assert regua.estado_de_hoje(estado=regua.CANCELADA, pago_ate=vencido_ha(1), hoje=HOJE) == regua.ENCERRADA

    def test_cancelar_sem_ciclo_pago_encerra_na_hora(self):
        assert regua.estado_de_hoje(estado=regua.CANCELADA, pago_ate=None, hoje=HOJE) == regua.ENCERRADA


@pytest.mark.unit
class TestRetencao:
    def test_a_remocao_e_noventa_dias_depois_de_encerrar(self):
        assert regua.DIAS_DE_RETENCAO == 90
        assert regua.data_de_remocao(date(2026, 8, 21)) == date(2026, 11, 19)

    def test_no_octogesimo_nono_dia_os_dados_ainda_existem(self):
        encerrada = HOJE - timedelta(days=89)
        assert (
            regua.estado_de_hoje(estado=regua.ENCERRADA, pago_ate=None, hoje=HOJE, encerrada_em=encerrada)
            == regua.ENCERRADA
        )

    def test_no_nonagesimo_os_dados_vao_embora(self):
        encerrada = HOJE - timedelta(days=90)
        assert (
            regua.estado_de_hoje(estado=regua.ENCERRADA, pago_ate=None, hoje=HOJE, encerrada_em=encerrada)
            == regua.REMOVIDA
        )

    def test_encerrada_sem_data_nao_remove_nada(self):
        """Sem saber quando encerrou, a régua não apaga por conta própria."""
        assert (
            regua.estado_de_hoje(estado=regua.ENCERRADA, pago_ate=None, hoje=HOJE) == regua.ENCERRADA
        )


@pytest.mark.unit
class TestEstadosQueNaoSeMovem:
    @pytest.mark.parametrize("estado", [regua.SEM_ASSINATURA, regua.REMOVIDA])
    def test_parados(self, estado):
        assert regua.estado_de_hoje(estado=estado, pago_ate=vencido_ha(500), hoje=HOJE) == estado

    def test_ativa_sem_prazo_nao_vira_nada(self):
        """Dado incompleto não é caso a adivinhar: a régua não inventa prazo."""
        assert regua.estado_de_hoje(estado=regua.ATIVA, pago_ate=None, hoje=HOJE) == regua.ATIVA

    def test_estado_desconhecido_e_erro(self):
        with pytest.raises(ValueError, match="Estado desconhecido"):
            regua.estado_de_hoje(estado="suspensa", pago_ate=HOJE, hoje=HOJE)


@pytest.mark.unit
class TestQuemEscreveEQuemLe:
    @pytest.mark.parametrize(
        "estado,escreve,le",
        [
            (regua.SEM_ASSINATURA, False, True),
            (regua.EM_CORTESIA, True, True),
            (regua.ATIVA, True, True),
            (regua.ATRASADA, True, True),
            (regua.RESTRITA, False, True),
            (regua.BLOQUEADA, False, True),
            (regua.CANCELADA, True, True),
            (regua.ENCERRADA, False, False),
            (regua.REMOVIDA, False, False),
        ],
    )
    def test_a_tabela_inteira(self, estado, escreve, le):
        assert regua.permite_escrita(estado) is escreve
        assert regua.permite_leitura(estado) is le

    def test_bloqueado_ainda_le_porque_ainda_exporta(self):
        """É o que torna o bloqueio defensável — ver ADR 0021."""
        assert regua.permite_leitura(regua.BLOQUEADA)
        assert not regua.permite_escrita(regua.BLOQUEADA)

    def test_todos_os_estados_estao_classificados(self):
        for estado in regua.ESTADOS:
            assert isinstance(regua.permite_escrita(estado), bool)
            assert isinstance(regua.permite_leitura(estado), bool)


@pytest.mark.unit
class TestProximoMarco:
    def test_em_dia_o_proximo_aperto_e_a_restricao(self):
        assert regua.proximo_marco(estado=regua.ATIVA, pago_ate=HOJE, hoje=HOJE) == (
            HOJE + timedelta(days=7),
            regua.RESTRITA,
        )

    def test_ja_restrito_o_proximo_e_o_bloqueio(self):
        pago_ate = vencido_ha(8)
        assert regua.proximo_marco(estado=regua.RESTRITA, pago_ate=pago_ate, hoje=HOJE) == (
            pago_ate + timedelta(days=15),
            regua.BLOQUEADA,
        )

    def test_depois_do_encerramento_nao_ha_mais_marco(self):
        assert regua.proximo_marco(estado=regua.BLOQUEADA, pago_ate=vencido_ha(50), hoje=HOJE) is None

    def test_estados_sem_ciclo_nao_tem_marco(self):
        assert regua.proximo_marco(estado=regua.SEM_ASSINATURA, pago_ate=HOJE, hoje=HOJE) is None
        assert regua.proximo_marco(estado=regua.ENCERRADA, pago_ate=HOJE, hoje=HOJE) is None
