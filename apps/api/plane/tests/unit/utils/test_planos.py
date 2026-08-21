# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""O catálogo de planos é testado porque é onde o preço mora (ADR 0021).

Tabela de preço incoerente não quebra nada: ela roda, cobra, e só aparece na
reunião em que alguém percebe que esticar o plano pequeno saía mais barato que
subir. Estes testes são o lugar onde isso aparece antes.

Os números da régua estão escritos aqui **na mão**, e não derivados do catálogo:
um teste que recalcula o que o código calcula concorda com o código sempre,
inclusive quando os dois estão errados.
"""

import pytest

from plane.utils import planos
from plane.utils.planos import (
    AVANCADO,
    CICLO_ANUAL,
    CICLO_MENSAL,
    ESSENCIAL,
    LIMITE_AUTOMACOES,
    LIMITE_PROPRIEDADES,
    MESES_DO_CICLO_ANUAL,
    PROFISSIONAL,
    RECURSO_ANALYTICS,
    RECURSO_API_PUBLICA,
    RECURSO_WEBHOOKS,
)


@pytest.mark.unit
class TestOsPrecos:
    def test_os_valores_publicados(self):
        assert planos.plano(ESSENCIAL).mensal == 29000
        assert planos.plano(PROFISSIONAL).mensal == 69000
        assert planos.plano(AVANCADO).mensal == 159000

    def test_os_assentos_incluidos(self):
        assert planos.plano(ESSENCIAL).assentos == 3
        assert planos.plano(PROFISSIONAL).assentos == 10
        assert planos.plano(AVANCADO).assentos == 30

    def test_o_anual_custa_dez_mensalidades(self):
        """Dois meses grátis — a âncora do mercado brasileiro."""
        assert MESES_DO_CICLO_ANUAL == 10
        for chave in planos.ORDEM:
            escolhido = planos.plano(chave)
            assert escolhido.anual == escolhido.mensal * 10
            assert escolhido.adicional_anual == escolhido.adicional_mensal * 10


@pytest.mark.unit
class TestARegua:
    """As duas regras que fazem a escada empurrar em vez de decorar."""

    def test_esticar_o_essencial_custa_mais_que_subir(self):
        # 3 assentos + 7 adicionais = 10, que é o teto do Profissional.
        esticado = 29000 + 9000 * 7
        assert esticado == 92000
        assert esticado > 69000

    def test_esticar_o_profissional_custa_mais_que_subir(self):
        # 10 assentos + 20 adicionais = 30, que é o teto do Avançado.
        esticado = 69000 + 6500 * 20
        assert esticado == 199000
        assert esticado > 159000

    def test_o_cruzamento_do_essencial_acontece_na_oitava_pessoa(self):
        """Com 8 pessoas o plano do meio já é mais barato — e traz mais."""
        assert 29000 + 9000 * 4 == 65000  # 7 pessoas: ainda vale ficar
        assert 29000 + 9000 * 4 < 69000
        assert 29000 + 9000 * 5 == 74000  # 8 pessoas: passou
        assert 29000 + 9000 * 5 > 69000

    def test_o_cruzamento_do_profissional_acontece_na_vigesima_quarta(self):
        assert 69000 + 6500 * 13 < 159000  # 23 pessoas
        assert 69000 + 6500 * 14 > 159000  # 24 pessoas

    def test_o_assento_fica_mais_barato_a_cada_nivel(self):
        assert planos.plano(ESSENCIAL).por_assento == 9666
        assert planos.plano(PROFISSIONAL).por_assento == 6900
        assert planos.plano(AVANCADO).por_assento == 5300

    def test_o_adicional_fica_mais_barato_a_cada_nivel(self):
        assert planos.plano(ESSENCIAL).adicional_mensal == 9000
        assert planos.plano(PROFISSIONAL).adicional_mensal == 6500
        assert planos.plano(AVANCADO).adicional_mensal == 4900

    def test_o_adicional_e_menor_que_o_assento_do_proprio_plano(self):
        """A plataforma já está paga; o que entra é gente."""
        for chave in planos.ORDEM:
            escolhido = planos.plano(chave)
            assert escolhido.adicional_mensal < escolhido.por_assento

    def test_o_catalogo_publicado_nao_tem_incoerencia(self):
        assert planos.incoerencias() == []


@pytest.mark.unit
class TestAConferenciaEnxerga:
    """A conferência precisa acusar catálogo quebrado — senão não é conferência.

    Cada caso muda **um** número e confere que a mensagem correspondente
    aparece. Vale notar que as regras se tocam: um preço por assento fora da
    ordem também derruba o funil, e é matematicamente impossível quebrar uma
    sem a outra. Por isso a asserção procura a mensagem que interessa, em vez
    de exigir que exista uma só.
    """

    def _trocar(self, monkeypatch, chave, **campos):
        from dataclasses import replace

        monkeypatch.setitem(planos.PLANOS, chave, replace(planos.PLANOS[chave], **campos))

    def test_acusa_quando_esticar_fica_mais_barato_que_subir(self, monkeypatch):
        # Adicional de R$ 50: 29000 + 5000×7 = 64000, abaixo dos 69000.
        self._trocar(monkeypatch, ESSENCIAL, adicional_mensal=5000)
        problemas = planos.incoerencias()
        assert any("acumular excedente ficou mais barato que subir" in p for p in problemas)

    def test_acusa_quando_o_assento_do_plano_maior_nao_e_mais_barato(self, monkeypatch):
        # 30 assentos por R$ 2.400 dá R$ 80 o assento, acima dos R$ 69 do meio.
        self._trocar(monkeypatch, AVANCADO, mensal=240000)
        problemas = planos.incoerencias()
        assert any("não é mais barato" in p and "Avançado" in p for p in problemas)

    def test_acusa_quando_o_adicional_do_plano_maior_sobe(self, monkeypatch):
        self._trocar(monkeypatch, PROFISSIONAL, adicional_mensal=9500)
        problemas = planos.incoerencias()
        assert any("adicional do Profissional" in p for p in problemas)


@pytest.mark.unit
class TestRecursosELimites:
    def test_o_essencial_nao_inclui_nenhum_dos_tres_recursos(self):
        essencial = planos.plano(ESSENCIAL)
        assert not essencial.inclui(RECURSO_ANALYTICS)
        assert not essencial.inclui(RECURSO_API_PUBLICA)
        assert not essencial.inclui(RECURSO_WEBHOOKS)

    def test_profissional_e_avancado_liberam_o_mesmo(self):
        """O Avançado vende escala, não funcionalidade (ADR 0021)."""
        assert planos.plano(PROFISSIONAL).recursos == planos.plano(AVANCADO).recursos
        assert planos.plano(PROFISSIONAL).limites == planos.plano(AVANCADO).limites

    def test_os_tetos_por_plano(self):
        assert planos.plano(ESSENCIAL).teto(LIMITE_PROPRIEDADES) == 5
        assert planos.plano(PROFISSIONAL).teto(LIMITE_PROPRIEDADES) == 30
        assert planos.plano(ESSENCIAL).teto(LIMITE_AUTOMACOES) == 2
        # `None` é sem teto, e é diferente de zero, que seria "nenhuma".
        assert planos.plano(PROFISSIONAL).teto(LIMITE_AUTOMACOES) is None

    def test_planos_com_diz_onde_esta_o_recurso(self):
        """Recusar sem dizer onde encontrar transforma a trava em parede."""
        assert planos.planos_com(RECURSO_ANALYTICS) == (PROFISSIONAL, AVANCADO)

    def test_planos_com_recusa_recurso_desconhecido(self):
        with pytest.raises(ValueError, match="Recurso desconhecido"):
            planos.planos_com("telepatia")


@pytest.mark.unit
class TestConvidados:
    def test_o_essencial_nao_tem_convidado(self):
        assert planos.convidados_permitidos(ESSENCIAL, assentos_pagos=3) == 0

    def test_a_cota_e_multiplo_dos_assentos_pagos(self):
        assert planos.convidados_permitidos(PROFISSIONAL, assentos_pagos=10) == 20
        assert planos.convidados_permitidos(AVANCADO, assentos_pagos=30) == 150

    def test_assento_extra_aumenta_a_cota(self):
        assert planos.convidados_permitidos(PROFISSIONAL, assentos_pagos=12) == 24

    def test_recusa_assento_negativo(self):
        with pytest.raises(ValueError):
            planos.convidados_permitidos(PROFISSIONAL, assentos_pagos=-1)


@pytest.mark.unit
class TestValorDoCiclo:
    def test_sem_excedente_e_o_preco_do_plano(self):
        assert planos.valor_do_ciclo(PROFISSIONAL, CICLO_MENSAL) == 69000
        assert planos.valor_do_ciclo(PROFISSIONAL, CICLO_ANUAL) == 690000

    def test_com_excedente_soma_o_adicional(self):
        assert planos.valor_do_ciclo(PROFISSIONAL, CICLO_MENSAL, assentos_extras=3) == 69000 + 19500
        assert planos.valor_do_ciclo(PROFISSIONAL, CICLO_ANUAL, assentos_extras=3) == 690000 + 195000

    def test_recusa_ciclo_desconhecido(self):
        with pytest.raises(ValueError, match="Ciclo desconhecido"):
            planos.valor_do_ciclo(PROFISSIONAL, "quinzenal")

    def test_recusa_excedente_negativo(self):
        with pytest.raises(ValueError):
            planos.valor_do_ciclo(PROFISSIONAL, CICLO_MENSAL, assentos_extras=-1)


@pytest.mark.unit
class TestNavegacao:
    def test_seguinte_sobe_um_degrau(self):
        assert planos.seguinte(ESSENCIAL).chave == PROFISSIONAL
        assert planos.seguinte(PROFISSIONAL).chave == AVANCADO

    def test_no_topo_nao_ha_seguinte(self):
        assert planos.seguinte(AVANCADO) is None

    def test_plano_desconhecido_diz_quais_existem(self):
        with pytest.raises(ValueError) as erro:
            planos.plano("premium")
        assert "essencial" in str(erro.value)

    def test_existe(self):
        assert planos.existe(ESSENCIAL)
        assert not planos.existe("premium")
