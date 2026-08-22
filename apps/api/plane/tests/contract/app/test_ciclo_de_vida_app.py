# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Cancelar, reativar, pedir reembolso — e a régua que roda sozinha (ADR 0021).

O que estes testes fixam são promessas ditas ao cliente: "o acesso vai até o
fim do ciclo pago", "os dados ficam 90 dias", "encerrar para de cobrar". Uma
frase dessas errada por um dia é cobrança indevida ou dado apagado antes da
hora.
"""

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from plane.bgtasks.faturamento_regua import avancar_regua
from plane.db.models import HistoricoDeAssinatura, Workspace
from plane.utils import regua
from plane.utils.planos import CICLO_MENSAL, PROFISSIONAL, copia_para_contrato

CANCELAR_URL = "/api/workspaces/{slug}/faturamento/cancelar/"
REATIVAR_URL = "/api/workspaces/{slug}/faturamento/reativar/"
REEMBOLSO_URL = "/api/workspaces/{slug}/faturamento/reembolso/"

HOJE = timezone.now().date()


@pytest.fixture
def session_client(create_user):
    cliente = APIClient()
    cliente.force_authenticate(user=create_user)
    return cliente


@pytest.fixture
def assinada(db, workspace, mocker):
    mocker.patch("plane.app.views.faturamento.ciclo_de_vida.cancelar_assinatura", return_value={})
    mocker.patch("plane.bgtasks.faturamento_regua.cancelar_assinatura", return_value={})
    assinatura = workspace.assinatura
    for campo, valor in copia_para_contrato(PROFISSIONAL, CICLO_MENSAL).items():
        setattr(assinatura, campo, valor)
    assinatura.status = regua.ATIVA
    assinatura.pago_ate = HOJE + timedelta(days=12)
    assinatura.asaas_subscription_id = "sub_001"
    assinatura.save()
    return assinatura


@pytest.mark.contract
class TestCancelar:
    def test_o_acesso_vai_ate_o_fim_do_ciclo_pago(self, session_client, workspace, assinada):
        resposta = session_client.post(CANCELAR_URL.format(slug=workspace.slug), {}, format="json")

        assert resposta.status_code == status.HTTP_200_OK
        assinada.refresh_from_db()
        assert assinada.status == regua.CANCELADA
        assert assinada.pago_ate == HOJE + timedelta(days=12)
        assert regua.permite_escrita(assinada.status)

    def test_a_cobranca_para_junto(self, session_client, workspace, assinada, mocker):
        parar = mocker.patch("plane.app.views.faturamento.ciclo_de_vida.cancelar_assinatura", return_value={})

        session_client.post(CANCELAR_URL.format(slug=workspace.slug), {}, format="json")

        parar.assert_called_once_with("sub_001")

    def test_se_o_asaas_recusa_nao_cancela_aqui(self, session_client, workspace, assinada, mocker):
        """Cancelar aqui e seguir cobrando lá é o defeito que vira estorno."""
        from plane.utils.asaas import ErroDoAsaas

        mocker.patch(
            "plane.app.views.faturamento.ciclo_de_vida.cancelar_assinatura",
            side_effect=ErroDoAsaas("502", status=502, corpo={}),
        )

        resposta = session_client.post(CANCELAR_URL.format(slug=workspace.slug), {}, format="json")

        assert resposta.status_code == status.HTTP_502_BAD_GATEWAY
        assinada.refresh_from_db()
        assert assinada.status == regua.ATIVA

    def test_o_motivo_fica_registrado(self, session_client, workspace, assinada):
        session_client.post(
            CANCELAR_URL.format(slug=workspace.slug), {"motivo": "Ficou caro"}, format="json"
        )

        registro = HistoricoDeAssinatura.objects.get(evento="cancelamento")
        assert registro.motivo == "Ficou caro"

    def test_cancelar_duas_vezes_nao_muda_nada(self, session_client, workspace, assinada):
        session_client.post(CANCELAR_URL.format(slug=workspace.slug), {}, format="json")

        resposta = session_client.post(CANCELAR_URL.format(slug=workspace.slug), {}, format="json")

        assert resposta.data["error_message"] == "JA_CANCELADA"


@pytest.mark.contract
class TestReativar:
    def test_dentro_do_ciclo_volta_ativa(self, session_client, workspace, assinada):
        session_client.post(CANCELAR_URL.format(slug=workspace.slug), {}, format="json")

        resposta = session_client.post(REATIVAR_URL.format(slug=workspace.slug), {}, format="json")

        assert resposta.status_code == status.HTTP_200_OK
        assinada.refresh_from_db()
        assert assinada.status == regua.ATIVA
        assert assinada.cancelada_em is None

    def test_encerrada_ha_muito_tempo_volta_lendo_e_com_por_onde_pagar(
        self, session_client, workspace, assinada
    ):
        """Voltar direto para `encerrada` faria o botão de reativar não fazer nada."""
        assinada.status = regua.ENCERRADA
        assinada.pago_ate = HOJE - timedelta(days=200)
        assinada.encerrada_em = HOJE - timedelta(days=60)
        assinada.remover_dados_em = HOJE + timedelta(days=30)
        assinada.save()

        session_client.post(REATIVAR_URL.format(slug=workspace.slug), {}, format="json")

        assinada.refresh_from_db()
        assert assinada.status == regua.RESTRITA
        assert regua.permite_leitura(assinada.status)
        assert not regua.permite_escrita(assinada.status)
        assert assinada.remover_dados_em is None

    def test_depois_da_remocao_nao_ha_o_que_recuperar(self, session_client, workspace, assinada):
        assinada.status = regua.REMOVIDA
        assinada.save()

        resposta = session_client.post(REATIVAR_URL.format(slug=workspace.slug), {}, format="json")

        assert resposta.data["error_message"] == "DADOS_REMOVIDOS"

    def test_assinatura_ativa_nao_se_reativa(self, session_client, workspace, assinada):
        resposta = session_client.post(REATIVAR_URL.format(slug=workspace.slug), {}, format="json")

        assert resposta.data["error_message"] == "NAO_ESTA_CANCELADA"


@pytest.mark.contract
class TestReembolso:
    def test_o_pedido_fica_registrado_com_motivo(self, session_client, workspace, assinada):
        resposta = session_client.post(
            REEMBOLSO_URL.format(slug=workspace.slug), {"motivo": "Não era o que eu esperava"}, format="json"
        )

        assert resposta.status_code == status.HTTP_200_OK
        assert resposta.data["dias_de_garantia"] == 30
        assert HistoricoDeAssinatura.objects.filter(evento="pedido_de_reembolso").exists()

    def test_sem_motivo_nao_registra(self, session_client, workspace, assinada):
        resposta = session_client.post(REEMBOLSO_URL.format(slug=workspace.slug), {}, format="json")

        assert resposta.data["error_message"] == "MOTIVO_OBRIGATORIO"
        assert not HistoricoDeAssinatura.objects.filter(evento="pedido_de_reembolso").exists()

    def test_pedir_reembolso_nao_encerra_sozinho(self, session_client, workspace, assinada):
        """Quem encerra é o estorno processado, que volta pelo webhook."""
        session_client.post(REEMBOLSO_URL.format(slug=workspace.slug), {"motivo": "x"}, format="json")

        assinada.refresh_from_db()
        assert assinada.status == regua.ATIVA


@pytest.mark.contract
class TestAReguaDiaria:
    def test_atrasado_ha_sete_dias_vira_restrito(self, workspace, assinada):
        assinada.pago_ate = HOJE - timedelta(days=7)
        assinada.save()

        avancar_regua()

        assinada.refresh_from_db()
        assert assinada.status == regua.RESTRITA
        assert HistoricoDeAssinatura.objects.filter(evento="regua", para=regua.RESTRITA).exists()

    def test_a_rotina_parada_uma_semana_nao_atrasa_o_bloqueio(self, workspace, assinada):
        assinada.pago_ate = HOJE - timedelta(days=20)
        assinada.save()

        avancar_regua()

        assinada.refresh_from_db()
        assert assinada.status == regua.BLOQUEADA

    def test_encerrar_para_de_cobrar_e_agenda_a_remocao(self, workspace, assinada, mocker):
        parar = mocker.patch("plane.bgtasks.faturamento_regua.cancelar_assinatura", return_value={})
        assinada.pago_ate = HOJE - timedelta(days=45)
        assinada.save()

        avancar_regua()

        assinada.refresh_from_db()
        assert assinada.status == regua.ENCERRADA
        assert assinada.encerrada_em == HOJE
        assert assinada.remover_dados_em == HOJE + timedelta(days=90)
        parar.assert_called_once_with("sub_001")

    def test_o_asaas_fora_do_ar_nao_impede_o_encerramento(self, workspace, assinada, mocker):
        from plane.utils.asaas import ErroDoAsaas

        mocker.patch(
            "plane.bgtasks.faturamento_regua.cancelar_assinatura", side_effect=ErroDoAsaas("502")
        )
        assinada.pago_ate = HOJE - timedelta(days=45)
        assinada.save()

        avancar_regua()

        assinada.refresh_from_db()
        assert assinada.status == regua.ENCERRADA

    def test_noventa_dias_depois_o_espaco_e_removido(self, workspace, assinada):
        assinada.status = regua.ENCERRADA
        assinada.encerrada_em = HOJE - timedelta(days=90)
        assinada.pago_ate = HOJE - timedelta(days=140)
        assinada.save()

        avancar_regua()

        assinada.refresh_from_db()
        assert assinada.status == regua.REMOVIDA
        assert Workspace.objects.filter(pk=workspace.id).first() is None
        assert Workspace.all_objects.filter(pk=workspace.id).exists()

    def test_no_octogesimo_nono_dia_o_espaco_continua_de_pe(self, workspace, assinada):
        assinada.status = regua.ENCERRADA
        assinada.encerrada_em = HOJE - timedelta(days=89)
        assinada.pago_ate = HOJE - timedelta(days=139)
        assinada.save()

        avancar_regua()

        assinada.refresh_from_db()
        assert assinada.status == regua.ENCERRADA
        assert Workspace.objects.filter(pk=workspace.id).exists()

    def test_quem_esta_em_dia_nao_e_tocado(self, workspace, assinada):
        resultado = avancar_regua()

        assinada.refresh_from_db()
        assert assinada.status == regua.ATIVA
        assert resultado["mudaram"] == 0
