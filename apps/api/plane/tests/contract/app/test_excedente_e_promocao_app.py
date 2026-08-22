# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Excedente, fim de promoção e os números do painel (ADR 0021).

Três rotinas que mexem em dinheiro sem ninguém olhando, e é por isso que os
testes aqui são explícitos sobre **quanto**: um excedente que cobra a mais e uma
promoção que nunca acaba são defeitos que só aparecem quando alguém soma a
receita à mão, meses depois.
"""

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from plane.bgtasks.faturamento_excedente import ajustar_excedentes
from plane.bgtasks.faturamento_promocao import encerrar_promocoes
from plane.db.models import HistoricoDeAssinatura, Workspace, WorkspaceMember
from plane.license.models import Instance, InstanceAdmin
from plane.utils import regua
from plane.utils.planos import (
    AVANCADO,
    CICLO_ANUAL,
    CICLO_MENSAL,
    ESSENCIAL,
    PROFISSIONAL,
    copia_para_contrato,
)

RESUMO_URL = "/api/instances/assinaturas/resumo/"
HOJE = timezone.now().date()


@pytest.fixture
def sem_asaas(mocker):
    """As rotinas falam com o Asaas; aqui nenhuma chamada sai da máquina."""
    return {
        "excedente": mocker.patch("plane.bgtasks.faturamento_excedente.atualizar_assinatura", return_value={}),
        "promocao": mocker.patch("plane.bgtasks.faturamento_promocao.atualizar_assinatura", return_value={}),
    }


@pytest.fixture
def assinada(db, workspace):
    assinatura = workspace.assinatura
    for campo, valor in copia_para_contrato(ESSENCIAL, CICLO_MENSAL).items():
        setattr(assinatura, campo, valor)
    assinatura.status = regua.ATIVA
    assinatura.pago_ate = HOJE + timedelta(days=10)
    assinatura.asaas_subscription_id = "sub_001"
    assinatura.save()
    return assinatura


def povoar(workspace, django_user_model, quantos, papel=15):
    for indice in range(quantos):
        membro = django_user_model.objects.create(
            email=f"pessoa{indice}-{papel}@exemplo.com", username=f"pessoa{indice}-{papel}"
        )
        WorkspaceMember.objects.create(workspace=workspace, member=membro, role=papel, is_active=True)


@pytest.mark.contract
class TestExcedente:
    def test_membro_a_mais_entra_no_valor_do_ciclo_seguinte(
        self, workspace, assinada, django_user_model, sem_asaas
    ):
        # 3 incluídos no Essencial; com o dono são 5 pessoas.
        povoar(workspace, django_user_model, 4)

        ajustar_excedentes()

        assinada.refresh_from_db()
        assert assinada.assentos_extras == 2
        # R$ 290 + 2 × R$ 90 = R$ 470,00 — mandado ao Asaas em reais.
        sem_asaas["excedente"].assert_called_once_with("sub_001", value=470.0)

    def test_a_cobranca_ja_gerada_nao_muda(self, workspace, assinada, django_user_model, sem_asaas):
        """Mudar o valor de uma cobrança que o cliente já recebeu vira contestação."""
        povoar(workspace, django_user_model, 4)

        ajustar_excedentes()

        _, argumentos = sem_asaas["excedente"].call_args
        assert "updatePendingPayments" not in argumentos

    def test_quem_cabe_no_plano_nao_e_tocado(self, workspace, assinada, sem_asaas):
        resultado = ajustar_excedentes()

        assinada.refresh_from_db()
        assert assinada.assentos_extras == 0
        assert resultado["ajustadas"] == 0
        sem_asaas["excedente"].assert_not_called()

    def test_tirar_gente_derruba_a_conta_na_mesma_rotina(
        self, workspace, assinada, django_user_model, sem_asaas
    ):
        """Contador que só sobe é contador que cobra a mais."""
        povoar(workspace, django_user_model, 4)
        ajustar_excedentes()
        WorkspaceMember.objects.filter(role=15).delete()

        ajustar_excedentes()

        assinada.refresh_from_db()
        assert assinada.assentos_extras == 0

    def test_convidado_nao_conta_como_assento(self, workspace, assinada, django_user_model, sem_asaas):
        povoar(workspace, django_user_model, 6, papel=5)

        ajustar_excedentes()

        assinada.refresh_from_db()
        assert assinada.assentos_extras == 0

    def test_cortesia_nao_gera_excedente(self, workspace, assinada, django_user_model, sem_asaas):
        """Cobrar assento extra de quem não paga assento nenhum não faz sentido."""
        assinada.status = regua.EM_CORTESIA
        assinada.save()
        povoar(workspace, django_user_model, 4)

        ajustar_excedentes()

        assinada.refresh_from_db()
        assert assinada.assentos_extras == 0

    def test_o_ajuste_fica_no_historico_com_o_valor_novo(
        self, workspace, assinada, django_user_model, sem_asaas
    ):
        povoar(workspace, django_user_model, 4)

        ajustar_excedentes()

        linha = HistoricoDeAssinatura.objects.get(evento="excedente")
        assert linha.de == "0"
        assert linha.para == "2"
        assert "470" in linha.motivo

    def test_o_asaas_fora_do_ar_nao_desfaz_o_ajuste(self, workspace, assinada, django_user_model, mocker):
        from plane.utils.asaas import ErroDoAsaas

        mocker.patch(
            "plane.bgtasks.faturamento_excedente.atualizar_assinatura", side_effect=ErroDoAsaas("502")
        )
        povoar(workspace, django_user_model, 4)

        ajustar_excedentes()

        assinada.refresh_from_db()
        assert assinada.assentos_extras == 2


@pytest.mark.contract
class TestFimDaPromocao:
    def test_cupom_vencido_devolve_o_preco_cheio(self, workspace, assinada, sem_asaas):
        """Sem esta rotina, 100% de desconto é grátis para sempre, em silêncio."""
        assinada.valor_base = 0
        assinada.promocao_termina_em = HOJE
        assinada.save()

        encerrar_promocoes()

        assinada.refresh_from_db()
        assert assinada.valor_base == 29000
        assert assinada.promocao_termina_em is None
        sem_asaas["promocao"].assert_called_once_with("sub_001", value=290.0)

    def test_promocao_futura_nao_e_tocada(self, workspace, assinada, sem_asaas):
        assinada.valor_base = 14500
        assinada.promocao_termina_em = HOJE + timedelta(days=5)
        assinada.save()

        resultado = encerrar_promocoes()

        assinada.refresh_from_db()
        assert assinada.valor_base == 14500
        assert resultado["encerradas"] == 0

    def test_o_excedente_continua_valendo_no_preco_de_volta(self, workspace, assinada, sem_asaas):
        assinada.valor_base = 0
        assinada.assentos_extras = 2
        assinada.promocao_termina_em = HOJE
        assinada.save()

        encerrar_promocoes()

        # R$ 290 do plano + 2 × R$ 90 dos assentos extras.
        sem_asaas["promocao"].assert_called_once_with("sub_001", value=470.0)

    def test_o_fim_fica_no_historico(self, workspace, assinada, sem_asaas):
        assinada.valor_base = 0
        assinada.promocao_termina_em = HOJE
        assinada.save()

        encerrar_promocoes()

        assert HistoricoDeAssinatura.objects.filter(evento="fim_da_promocao").exists()


@pytest.mark.contract
class TestResumoDoFaturamento:
    @pytest.fixture
    def admin_da_instancia(self, db, create_user):
        instancia = Instance.objects.create(
            instance_name="QooWork",
            instance_id="teste",
            current_version="1.0.0",
            last_checked_at=timezone.now(),
        )
        InstanceAdmin.objects.create(instance=instancia, user=create_user, role=20)
        cliente = APIClient()
        cliente.force_authenticate(user=create_user)
        return cliente

    def _espaco(self, create_user, nome, plano, ciclo, estado, extras=0):
        espaco = Workspace.objects.create(name=nome, slug=nome.lower(), owner=create_user)
        assinatura = espaco.assinatura
        for campo, valor in copia_para_contrato(plano, ciclo).items():
            setattr(assinatura, campo, valor)
        assinatura.status = estado
        assinatura.assentos_extras = extras
        assinatura.save()
        return assinatura

    def test_a_receita_e_mensalizada(self, admin_da_instancia, create_user, workspace):
        """Um anual de R$ 6.900 é R$ 690 de receita recorrente mensal, não R$ 6.900."""
        self._espaco(create_user, "mensal", PROFISSIONAL, CICLO_MENSAL, regua.ATIVA)
        self._espaco(create_user, "anual", PROFISSIONAL, CICLO_ANUAL, regua.ATIVA)

        resposta = admin_da_instancia.get(RESUMO_URL)

        assert resposta.status_code == status.HTTP_200_OK
        assert resposta.data["receita_recorrente_mensal"] == 69000 + 69000

    def test_o_excedente_entra_na_receita(self, admin_da_instancia, create_user, workspace):
        self._espaco(create_user, "cheio", ESSENCIAL, CICLO_MENSAL, regua.ATIVA, extras=3)

        resposta = admin_da_instancia.get(RESUMO_URL)

        # R$ 290 + 3 × R$ 90.
        assert resposta.data["receita_recorrente_mensal"] == 29000 + 27000
        assert resposta.data["excedentes"] == 1

    def test_cortesia_nao_infla_a_receita(self, admin_da_instancia, create_user, workspace):
        cortesia = self._espaco(create_user, "cortesia", AVANCADO, CICLO_MENSAL, regua.EM_CORTESIA)
        cortesia.valor_base = 0
        cortesia.save()
        self._espaco(create_user, "pagante", ESSENCIAL, CICLO_MENSAL, regua.ATIVA)

        resposta = admin_da_instancia.get(RESUMO_URL)

        assert resposta.data["receita_recorrente_mensal"] == 29000
        assert resposta.data["assinaturas_cobrando"] == 1
        # Dois no Avançado: o que este teste criou e o do fixture `workspace`,
        # que nasce na cortesia de transição — no plano maior, com preço zero.
        # A distribuição por plano conta contrato; a receita, dinheiro.
        assert resposta.data["por_plano"][AVANCADO] == 2

    def test_a_inadimplencia_conta_atrasado_restrito_e_bloqueado(
        self, admin_da_instancia, create_user, workspace
    ):
        self._espaco(create_user, "emdia", ESSENCIAL, CICLO_MENSAL, regua.ATIVA)
        self._espaco(create_user, "atrasado", ESSENCIAL, CICLO_MENSAL, regua.ATRASADA)
        self._espaco(create_user, "restrito", ESSENCIAL, CICLO_MENSAL, regua.RESTRITA)
        self._espaco(create_user, "bloqueado", ESSENCIAL, CICLO_MENSAL, regua.BLOQUEADA)
        self._espaco(create_user, "cancelado", ESSENCIAL, CICLO_MENSAL, regua.CANCELADA)

        resposta = admin_da_instancia.get(RESUMO_URL)

        assert resposta.data["assinaturas_cobrando"] == 4
        assert resposta.data["inadimplentes"] == 3

    def test_conta_as_promocoes_da_semana(self, admin_da_instancia, create_user, workspace):
        perto = self._espaco(create_user, "perto", ESSENCIAL, CICLO_MENSAL, regua.ATIVA)
        perto.promocao_termina_em = HOJE + timedelta(days=3)
        perto.save()
        longe = self._espaco(create_user, "longe", ESSENCIAL, CICLO_MENSAL, regua.ATIVA)
        longe.promocao_termina_em = HOJE + timedelta(days=40)
        longe.save()

        resposta = admin_da_instancia.get(RESUMO_URL)

        assert resposta.data["promocoes_a_vencer"] == 1
