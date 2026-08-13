# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Endpoints das tarefas recorrentes (ADR 0010, revisão 13/08/2026).

O que se fixa aqui é a fronteira: quem pode criar, as travas da origem — as que
impedem a série de virar árvore —, e o relógio da regra nascendo junto com ela.
"""

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from plane.db.models import (
    Issue,
    Project,
    ProjectMember,
    RecurringWorkItem,
    RecurringWorkItemOccurrence,
    State,
    User,
    WorkspaceMember,
)

LISTA_URL = "/api/workspaces/{slug}/projects/{project_id}/recurring-work-items/"
PREVIEW_URL = "/api/workspaces/{slug}/projects/{project_id}/recurring-work-items/preview/"
ITEM_URL = "/api/workspaces/{slug}/projects/{project_id}/recurring-work-items/{pk}/"
PARA_TAREFA_URL = "/api/workspaces/{slug}/projects/{project_id}/recurring-work-items/for-issue/{issue_id}/"

AGENDA_SEMANAL = {
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
def origem(db, projeto, create_user):
    return Issue.objects.create(
        name="Relatório semanal", project=projeto, workspace=projeto.workspace, created_by=create_user
    )


def _payload(origem, **campos):
    dados = {**AGENDA_SEMANAL, "source_issue": str(origem.id)}
    dados.update(campos)
    return dados


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
    def test_admin_creates_a_rule_with_its_clock_set(self, session_client, workspace, projeto, origem):
        """A regra nasce com `next_run_at`: sem relógio, o job nunca a enxerga."""
        resposta = session_client.post(
            LISTA_URL.format(slug=workspace.slug, project_id=projeto.id), _payload(origem), format="json"
        )

        assert resposta.status_code == status.HTTP_201_CREATED
        regra = RecurringWorkItem.objects.get(pk=resposta.data["id"])
        assert regra.project_id == projeto.id
        assert str(regra.source_issue_id) == str(origem.id)
        assert regra.next_run_at is not None
        assert resposta.data["next_occurrences"]
        assert resposta.data["source_issue_detail"]["name"] == "Relatório semanal"

    def test_member_cannot_create_but_can_read(self, cliente_membro, workspace, projeto, origem):
        """Escrever é porta de admin; ler é de todos — o selo é informação."""
        criada = cliente_membro.post(
            LISTA_URL.format(slug=workspace.slug, project_id=projeto.id), _payload(origem), format="json"
        )
        assert criada.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED)

        lista = cliente_membro.get(LISTA_URL.format(slug=workspace.slug, project_id=projeto.id))
        assert lista.status_code == status.HTTP_200_OK

    def test_one_rule_per_task(self, session_client, workspace, projeto, origem):
        """O interruptor "Repetir" liga UMA agenda, não uma coleção delas."""
        session_client.post(
            LISTA_URL.format(slug=workspace.slug, project_id=projeto.id), _payload(origem), format="json"
        )
        resposta = session_client.post(
            LISTA_URL.format(slug=workspace.slug, project_id=projeto.id), _payload(origem), format="json"
        )
        assert resposta.status_code == status.HTTP_400_BAD_REQUEST

    def test_a_generated_task_cannot_become_a_source(self, session_client, workspace, projeto, origem, create_user):
        """A trava que impede a série de virar árvore — e que dá o rastro."""
        gerada = Issue.objects.create(
            name="Relatório semanal", project=projeto, workspace=projeto.workspace, created_by=create_user
        )
        regra = RecurringWorkItem.objects.create(
            source_issue=origem,
            project=projeto,
            workspace=projeto.workspace,
            frequency="weekly",
            interval=1,
            weekdays=[1],
            time_of_day="08:00:00",
            start_date="2026-08-03",
            created_by=create_user,
        )
        RecurringWorkItemOccurrence.objects.create(
            recurring_work_item=regra,
            workspace=projeto.workspace,
            scheduled_for="2026-08-10T11:00:00Z",
            issue=gerada,
        )

        resposta = session_client.post(
            LISTA_URL.format(slug=workspace.slug, project_id=projeto.id), _payload(gerada), format="json"
        )
        assert resposta.status_code == status.HTTP_400_BAD_REQUEST
        assert "source_issue" in resposta.data

    def test_a_subtask_cannot_become_a_source(self, session_client, workspace, projeto, origem, create_user):
        filha = Issue.objects.create(
            name="Parte do relatório",
            parent=origem,
            project=projeto,
            workspace=projeto.workspace,
            created_by=create_user,
        )
        resposta = session_client.post(
            LISTA_URL.format(slug=workspace.slug, project_id=projeto.id), _payload(filha), format="json"
        )
        assert resposta.status_code == status.HTTP_400_BAD_REQUEST

    def test_for_issue_tells_each_role(self, session_client, workspace, projeto, origem, create_user):
        """A seção "Repetir" do cartão pergunta aqui: origem, gerada, ou nada."""
        criada = session_client.post(
            LISTA_URL.format(slug=workspace.slug, project_id=projeto.id), _payload(origem), format="json"
        )
        gerada = Issue.objects.create(
            name="Relatório semanal", project=projeto, workspace=projeto.workspace, created_by=create_user
        )
        RecurringWorkItemOccurrence.objects.create(
            recurring_work_item_id=criada.data["id"],
            workspace=projeto.workspace,
            scheduled_for="2026-08-10T11:00:00Z",
            issue=gerada,
        )
        comum = Issue.objects.create(
            name="Avulsa", project=projeto, workspace=projeto.workspace, created_by=create_user
        )

        como_origem = session_client.get(
            PARA_TAREFA_URL.format(slug=workspace.slug, project_id=projeto.id, issue_id=origem.id)
        )
        como_gerada = session_client.get(
            PARA_TAREFA_URL.format(slug=workspace.slug, project_id=projeto.id, issue_id=gerada.id)
        )
        como_comum = session_client.get(
            PARA_TAREFA_URL.format(slug=workspace.slug, project_id=projeto.id, issue_id=comum.id)
        )

        assert como_origem.data["role"] == "source"
        assert como_gerada.data["role"] == "occurrence"
        assert como_gerada.data["rule"]["source_issue_detail"]["sequence_id"] == origem.sequence_id
        assert como_comum.data["role"] is None

    def test_weekly_without_weekdays_is_rejected(self, session_client, workspace, projeto, origem):
        """Sem dia escolhido a agenda erraria em silêncio, que é o pior jeito."""
        resposta = session_client.post(
            LISTA_URL.format(slug=workspace.slug, project_id=projeto.id),
            _payload(origem, weekdays=[]),
            format="json",
        )
        assert resposta.status_code == status.HTTP_400_BAD_REQUEST
        assert "weekdays" in resposta.data

    def test_monthly_without_day_is_rejected(self, session_client, workspace, projeto, origem):
        resposta = session_client.post(
            LISTA_URL.format(slug=workspace.slug, project_id=projeto.id),
            _payload(origem, frequency="monthly", monthly_mode="day_of_month"),
            format="json",
        )
        assert resposta.status_code == status.HTTP_400_BAD_REQUEST
        assert "day_of_month" in resposta.data

    def test_end_on_date_without_date_is_rejected(self, session_client, workspace, projeto, origem):
        resposta = session_client.post(
            LISTA_URL.format(slug=workspace.slug, project_id=projeto.id),
            _payload(origem, end_mode="on_date"),
            format="json",
        )
        assert resposta.status_code == status.HTTP_400_BAD_REQUEST

    def test_preview_answers_without_saving(self, session_client, workspace, projeto, origem):
        """A pré-visualização é da agenda em edição, não de uma regra salva."""
        resposta = session_client.post(
            PREVIEW_URL.format(slug=workspace.slug, project_id=projeto.id),
            _payload(origem, frequency="monthly", monthly_mode="day_of_month", day_of_month=31),
            format="json",
        )

        assert resposta.status_code == status.HTTP_200_OK
        assert len(resposta.data["next_occurrences"]) == 5
        assert RecurringWorkItem.objects.count() == 0

    def test_editing_the_schedule_resets_the_clock(self, session_client, workspace, projeto, origem):
        criada = session_client.post(
            LISTA_URL.format(slug=workspace.slug, project_id=projeto.id), _payload(origem), format="json"
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

    def test_deleting_keeps_the_work_items_already_generated(self, session_client, workspace, projeto, origem):
        """As tarefas geradas são trabalho, não histórico da regra."""
        criada = session_client.post(
            LISTA_URL.format(slug=workspace.slug, project_id=projeto.id), _payload(origem), format="json"
        )

        resposta = session_client.delete(
            ITEM_URL.format(slug=workspace.slug, project_id=projeto.id, pk=criada.data["id"])
        )

        assert resposta.status_code == status.HTTP_204_NO_CONTENT
        assert RecurringWorkItem.objects.filter(pk=criada.data["id"]).count() == 0
        assert Issue.objects.filter(pk=origem.id).count() == 1
