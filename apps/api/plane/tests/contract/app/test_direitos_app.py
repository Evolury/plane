# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""As travas do plano, uma por uma (ADR 0021).

A tela esconde o que o plano não inclui, mas quem recusa é o servidor —
qualquer cliente pode falar com a API sem passar pelo front. Estes testes
existem para provar isso: nenhum deles abre uma página.

Todos partem de um espaço posto num plano à mão, porque a contratação é a E4.
"""

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from plane.db.models import Automation, Project, ProjectMember, State, WorkspaceMemberInvite
from plane.utils import direitos, regua
from plane.utils.planos import (
    AVANCADO,
    CICLO_MENSAL,
    ESSENCIAL,
    LIMITE_AUTOMACOES,
    LIMITE_PROPRIEDADES,
    PROFISSIONAL,
    copia_para_contrato,
    plano,
)

ANALYTICS_URL = "/api/workspaces/{slug}/analytics/?x_axis=priority&y_axis=issue_count"
WEBHOOKS_URL = "/api/workspaces/{slug}/webhooks/"
PROPRIEDADES_URL = "/api/workspaces/{slug}/projects/{project_id}/issue-properties/"
AUTOMACOES_URL = "/api/workspaces/{slug}/projects/{project_id}/automations/"
AUTOMACAO_URL = "/api/workspaces/{slug}/projects/{project_id}/automations/{pk}/"
CONVITES_URL = "/api/workspaces/{slug}/invitations/"
PLANO_URL = "/api/workspaces/{slug}/faturamento/plano/"
API_PUBLICA_URL = "/api/v1/workspaces/{slug}/projects/"


@pytest.fixture
def session_client(create_user):
    cliente = APIClient()
    cliente.force_authenticate(user=create_user)
    return cliente


@pytest.fixture
def projeto(db, workspace, create_user):
    projeto = Project.objects.create(
        name="Projeto", identifier="PRJ", workspace=workspace, created_by=create_user
    )
    ProjectMember.objects.create(project=projeto, member=create_user, role=20, is_active=True)
    State.objects.filter(project=projeto).delete()
    State.objects.create(
        name="Pendente", group="backlog", project=projeto, workspace=workspace, color="#000", default=True
    )
    return projeto


def assinar(workspace, chave, status_da_assinatura=regua.ATIVA):
    """Põe o espaço num plano — o que a E4 vai fazer pela contratação."""
    assinatura = workspace.assinatura
    for campo, valor in copia_para_contrato(chave, CICLO_MENSAL).items():
        setattr(assinatura, campo, valor)
    assinatura.status = status_da_assinatura
    assinatura.pago_ate = timezone.now().date() + timedelta(days=30)
    assinatura.save()
    return assinatura


def _propriedades(session_client, workspace, projeto, quantas, inicio=0):
    for indice in range(inicio, inicio + quantas):
        resposta = session_client.post(
            PROPRIEDADES_URL.format(slug=workspace.slug, project_id=projeto.id),
            {"name": f"Campo {indice}", "property_type": "text"},
            format="json",
        )
        assert resposta.status_code == status.HTTP_201_CREATED, resposta.data


@pytest.mark.contract
class TestAnalytics:
    def test_o_essencial_nao_tem_analytics(self, session_client, workspace):
        assinar(workspace, ESSENCIAL)

        resposta = session_client.get(ANALYTICS_URL.format(slug=workspace.slug))

        assert resposta.status_code == status.HTTP_402_PAYMENT_REQUIRED
        assert resposta.data["error_message"] == "PLANO_NAO_INCLUI"
        assert resposta.data["recurso"] == "analytics"
        # Recusar sem dizer onde encontrar transforma a trava em parede.
        assert resposta.data["planos_com"] == [PROFISSIONAL, AVANCADO]

    def test_o_profissional_tem(self, session_client, workspace):
        assinar(workspace, PROFISSIONAL)

        resposta = session_client.get(ANALYTICS_URL.format(slug=workspace.slug))

        assert resposta.status_code == status.HTTP_200_OK


@pytest.mark.contract
class TestWebhooks:
    def test_o_essencial_nao_tem_webhook(self, session_client, workspace):
        assinar(workspace, ESSENCIAL)

        resposta = session_client.get(WEBHOOKS_URL.format(slug=workspace.slug))

        assert resposta.status_code == status.HTTP_402_PAYMENT_REQUIRED
        assert resposta.data["recurso"] == "webhooks"

    def test_o_profissional_tem(self, session_client, workspace):
        assinar(workspace, PROFISSIONAL)

        resposta = session_client.get(WEBHOOKS_URL.format(slug=workspace.slug))

        assert resposta.status_code == status.HTTP_200_OK


@pytest.mark.contract
class TestAPIPublica:
    """A trava é no uso, não na criação do token (ADR 0021)."""

    def test_o_essencial_nao_atende_pela_api(self, api_key_client, workspace):
        assinar(workspace, ESSENCIAL)

        resposta = api_key_client.get(API_PUBLICA_URL.format(slug=workspace.slug))

        assert resposta.status_code == status.HTTP_402_PAYMENT_REQUIRED
        # Vem do middleware, então é JsonResponse: `.json()`, não `.data`.
        assert resposta.json()["recurso"] == "api_publica"

    def test_o_profissional_atende(self, api_key_client, workspace):
        assinar(workspace, PROFISSIONAL)

        resposta = api_key_client.get(API_PUBLICA_URL.format(slug=workspace.slug))

        assert resposta.status_code == status.HTTP_200_OK

    def test_identidade_nunca_e_recusada(self, api_key_client, workspace):
        """Quem tem token válido pode ao menos saber quem é."""
        assinar(workspace, ESSENCIAL)

        resposta = api_key_client.get("/api/v1/users/me/")

        assert resposta.status_code == status.HTTP_200_OK


@pytest.mark.contract
class TestPropriedades:
    def test_o_teto_do_essencial_e_cinco(self, session_client, workspace, projeto):
        assinar(workspace, ESSENCIAL)
        teto = plano(ESSENCIAL).teto(LIMITE_PROPRIEDADES)
        assert teto == 5

        _propriedades(session_client, workspace, projeto, teto)
        resposta = session_client.post(
            PROPRIEDADES_URL.format(slug=workspace.slug, project_id=projeto.id),
            {"name": "A sexta", "property_type": "text"},
            format="json",
        )

        assert resposta.status_code == status.HTTP_402_PAYMENT_REQUIRED
        assert resposta.data["error_message"] == "LIMITE_DO_PLANO"
        assert resposta.data["teto"] == 5
        assert resposta.data["planos_com_mais"] == [PROFISSIONAL, AVANCADO]

    def test_o_profissional_passa_de_cinco(self, session_client, workspace, projeto):
        assinar(workspace, PROFISSIONAL)

        _propriedades(session_client, workspace, projeto, 6)

        lista = session_client.get(PROPRIEDADES_URL.format(slug=workspace.slug, project_id=projeto.id))
        assert lista.data["cap"] == 30
        assert len(lista.data["properties"]) == 6

    def test_cair_de_plano_nao_apaga_propriedade(self, session_client, workspace, projeto):
        """Apagar dado por mudança de contrato cobraria o cliente duas vezes."""
        assinar(workspace, PROFISSIONAL)
        _propriedades(session_client, workspace, projeto, 6)

        assinar(workspace, ESSENCIAL)

        lista = session_client.get(PROPRIEDADES_URL.format(slug=workspace.slug, project_id=projeto.id))
        assert len(lista.data["properties"]) == 6
        assert lista.data["cap"] == 5


@pytest.mark.contract
class TestAutomacoes:
    def _regra(self, projeto, workspace, nome, ativa=True):
        return Automation.objects.create(
            project=projeto,
            workspace=workspace,
            name=nome,
            trigger_type="work_item_created",
            trigger_config={},
            condition=None,
            actions=[{"type": "set_priority", "config": {"priority": "high"}}],
            is_active=ativa,
        )

    def _criar(self, session_client, workspace, projeto, nome):
        return session_client.post(
            AUTOMACOES_URL.format(slug=workspace.slug, project_id=projeto.id),
            {
                "name": nome,
                "trigger_type": "work_item_created",
                "trigger_config": {},
                "condition": None,
                "actions": [{"type": "set_priority", "config": {"priority": "high"}}],
            },
            format="json",
        )

    def test_o_teto_do_essencial_e_duas(self, session_client, workspace, projeto):
        assinar(workspace, ESSENCIAL)
        assert plano(ESSENCIAL).teto(LIMITE_AUTOMACOES) == 2

        self._regra(projeto, workspace, "Primeira")
        self._regra(projeto, workspace, "Segunda")

        resposta = self._criar(session_client, workspace, projeto, "Terceira")

        assert resposta.status_code == status.HTTP_402_PAYMENT_REQUIRED
        assert resposta.data["limite"] == LIMITE_AUTOMACOES
        assert resposta.data["teto"] == 2

    def test_regra_desligada_nao_ocupa_vaga(self, session_client, workspace, projeto):
        assinar(workspace, ESSENCIAL)
        self._regra(projeto, workspace, "Primeira")
        self._regra(projeto, workspace, "Dormindo", ativa=False)

        resposta = self._criar(session_client, workspace, projeto, "Segunda ativa")

        assert resposta.status_code == status.HTTP_201_CREATED

    def test_religar_conta_como_criar(self, session_client, workspace, projeto):
        """Desligar e religar seria o caminho de contorno do teto."""
        assinar(workspace, ESSENCIAL)
        self._regra(projeto, workspace, "Primeira")
        self._regra(projeto, workspace, "Segunda")
        dormindo = self._regra(projeto, workspace, "Dormindo", ativa=False)

        resposta = session_client.patch(
            AUTOMACAO_URL.format(slug=workspace.slug, project_id=projeto.id, pk=dormindo.id),
            {"is_active": True},
            format="json",
        )

        assert resposta.status_code == status.HTTP_402_PAYMENT_REQUIRED

    def test_o_profissional_nao_tem_teto(self, session_client, workspace, projeto):
        assinar(workspace, PROFISSIONAL)
        assert plano(PROFISSIONAL).teto(LIMITE_AUTOMACOES) is None

        for indice in range(4):
            self._regra(projeto, workspace, f"Regra {indice}")

        resposta = self._criar(session_client, workspace, projeto, "Mais uma")

        assert resposta.status_code == status.HTTP_201_CREATED


@pytest.mark.contract
class TestConvidados:
    def test_o_essencial_nao_tem_convidado(self, session_client, workspace):
        assinar(workspace, ESSENCIAL)

        resposta = session_client.post(
            CONVITES_URL.format(slug=workspace.slug),
            {"emails": [{"email": "de-fora@exemplo.com", "role": 5}]},
            format="json",
        )

        assert resposta.status_code == status.HTTP_402_PAYMENT_REQUIRED
        assert resposta.data["limite"] == "convidados"
        assert resposta.data["planos_com_mais"] == [PROFISSIONAL, AVANCADO]

    def test_o_profissional_tem_cota(self, session_client, workspace):
        assinar(workspace, PROFISSIONAL)
        assert direitos.cota_de_convidados(slug=workspace.slug) == 20

        resposta = session_client.post(
            CONVITES_URL.format(slug=workspace.slug),
            {"emails": [{"email": "de-fora@exemplo.com", "role": 5}]},
            format="json",
        )

        assert resposta.status_code == status.HTTP_200_OK

    def test_convite_pendente_ocupa_vaga(self, session_client, workspace):
        """Aceitar depois não pode estourar a cota."""
        assinar(workspace, PROFISSIONAL)
        assinatura = workspace.assinatura
        assinatura.convidados_por_assento = 0
        assinatura.save()
        WorkspaceMemberInvite.objects.create(
            workspace=workspace, email="ja-convidado@exemplo.com", role=5, token="t1"
        )

        resposta = session_client.post(
            CONVITES_URL.format(slug=workspace.slug),
            {"emails": [{"email": "outro@exemplo.com", "role": 5}]},
            format="json",
        )

        assert resposta.status_code == status.HTTP_402_PAYMENT_REQUIRED


@pytest.mark.contract
class TestAssentoNaoBloqueia:
    """A não-trava, e ela é decisão (ADR 0021).

    Convidar membro acima do teto **não** é recusado: o excedente entra no ciclo
    seguinte. Bloquear convite é atrito que gera suporte e não gera receita.
    """

    def test_convidar_acima_do_teto_passa(self, session_client, workspace):
        assinar(workspace, ESSENCIAL)
        assert workspace.assinatura.assentos_incluidos == 3

        resposta = session_client.post(
            CONVITES_URL.format(slug=workspace.slug),
            {"emails": [{"email": f"pessoa{i}@exemplo.com", "role": 15} for i in range(5)]},
            format="json",
        )

        assert resposta.status_code == status.HTTP_200_OK


@pytest.mark.contract
class TestRetratoDoPlano:
    def test_uma_chamada_traz_plano_estado_e_uso(self, session_client, workspace, projeto):
        assinar(workspace, PROFISSIONAL)
        _propriedades(session_client, workspace, projeto, 2)

        resposta = session_client.get(PLANO_URL.format(slug=workspace.slug))

        assert resposta.status_code == status.HTTP_200_OK
        assert resposta.data["plano"] == PROFISSIONAL
        assert resposta.data["nome"] == "Profissional"
        assert resposta.data["status"] == regua.ATIVA
        assert resposta.data["pode_escrever"] is True
        assert resposta.data["recursos"] == {"analytics": True, "api_publica": True, "webhooks": True}
        assert resposta.data["limites"] == {"propriedades_por_projeto": 30, "automacoes_ativas": None}
        assert resposta.data["assentos"] == {"incluidos": 10, "extras": 0, "usados": 1}
        assert resposta.data["convidados"] == {"cota": 20, "usados": 0}

    def test_o_essencial_mostra_o_que_nao_tem(self, session_client, workspace):
        assinar(workspace, ESSENCIAL)

        resposta = session_client.get(PLANO_URL.format(slug=workspace.slug))

        assert resposta.data["recursos"] == {"analytics": False, "api_publica": False, "webhooks": False}
        assert resposta.data["limites"]["propriedades_por_projeto"] == 5


@pytest.mark.contract
class TestOCacheNaoAtrasaAMudanca:
    def test_trocar_de_plano_vale_na_chamada_seguinte(self, session_client, workspace):
        """Invalidação que depende de alguém lembrar falha no caminho novo."""
        assinar(workspace, ESSENCIAL)
        assert session_client.get(ANALYTICS_URL.format(slug=workspace.slug)).status_code == 402

        assinar(workspace, PROFISSIONAL)

        assert session_client.get(ANALYTICS_URL.format(slug=workspace.slug)).status_code == 200
