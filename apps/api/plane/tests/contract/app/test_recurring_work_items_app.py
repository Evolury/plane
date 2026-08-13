# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Endpoints das tarefas recorrentes (ADR 0010).

O que se fixa aqui é a fronteira: quem pode criar, o que é recusado antes de
virar agenda errada, e o relógio da regra nascendo junto com ela.
"""

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from plane.db.models import (
    Project,
    ProjectMember,
    RecurringWorkItem,
    State,
    User,
    WorkspaceMember,
)

LISTA_URL = "/api/workspaces/{slug}/projects/{project_id}/recurring-work-items/"
PREVIEW_URL = "/api/workspaces/{slug}/projects/{project_id}/recurring-work-items/preview/"
ITEM_URL = "/api/workspaces/{slug}/projects/{project_id}/recurring-work-items/{pk}/"

SEMANAL = {
    "name": "Relatório semanal",
    "frequency": "weekly",
    "interval": 1,
    "weekdays": [1],
    "time_of_day": "08:00:00",
    "start_date": "2026-08-03",
}


@pytest.fixture
def projeto(db, workspace, create_user):
    projeto = Project.objects.create(
        name="Projeto", identifier="PRJ", workspace=workspace, created_by=create_user
    )
    ProjectMember.objects.create(project=projeto, member=create_user, role=20, is_active=True)
    State.objects.filter(project=projeto).delete()
    State.objects.create(
        name="Em espera", group="backlog", project=projeto, workspace=workspace, color="#000", default=True
    )
    return projeto


@pytest.fixture
def cliente_membro(db, workspace, projeto):
    """Membro do projeto, não admin."""
    membro = User.objects.create(email="membro@evolury.com.br", username="membro")
    membro.set_password("x")
    membro.save()
    WorkspaceMember.objects.create(workspace=workspace, member=membro, role=15)
    ProjectMember.objects.create(project=projeto, member=membro, role=15, is_active=True)
    cliente = APIClient()
    cliente.force_authenticate(user=membro)
    return cliente


@pytest.mark.contract
class TestRecurringWorkItems:
    def test_admin_creates_a_rule_with_its_clock_set(self, session_client, workspace, projeto):
        """A regra nasce com `next_run_at`: sem relógio, o job nunca a enxerga."""
        resposta = session_client.post(
            LISTA_URL.format(slug=workspace.slug, project_id=projeto.id), SEMANAL, format="json"
        )

        assert resposta.status_code == status.HTTP_201_CREATED
        regra = RecurringWorkItem.objects.get(pk=resposta.data["id"])
        assert regra.project_id == projeto.id
        assert regra.next_run_at is not None
        assert resposta.data["next_occurrences"]

    def test_member_cannot_create(self, cliente_membro, workspace, projeto):
        """A regra cria trabalho para os outros — é porta de admin."""
        resposta = cliente_membro.post(
            LISTA_URL.format(slug=workspace.slug, project_id=projeto.id), SEMANAL, format="json"
        )
        assert resposta.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED)

    def test_weekly_without_weekdays_is_rejected(self, session_client, workspace, projeto):
        """Sem dia escolhido a agenda erraria em silêncio, que é o pior jeito."""
        resposta = session_client.post(
            LISTA_URL.format(slug=workspace.slug, project_id=projeto.id),
            {**SEMANAL, "weekdays": []},
            format="json",
        )
        assert resposta.status_code == status.HTTP_400_BAD_REQUEST
        assert "weekdays" in resposta.data

    def test_monthly_without_day_is_rejected(self, session_client, workspace, projeto):
        resposta = session_client.post(
            LISTA_URL.format(slug=workspace.slug, project_id=projeto.id),
            {**SEMANAL, "frequency": "monthly", "monthly_mode": "day_of_month"},
            format="json",
        )
        assert resposta.status_code == status.HTTP_400_BAD_REQUEST
        assert "day_of_month" in resposta.data

    def test_end_on_date_without_date_is_rejected(self, session_client, workspace, projeto):
        resposta = session_client.post(
            LISTA_URL.format(slug=workspace.slug, project_id=projeto.id),
            {**SEMANAL, "end_mode": "on_date"},
            format="json",
        )
        assert resposta.status_code == status.HTTP_400_BAD_REQUEST

    def test_preview_answers_without_saving(self, session_client, workspace, projeto):
        """A pré-visualização é da agenda em edição, não de uma regra salva."""
        resposta = session_client.post(
            PREVIEW_URL.format(slug=workspace.slug, project_id=projeto.id),
            {**SEMANAL, "frequency": "monthly", "monthly_mode": "day_of_month", "day_of_month": 31},
            format="json",
        )

        assert resposta.status_code == status.HTTP_200_OK
        assert len(resposta.data["next_occurrences"]) == 5
        assert RecurringWorkItem.objects.count() == 0

    def test_editing_the_schedule_resets_the_clock(self, session_client, workspace, projeto):
        criada = session_client.post(
            LISTA_URL.format(slug=workspace.slug, project_id=projeto.id), SEMANAL, format="json"
        )
        antes = RecurringWorkItem.objects.get(pk=criada.data["id"]).next_run_at

        resposta = session_client.patch(
            ITEM_URL.format(slug=workspace.slug, project_id=projeto.id, pk=criada.data["id"]),
            {"weekdays": [5]},
            format="json",
        )

        assert resposta.status_code == status.HTTP_200_OK
        depois = RecurringWorkItem.objects.get(pk=criada.data["id"]).next_run_at
        assert depois != antes

    def test_deleting_keeps_the_work_items_already_generated(self, session_client, workspace, projeto):
        """As tarefas geradas são trabalho, não histórico da regra."""
        criada = session_client.post(
            LISTA_URL.format(slug=workspace.slug, project_id=projeto.id), SEMANAL, format="json"
        )

        resposta = session_client.delete(
            ITEM_URL.format(slug=workspace.slug, project_id=projeto.id, pk=criada.data["id"])
        )

        assert resposta.status_code == status.HTTP_204_NO_CONTENT
        assert RecurringWorkItem.objects.filter(pk=criada.data["id"]).count() == 0
