# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""A porta do Asaas (ADR 0021).

O que estes testes protegem é uma decisão contraintuitiva: **esta porta quase
nunca responde erro**. Corpo ilegível, evento sem id, evento repetido, evento de
outro negócio — tudo responde 200. Só o token errado é recusado.

O motivo é caro: quinze respostas de erro seguidas interrompem a fila do Asaas,
e a fila é da conta inteira. A conta da Evolury atende outros negócios, então um
erro nosso calaria a cobrança deles.
"""

import json

import pytest
from django.test import Client
from rest_framework import status

from plane.db.models import EventoAsaas
from plane.license.models import InstanceConfiguration
from plane.license.utils.encryption import encrypt_data

URL = "/api/faturamento/asaas/webhook/"
TOKEN = "um-token-de-webhook-com-mais-de-trinta-e-dois-caracteres"


@pytest.fixture
def token_configurado(db):
    InstanceConfiguration.objects.create(
        key="ASAAS_WEBHOOK_TOKEN", value=encrypt_data(TOKEN), category="FATURAMENTO", is_encrypted=True
    )
    return TOKEN


@pytest.fixture
def cliente_cru(db):
    """Cliente do Django puro: esta rota não tem sessão nem DRF."""
    return Client()


def _corpo(identificador="evt_001", evento="PAYMENT_CONFIRMED"):
    return {
        "id": identificador,
        "event": evento,
        "dateCreated": "2026-08-21",
        "payment": {
            "object": "payment",
            "id": "pay_001",
            "subscription": "sub_desconhecida",
            "status": "CONFIRMED",
            "billingType": "PIX",
            "value": 290.0,
            "dueDate": "2026-08-22",
            "invoiceUrl": "https://www.asaas.com/i/exemplo",
        },
    }


@pytest.mark.contract
class TestOToken:
    def test_sem_token_configurado_recusa(self, cliente_cru, db):
        """Instância recém-instalada não pode aceitar pagamento forjado."""
        resposta = cliente_cru.post(URL, data=json.dumps(_corpo()), content_type="application/json")

        assert resposta.status_code == status.HTTP_401_UNAUTHORIZED
        assert EventoAsaas.objects.count() == 0

    def test_token_errado_recusa_e_nao_grava(self, cliente_cru, token_configurado):
        resposta = cliente_cru.post(
            URL,
            data=json.dumps(_corpo()),
            content_type="application/json",
            headers={"asaas-access-token": "chute"},
        )

        assert resposta.status_code == status.HTTP_401_UNAUTHORIZED
        assert EventoAsaas.objects.count() == 0

    def test_token_certo_aceita(self, cliente_cru, token_configurado, mocker):
        mocker.patch("plane.app.views.faturamento.webhook.processar_evento_do_asaas.delay")

        resposta = cliente_cru.post(
            URL,
            data=json.dumps(_corpo()),
            content_type="application/json",
            headers={"asaas-access-token": TOKEN},
        )

        assert resposta.status_code == status.HTTP_200_OK
        assert resposta.json() == {"recebido": True, "repetido": False}
        assert EventoAsaas.objects.count() == 1


@pytest.mark.contract
class TestIdempotencia:
    def test_o_mesmo_evento_duas_vezes_grava_uma(self, cliente_cru, token_configurado, mocker):
        """O Asaas entrega at-least-once e reenvia a fila ao reativá-la."""
        enfileirar = mocker.patch("plane.app.views.faturamento.webhook.processar_evento_do_asaas.delay")
        corpo = json.dumps(_corpo())

        primeira = cliente_cru.post(
            URL, data=corpo, content_type="application/json", headers={"asaas-access-token": TOKEN}
        )
        segunda = cliente_cru.post(
            URL, data=corpo, content_type="application/json", headers={"asaas-access-token": TOKEN}
        )

        assert primeira.json()["repetido"] is False
        assert segunda.json()["repetido"] is True
        assert EventoAsaas.objects.count() == 1
        # E, principalmente, não processa de novo.
        assert enfileirar.call_count == 1


@pytest.mark.contract
class TestOQueNaoVoltaComoErro:
    def test_corpo_ilegivel_responde_200(self, cliente_cru, token_configurado):
        """Voltaria para sempre: o Asaas reenvia o mesmo corpo."""
        resposta = cliente_cru.post(
            URL,
            data="isto não é json",
            content_type="application/json",
            headers={"asaas-access-token": TOKEN},
        )

        assert resposta.status_code == status.HTTP_200_OK
        assert resposta.json()["motivo"] == "CORPO_INVALIDO"

    def test_evento_sem_id_responde_200(self, cliente_cru, token_configurado):
        corpo = _corpo()
        corpo.pop("id")

        resposta = cliente_cru.post(
            URL,
            data=json.dumps(corpo),
            content_type="application/json",
            headers={"asaas-access-token": TOKEN},
        )

        assert resposta.status_code == status.HTTP_200_OK
        assert resposta.json()["motivo"] == "SEM_ID"
        assert EventoAsaas.objects.count() == 0

    def test_evento_de_outro_negocio_e_aceito(self, cliente_cru, token_configurado, mocker):
        """A conta atende outros negócios da Evolury. Recusar calaria a fila deles."""
        mocker.patch("plane.app.views.faturamento.webhook.processar_evento_do_asaas.delay")

        resposta = cliente_cru.post(
            URL,
            data=json.dumps(_corpo(identificador="evt_de_outro")),
            content_type="application/json",
            headers={"asaas-access-token": TOKEN},
        )

        assert resposta.status_code == status.HTTP_200_OK
        assert EventoAsaas.objects.filter(asaas_event_id="evt_de_outro").exists()


@pytest.mark.contract
class TestMetodo:
    def test_get_nao_serve(self, cliente_cru, token_configurado):
        resposta = cliente_cru.get(URL, headers={"asaas-access-token": TOKEN})

        assert resposta.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
