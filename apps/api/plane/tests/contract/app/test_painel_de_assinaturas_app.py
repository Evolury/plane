# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""O painel de assinaturas do god-mode (ADR 0021).

Duas promessas para o financeiro, e as duas são testadas aqui: **bloquear sem
`psql` e sem depender de webhook**, e **nenhum ato sem autor e motivo**.

E uma promessa para quem mantém o código: a listagem sai em um número fixo de
consultas. Um painel que faz uma consulta por linha funciona com três espaços e
derruba a página com trezentos.
"""

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from plane.db.models import HistoricoDeAssinatura, Workspace, WorkspaceMember
from plane.license.models import Instance, InstanceAdmin
from plane.utils import regua
from plane.utils.planos import AVANCADO, CICLO_MENSAL, ESSENCIAL, PROFISSIONAL, copia_para_contrato

LISTA_URL = "/api/instances/assinaturas/"
SAUDE_URL = "/api/instances/assinaturas/saude/"
ITEM_URL = "/api/instances/assinaturas/{workspace_id}/"

HOJE = timezone.now().date()


@pytest.fixture
def admin_da_instancia(db, create_user):
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


@pytest.fixture
def assinada(db, workspace):
    assinatura = workspace.assinatura
    for campo, valor in copia_para_contrato(ESSENCIAL, CICLO_MENSAL).items():
        setattr(assinatura, campo, valor)
    assinatura.status = regua.ATIVA
    assinatura.pago_ate = HOJE + timedelta(days=10)
    assinatura.save()
    return assinatura


@pytest.mark.contract
class TestAListagem:
    def test_mostra_plano_estado_e_uso(self, admin_da_instancia, workspace, assinada):
        resposta = admin_da_instancia.get(LISTA_URL)

        assert resposta.status_code == status.HTTP_200_OK
        linha = next(linha for linha in resposta.data["results"] if linha["slug"] == workspace.slug)
        assert linha["plano"] == ESSENCIAL
        assert linha["status"] == regua.ATIVA
        assert linha["assentos_incluidos"] == 3
        assert linha["membros"] == 1
        assert linha["valor"] == 29000

    def test_o_excedente_aparece(self, admin_da_instancia, workspace, assinada, create_bot_user, django_user_model):
        # Cinco membros num plano de três assentos: dois de excedente.
        for indice in range(4):
            membro = django_user_model.objects.create(
                email=f"pessoa{indice}@exemplo.com", username=f"pessoa{indice}"
            )
            WorkspaceMember.objects.create(workspace=workspace, member=membro, role=15, is_active=True)

        resultados = admin_da_instancia.get(LISTA_URL).data["results"]
        linha = next(item for item in resultados if item["slug"] == workspace.slug)

        assert linha["membros"] == 5
        assert linha["excedente"] == 2

    def test_robo_nao_conta_como_assento(self, admin_da_instancia, workspace, assinada, create_bot_user):
        WorkspaceMember.objects.create(workspace=workspace, member=create_bot_user, role=15, is_active=True)

        resultados = admin_da_instancia.get(LISTA_URL).data["results"]
        linha = next(item for item in resultados if item["slug"] == workspace.slug)

        assert linha["membros"] == 1

    def test_filtra_por_estado(self, admin_da_instancia, workspace, assinada):
        assert admin_da_instancia.get(f"{LISTA_URL}?status=ativa").data["results"]
        assert admin_da_instancia.get(f"{LISTA_URL}?status=bloqueada").data["results"] == []

    def test_busca_por_nome_ou_slug(self, admin_da_instancia, workspace, assinada):
        assert admin_da_instancia.get(f"{LISTA_URL}?search={workspace.slug[:4]}").data["results"]
        assert admin_da_instancia.get(f"{LISTA_URL}?search=inexistente").data["results"] == []

    def test_uma_consulta_por_pagina_e_nao_por_linha(
        self, admin_da_instancia, workspace, assinada, django_assert_max_num_queries, create_user
    ):
        """Painel que consulta por linha funciona com três espaços e cai com trezentos."""
        for indice in range(5):
            outro = Workspace.objects.create(
                name=f"Espaço {indice}", slug=f"espaco-{indice}", owner=create_user
            )
            WorkspaceMember.objects.create(workspace=outro, member=create_user, role=20)

        # Cinco: sessão, permissão de instância, contagem da paginação, a
        # listagem com as duas subconsultas dentro dela, e o espaço do usuário.
        # O número é medido, e apertado de propósito — um orçamento folgado
        # deixaria o `select_related` cair sem ninguém notar (foi o que
        # aconteceu com o teto em 12).
        with django_assert_max_num_queries(5):
            resposta = admin_da_instancia.get(LISTA_URL)

        assert len(resposta.data["results"]) == 6

    def test_quem_nao_e_admin_da_instancia_nao_ve(self, workspace, assinada, create_user):
        cliente = APIClient()
        cliente.force_authenticate(user=create_user)

        assert cliente.get(LISTA_URL).status_code in (
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN,
        )


@pytest.mark.contract
class TestBloqueioManual:
    def test_o_financeiro_bloqueia_sem_webhook(self, admin_da_instancia, workspace, assinada):
        resposta = admin_da_instancia.patch(
            ITEM_URL.format(workspace_id=workspace.id),
            {"acao": "bloquear", "motivo": "Estorno processado no Asaas"},
            format="json",
        )

        assert resposta.status_code == status.HTTP_200_OK
        assinada.refresh_from_db()
        assert assinada.status == regua.BLOQUEADA
        assert not regua.permite_escrita(assinada.status)

    def test_liberar_nao_perdoa_divida(self, admin_da_instancia, workspace, assinada):
        """Desfaz o bloqueio manual, e devolve o espaço ao que a régua disser."""
        assinada.status = regua.BLOQUEADA
        assinada.pago_ate = HOJE - timedelta(days=9)
        assinada.save()

        admin_da_instancia.patch(
            ITEM_URL.format(workspace_id=workspace.id),
            {"acao": "liberar", "motivo": "Pagamento conferido à mão"},
            format="json",
        )

        assinada.refresh_from_db()
        assert assinada.status == regua.RESTRITA

    def test_sem_motivo_nao_faz_nada(self, admin_da_instancia, workspace, assinada):
        resposta = admin_da_instancia.patch(
            ITEM_URL.format(workspace_id=workspace.id), {"acao": "bloquear"}, format="json"
        )

        assert resposta.status_code == status.HTTP_400_BAD_REQUEST
        assinada.refresh_from_db()
        assert assinada.status == regua.ATIVA

    def test_acao_desconhecida_e_recusada(self, admin_da_instancia, workspace, assinada):
        resposta = admin_da_instancia.patch(
            ITEM_URL.format(workspace_id=workspace.id),
            {"acao": "explodir", "motivo": "curiosidade"},
            format="json",
        )

        assert resposta.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.contract
class TestPlanoECortesia:
    def test_atribuir_plano_copia_o_catalogo(self, admin_da_instancia, workspace, assinada):
        admin_da_instancia.patch(
            ITEM_URL.format(workspace_id=workspace.id),
            {"acao": "atribuir_plano", "plano": PROFISSIONAL, "motivo": "Contrato fechado por fora"},
            format="json",
        )

        assinada.refresh_from_db()
        assert assinada.plano == PROFISSIONAL
        assert assinada.assentos_incluidos == 10
        assert assinada.valor_base == 69000

    def test_cortesia_tem_prazo_e_preco_zero(self, admin_da_instancia, workspace, assinada):
        admin_da_instancia.patch(
            ITEM_URL.format(workspace_id=workspace.id),
            {"acao": "conceder_cortesia", "dias": 45, "plano": AVANCADO, "motivo": "Piloto com o cliente"},
            format="json",
        )

        assinada.refresh_from_db()
        assert assinada.status == regua.EM_CORTESIA
        assert assinada.pago_ate == HOJE + timedelta(days=45)
        assert assinada.promocao_termina_em == assinada.pago_ate
        assert assinada.valor_base == 0
        assert assinada.assentos_incluidos == 30

    def test_cortesia_sem_prazo_e_recusada(self, admin_da_instancia, workspace, assinada):
        resposta = admin_da_instancia.patch(
            ITEM_URL.format(workspace_id=workspace.id),
            {"acao": "conceder_cortesia", "dias": 0, "motivo": "sem prazo"},
            format="json",
        )

        assert resposta.status_code == status.HTTP_400_BAD_REQUEST

    def test_plano_inexistente_e_recusado(self, admin_da_instancia, workspace, assinada):
        resposta = admin_da_instancia.patch(
            ITEM_URL.format(workspace_id=workspace.id),
            {"acao": "atribuir_plano", "plano": "premium", "motivo": "x"},
            format="json",
        )

        assert resposta.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.contract
class TestHistorico:
    def test_todo_ato_grava_autor_e_motivo(self, admin_da_instancia, workspace, assinada, create_user):
        admin_da_instancia.patch(
            ITEM_URL.format(workspace_id=workspace.id),
            {"acao": "bloquear", "motivo": "Estorno processado"},
            format="json",
        )

        linha = HistoricoDeAssinatura.objects.get(evento="god_mode:bloquear")
        assert linha.motivo == "Estorno processado"
        assert linha.created_by_id == create_user.id

        resposta = admin_da_instancia.get(ITEM_URL.format(workspace_id=workspace.id))
        assert resposta.data[0]["evento"] == "god_mode:bloquear"
        assert resposta.data[0]["quem"] == create_user.display_name


@pytest.mark.contract
class TestSaudeDaIntegracao:
    def test_mostra_o_alarme_e_a_contagem_por_estado(self, admin_da_instancia, workspace, assinada):
        from django.core.cache import cache

        from plane.bgtasks.faturamento_conciliacao import CHAVE_DO_ALARME

        cache.set(CHAVE_DO_ALARME, "Nenhum evento do Asaas há mais de 24h", None)

        resposta = admin_da_instancia.get(SAUDE_URL)

        assert resposta.status_code == status.HTTP_200_OK
        assert "24h" in resposta.data["alarme"]
        assert resposta.data["por_status"]["ativa"] == 1
        assert resposta.data["por_status"]["bloqueada"] == 0
