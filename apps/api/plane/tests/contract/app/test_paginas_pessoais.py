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

from plane.db.models import Page, PageShare, Project, ProjectMember, ProjectPage, User, WorkspaceMember


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


def url_shares(slug, page_id):
    return f"/api/workspaces/{slug}/my-tasks/pages/{page_id}/shares/"


def url_compartilhadas(slug):
    return f"/api/workspaces/{slug}/my-tasks/shared-pages/"


@pytest.fixture
def de_fora(db):
    """Pessoa que existe, mas não é membro deste workspace."""
    pessoa = User.objects.create(email="fora@evolury.test", username="fora")
    pessoa.set_password("senha-de-teste")
    pessoa.save()
    return pessoa


@pytest.mark.django_db
class TestCompartilhamento:
    def test_compartilhada_aparece_para_quem_recebeu_e_ele_consegue_ler(
        self, session_client, cliente_da_outra, outra_pessoa, workspace
    ):
        criada = session_client.post(url_lista(workspace.slug), {"name": "Ata"}, format="json")
        session_client.post(
            url_shares(workspace.slug, criada.data["id"]),
            {"shared_with": str(outra_pessoa.id), "role": PageShare.READ},
            format="json",
        )

        listagem = cliente_da_outra.get(url_compartilhadas(workspace.slug))
        detalhe = cliente_da_outra.get(url_pagina(workspace.slug, criada.data["id"]))

        assert [p["id"] for p in listagem.data] == [criada.data["id"]]
        assert detalhe.status_code == status.HTTP_200_OK

    def test_compartilhada_nao_entra_na_aba_paginas_de_quem_recebeu(
        self, session_client, cliente_da_outra, outra_pessoa, workspace
    ):
        criada = session_client.post(url_lista(workspace.slug), {"name": "Ata"}, format="json")
        session_client.post(
            url_shares(workspace.slug, criada.data["id"]),
            {"shared_with": str(outra_pessoa.id), "role": PageShare.READ},
            format="json",
        )

        # "Páginas" é o que é meu; "Compartilhado comigo" é o que é dos outros.
        assert cliente_da_outra.get(url_lista(workspace.slug)).data == []

    def test_pode_ler_nao_escreve(self, session_client, cliente_da_outra, outra_pessoa, workspace):
        criada = session_client.post(url_lista(workspace.slug), {"name": "Ata"}, format="json")
        session_client.post(
            url_shares(workspace.slug, criada.data["id"]),
            {"shared_with": str(outra_pessoa.id), "role": PageShare.READ},
            format="json",
        )

        resposta = cliente_da_outra.patch(
            url_pagina(workspace.slug, criada.data["id"]), {"name": "Mexi"}, format="json"
        )

        assert resposta.status_code == status.HTTP_403_FORBIDDEN
        assert Page.objects.get(pk=criada.data["id"]).name == "Ata"

    def test_pode_editar_escreve(self, session_client, cliente_da_outra, outra_pessoa, workspace):
        criada = session_client.post(url_lista(workspace.slug), {"name": "Ata"}, format="json")
        session_client.post(
            url_shares(workspace.slug, criada.data["id"]),
            {"shared_with": str(outra_pessoa.id), "role": PageShare.WRITE},
            format="json",
        )

        resposta = cliente_da_outra.patch(
            url_pagina(workspace.slug, criada.data["id"]), {"name": "A quatro mãos"}, format="json"
        )

        assert resposta.status_code == status.HTTP_200_OK
        assert Page.objects.get(pk=criada.data["id"]).name == "A quatro mãos"

    def test_pode_editar_nao_exclui_nem_recompartilha(
        self, session_client, cliente_da_outra, outra_pessoa, workspace, de_fora
    ):
        criada = session_client.post(url_lista(workspace.slug), {"name": "Ata"}, format="json")
        session_client.post(
            url_shares(workspace.slug, criada.data["id"]),
            {"shared_with": str(outra_pessoa.id), "role": PageShare.WRITE},
            format="json",
        )
        Page.objects.filter(pk=criada.data["id"]).update(archived_at=timezone.now())

        exclusao = cliente_da_outra.delete(url_pagina(workspace.slug, criada.data["id"]))
        repasse = cliente_da_outra.post(
            url_shares(workspace.slug, criada.data["id"]),
            {"shared_with": str(de_fora.id), "role": PageShare.READ},
            format="json",
        )

        assert exclusao.status_code == status.HTTP_403_FORBIDDEN
        assert repasse.status_code == status.HTTP_403_FORBIDDEN
        assert Page.objects.filter(pk=criada.data["id"]).exists()

    def test_tirar_o_compartilhamento_tira_o_acesso(
        self, session_client, cliente_da_outra, outra_pessoa, workspace
    ):
        criada = session_client.post(url_lista(workspace.slug), {"name": "Ata"}, format="json")
        share = session_client.post(
            url_shares(workspace.slug, criada.data["id"]),
            {"shared_with": str(outra_pessoa.id), "role": PageShare.READ},
            format="json",
        )

        session_client.delete(f"{url_shares(workspace.slug, criada.data['id'])}{share.data['id']}/")

        assert cliente_da_outra.get(url_pagina(workspace.slug, criada.data["id"])).status_code == (
            status.HTTP_404_NOT_FOUND
        )


@pytest.mark.django_db
class TestTravasDoCompartilhamento:
    def test_pagina_de_projeto_nao_se_compartilha(self, session_client, workspace, create_user, outra_pessoa):
        projeto = Project.objects.create(name="Projeto", identifier="PRJ", workspace=workspace)
        pagina = Page.objects.create(name="Do projeto", workspace=workspace, owned_by=create_user)
        ProjectPage.objects.create(workspace=workspace, project=projeto, page=pagina)

        resposta = session_client.post(
            url_shares(workspace.slug, pagina.id),
            {"shared_with": str(outra_pessoa.id), "role": PageShare.READ},
            format="json",
        )

        # A rota pessoal não enxerga página que está em projeto — nem para dizer
        # que existe.
        assert resposta.status_code == status.HTTP_404_NOT_FOUND
        assert PageShare.objects.count() == 0

    def test_nao_compartilha_com_quem_esta_fora_do_workspace(self, session_client, workspace, de_fora):
        criada = session_client.post(url_lista(workspace.slug), {"name": "Ata"}, format="json")

        resposta = session_client.post(
            url_shares(workspace.slug, criada.data["id"]),
            {"shared_with": str(de_fora.id), "role": PageShare.READ},
            format="json",
        )

        assert resposta.status_code == status.HTTP_400_BAD_REQUEST
        assert PageShare.objects.count() == 0

    def test_nao_compartilha_consigo_mesmo(self, session_client, workspace, create_user):
        criada = session_client.post(url_lista(workspace.slug), {"name": "Ata"}, format="json")

        resposta = session_client.post(
            url_shares(workspace.slug, criada.data["id"]),
            {"shared_with": str(create_user.id), "role": PageShare.READ},
            format="json",
        )

        assert resposta.status_code == status.HTTP_400_BAD_REQUEST
        assert PageShare.objects.count() == 0

    def test_o_papel_vem_junto_na_resposta(self, session_client, cliente_da_outra, outra_pessoa, workspace):
        criada = session_client.post(url_lista(workspace.slug), {"name": "Ata"}, format="json")
        session_client.post(
            url_shares(workspace.slug, criada.data["id"]),
            {"shared_with": str(outra_pessoa.id), "role": PageShare.WRITE},
            format="json",
        )

        minha = session_client.get(url_pagina(workspace.slug, criada.data["id"]))
        dela = cliente_da_outra.get(url_pagina(workspace.slug, criada.data["id"]))

        # É por este campo que a tela sabe se pode deixar escrever.
        assert minha.data["share_role"] is None
        assert dela.data["share_role"] == PageShare.WRITE


def url_mover(slug, page_id):
    return f"/api/workspaces/{slug}/my-tasks/pages/{page_id}/move/"


def url_recolher(slug, project_id, page_id):
    return f"/api/workspaces/{slug}/projects/{project_id}/pages/{page_id}/move-to-personal/"


@pytest.mark.django_db
class TestMover:
    def test_pessoal_vira_de_projeto_e_some_da_lista_pessoal(self, session_client, workspace, create_user):
        projeto = Project.objects.create(name="Projeto", identifier="PRJ", workspace=workspace)
        ProjectMember.objects.create(workspace=workspace, project=projeto, member=create_user, role=20)
        criada = session_client.post(url_lista(workspace.slug), {"name": "Rascunho"}, format="json")

        resposta = session_client.post(
            url_mover(workspace.slug, criada.data["id"]), {"project_id": str(projeto.id)}, format="json"
        )

        assert resposta.status_code == status.HTTP_200_OK
        assert ProjectPage.objects.filter(page_id=criada.data["id"], project=projeto).count() == 1
        assert session_client.get(url_lista(workspace.slug)).data == []

    def test_mover_para_projeto_apaga_os_compartilhamentos(
        self, session_client, workspace, create_user, outra_pessoa
    ):
        projeto = Project.objects.create(name="Projeto", identifier="PRJ", workspace=workspace)
        ProjectMember.objects.create(workspace=workspace, project=projeto, member=create_user, role=20)
        criada = session_client.post(url_lista(workspace.slug), {"name": "Rascunho"}, format="json")
        session_client.post(
            url_shares(workspace.slug, criada.data["id"]),
            {"shared_with": str(outra_pessoa.id), "role": PageShare.READ},
            format="json",
        )
        assert PageShare.objects.filter(page_id=criada.data["id"]).count() == 1

        resposta = session_client.post(
            url_mover(workspace.slug, criada.data["id"]), {"project_id": str(projeto.id)}, format="json"
        )

        # No projeto quem manda é o projeto: as duas fontes de acesso juntas
        # fariam "quem pode ler isto?" ter duas respostas.
        assert resposta.data["shares_removed"] == 1
        assert PageShare.objects.filter(page_id=criada.data["id"]).count() == 0

    def test_nao_move_para_projeto_onde_nao_posso_criar(self, session_client, workspace, create_user):
        projeto = Project.objects.create(name="Alheio", identifier="ALH", workspace=workspace)
        criada = session_client.post(url_lista(workspace.slug), {"name": "Rascunho"}, format="json")

        resposta = session_client.post(
            url_mover(workspace.slug, criada.data["id"]), {"project_id": str(projeto.id)}, format="json"
        )

        assert resposta.status_code == status.HTTP_403_FORBIDDEN
        assert ProjectPage.objects.filter(page_id=criada.data["id"]).count() == 0

    def test_de_projeto_volta_para_o_pessoal(self, session_client, workspace, create_user):
        projeto = Project.objects.create(name="Projeto", identifier="PRJ", workspace=workspace)
        ProjectMember.objects.create(workspace=workspace, project=projeto, member=create_user, role=20)
        pagina = Page.objects.create(name="Do projeto", workspace=workspace, owned_by=create_user)
        ProjectPage.objects.create(workspace=workspace, project=projeto, page=pagina)

        resposta = session_client.post(url_recolher(workspace.slug, projeto.id, pagina.id))

        assert resposta.status_code == status.HTTP_204_NO_CONTENT
        assert ProjectPage.objects.filter(page_id=pagina.id).count() == 0
        assert [str(p["id"]) for p in session_client.get(url_lista(workspace.slug)).data] == [str(pagina.id)]

    def test_so_o_dono_recolhe(self, session_client, cliente_da_outra, workspace, create_user, outra_pessoa):
        projeto = Project.objects.create(name="Projeto", identifier="PRJ", workspace=workspace)
        ProjectMember.objects.create(workspace=workspace, project=projeto, member=create_user, role=20)
        ProjectMember.objects.create(workspace=workspace, project=projeto, member=outra_pessoa, role=20)
        pagina = Page.objects.create(name="Do projeto", workspace=workspace, owned_by=create_user)
        ProjectPage.objects.create(workspace=workspace, project=projeto, page=pagina)

        resposta = cliente_da_outra.post(url_recolher(workspace.slug, projeto.id, pagina.id))

        assert resposta.status_code == status.HTTP_403_FORBIDDEN
        assert ProjectPage.objects.filter(page_id=pagina.id).count() == 1
