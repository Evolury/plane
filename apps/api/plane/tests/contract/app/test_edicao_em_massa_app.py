# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Preencher campos de muitas tarefas de uma vez (ADR 0019).

O cliente disto já existia no repositório — serviço, store, tipo do payload e as
mensagens de erro traduzidas. O servidor é da edição paga, e é o que se fixa
aqui.

Três regras que só aparecem quando se escreve em muitas de uma vez:

* **etiqueta soma, e não substitui** — o padrão que o Jira levou anos para
  aceitar depois de gente apagar etiqueta achando que estava somando;
* **responsável substitui sempre** — uma tarefa tem um só (ADR 0016), e o banco
  cobra isso com índice único;
* **data é conferida contra o que a tarefa JÁ tem** — e o pedido inteiro é
  recusado, não a metade que passou.
"""

from unittest.mock import patch

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from plane.db.models import (
    Issue,
    IssueAssignee,
    IssueLabel,
    Label,
    Project,
    ProjectMember,
    State,
    User,
    WorkspaceMember,
)

URL = "/api/workspaces/{slug}/projects/{pid}/bulk-operation-issues/"
ATIVIDADE = "plane.app.views.issue.base.issue_activity"


@pytest.fixture
def projeto(db, workspace, create_user):
    projeto = Project.objects.create(name="Projeto", identifier="PRJ", workspace=workspace, created_by=create_user)
    ProjectMember.objects.create(project=projeto, member=create_user, role=20, is_active=True)
    return projeto


@pytest.fixture
def tarefas(db, projeto, workspace):
    return [
        Issue.objects.create(name=f"T{i}", project=projeto, workspace=workspace) for i in range(3)
    ]


@pytest.fixture
def etiquetas(db, projeto, workspace):
    return [
        Label.objects.create(name=nome, project=projeto, workspace=workspace, color="#000")
        for nome in ("Urgente", "Suporte", "Interno")
    ]


def pedir(cliente, workspace, projeto, corpo):
    with patch(ATIVIDADE) as atividade:
        resposta = cliente.post(URL.format(slug=workspace.slug, pid=projeto.id), corpo, format="json")
    return resposta, atividade


def etiquetas_de(tarefa):
    return set(str(x) for x in IssueLabel.objects.filter(issue=tarefa).values_list("label_id", flat=True))


@pytest.mark.contract
class TestCamposSimples:
    def test_sets_the_priority_on_every_selected_item(self, session_client, workspace, projeto, tarefas):
        resposta, _ = pedir(
            session_client, workspace, projeto,
            {"issue_ids": [str(t.id) for t in tarefas], "properties": {"priority": "urgent"}},
        )
        assert resposta.status_code == status.HTTP_200_OK
        assert resposta.data["updated"] == 3
        for tarefa in tarefas:
            tarefa.refresh_from_db()
            assert tarefa.priority == "urgent"

    def test_records_who_edited(self, session_client, workspace, projeto, tarefas, create_user):
        """`bulk_update` não passa pelo `save()`: sem pôr `updated_by` na lista,
        uma edição em massa não teria autor no registro da tarefa."""
        pedir(session_client, workspace, projeto,
              {"issue_ids": [str(tarefas[0].id)], "properties": {"priority": "high"}})
        tarefas[0].refresh_from_db()
        assert tarefas[0].updated_by_id == create_user.id

    def test_refuses_a_state_from_another_project(self, session_client, workspace, projeto, tarefas, create_user):
        vizinho = Project.objects.create(name="Vizinho", identifier="VIZ", workspace=workspace, created_by=create_user)
        alheio = State.objects.create(
            name="Feito", group="completed", project=vizinho, workspace=workspace, color="#000"
        )
        resposta, _ = pedir(
            session_client, workspace, projeto,
            {"issue_ids": [str(tarefas[0].id)], "properties": {"state_id": str(alheio.id)}},
        )
        assert resposta.status_code == status.HTTP_400_BAD_REQUEST
        assert resposta.data["error"] == "STATE_NOT_IN_PROJECT"

    def test_refuses_an_unknown_property(self, session_client, workspace, projeto, tarefas):
        resposta, _ = pedir(
            session_client, workspace, projeto,
            {"issue_ids": [str(tarefas[0].id)], "properties": {"name": "renomeada em massa"}},
        )
        assert resposta.status_code == status.HTTP_400_BAD_REQUEST
        assert resposta.data["error"] == "UNKNOWN_PROPERTY"

    def test_refuses_more_than_the_ceiling(self, session_client, workspace, projeto):
        resposta, _ = pedir(
            session_client, workspace, projeto,
            {"issue_ids": [str(n) for n in range(501)], "properties": {"priority": "low"}},
        )
        assert resposta.status_code == status.HTTP_400_BAD_REQUEST
        assert resposta.data["error"] == "TOO_MANY_ISSUES"


@pytest.mark.contract
class TestModosDeLista:
    def test_add_keeps_the_labels_that_were_there(self, session_client, workspace, projeto, tarefas, etiquetas):
        IssueLabel.objects.create(issue=tarefas[0], label=etiquetas[0], project=projeto, workspace=workspace)

        pedir(session_client, workspace, projeto,
              {"issue_ids": [str(tarefas[0].id)], "properties": {"label_ids": [str(etiquetas[1].id)]}})

        assert etiquetas_de(tarefas[0]) == {str(etiquetas[0].id), str(etiquetas[1].id)}

    def test_add_is_the_default_when_no_mode_is_given(self, session_client, workspace, projeto, tarefas, etiquetas):
        """Sem modo, soma. É o padrão, e é o que impede alguém de apagar
        etiqueta achando que estava acrescentando."""
        IssueLabel.objects.create(issue=tarefas[0], label=etiquetas[0], project=projeto, workspace=workspace)
        pedir(session_client, workspace, projeto,
              {"issue_ids": [str(tarefas[0].id)], "properties": {"label_ids": [str(etiquetas[1].id)]}, "modes": {}})
        assert len(etiquetas_de(tarefas[0])) == 2

    def test_replace_replaces(self, session_client, workspace, projeto, tarefas, etiquetas):
        IssueLabel.objects.create(issue=tarefas[0], label=etiquetas[0], project=projeto, workspace=workspace)

        pedir(session_client, workspace, projeto,
              {"issue_ids": [str(tarefas[0].id)],
               "properties": {"label_ids": [str(etiquetas[1].id)]},
               "modes": {"label_ids": "replace"}})

        assert etiquetas_de(tarefas[0]) == {str(etiquetas[1].id)}

    def test_remove_takes_only_the_asked_label(self, session_client, workspace, projeto, tarefas, etiquetas):
        for etiqueta in etiquetas[:2]:
            IssueLabel.objects.create(issue=tarefas[0], label=etiqueta, project=projeto, workspace=workspace)

        pedir(session_client, workspace, projeto,
              {"issue_ids": [str(tarefas[0].id)],
               "properties": {"label_ids": [str(etiquetas[0].id)]},
               "modes": {"label_ids": "remove"}})

        assert etiquetas_de(tarefas[0]) == {str(etiquetas[1].id)}

    def test_refuses_a_label_from_another_project(self, session_client, workspace, projeto, tarefas, create_user):
        vizinho = Project.objects.create(name="Vizinho", identifier="VIZ", workspace=workspace, created_by=create_user)
        alheia = Label.objects.create(name="De fora", project=vizinho, workspace=workspace, color="#000")
        resposta, _ = pedir(session_client, workspace, projeto,
                            {"issue_ids": [str(tarefas[0].id)], "properties": {"label_ids": [str(alheia.id)]}})
        assert resposta.status_code == status.HTTP_400_BAD_REQUEST
        assert resposta.data["error"] == "LABEL_NOT_IN_PROJECT"


@pytest.mark.contract
class TestResponsavel:
    def test_the_assignee_is_replaced_never_added(self, session_client, workspace, projeto, tarefas, create_user):
        """Uma tarefa tem UM responsável (ADR 0016). Somar seria pedir ao banco
        o que o índice único recusa."""
        outro = User.objects.create(email="outro@evolury.com.br", username="outro")
        WorkspaceMember.objects.create(workspace=workspace, member=outro, role=15)
        ProjectMember.objects.create(project=projeto, member=outro, role=15, is_active=True)
        IssueAssignee.objects.create(issue=tarefas[0], assignee=create_user, project=projeto, workspace=workspace)

        pedir(session_client, workspace, projeto,
              {"issue_ids": [str(tarefas[0].id)], "properties": {"assignee_ids": [str(outro.id)]}})

        responsaveis = list(IssueAssignee.objects.filter(issue=tarefas[0]).values_list("assignee_id", flat=True))
        assert responsaveis == [outro.id]

    def test_refuses_two_assignees(self, session_client, workspace, projeto, tarefas, create_user):
        outro = User.objects.create(email="outro2@evolury.com.br", username="outro2")
        ProjectMember.objects.create(project=projeto, member=outro, role=15, is_active=True)
        resposta, _ = pedir(session_client, workspace, projeto,
                            {"issue_ids": [str(tarefas[0].id)],
                             "properties": {"assignee_ids": [str(create_user.id), str(outro.id)]}})
        assert resposta.status_code == status.HTTP_400_BAD_REQUEST
        assert resposta.data["error"] == "SINGLE_ASSIGNEE_ONLY"

    def test_refuses_someone_from_outside_the_project(self, session_client, workspace, projeto, tarefas):
        de_fora = User.objects.create(email="fora@evolury.com.br", username="fora")
        resposta, _ = pedir(session_client, workspace, projeto,
                            {"issue_ids": [str(tarefas[0].id)], "properties": {"assignee_ids": [str(de_fora.id)]}})
        assert resposta.status_code == status.HTTP_400_BAD_REQUEST
        assert resposta.data["error"] == "ASSIGNEE_NOT_IN_PROJECT"


@pytest.mark.contract
class TestDatas:
    def test_refuses_a_start_date_after_an_existing_target_date(self, session_client, workspace, projeto, tarefas):
        tarefas[0].target_date = "2026-08-10"
        tarefas[0].save()

        resposta, _ = pedir(session_client, workspace, projeto,
                            {"issue_ids": [str(t.id) for t in tarefas],
                             "properties": {"start_date": "2026-08-20"}})

        assert resposta.status_code == status.HTTP_400_BAD_REQUEST
        assert resposta.data["error_message"] == "INVALID_ISSUE_START_DATE"

    def test_nothing_is_written_when_one_item_breaks_the_rule(self, session_client, workspace, projeto, tarefas):
        """Recusa inteira: preencher duas e recusar a terceira deixaria o
        usuário sem saber o que ficou como."""
        tarefas[0].target_date = "2026-08-10"
        tarefas[0].save()

        pedir(session_client, workspace, projeto,
              {"issue_ids": [str(t.id) for t in tarefas], "properties": {"start_date": "2026-08-20"}})

        for tarefa in tarefas:
            tarefa.refresh_from_db()
            assert tarefa.start_date is None

    def test_accepts_coherent_dates(self, session_client, workspace, projeto, tarefas):
        resposta, _ = pedir(session_client, workspace, projeto,
                            {"issue_ids": [str(tarefas[0].id)],
                             "properties": {"start_date": "2026-08-01", "target_date": "2026-08-10"}})
        assert resposta.status_code == status.HTTP_200_OK


@pytest.mark.contract
class TestHistorico:
    def test_it_logs_one_line_per_work_item(self, session_client, workspace, projeto, tarefas):
        _, atividade = pedir(session_client, workspace, projeto,
                             {"issue_ids": [str(t.id) for t in tarefas], "properties": {"priority": "urgent"}})
        assert atividade.delay.call_count == 3

    def test_the_history_receives_the_final_value_of_each_item(
        self, session_client, workspace, projeto, tarefas, etiquetas
    ):
        """O histórico compara pedido com anterior. Mandando o DELTA em vez do
        valor final, "de A para B" viraria "de A para B-menos-A"."""
        import json

        IssueLabel.objects.create(issue=tarefas[0], label=etiquetas[0], project=projeto, workspace=workspace)
        _, atividade = pedir(session_client, workspace, projeto,
                             {"issue_ids": [str(tarefas[0].id)], "properties": {"label_ids": [str(etiquetas[1].id)]}})

        pedido = json.loads(atividade.delay.call_args.kwargs["requested_data"])
        anterior = json.loads(atividade.delay.call_args.kwargs["current_instance"])
        assert set(pedido["label_ids"]) == {str(etiquetas[0].id), str(etiquetas[1].id)}
        assert anterior["label_ids"] == [str(etiquetas[0].id)]

    def test_the_snapshot_is_taken_before_writing(self, session_client, workspace, projeto, tarefas):
        """O retrato do ANTES tem de ser anterior à escrita.

        Tirado depois, ele traz o valor NOVO — e o histórico, que registra a
        diferença entre pedido e anterior, não encontra diferença nenhuma e não
        escreve linha nenhuma. A mudança acontece e some do registro.
        """
        import json

        tarefas[0].priority = "low"
        tarefas[0].save()

        _, atividade = pedir(session_client, workspace, projeto,
                             {"issue_ids": [str(tarefas[0].id)], "properties": {"priority": "urgent"}})

        anterior = json.loads(atividade.delay.call_args.kwargs["current_instance"])
        pedido = json.loads(atividade.delay.call_args.kwargs["requested_data"])
        assert anterior["priority"] == "low"
        assert pedido["priority"] == "urgent"

    def test_it_does_not_notify_item_by_item(self, session_client, workspace, projeto, tarefas):
        """Uma edição é um evento; duzentas são um preenchimento (ADR 0018)."""
        _, atividade = pedir(session_client, workspace, projeto,
                             {"issue_ids": [str(tarefas[0].id)], "properties": {"priority": "low"}})
        assert atividade.delay.call_args.kwargs["notification"] is False


@pytest.mark.contract
class TestPermissao:
    def test_a_guest_cannot_fill_other_peoples_work_items(self, api_client, workspace, projeto, tarefas):
        convidado = User.objects.create(email="convidado@evolury.com.br", username="convidado")
        WorkspaceMember.objects.create(workspace=workspace, member=convidado, role=5)
        ProjectMember.objects.create(project=projeto, member=convidado, role=5, is_active=True)
        cliente = APIClient()
        cliente.force_authenticate(user=convidado)

        resposta = cliente.post(
            URL.format(slug=workspace.slug, pid=projeto.id),
            {"issue_ids": [str(tarefas[0].id)], "properties": {"priority": "urgent"}},
            format="json",
        )

        assert resposta.status_code == status.HTTP_403_FORBIDDEN
        tarefas[0].refresh_from_db()
        assert tarefas[0].priority == "none"
