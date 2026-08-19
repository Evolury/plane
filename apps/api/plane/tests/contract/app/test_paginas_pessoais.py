# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Evolury — páginas pessoais de "Minhas tarefas" (ADR 0015, F1).

O que estes testes prendem: uma página pessoal é uma `Page` do workspace **sem**
vínculo em `ProjectPage`, e quem manda nela é o dono. Nem papel de workspace nem
papel de projeto entram na conta.
"""

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from plane.db.models import Page, Project, ProjectPage, User, WorkspaceMember


def url_lista(slug):
    return f"/api/workspaces/{slug}/my-tasks/pages/"


def url_pagina(slug, page_id):
    return f"/api/workspaces/{slug}/my-tasks/pages/{page_id}/"


@pytest.fixture
def outra_pessoa(db, workspace):
    """Membro do mesmo workspace — só não é dono das páginas."""
    pessoa = User.objects.create(email="outra@evolury.test", username="outra")
    pessoa.set_password("senha-de-teste")
    pessoa.save()
    WorkspaceMember.objects.create(workspace=workspace, member=pessoa, role=20)
    return pessoa


@pytest.fixture
def cliente_da_outra(outra_pessoa):
    # APIClient próprio de propósito: reautenticar o `api_client` compartilhado
    # troca também o `session_client`, e o teste passa a fazer as duas pontas
    # como a mesma pessoa — foi exatamente o que aconteceu na primeira versão.
    cliente = APIClient()
    cliente.force_authenticate(user=outra_pessoa)
    return cliente


@pytest.mark.django_db
class TestPaginaPessoalNasceSemProjeto:
    def test_criada_pela_rota_pessoal_nao_ganha_vinculo_de_projeto(self, session_client, workspace):
        resposta = session_client.post(url_lista(workspace.slug), {"name": "Notas da reunião"}, format="json")

        assert resposta.status_code == status.HTTP_201_CREATED
        assert resposta.data["project_ids"] == []
        assert ProjectPage.objects.filter(page_id=resposta.data["id"]).count() == 0
        assert Page.objects.get(pk=resposta.data["id"]).workspace_id == workspace.id

    def test_pagina_de_projeto_nao_aparece_na_lista_pessoal(self, session_client, workspace, create_user):
        projeto = Project.objects.create(name="Projeto", identifier="PRJ", workspace=workspace)
        pagina = Page.objects.create(name="Do projeto", workspace=workspace, owned_by=create_user)
        ProjectPage.objects.create(workspace=workspace, project=projeto, page=pagina)

        resposta = session_client.get(url_lista(workspace.slug))

        assert resposta.status_code == status.HTTP_200_OK
        assert [p["id"] for p in resposta.data] == []


@pytest.mark.django_db
class TestSoODonoEnxerga:
    def test_estranho_recebe_404_e_nao_403(self, session_client, cliente_da_outra, workspace):
        criada = session_client.post(url_lista(workspace.slug), {"name": "Minha"}, format="json")

        resposta = cliente_da_outra.get(url_pagina(workspace.slug, criada.data["id"]))

        # 403 responderia "existe, mas não é sua" — informação sobre a página
        # de outra pessoa.
        assert resposta.status_code == status.HTTP_404_NOT_FOUND

    def test_lista_do_outro_nao_traz_a_minha(self, session_client, cliente_da_outra, workspace):
        session_client.post(url_lista(workspace.slug), {"name": "Minha"}, format="json")

        resposta = cliente_da_outra.get(url_lista(workspace.slug))

        assert resposta.status_code == status.HTTP_200_OK
        assert resposta.data == []

    def test_estranho_nao_edita(self, session_client, cliente_da_outra, workspace):
        criada = session_client.post(url_lista(workspace.slug), {"name": "Minha"}, format="json")

        resposta = cliente_da_outra.patch(
            url_pagina(workspace.slug, criada.data["id"]), {"name": "Sequestrada"}, format="json"
        )

        assert resposta.status_code == status.HTTP_404_NOT_FOUND
        assert Page.objects.get(pk=criada.data["id"]).name == "Minha"


@pytest.mark.django_db
class TestCicloDeVida:
    def test_dono_renomeia(self, session_client, workspace):
        criada = session_client.post(url_lista(workspace.slug), {"name": "Rascunho"}, format="json")

        resposta = session_client.patch(
            url_pagina(workspace.slug, criada.data["id"]), {"name": "Ata"}, format="json"
        )

        assert resposta.status_code == status.HTTP_200_OK
        assert Page.objects.get(pk=criada.data["id"]).name == "Ata"

    def test_excluir_exige_arquivar_antes(self, session_client, workspace):
        criada = session_client.post(url_lista(workspace.slug), {"name": "Rascunho"}, format="json")

        resposta = session_client.delete(url_pagina(workspace.slug, criada.data["id"]))

        assert resposta.status_code == status.HTTP_400_BAD_REQUEST
        assert Page.objects.filter(pk=criada.data["id"]).exists()

    def test_arquivada_pode_ser_excluida(self, session_client, workspace):
        criada = session_client.post(url_lista(workspace.slug), {"name": "Rascunho"}, format="json")
        Page.objects.filter(pk=criada.data["id"]).update(archived_at=timezone.now())

        resposta = session_client.delete(url_pagina(workspace.slug, criada.data["id"]))

        assert resposta.status_code == status.HTTP_204_NO_CONTENT
        assert not Page.objects.filter(pk=criada.data["id"]).exists()
