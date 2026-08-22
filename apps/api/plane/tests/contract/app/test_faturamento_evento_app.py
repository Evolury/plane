# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""O que cada evento do Asaas faz com a assinatura (ADR 0021).

Duas regras atravessam o arquivo inteiro:

1. **O estado sai da cobrança**, porque o Asaas não tem webhook de assinatura
   para pagamento.
2. **O que não é nosso é ignorado, e ignorar não é falhar.** A conta atende
   outros negócios da Evolury — 9 assinaturas e 259 cobranças que não são do
   QooWork, medidas em 21/08/2026.
"""

from datetime import date, timedelta

import pytest
from django.core.cache import cache
from django.utils import timezone

from plane.bgtasks.faturamento_conciliacao import (
    CHAVE_DO_ALARME,
    CHAVE_DO_ULTIMO_EVENTO,
    alarme_de_silencio_do_asaas,
    conciliar_assinaturas,
)
from plane.bgtasks.faturamento_evento import processar_evento_do_asaas
from plane.db.models import Cobranca, EventoAsaas, HistoricoDeAssinatura
from plane.utils import regua
from plane.utils.asaas import ErroDoAsaas, referencia_de
from plane.utils.planos import CICLO_MENSAL, PROFISSIONAL, copia_para_contrato

ASSINATURA_NO_ASAAS = "sub_qoowork_001"


@pytest.fixture
def assinatura(db, workspace):
    assinatura = workspace.assinatura
    for campo, valor in copia_para_contrato(PROFISSIONAL, CICLO_MENSAL).items():
        setattr(assinatura, campo, valor)
    assinatura.status = regua.ATIVA
    assinatura.pago_ate = date(2026, 8, 22)
    assinatura.asaas_subscription_id = ASSINATURA_NO_ASAAS
    assinatura.save()
    return assinatura


def guardar(tipo, objeto, identificador="evt_001", chave="payment"):
    return EventoAsaas.objects.create(
        asaas_event_id=identificador,
        tipo=tipo,
        payload={"id": identificador, "event": tipo, chave: objeto},
    )


def cobranca(**campos):
    padrao = {
        "object": "payment",
        "id": "pay_001",
        "subscription": ASSINATURA_NO_ASAAS,
        "status": "CONFIRMED",
        "billingType": "PIX",
        "value": 690.0,
        "dueDate": "2026-08-22",
        "invoiceUrl": "https://www.asaas.com/i/exemplo",
    }
    padrao.update(campos)
    return padrao


@pytest.mark.contract
class TestPagamento:
    def test_pagamento_confirmado_estende_o_ciclo(self, assinatura):
        evento = guardar("PAYMENT_CONFIRMED", cobranca())

        processar_evento_do_asaas(str(evento.id))

        assinatura.refresh_from_db()
        evento.refresh_from_db()
        assert evento.resultado == "aplicado"
        assert evento.processado_em is not None
        assert assinatura.status == regua.ATIVA
        # Vencimento pago em 22/08 num ciclo mensal: em dia até 22/09.
        assert assinatura.pago_ate == date(2026, 9, 22)
        assert assinatura.proxima_cobranca_em == date(2026, 9, 22)

    def test_a_cobranca_vira_historico_da_tela(self, assinatura):
        evento = guardar("PAYMENT_CONFIRMED", cobranca())

        processar_evento_do_asaas(str(evento.id))

        guardada = Cobranca.objects.get(asaas_payment_id="pay_001")
        assert guardada.assinatura_id == assinatura.id
        assert guardada.valor == 69000
        assert guardada.forma == "PIX"
        assert guardada.link.endswith("/exemplo")

    def test_espaco_atrasado_volta_a_escrever_ao_pagar(self, assinatura):
        assinatura.status = regua.RESTRITA
        assinatura.save()
        evento = guardar("PAYMENT_RECEIVED", cobranca(status="RECEIVED", paymentDate="2026-08-22"))

        processar_evento_do_asaas(str(evento.id))

        assinatura.refresh_from_db()
        assert assinatura.status == regua.ATIVA
        assert regua.permite_escrita(assinatura.status)

    def test_cancelada_que_paga_continua_cancelada(self, assinatura):
        """Ela já disse que não renova: pagar a última cobrança não desdiz isso."""
        assinatura.status = regua.CANCELADA
        assinatura.save()
        evento = guardar("PAYMENT_CONFIRMED", cobranca())

        processar_evento_do_asaas(str(evento.id))

        assinatura.refresh_from_db()
        assert assinatura.status == regua.CANCELADA

    def test_cobranca_repetida_atualiza_em_vez_de_duplicar(self, assinatura):
        processar_evento_do_asaas(str(guardar("PAYMENT_CREATED", cobranca(status="PENDING")).id))
        processar_evento_do_asaas(
            str(guardar("PAYMENT_CONFIRMED", cobranca(), identificador="evt_002").id)
        )

        assert Cobranca.objects.filter(asaas_payment_id="pay_001").count() == 1
        assert Cobranca.objects.get(asaas_payment_id="pay_001").status == "CONFIRMED"


@pytest.mark.contract
class TestEstornoECancelamento:
    def test_estorno_encerra_e_agenda_a_remocao(self, assinatura):
        evento = guardar("PAYMENT_REFUNDED", cobranca(status="REFUNDED"))

        processar_evento_do_asaas(str(evento.id))

        assinatura.refresh_from_db()
        assert assinatura.status == regua.ENCERRADA
        assert assinatura.encerrada_em == timezone.now().date()
        assert assinatura.remover_dados_em == regua.data_de_remocao(timezone.now().date())

    def test_cancelar_no_asaas_honra_o_ciclo_pago(self, assinatura):
        evento = guardar(
            "SUBSCRIPTION_DELETED",
            {"object": "subscription", "id": ASSINATURA_NO_ASAAS},
            chave="subscription",
        )

        processar_evento_do_asaas(str(evento.id))

        assinatura.refresh_from_db()
        assert assinatura.status == regua.CANCELADA
        assert assinatura.pago_ate == date(2026, 8, 22)
        assert regua.permite_escrita(assinatura.status)


@pytest.mark.contract
class TestOQueNaoENosso:
    def test_cobranca_de_outro_negocio_e_ignorada(self, assinatura):
        evento = guardar("PAYMENT_CONFIRMED", cobranca(subscription="sub_de_outro_negocio"))

        processar_evento_do_asaas(str(evento.id))

        evento.refresh_from_db()
        assinatura.refresh_from_db()
        assert evento.resultado == "ignorado"
        assert evento.erro == ""
        assert assinatura.pago_ate == date(2026, 8, 22)
        assert Cobranca.objects.count() == 0

    def test_referencia_de_outro_sistema_nao_serve(self, assinatura):
        """Há assinatura na conta com UUID puro no `externalReference`."""
        evento = guardar(
            "PAYMENT_CONFIRMED",
            cobranca(subscription=None, externalReference="7dcf92dd-3b07-4107-a524-938b4b618353"),
        )

        processar_evento_do_asaas(str(evento.id))

        evento.refresh_from_db()
        assert evento.resultado == "ignorado"

    def test_a_referencia_com_prefixo_acha_o_espaco(self, assinatura, workspace):
        assinatura.asaas_subscription_id = ""
        assinatura.save()
        evento = guardar(
            "PAYMENT_CONFIRMED",
            cobranca(subscription=None, externalReference=referencia_de(workspace.id)),
        )

        processar_evento_do_asaas(str(evento.id))

        evento.refresh_from_db()
        assinatura.refresh_from_db()
        assert evento.resultado == "aplicado"
        assert assinatura.pago_ate == date(2026, 9, 22)


@pytest.mark.contract
class TestFalhaNoProcessamento:
    def test_erro_fica_registrado_e_nao_explode(self, assinatura, mocker):
        """A resposta ao Asaas já foi 200: falhar aqui é assunto nosso."""
        mocker.patch(
            "plane.bgtasks.faturamento_evento.aplicar", side_effect=RuntimeError("banco fora do ar")
        )
        evento = guardar("PAYMENT_CONFIRMED", cobranca())

        processar_evento_do_asaas(str(evento.id))

        evento.refresh_from_db()
        assert evento.resultado == "erro"
        assert "banco fora do ar" in evento.erro
        assert evento.tentativas == 1
        # Não marcado como processado: continua elegível para reprocessamento.
        assert evento.processado_em is None

    def test_evento_ja_processado_nao_roda_de_novo(self, assinatura):
        evento = guardar("PAYMENT_CONFIRMED", cobranca())
        processar_evento_do_asaas(str(evento.id))
        assinatura.refresh_from_db()
        primeiro_pago_ate = assinatura.pago_ate

        processar_evento_do_asaas(str(evento.id))

        assinatura.refresh_from_db()
        assert assinatura.pago_ate == primeiro_pago_ate


@pytest.mark.contract
class TestConciliacao:
    def test_corrige_a_proxima_cobranca(self, assinatura, mocker):
        mocker.patch(
            "plane.bgtasks.faturamento_conciliacao.buscar_assinatura",
            return_value={"status": "ACTIVE", "nextDueDate": "2026-10-05", "value": 690.0},
        )

        resultado = conciliar_assinaturas()

        assinatura.refresh_from_db()
        assert resultado["corrigidas"] == 1
        assert assinatura.proxima_cobranca_em == date(2026, 10, 5)
        assert HistoricoDeAssinatura.objects.filter(evento="conciliacao").exists()

    def test_nao_devolve_acesso_a_quem_nao_pagou(self, assinatura, mocker):
        """"ACTIVE" no Asaas quer dizer que a assinatura existe, não que está paga."""
        assinatura.status = regua.RESTRITA
        assinatura.save()
        mocker.patch(
            "plane.bgtasks.faturamento_conciliacao.buscar_assinatura",
            return_value={"status": "ACTIVE", "nextDueDate": "2026-08-22", "value": 690.0},
        )

        conciliar_assinaturas()

        assinatura.refresh_from_db()
        assert assinatura.status == regua.RESTRITA

    def test_inativada_no_painel_vira_cancelada_aqui(self, assinatura, mocker):
        mocker.patch(
            "plane.bgtasks.faturamento_conciliacao.buscar_assinatura",
            return_value={"status": "INACTIVE", "nextDueDate": "2026-08-22", "value": 690.0},
        )

        conciliar_assinaturas()

        assinatura.refresh_from_db()
        assert assinatura.status == regua.CANCELADA

    def test_asaas_fora_do_ar_nao_derruba_a_rotina(self, assinatura, mocker):
        mocker.patch(
            "plane.bgtasks.faturamento_conciliacao.buscar_assinatura",
            side_effect=ErroDoAsaas("502"),
        )

        resultado = conciliar_assinaturas()

        assert resultado == {"conferidas": 0, "corrigidas": 0}


@pytest.mark.contract
class TestAlarmeDeSilencio:
    def test_silencio_com_assinatura_viva_acende(self, assinatura):
        cache.delete(CHAVE_DO_ULTIMO_EVENTO)

        resultado = alarme_de_silencio_do_asaas()

        assert resultado["alarme"] is True
        assert "interrompida" in cache.get(CHAVE_DO_ALARME)

    def test_evento_recente_apaga_o_alarme(self, assinatura):
        cache.set(CHAVE_DO_ULTIMO_EVENTO, timezone.now().isoformat(), None)

        resultado = alarme_de_silencio_do_asaas()

        assert resultado["alarme"] is False
        assert cache.get(CHAVE_DO_ALARME) is None

    def test_evento_antigo_acende(self, assinatura):
        cache.set(CHAVE_DO_ULTIMO_EVENTO, (timezone.now() - timedelta(hours=30)).isoformat(), None)

        assert alarme_de_silencio_do_asaas()["alarme"] is True

    def test_sem_assinatura_viva_nao_ha_o_que_alarmar(self, assinatura):
        assinatura.status = regua.ENCERRADA
        assinatura.save()
        cache.delete(CHAVE_DO_ULTIMO_EVENTO)

        resultado = alarme_de_silencio_do_asaas()

        assert resultado["alarme"] is False
