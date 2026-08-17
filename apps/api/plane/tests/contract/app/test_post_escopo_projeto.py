# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Criar coisa DENTRO de um projeto exige estar no projeto.

Defeito da revisão do upstream (SECUR-247): em ``ProjectBasePermission`` e
``ProjectMemberPermission``, o ramo do POST consultava ``WorkspaceMember`` e
nunca ``ProjectMember`` com ``project_id``. O comentário do próprio código
dizia a intenção — *"only workspace owners or admins can create the projects"*
— mas o teste pegava **todo** POST, e a maioria dos POST que passam por essas
classes cria coisa dentro de um projeto que já existe.

Medido antes da correção, com um membro do workspace que NÃO participa do
projeto: publicava o quadro de um projeto alheio na web (``POST
project-deploy-boards/``) e arquivava projeto alheio pela API pública.

Publicar é o pior dos dois: transforma um projeto interno em página aberta.

Corrigir era escolher a régua certa e não a mais apertada. Os POST afetados
passam a responder à mesma checagem que os PATCH e DELETE das mesmas classes
já respondiam — nem mais frouxa, nem mais rígida. Por isso cada teste de recusa
aqui tem um par que prova que quem pode continua podendo: apertar demais também
é defeito, e um ``return False`` chapado passaria em metade deste arquivo.
"""

from uuid import uuid4

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from plane.db.models import DeployBoard, Project, ProjectMember, User, WorkspaceMember


def quadro_publicado_url(slug, project_id):
    return f"/api/workspaces/{slug}/projects/{project_id}/project-deploy-boards/"


@pytest.fixture
def projeto_alheio(db, workspace):
    """Um projeto de outra pessoa; quem testa não participa dele."""
    marca = uuid4().hex[:8]
    dono = User.objects.create(email=f"dono-{marca}@plane.so", username=f"dono_{marca}")
    dono.set_password("test-password")
    dono.save()
    WorkspaceMember.objects.create(workspace=workspace, member=dono, role=20)
    projeto = Project.objects.create(name="Alheio", identifier="ALH", workspace=workspace, created_by=dono)
    ProjectMember.objects.create(project=projeto, member=dono, workspace=workspace, role=20)
    return projeto


@pytest.fixture
def cliente_de_fora(db, workspace):
    """Membro do workspace, e membro de OUTRO projeto.

    A participação no outro projeto é de propósito: sem ela, a recusa poderia
    vir de "não participa de nada", que não é o recorte em teste.
    """
    marca = uuid4().hex[:8]
    de_fora = User.objects.create(email=f"defora-{marca}@plane.so", username=f"defora_{marca}")
    de_fora.set_password("test-password")
    de_fora.save()
    WorkspaceMember.objects.create(workspace=workspace, member=de_fora, role=15)
    seu_projeto = Project.objects.create(name="Dele", identifier="DEL", workspace=workspace, created_by=de_fora)
    ProjectMember.objects.create(project=seu_projeto, member=de_fora, workspace=workspace, role=15)
    cliente = APIClient()
    cliente.force_authenticate(user=de_fora)
    return cliente


@pytest.mark.contract
class TestPublicarQuadro:
    @pytest.mark.django_db
    def test_de_fora_nao_publica_projeto_alheio(self, cliente_de_fora, workspace, projeto_alheio):
        resposta = cliente_de_fora.post(
            quadro_publicado_url(workspace.slug, projeto_alheio.id), {"is_comments_enabled": True}, format="json"
        )
        assert resposta.status_code == status.HTTP_403_FORBIDDEN, f"respondeu {resposta.status_code}"

    @pytest.mark.django_db
    def test_e_o_projeto_continua_sem_quadro_publicado(self, cliente_de_fora, workspace, projeto_alheio):
        """A promessa é o 403; o cumprimento é não existir quadro no banco."""
        cliente_de_fora.post(
            quadro_publicado_url(workspace.slug, projeto_alheio.id), {"is_comments_enabled": True}, format="json"
        )
        assert not DeployBoard.objects.filter(entity_identifier=projeto_alheio.id).exists()

    @pytest.mark.django_db
    def test_membro_do_projeto_continua_publicando(self, db, workspace, create_user):
        """O outro lado: o guarda não pode ter fechado a porta de quem pode."""
        projeto = Project.objects.create(name="Meu", identifier="MEU", workspace=workspace, created_by=create_user)
        ProjectMember.objects.create(project=projeto, member=create_user, workspace=workspace, role=20)
        cliente = APIClient()
        cliente.force_authenticate(user=create_user)

        resposta = cliente.post(
            quadro_publicado_url(workspace.slug, projeto.id), {"is_comments_enabled": True}, format="json"
        )
        assert resposta.status_code == status.HTTP_200_OK, (
            f"{resposta.status_code}: {getattr(resposta, 'data', None)!r}"
        )
        assert DeployBoard.objects.filter(entity_identifier=projeto.id).exists()


@pytest.mark.contract
class TestArquivarPelaApiPublica:
    """A mesma falha na `ProjectBasePermission`, pela porta da API pública."""

    @pytest.mark.django_db
    def test_de_fora_nao_arquiva_projeto_alheio(self, api_key_client, workspace, create_user, projeto_alheio):
        # O dono do token participa de OUTRO projeto do workspace.
        seu = Project.objects.create(name="Dele", identifier="DEL", workspace=workspace, created_by=create_user)
        ProjectMember.objects.create(project=seu, member=create_user, workspace=workspace, role=20)

        resposta = api_key_client.post(f"/api/v1/workspaces/{workspace.slug}/projects/{projeto_alheio.id}/archive/")

        assert resposta.status_code == status.HTTP_403_FORBIDDEN, f"respondeu {resposta.status_code}"
        projeto_alheio.refresh_from_db()
        assert projeto_alheio.archived_at is None

    @pytest.mark.django_db
    def test_criar_projeto_continua_sendo_decisao_de_workspace(self, api_key_client, workspace):
        """A porta que o atalho existia para abrir precisa continuar aberta.

        Não há projeto na URL — não existe participação a consultar. Se este
        teste ficar vermelho, a correção passou do ponto e ninguém mais cria
        projeto nenhum.
        """
        resposta = api_key_client.post(
            f"/api/v1/workspaces/{workspace.slug}/projects/",
            {"name": "Projeto novo", "identifier": "PNOV"},
            format="json",
        )
        assert resposta.status_code == status.HTTP_201_CREATED, (
            f"{resposta.status_code}: {getattr(resposta, 'data', None)!r}"
        )
