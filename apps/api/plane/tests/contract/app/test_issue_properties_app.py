# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Configuração das propriedades personalizadas (ADR 0011, P1).

O que se fixa aqui são as travas que, erradas, só aparecem quando já existe
dado dependendo delas: a troca de tipo que perderia valor, o teto, a porta de
admin, e a exclusão que precisa dizer o tamanho do estrago em vez de bloquear.
"""

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from plane.db.models import (
    Issue,
    IssueProperty,
    IssuePropertyOption,
    IssuePropertyValue,
    Project,
    ProjectMember,
    State,
    TETO_DE_PROPRIEDADES,
    User,
    WorkspaceMember,
)

LISTA_URL = "/api/workspaces/{slug}/projects/{project_id}/issue-properties/"
ITEM_URL = "/api/workspaces/{slug}/projects/{project_id}/issue-properties/{pk}/"
OPCAO_URL = "/api/workspaces/{slug}/projects/{project_id}/issue-properties/{pk}/options/{option_id}/"
USO_URL = "/api/workspaces/{slug}/projects/{project_id}/issue-properties/{pk}/options/{option_id}/usage/"
ORDEM_URL = "/api/workspaces/{slug}/projects/{project_id}/issue-properties/reorder/"


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


@pytest.fixture
def session_client(create_user):
    cliente = APIClient()
    cliente.force_authenticate(user=create_user)
    return cliente


def _propriedade(projeto, **campos):
    padrao = dict(
        name="Categoria",
        property_type="select",
        project=projeto,
        workspace=projeto.workspace,
    )
    padrao.update(campos)
    return IssueProperty.objects.create(**padrao)


@pytest.mark.contract
class TestConfiguracao:
    def test_the_six_types_round_trip(self, session_client, workspace, projeto):
        """Os seis tipos da v1, criados pela API e devolvidos na lista."""
        url = LISTA_URL.format(slug=workspace.slug, project_id=projeto.id)
        tipos = ["text", "number", "date", "select", "multi_select", "currency"]
        for tipo in tipos:
            corpo = {"name": f"Campo {tipo}", "property_type": tipo}
            if tipo == "currency":
                corpo |= {"currency": "BRL", "decimal_places": 2}
            if tipo in ("select", "multi_select"):
                corpo["options"] = [{"name": "A", "color": "#f00"}, {"name": "B", "color": "#0f0"}]
            resposta = session_client.post(url, corpo, format="json")
            assert resposta.status_code == status.HTTP_201_CREATED, (tipo, resposta.data)

        lista = session_client.get(url)
        assert [p["property_type"] for p in lista.data["properties"]] == tipos
        assert lista.data["cap"] == TETO_DE_PROPRIEDADES
        selecao = next(p for p in lista.data["properties"] if p["property_type"] == "select")
        assert [o["name"] for o in selecao["options"]] == ["A", "B"]

    def test_the_type_cannot_be_changed(self, session_client, workspace, projeto):
        """Converter texto em número não tem resposta certa para o que já foi escrito."""
        propriedade = _propriedade(projeto, name="Observação", property_type="text")

        resposta = session_client.patch(
            ITEM_URL.format(slug=workspace.slug, project_id=projeto.id, pk=propriedade.id),
            {"property_type": "number"},
            format="json",
        )

        assert resposta.status_code == status.HTTP_400_BAD_REQUEST
        assert "property_type" in resposta.data

    def test_single_select_converts_to_multi(self, session_client, workspace, projeto):
        """A única conversão que não perde nada: cada valor vira lista de um."""
        propriedade = _propriedade(projeto, property_type="select")

        virou = session_client.patch(
            ITEM_URL.format(slug=workspace.slug, project_id=projeto.id, pk=propriedade.id),
            {"property_type": "multi_select"},
            format="json",
        )
        assert virou.status_code == status.HTTP_200_OK

        # E o caminho de volta continua proibido, porque ele perde.
        voltou = session_client.patch(
            ITEM_URL.format(slug=workspace.slug, project_id=projeto.id, pk=propriedade.id),
            {"property_type": "select"},
            format="json",
        )
        assert voltou.status_code == status.HTTP_400_BAD_REQUEST

    def test_currency_needs_a_declared_currency(self, session_client, workspace, projeto):
        """Moeda é da propriedade, não do valor — senão soma-se real com dólar."""
        url = LISTA_URL.format(slug=workspace.slug, project_id=projeto.id)

        sem = session_client.post(url, {"name": "Contrato", "property_type": "currency"}, format="json")
        assert sem.status_code == status.HTTP_400_BAD_REQUEST
        assert "currency" in sem.data

        demais = session_client.post(
            url,
            {"name": "Contrato", "property_type": "currency", "currency": "BRL", "decimal_places": 9},
            format="json",
        )
        assert demais.status_code == status.HTTP_400_BAD_REQUEST

    def test_currency_is_cleared_on_a_non_currency_type(self, session_client, workspace, projeto):
        """Configuração morta vira pergunta seis meses depois."""
        resposta = session_client.post(
            LISTA_URL.format(slug=workspace.slug, project_id=projeto.id),
            {"name": "Peso", "property_type": "number", "currency": "USD"},
            format="json",
        )

        assert resposta.status_code == status.HTTP_201_CREATED
        assert resposta.data["currency"] is None

    def test_the_cap_holds(self, session_client, workspace, projeto):
        """Trinta colunas já é mais do que cabe numa tela."""
        for indice in range(TETO_DE_PROPRIEDADES):
            _propriedade(projeto, name=f"Campo {indice}", property_type="text")

        resposta = session_client.post(
            LISTA_URL.format(slug=workspace.slug, project_id=projeto.id),
            {"name": "Uma a mais", "property_type": "text"},
            format="json",
        )

        assert resposta.status_code == status.HTTP_400_BAD_REQUEST

    def test_two_properties_cannot_share_a_name(self, session_client, workspace, projeto):
        """Duas colunas indistinguíveis na tabela e na exportação."""
        _propriedade(projeto, name="Canal", property_type="text")

        resposta = session_client.post(
            LISTA_URL.format(slug=workspace.slug, project_id=projeto.id),
            {"name": "Canal", "property_type": "text"},
            format="json",
        )

        assert resposta.status_code == status.HTTP_400_BAD_REQUEST

    def test_deleting_an_option_in_use_reports_the_damage(
        self, session_client, workspace, projeto, create_user
    ):
        """O ato não é bloqueado, e a consequência não é silenciosa (ADR 0011).

        Bloquear criaria o incentivo perverso de sempre: a saída mais rápida do
        bloqueio seria apagar a propriedade inteira.
        """
        propriedade = _propriedade(projeto, property_type="select")
        opcao = IssuePropertyOption.objects.create(
            issue_property=propriedade, name="Inbound", project=projeto, workspace=projeto.workspace
        )
        for indice in range(3):
            tarefa = Issue.objects.create(
                name=f"Tarefa {indice}", project=projeto, workspace=projeto.workspace, created_by=create_user
            )
            IssuePropertyValue.objects.create(
                issue=tarefa,
                issue_property=propriedade,
                value_option=opcao,
                project=projeto,
                workspace=projeto.workspace,
            )

        uso = session_client.get(
            USO_URL.format(
                slug=workspace.slug, project_id=projeto.id, pk=propriedade.id, option_id=opcao.id
            )
        )
        assert uso.data["work_items"] == 3

        apagou = session_client.delete(
            OPCAO_URL.format(
                slug=workspace.slug, project_id=projeto.id, pk=propriedade.id, option_id=opcao.id
            )
        )
        assert apagou.status_code == status.HTTP_200_OK
        assert apagou.data["cleared_work_items"] == 3

    def test_the_usage_count_is_work_items_not_rows(
        self, session_client, workspace, projeto, create_user
    ):
        """Seleção múltipla grava uma linha por opção.

        Dizer "4 valores serão perdidos" onde são 2 tarefas assustaria com um
        número que não responde à pergunta de quem está lendo.
        """
        propriedade = _propriedade(projeto, property_type="multi_select")
        opcoes = [
            IssuePropertyOption.objects.create(
                issue_property=propriedade, name=nome, project=projeto, workspace=projeto.workspace
            )
            for nome in ("A", "B")
        ]
        for indice in range(2):
            tarefa = Issue.objects.create(
                name=f"Tarefa {indice}", project=projeto, workspace=projeto.workspace, created_by=create_user
            )
            for opcao in opcoes:
                IssuePropertyValue.objects.create(
                    issue=tarefa,
                    issue_property=propriedade,
                    value_option=opcao,
                    project=projeto,
                    workspace=projeto.workspace,
                )

        lista = session_client.get(LISTA_URL.format(slug=workspace.slug, project_id=projeto.id))

        assert lista.data["properties"][0]["values_count"] == 2  # tarefas, não as 4 linhas

    def test_a_deleted_work_item_does_not_count(
        self, session_client, workspace, projeto, create_user
    ):
        """A junção não passa pelo manager de exclusão lógica.

        É a armadilha que já mordeu esta base duas vezes: sem o filtro
        explícito, a contagem incluiria tarefa que ninguém mais vê.
        """
        propriedade = _propriedade(projeto, property_type="text")
        tarefa = Issue.objects.create(
            name="Excluída", project=projeto, workspace=projeto.workspace, created_by=create_user
        )
        IssuePropertyValue.objects.create(
            issue=tarefa,
            issue_property=propriedade,
            value_text="algo",
            project=projeto,
            workspace=projeto.workspace,
        )
        tarefa.delete()

        lista = session_client.get(LISTA_URL.format(slug=workspace.slug, project_id=projeto.id))

        assert lista.data["properties"][0]["values_count"] == 0

    def test_reorder_sets_the_display_order(self, session_client, workspace, projeto):
        primeira = _propriedade(projeto, name="Primeira", property_type="text")
        segunda = _propriedade(projeto, name="Segunda", property_type="text")

        session_client.post(
            ORDEM_URL.format(slug=workspace.slug, project_id=projeto.id),
            {"order": [str(segunda.id), str(primeira.id)]},
            format="json",
        )

        lista = session_client.get(LISTA_URL.format(slug=workspace.slug, project_id=projeto.id))
        assert [p["name"] for p in lista.data["properties"]] == ["Segunda", "Primeira"]

    def test_configuring_is_an_admin_door(self, workspace, projeto, create_user):
        """Criar propriedade cria trabalho para os outros.

        Ler é de todos, porque preencher valor é de quem pode editar a tarefa.
        """
        membro = User.objects.create(email="membro@evolury.com.br", username="membro", display_name="Membro")
        ProjectMember.objects.create(project=projeto, member=membro, role=15, is_active=True)
        WorkspaceMember.objects.create(workspace=workspace, member=membro, role=15, is_active=True)
        cliente = APIClient()
        cliente.force_authenticate(user=membro)
        url = LISTA_URL.format(slug=workspace.slug, project_id=projeto.id)

        criou = cliente.post(url, {"name": "Canal", "property_type": "text"}, format="json")
        leu = cliente.get(url)

        assert criou.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)
        assert leu.status_code == status.HTTP_200_OK

    def test_deactivating_keeps_the_values(self, session_client, workspace, projeto, create_user):
        """Desativar é o meio-termo que preserva o histórico."""
        propriedade = _propriedade(projeto, property_type="text")
        tarefa = Issue.objects.create(
            name="Tarefa", project=projeto, workspace=projeto.workspace, created_by=create_user
        )
        IssuePropertyValue.objects.create(
            issue=tarefa,
            issue_property=propriedade,
            value_text="guardado",
            project=projeto,
            workspace=projeto.workspace,
        )

        session_client.patch(
            ITEM_URL.format(slug=workspace.slug, project_id=projeto.id, pk=propriedade.id),
            {"is_active": False},
            format="json",
        )

        assert IssuePropertyValue.objects.filter(issue_property=propriedade).count() == 1
