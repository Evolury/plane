# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Regressão de GHSA-r68c-48rr-m67f — convites de projeto são porta de admin.

O convite carrega **o e-mail de quem foi convidado e o token bruto** que aceita
o convite. Antes da correção, só `create` tinha `@allow_permission([ROLE.ADMIN])`;
`list`, `retrieve` e `destroy` herdavam apenas `IsAuthenticated`, então qualquer
pessoa do workspace lia — ou apagava — convites de qualquer projeto, inclusive
de projetos dos quais não participa.

Levantado na revisão de releases do upstream de 14/08/2026 e conferido no nosso
código (docs/evolury/processos/historico-de-revisoes.md).
"""

import uuid

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from plane.db.models import Project, ProjectMember, ProjectMemberInvite, User, WorkspaceMember

LISTA_URL = "/api/workspaces/{slug}/projects/{project_id}/invitations/"
ITEM_URL = "/api/workspaces/{slug}/projects/{project_id}/invitations/{pk}/"


def _usuario(email: str) -> User:
    apelido = email.split("@")[0]
    pessoa = User.objects.create(email=email, username=apelido, first_name=apelido)
    pessoa.set_password("x")
    pessoa.save()
    return pessoa


def _cliente(pessoa: User) -> APIClient:
    cliente = APIClient()
    cliente.force_authenticate(user=pessoa)
    return cliente


@pytest.fixture
def projeto(db, workspace, create_user):
    projeto = Project.objects.create(
        name="Projeto", identifier="PRJ", workspace=workspace, created_by=create_user
    )
    ProjectMember.objects.create(project=projeto, member=create_user, role=20, is_active=True)
    return projeto


@pytest.fixture
def convite(db, workspace, projeto, create_user):
    """O que estava exposto: e-mail de quem foi convidado e o token de aceite."""
    return ProjectMemberInvite.objects.create(
        project=projeto,
        workspace=workspace,
        email="convidado@evolury.com.br",
        token=uuid.uuid4().hex,
        role=15,
        created_by=create_user,
    )


@pytest.fixture
def membro_comum(db, workspace, projeto):
    """Membro do projeto — participa, mas não administra."""
    pessoa = _usuario("membro@evolury.com.br")
    WorkspaceMember.objects.create(workspace=workspace, member=pessoa, role=15, is_active=True)
    ProjectMember.objects.create(project=projeto, member=pessoa, role=15, is_active=True)
    return _cliente(pessoa)


@pytest.fixture
def estranho(db, workspace, projeto):
    """Está no workspace, mas não neste projeto — o pior caso do vazamento."""
    pessoa = _usuario("estranho@evolury.com.br")
    WorkspaceMember.objects.create(workspace=workspace, member=pessoa, role=15, is_active=True)
    return _cliente(pessoa)


@pytest.mark.contract
class TestConvitesDeProjeto:
    def test_member_cannot_list_invitations(self, membro_comum, workspace, projeto, convite):
        """Listar entrega e-mail e token de quem foi convidado."""
        resposta = membro_comum.get(LISTA_URL.format(slug=workspace.slug, project_id=projeto.id))

        assert resposta.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED)

    def test_member_cannot_retrieve_an_invitation(self, membro_comum, workspace, projeto, convite):
        resposta = membro_comum.get(
            ITEM_URL.format(slug=workspace.slug, project_id=projeto.id, pk=convite.id)
        )

        assert resposta.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED)

    def test_member_cannot_delete_an_invitation(self, membro_comum, workspace, projeto, convite):
        """Apagar o convite de outra pessoa é sabotagem silenciosa do onboarding."""
        resposta = membro_comum.delete(
            ITEM_URL.format(slug=workspace.slug, project_id=projeto.id, pk=convite.id)
        )

        assert resposta.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED)
        assert ProjectMemberInvite.objects.filter(pk=convite.id).exists()

    def test_an_outsider_cannot_read_invitations(self, estranho, workspace, projeto, convite):
        """Quem nem participa do projeto não deveria enxergar nada dele."""
        resposta = estranho.get(LISTA_URL.format(slug=workspace.slug, project_id=projeto.id))

        assert resposta.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED)

    def test_admin_still_manages_invitations(self, session_client, workspace, projeto, convite):
        """A trava fecha para os outros sem tirar a porta de quem administra."""
        lista = session_client.get(LISTA_URL.format(slug=workspace.slug, project_id=projeto.id))
        assert lista.status_code == status.HTTP_200_OK

        detalhe = session_client.get(
            ITEM_URL.format(slug=workspace.slug, project_id=projeto.id, pk=convite.id)
        )
        assert detalhe.status_code == status.HTTP_200_OK

        remocao = session_client.delete(
            ITEM_URL.format(slug=workspace.slug, project_id=projeto.id, pk=convite.id)
        )
        assert remocao.status_code == status.HTTP_204_NO_CONTENT
        assert not ProjectMemberInvite.objects.filter(pk=convite.id).exists()
