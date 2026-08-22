# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Espaço restrito lê e não escreve — e o resto continua de pé (ADR 0021).

Esta é a peça capaz de quebrar o produto inteiro para quem está em dia, e é por
isso que metade destes testes prova o contrário do que o nome do arquivo sugere:
que espaço `ativa` não sofre nada, que `atrasada` também não, e que exportar e
pagar continuam funcionando mesmo com tudo travado.

Uma trava sem essas provas é uma trava que ninguém tem coragem de ligar.
"""

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from plane.db.models import Issue, Project, ProjectMember, State
from plane.utils import regua

TAREFAS_URL = "/api/workspaces/{slug}/projects/{project_id}/issues/"
PLANO_URL = "/api/workspaces/{slug}/faturamento/plano/"
EXPORTAR_URL = "/api/workspaces/{slug}/export-issues/"
EU_URL = "/api/users/me/"


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


def em(workspace, estado):
    assinatura = workspace.assinatura
    assinatura.status = estado
    assinatura.pago_ate = timezone.now().date() - timedelta(days=10)
    assinatura.save()
    return assinatura


def criar_tarefa(session_client, workspace, projeto, nome="Uma tarefa"):
    return session_client.post(
        TAREFAS_URL.format(slug=workspace.slug, project_id=projeto.id),
        {"name": nome},
        format="json",
    )


@pytest.mark.contract
class TestOEspacoEmDiaNaoSofreNada:
    """A prova que importa mais: a trava não pega quem está pagando."""

    def test_ativa_cria_edita_e_exclui(self, session_client, workspace, projeto):
        em(workspace, regua.ATIVA)

        criada = criar_tarefa(session_client, workspace, projeto)
        assert criada.status_code == status.HTTP_201_CREATED

        item = f"{TAREFAS_URL.format(slug=workspace.slug, project_id=projeto.id)}{criada.data['id']}/"
        # PATCH de tarefa responde 204 nesta API — medido, não suposto.
        assert session_client.patch(item, {"name": "Outro nome"}, format="json").status_code == 204
        assert session_client.delete(item).status_code == 204

    def test_atrasada_ainda_escreve(self, session_client, workspace, projeto):
        """O Asaas ainda está tentando o cartão. Restringir no D+0 puniria quem paga no D+1."""
        em(workspace, regua.ATRASADA)

        assert criar_tarefa(session_client, workspace, projeto).status_code == status.HTTP_201_CREATED

    def test_cancelada_escreve_ate_o_fim_do_ciclo(self, session_client, workspace, projeto):
        em(workspace, regua.CANCELADA)

        assert criar_tarefa(session_client, workspace, projeto).status_code == status.HTTP_201_CREATED

    def test_sem_assinatura_ainda_escreve_ate_haver_como_contratar(
        self, session_client, workspace, projeto
    ):
        """Decisão temporária, e ela tem data para cair.

        A régua diz que `sem_assinatura` não escreve, e é a regra do produto.
        Aplicá-la antes da E4 trancaria todo espaço novo num produto sem forma
        de pagamento. Quem passa a cobrá-la é a E5 — este teste é o lembrete
        vermelho de que a decisão existe.
        """
        em(workspace, regua.SEM_ASSINATURA)

        assert criar_tarefa(session_client, workspace, projeto).status_code == status.HTTP_201_CREATED


@pytest.mark.contract
class TestRestrita:
    def test_nao_cria(self, session_client, workspace, projeto):
        em(workspace, regua.RESTRITA)

        resposta = criar_tarefa(session_client, workspace, projeto)

        assert resposta.status_code == status.HTTP_402_PAYMENT_REQUIRED
        assert resposta.json()["error_message"] == "ESPACO_SOMENTE_LEITURA"
        assert resposta.json()["status_da_assinatura"] == regua.RESTRITA

    def test_nao_edita_nem_exclui(self, session_client, workspace, projeto, create_user):
        tarefa = Issue.objects.create(
            name="Já existia", project=projeto, workspace=workspace, created_by=create_user
        )
        em(workspace, regua.RESTRITA)

        item = f"{TAREFAS_URL.format(slug=workspace.slug, project_id=projeto.id)}{tarefa.id}/"
        assert session_client.patch(item, {"name": "Novo"}, format="json").status_code == 402
        assert session_client.delete(item).status_code == 402

    def test_continua_lendo(self, session_client, workspace, projeto, create_user):
        Issue.objects.create(name="Visível", project=projeto, workspace=workspace, created_by=create_user)
        em(workspace, regua.RESTRITA)

        resposta = session_client.get(TAREFAS_URL.format(slug=workspace.slug, project_id=projeto.id))

        assert resposta.status_code == status.HTTP_200_OK


@pytest.mark.contract
class TestBloqueadaEDepois:
    @pytest.mark.parametrize("estado", [regua.BLOQUEADA, regua.ENCERRADA, regua.REMOVIDA])
    def test_nao_escreve(self, session_client, workspace, projeto, estado):
        em(workspace, estado)

        resposta = criar_tarefa(session_client, workspace, projeto)

        assert resposta.status_code == status.HTTP_402_PAYMENT_REQUIRED
        assert resposta.json()["error_message"] == "ESPACO_BLOQUEADO"


@pytest.mark.contract
class TestAsExcecoes:
    """Curtas e explícitas: uma lista que cresce sozinha deixa de ser exceção."""

    def test_faturamento_passa_com_o_espaco_bloqueado(self, session_client, workspace):
        """Pagar não pode depender de estar pago."""
        em(workspace, regua.BLOQUEADA)

        resposta = session_client.get(PLANO_URL.format(slug=workspace.slug))

        assert resposta.status_code == status.HTTP_200_OK

    def test_exportar_passa_com_o_espaco_restrito(self, session_client, workspace, projeto):
        """É a linha que separa cobrança de sequestro de dado.

        O que se afirma aqui é só que o middleware deixou passar: o corpo do
        pedido de exportação é assunto do endpoint, e ele pode recusar por
        outros motivos sem que isso diga nada sobre a trava.
        """
        em(workspace, regua.RESTRITA)

        resposta = session_client.post(
            EXPORTAR_URL.format(slug=workspace.slug),
            {"provider": "csv", "project": [str(projeto.id)]},
            format="json",
        )

        assert resposta.status_code != status.HTTP_402_PAYMENT_REQUIRED

    def test_rota_sem_espaco_passa(self, session_client, workspace):
        """Trocar o próprio nome não é assunto da assinatura de um espaço."""
        em(workspace, regua.BLOQUEADA)

        resposta = session_client.patch(EU_URL, {"first_name": "Nome"}, format="json")

        assert resposta.status_code != status.HTTP_402_PAYMENT_REQUIRED

    def test_leitura_nunca_e_recusada(self, session_client, workspace, projeto):
        em(workspace, regua.BLOQUEADA)

        resposta = session_client.get(TAREFAS_URL.format(slug=workspace.slug, project_id=projeto.id))

        assert resposta.status_code == status.HTTP_200_OK
