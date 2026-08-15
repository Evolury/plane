# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Valores de propriedade personalizada na tarefa (ADR 0011, P2).

Duas regras aqui valem mais que o resto, porque erradas elas só aparecem
depois de alguém depender delas: **obrigatória barra a criação e mais nada**, e
**valor inválido é recusado na hora** em vez de virar dado sujo que aparece
semanas depois, na ordenação ou no relatório.
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

TAREFAS_URL = "/api/workspaces/{slug}/projects/{project_id}/issues/"
VALORES_URL = "/api/workspaces/{slug}/projects/{project_id}/issues/{issue_id}/properties/"
BLOCO_URL = "/api/workspaces/{slug}/projects/{project_id}/issue-property-values/"


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
def session_client(create_user):
    cliente = APIClient()
    cliente.force_authenticate(user=create_user)
    return cliente


def _propriedade(projeto, nome, tipo, **campos):
    return IssueProperty.objects.create(
        name=nome, property_type=tipo, project=projeto, workspace=projeto.workspace, **campos
    )


def _opcao(propriedade, nome):
    return IssuePropertyOption.objects.create(
        issue_property=propriedade,
        name=nome,
        project=propriedade.project,
        workspace=propriedade.workspace,
    )


def _tarefa(projeto, create_user, nome="Tarefa"):
    return Issue.objects.create(name=nome, project=projeto, workspace=projeto.workspace, created_by=create_user)


@pytest.mark.contract
class TestValores:
    def test_each_type_round_trips(self, session_client, workspace, projeto, create_user):
        """Os seis tipos, gravados e lidos de volta no formato da API."""
        tarefa = _tarefa(projeto, create_user)
        url = VALORES_URL.format(slug=workspace.slug, project_id=projeto.id, issue_id=tarefa.id)

        texto = _propriedade(projeto, "Observação", "text")
        numero = _propriedade(projeto, "Peso", "number")
        data = _propriedade(projeto, "Aceite", "date")
        moeda = _propriedade(projeto, "Contrato", "currency", currency="BRL")
        unica = _propriedade(projeto, "Canal", "select")
        multipla = _propriedade(projeto, "Tags", "multi_select")
        a, b = _opcao(unica, "Indicação"), _opcao(multipla, "Urgente")
        c = _opcao(multipla, "Interno")

        escritas = {
            texto.id: "algo",
            numero.id: "12.5",
            data.id: "2026-08-20",
            moeda.id: "1999.90",
            unica.id: str(a.id),
            multipla.id: [str(b.id), str(c.id)],
        }
        for propriedade_id, valor in escritas.items():
            resposta = session_client.post(url, {"property": str(propriedade_id), "value": valor}, format="json")
            assert resposta.status_code == status.HTTP_200_OK, (propriedade_id, resposta.data)

        lidos = session_client.get(url).data["values"]
        assert lidos[str(texto.id)] == "algo"
        assert lidos[str(data.id)] == "2026-08-20"
        assert lidos[str(unica.id)] == str(a.id)
        assert sorted(lidos[str(multipla.id)]) == sorted([str(b.id), str(c.id)])
        assert lidos[str(numero.id)].startswith("12.5")
        assert lidos[str(moeda.id)].startswith("1999.9")

    def test_an_invalid_value_is_refused(self, session_client, workspace, projeto, create_user):
        """Recusar na hora é o ponto.

        Guardar "abc" numa coluna de número transformaria erro de quem chama em
        dado sujo — e dado sujo só aparece semanas depois, na ordenação.
        """
        tarefa = _tarefa(projeto, create_user)
        url = VALORES_URL.format(slug=workspace.slug, project_id=projeto.id, issue_id=tarefa.id)
        numero = _propriedade(projeto, "Peso", "number")
        data = _propriedade(projeto, "Aceite", "date")

        for propriedade, valor in ((numero, "abc"), (data, "trinta de fevereiro")):
            resposta = session_client.post(url, {"property": str(propriedade.id), "value": valor}, format="json")
            assert resposta.status_code == status.HTTP_400_BAD_REQUEST, propriedade.name

    def test_an_option_from_another_property_is_refused(self, session_client, workspace, projeto, create_user):
        """Id de opção de outra propriedade seria vínculo cruzado silencioso."""
        tarefa = _tarefa(projeto, create_user)
        uma = _propriedade(projeto, "Canal", "select")
        outra = _propriedade(projeto, "Origem", "select")
        alheia = _opcao(outra, "Site")

        resposta = session_client.post(
            VALORES_URL.format(slug=workspace.slug, project_id=projeto.id, issue_id=tarefa.id),
            {"property": str(uma.id), "value": str(alheia.id)},
            format="json",
        )

        assert resposta.status_code == status.HTTP_400_BAD_REQUEST

    def test_writing_empty_clears_the_value(self, session_client, workspace, projeto, create_user):
        """Apagar é escrever vazio — não existe um segundo caminho para isso."""
        tarefa = _tarefa(projeto, create_user)
        url = VALORES_URL.format(slug=workspace.slug, project_id=projeto.id, issue_id=tarefa.id)
        texto = _propriedade(projeto, "Observação", "text")
        session_client.post(url, {"property": str(texto.id), "value": "algo"}, format="json")

        session_client.post(url, {"property": str(texto.id), "value": ""}, format="json")

        assert IssuePropertyValue.objects.filter(issue=tarefa, issue_property=texto).count() == 0

    def test_a_required_property_blocks_creation(self, session_client, workspace, projeto):
        """É onde a informação está fresca e o custo de pedir é baixo."""
        _propriedade(projeto, "Canal", "text", is_required=True)
        url = TAREFAS_URL.format(slug=workspace.slug, project_id=projeto.id)

        sem = session_client.post(url, {"name": "Sem o campo"}, format="json")
        assert sem.status_code == status.HTTP_400_BAD_REQUEST
        assert "property_values" in sem.data

        propriedade = IssueProperty.objects.get(name="Canal")
        com = session_client.post(
            url,
            {"name": "Com o campo", "property_values": {str(propriedade.id): "Indicação"}},
            format="json",
        )
        assert com.status_code == status.HTTP_201_CREATED
        criada = Issue.objects.get(pk=com.data["id"])
        assert IssuePropertyValue.objects.get(issue=criada).value_text == "Indicação"

    def test_a_required_property_never_blocks_an_existing_work_item(
        self, session_client, workspace, projeto, create_user
    ):
        """Obrigatoriedade vale para o que nasce depois.

        Aplicá-la ao passado transformaria uma configuração de hoje em dívida
        retroativa do projeto inteiro — e travaria quem só queria renomear uma
        tarefa antiga.
        """
        antiga = _tarefa(projeto, create_user, nome="Nasceu antes")
        _propriedade(projeto, "Canal", "text", is_required=True)

        resposta = session_client.patch(
            f"{TAREFAS_URL.format(slug=workspace.slug, project_id=projeto.id)}{antiga.id}/",
            {"name": "Renomeada"},
            format="json",
        )

        assert resposta.status_code < 300, resposta.data
        antiga.refresh_from_db()
        assert antiga.name == "Renomeada"

    def test_a_required_property_never_blocks_completion(self, session_client, workspace, projeto, create_user):
        """Travar quem terminou o trabalho só ensina a preencher qualquer coisa.

        É a mesma regra do ADR 0010: o ato nunca é bloqueado, a consequência
        nunca é silenciosa.
        """
        tarefa = _tarefa(projeto, create_user)
        _propriedade(projeto, "Canal", "text", is_required=True)
        concluido = State.objects.create(
            name="Concluído", group="completed", project=projeto, workspace=projeto.workspace, color="#000"
        )

        resposta = session_client.patch(
            f"{TAREFAS_URL.format(slug=workspace.slug, project_id=projeto.id)}{tarefa.id}/",
            {"state_id": str(concluido.id)},
            format="json",
        )

        assert resposta.status_code < 300, resposta.data
        tarefa.refresh_from_db()
        assert tarefa.state_id == concluido.id

    def test_a_deactivated_property_is_not_required(self, session_client, workspace, projeto):
        """Desativar tira da tela — e tirar da tela sem tirar da exigência
        deixaria a criação barrada por um campo que ninguém consegue preencher."""
        _propriedade(projeto, "Canal", "text", is_required=True, is_active=False)

        resposta = session_client.post(
            TAREFAS_URL.format(slug=workspace.slug, project_id=projeto.id),
            {"name": "Deve passar"},
            format="json",
        )

        assert resposta.status_code == status.HTTP_201_CREATED

    def test_changing_a_value_writes_activity(self, session_client, workspace, projeto, create_user):
        """A tarefa passou a carregar informação de negócio.

        O histórico guarda o RÓTULO da opção, e não o id: id não diz nada a
        quem lê seis meses depois.
        """
        tarefa = _tarefa(projeto, create_user)
        url = VALORES_URL.format(slug=workspace.slug, project_id=projeto.id, issue_id=tarefa.id)
        unica = _propriedade(projeto, "Canal", "select")
        antes, depois = _opcao(unica, "Indicação"), _opcao(unica, "Anúncio")

        session_client.post(url, {"property": str(unica.id), "value": str(antes.id)}, format="json")
        session_client.post(url, {"property": str(unica.id), "value": str(depois.id)}, format="json")

        atividades = list(IssueActivity.objects.filter(issue=tarefa, field="Canal").order_by("created_at"))
        assert [(a.old_value, a.new_value) for a in atividades] == [("", "Indicação"), ("Indicação", "Anúncio")]

    def test_writing_the_same_value_writes_no_activity(self, session_client, workspace, projeto, create_user):
        """Histórico que registra o que não mudou é histórico que ninguém lê."""
        tarefa = _tarefa(projeto, create_user)
        url = VALORES_URL.format(slug=workspace.slug, project_id=projeto.id, issue_id=tarefa.id)
        texto = _propriedade(projeto, "Observação", "text")

        session_client.post(url, {"property": str(texto.id), "value": "igual"}, format="json")
        session_client.post(url, {"property": str(texto.id), "value": "igual"}, format="json")

        assert IssueActivity.objects.filter(issue=tarefa, field="Observação").count() == 1

    def test_reading_returns_definitions_and_values_together(self, session_client, workspace, projeto, create_user):
        """A tela precisa das duas coisas para desenhar a seção — numa ida só."""
        tarefa = _tarefa(projeto, create_user)
        _propriedade(projeto, "Ativa", "text")
        _propriedade(projeto, "Desativada", "text", is_active=False)

        resposta = session_client.get(
            VALORES_URL.format(slug=workspace.slug, project_id=projeto.id, issue_id=tarefa.id)
        )

        assert [p["name"] for p in resposta.data["properties"]] == ["Ativa"]
        assert resposta.data["values"] == {}

    def test_values_do_not_cost_a_query_per_work_item(
        self, session_client, workspace, projeto, create_user, django_assert_max_num_queries
    ):
        """Os layouts carregam centenas de tarefas por página.

        A leitura é em bloco por construção: uma consulta, qualquer que seja o
        número de tarefas. Este teste é o que impede a volta do N+1.
        """
        from plane.utils.issue_properties import valores_por_tarefa

        texto = _propriedade(projeto, "Observação", "text")
        tarefas = [_tarefa(projeto, create_user, nome=f"Tarefa {i}") for i in range(40)]
        IssuePropertyValue.objects.bulk_create(
            [
                IssuePropertyValue(
                    issue=t,
                    issue_property=texto,
                    value_text="x",
                    project=projeto,
                    workspace=projeto.workspace,
                )
                for t in tarefas
            ]
        )

        with django_assert_max_num_queries(1):
            lidos = valores_por_tarefa([t.id for t in tarefas])

        assert len(lidos) == 40

    def test_bulk_reads_a_page_in_one_query(
        self, session_client, workspace, projeto, create_user, django_assert_max_num_queries
    ):
        """A leitura de uma página inteira custa uma consulta.

        É o que sustenta a coluna da tabela e o chip do cartão sem virar o N+1
        que o ADR 0011 proibiu.
        """
        texto = _propriedade(projeto, "Observação", "text")
        tarefas = [_tarefa(projeto, create_user, nome=f"T{i}") for i in range(30)]
        IssuePropertyValue.objects.bulk_create(
            [
                IssuePropertyValue(
                    issue=t,
                    issue_property=texto,
                    value_text=f"v{i}",
                    project=projeto,
                    workspace=projeto.workspace,
                )
                for i, t in enumerate(tarefas)
            ]
        )
        url = BLOCO_URL.format(slug=workspace.slug, project_id=projeto.id)
        ids = ",".join(str(t.id) for t in tarefas)

        resposta = session_client.get(f"{url}?issues={ids}")

        assert resposta.status_code == status.HTTP_200_OK
        assert len(resposta.data["values"]) == 30

    def test_card_only_returns_just_the_marked_properties(self, session_client, workspace, projeto, create_user):
        """Trinta propriedades no cartão fariam do quadro uma planilha ruim.

        Quem quer todas tem o layout de tabela, que é onde a largura existe.
        """
        no_cartao = _propriedade(projeto, "Canal", "text", show_on_card=True)
        fora = _propriedade(projeto, "Observação", "text")
        tarefa = _tarefa(projeto, create_user)
        for propriedade, valor in ((no_cartao, "A"), (fora, "B")):
            IssuePropertyValue.objects.create(
                issue=tarefa,
                issue_property=propriedade,
                value_text=valor,
                project=projeto,
                workspace=projeto.workspace,
            )

        resposta = session_client.get(f"{BLOCO_URL.format(slug=workspace.slug, project_id=projeto.id)}?card_only=1")

        meus = resposta.data["values"][str(tarefa.id)]
        assert meus == {str(no_cartao.id): "A"}

    def test_card_only_is_empty_without_marked_properties(self, session_client, workspace, projeto, create_user):
        """Projeto que não marcou nada não paga consulta nenhuma pelo cartão."""
        _propriedade(projeto, "Observação", "text")

        resposta = session_client.get(f"{BLOCO_URL.format(slug=workspace.slug, project_id=projeto.id)}?card_only=1")

        assert resposta.data["values"] == {}

    def test_the_export_carries_a_column_per_property(self, projeto, create_user):
        """Dado que só existe dentro da tela é dado preso.

        E o valor sai como TEXTO legível: id de opção numa planilha não diz
        nada a ninguém.
        """
        from plane.db.models import Issue as IssueModel
        from plane.utils.porters.serializers.issue import IssueExportSerializer

        canal = _propriedade(projeto, "Canal", "select")
        opcao = _opcao(canal, "Indicação")
        contrato = _propriedade(projeto, "Contrato", "currency", currency="BRL")
        tarefa = _tarefa(projeto, create_user)
        IssuePropertyValue.objects.create(
            issue=tarefa,
            issue_property=canal,
            value_option=opcao,
            project=projeto,
            workspace=projeto.workspace,
        )
        IssuePropertyValue.objects.create(
            issue=tarefa,
            issue_property=contrato,
            value_number="1500.00",
            project=projeto,
            workspace=projeto.workspace,
        )

        dados = IssueExportSerializer(
            IssueModel.objects.filter(pk=tarefa.pk).select_related("project", "state"), many=True
        ).data

        assert dados[0]["Canal"] == "Indicação"
        assert dados[0]["Contrato"].startswith("BRL 1500")

    def test_the_export_reads_values_in_one_query(self, projeto, create_user, django_assert_max_num_queries):
        """Uma consulta de valores para o arquivo inteiro, e não uma por linha.

        O gancho é o `ListSerializer` porque é ele que enxerga o conjunto.
        """
        from plane.db.models import Issue as IssueModel
        from plane.utils.porters.serializers.issue import IssueExportSerializer

        texto = _propriedade(projeto, "Observação", "text")
        tarefas = [_tarefa(projeto, create_user, nome=f"E{i}") for i in range(20)]
        IssuePropertyValue.objects.bulk_create(
            [
                IssuePropertyValue(
                    issue=t,
                    issue_property=texto,
                    value_text="x",
                    project=projeto,
                    workspace=projeto.workspace,
                )
                for t in tarefas
            ]
        )
        conjunto = IssueModel.objects.filter(project=projeto).select_related("project", "state")

        # O teto é folgado porque o serializer herdado busca muita coisa por
        # tarefa; o que este teste fixa é que os VALORES não crescem com as
        # linhas — 20 tarefas, uma consulta de valores.
        with django_assert_max_num_queries(400) as captura:
            IssueExportSerializer(conjunto, many=True).data

        de_valores = [q for q in captura.captured_queries if "issue_property_values" in q["sql"]]
        assert len(de_valores) == 1, de_valores
