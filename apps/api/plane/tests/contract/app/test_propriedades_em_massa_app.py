# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Preencher uma propriedade personalizada em muitas tarefas (ADR 0019).

É o "preencher a coluna" que a planilha faz e o produto não fazia: escolher
trinta tarefas e dizer que o Canal de todas é Indicação.

O que se fixa aqui é o que separa isto de um laço na tela: **o valor é conferido
uma vez, antes de escrever em qualquer tarefa**. Recusar na décima deixaria nove
preenchidas e vinte e uma não — e ninguém sabendo quais.
"""

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from plane.db.models import (
    Issue,
    IssueActivity,
    IssueProperty,
    IssuePropertyOption,
    IssuePropertyValue,
    Project,
    ProjectMember,
    State,
)

URL = "/api/workspaces/{slug}/projects/{pid}/issue-property-values/"


@pytest.fixture
def projeto(db, workspace, create_user):
    projeto = Project.objects.create(name="Projeto", identifier="PRJ", workspace=workspace, created_by=create_user)
    ProjectMember.objects.create(project=projeto, member=create_user, role=20, is_active=True)
    State.objects.filter(project=projeto).delete()
    State.objects.create(
        name="Pendente", group="backlog", project=projeto, workspace=workspace, color="#000", default=True
    )
    return projeto


@pytest.fixture
def cliente(create_user):
    api = APIClient()
    api.force_authenticate(user=create_user)
    return api


@pytest.fixture
def tarefas(db, projeto, workspace):
    return [Issue.objects.create(name=f"T{i}", project=projeto, workspace=workspace) for i in range(3)]


@pytest.fixture
def canal(db, projeto):
    propriedade = IssueProperty.objects.create(
        name="Canal", property_type="select", project=projeto, workspace=projeto.workspace
    )
    opcoes = [
        IssuePropertyOption.objects.create(
            issue_property=propriedade, name=nome, project=projeto, workspace=projeto.workspace
        )
        for nome in ("Indicação", "Anúncio")
    ]
    return propriedade, opcoes


def valores_de(propriedade, tarefas):
    return {
        str(linha.issue_id): str(linha.value_option_id)
        for linha in IssuePropertyValue.objects.filter(issue_property=propriedade, issue__in=tarefas)
    }


@pytest.mark.contract
class TestPreenchimentoEmMassa:
    def test_fills_the_same_value_in_every_selected_item(self, cliente, workspace, projeto, tarefas, canal):
        propriedade, opcoes = canal

        resposta = cliente.post(
            URL.format(slug=workspace.slug, pid=projeto.id),
            {"issue_ids": [str(t.id) for t in tarefas], "property": str(propriedade.id), "value": str(opcoes[0].id)},
            format="json",
        )

        assert resposta.status_code == status.HTTP_200_OK
        assert resposta.data["updated"] == 3
        assert set(valores_de(propriedade, tarefas).values()) == {str(opcoes[0].id)}

    def test_it_overwrites_what_was_there(self, cliente, workspace, projeto, tarefas, canal):
        propriedade, opcoes = canal
        IssuePropertyValue.objects.create(
            issue=tarefas[0], issue_property=propriedade, value_option=opcoes[1],
            project=projeto, workspace=projeto.workspace,
        )

        cliente.post(
            URL.format(slug=workspace.slug, pid=projeto.id),
            {"issue_ids": [str(t.id) for t in tarefas], "property": str(propriedade.id), "value": str(opcoes[0].id)},
            format="json",
        )

        assert valores_de(propriedade, tarefas)[str(tarefas[0].id)] == str(opcoes[0].id)

    def test_an_empty_value_clears_the_property(self, cliente, workspace, projeto, tarefas, canal):
        propriedade, opcoes = canal
        IssuePropertyValue.objects.create(
            issue=tarefas[0], issue_property=propriedade, value_option=opcoes[0],
            project=projeto, workspace=projeto.workspace,
        )

        cliente.post(
            URL.format(slug=workspace.slug, pid=projeto.id),
            {"issue_ids": [str(tarefas[0].id)], "property": str(propriedade.id), "value": ""},
            format="json",
        )

        assert valores_de(propriedade, tarefas) == {}

    def test_it_records_history_for_every_item(self, cliente, workspace, projeto, tarefas, canal):
        propriedade, opcoes = canal

        cliente.post(
            URL.format(slug=workspace.slug, pid=projeto.id),
            {"issue_ids": [str(t.id) for t in tarefas], "property": str(propriedade.id), "value": str(opcoes[0].id)},
            format="json",
        )

        linhas = IssueActivity.objects.filter(verb="property_updated", issue__in=tarefas)
        assert linhas.count() == 3
        assert set(linhas.values_list("new_value", flat=True)) == {"Indicação"}

    def test_an_invalid_value_writes_nothing(self, cliente, workspace, projeto, tarefas, canal):
        """A conferência vem antes da primeira escrita — senão o pedido pararia
        no meio, com metade das tarefas preenchidas."""
        propriedade, _ = canal

        resposta = cliente.post(
            URL.format(slug=workspace.slug, pid=projeto.id),
            {"issue_ids": [str(t.id) for t in tarefas], "property": str(propriedade.id),
             "value": "00000000-0000-0000-0000-000000000000"},
            format="json",
        )

        assert resposta.status_code == status.HTTP_400_BAD_REQUEST
        assert valores_de(propriedade, tarefas) == {}

    def test_it_refuses_a_property_from_another_project(self, cliente, workspace, projeto, tarefas, create_user):
        vizinho = Project.objects.create(name="Vizinho", identifier="VIZ", workspace=workspace, created_by=create_user)
        alheia = IssueProperty.objects.create(
            name="De fora", property_type="text", project=vizinho, workspace=workspace
        )

        resposta = cliente.post(
            URL.format(slug=workspace.slug, pid=projeto.id),
            {"issue_ids": [str(tarefas[0].id)], "property": str(alheia.id), "value": "x"},
            format="json",
        )

        assert resposta.status_code == status.HTTP_400_BAD_REQUEST

    def test_it_refuses_more_than_the_ceiling(self, cliente, workspace, projeto, canal):
        propriedade, opcoes = canal
        resposta = cliente.post(
            URL.format(slug=workspace.slug, pid=projeto.id),
            {"issue_ids": [str(n) for n in range(501)], "property": str(propriedade.id), "value": str(opcoes[0].id)},
            format="json",
        )
        assert resposta.status_code == status.HTTP_400_BAD_REQUEST
        assert resposta.data["error"] == "TOO_MANY_ISSUES"

    def test_reading_in_bulk_still_works(self, cliente, workspace, projeto, tarefas, canal):
        """O GET da mesma rota é o que a barra usa para mostrar "Vários"."""
        propriedade, opcoes = canal
        cliente.post(
            URL.format(slug=workspace.slug, pid=projeto.id),
            {"issue_ids": [str(tarefas[0].id)], "property": str(propriedade.id), "value": str(opcoes[0].id)},
            format="json",
        )

        resposta = cliente.get(
            URL.format(slug=workspace.slug, pid=projeto.id) + f"?issues={','.join(str(t.id) for t in tarefas)}"
        )

        assert resposta.status_code == status.HTTP_200_OK
        assert resposta.data["values"][str(tarefas[0].id)][str(propriedade.id)] == str(opcoes[0].id)
