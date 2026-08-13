# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Escolha do estado de conclusão do projeto (ADR 0009).

A configuração entra pelo PATCH comum de projeto. O que se fixa aqui é o
recorte: só estado do PRÓPRIO projeto e só do grupo concluído — sem isso, um id
trocado mandaria o botão de concluir para o estado de outro projeto.
"""

import pytest
from rest_framework import status

from plane.db.models import Project, ProjectMember, State

PROJECT_URL = "/api/workspaces/{slug}/projects/{pk}/"


@pytest.fixture
def projeto(db, workspace, create_user):
    projeto = Project.objects.create(
        name="Projeto", identifier="PRJ", workspace=workspace, created_by=create_user
    )
    ProjectMember.objects.create(project=projeto, member=create_user, role=20, is_active=True)
    return projeto


@pytest.fixture
def concluido(db, projeto, workspace):
    return State.objects.create(
        name="Concluído", group="completed", project=projeto, workspace=workspace, color="#000"
    )


@pytest.mark.contract
class TestProjectCompletionState:
    def test_accepts_a_completed_state_from_the_project(self, session_client, workspace, projeto, concluido):
        response = session_client.patch(
            PROJECT_URL.format(slug=workspace.slug, pk=projeto.id),
            {"completion_state": str(concluido.id)},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        projeto.refresh_from_db()
        assert projeto.completion_state_id == concluido.id

    def test_rejects_a_state_from_another_project(self, session_client, workspace, projeto, create_user):
        vizinho = Project.objects.create(
            name="Vizinho", identifier="VIZ", workspace=workspace, created_by=create_user
        )
        alheio = State.objects.create(
            name="Concluído", group="completed", project=vizinho, workspace=workspace, color="#000"
        )

        response = session_client.patch(
            PROJECT_URL.format(slug=workspace.slug, pk=projeto.id),
            {"completion_state": str(alheio.id)},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        projeto.refresh_from_db()
        assert projeto.completion_state_id is None

    def test_rejects_a_state_outside_the_completed_group(self, session_client, workspace, projeto):
        aberto = State.objects.create(
            name="Em andamento", group="started", project=projeto, workspace=workspace, color="#000"
        )

        response = session_client.patch(
            PROJECT_URL.format(slug=workspace.slug, pk=projeto.id),
            {"completion_state": str(aberto.id)},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        projeto.refresh_from_db()
        assert projeto.completion_state_id is None

    def test_clearing_returns_to_the_automatic_destination(self, session_client, workspace, projeto, concluido):
        """Voltar ao automático é gravar nulo — o resolvedor cuida do resto."""
        projeto.completion_state = concluido
        projeto.save(update_fields=["completion_state"])

        response = session_client.patch(
            PROJECT_URL.format(slug=workspace.slug, pk=projeto.id),
            {"completion_state": None},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        projeto.refresh_from_db()
        assert projeto.completion_state_id is None
