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
from django.utils import timezone
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
        # Formatado como a configuração pediu, e não como a coluna guarda.
        assert lidos[str(numero.id)] == "12.5"
        assert lidos[str(moeda.id)] == "1999.90"

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

    def test_the_activity_is_recognisable_by_the_screen(self, session_client, workspace, projeto, create_user):
        """A linha precisa se anunciar, senão a tela a engole.

        As três telas de atividade despacham por CAMPO conhecido e devolvem
        nada para o resto — e o campo aqui é o nome de uma propriedade do
        cliente, que nenhuma lista pode conter. O verbo próprio é o que a torna
        reconhecível; sem ele a mudança era gravada e nunca aparecia.

        O `new_identifier` guarda o id da PROPRIEDADE, e não o do valor: é o
        que sobrevive a um rename, enquanto `field` continua sendo o nome de
        quando a mudança aconteceu.
        """
        tarefa = _tarefa(projeto, create_user)
        url = VALORES_URL.format(slug=workspace.slug, project_id=projeto.id, issue_id=tarefa.id)
        canal = _propriedade(projeto, "Canal", "select")
        indicacao = _opcao(canal, "Indicação")

        session_client.post(url, {"property": str(canal.id), "value": str(indicacao.id)}, format="json")

        atividade = IssueActivity.objects.get(issue=tarefa, field="Canal")
        assert atividade.verb == "property_updated"
        assert atividade.new_identifier == canal.id

    def test_clearing_a_value_is_also_recorded(self, session_client, workspace, projeto, create_user):
        """Apagar é mudança, e a tela precisa poder dizer "limpou Canal"."""
        tarefa = _tarefa(projeto, create_user)
        url = VALORES_URL.format(slug=workspace.slug, project_id=projeto.id, issue_id=tarefa.id)
        canal = _propriedade(projeto, "Canal", "select")
        indicacao = _opcao(canal, "Indicação")

        session_client.post(url, {"property": str(canal.id), "value": str(indicacao.id)}, format="json")
        session_client.post(url, {"property": str(canal.id), "value": None}, format="json")

        ultima = IssueActivity.objects.filter(issue=tarefa, field="Canal").order_by("-created_at").first()
        assert (ultima.old_value, ultima.new_value) == ("Indicação", "")
        assert ultima.verb == "property_updated"

    def test_the_backfill_reaches_the_history_already_written(self, session_client, workspace, projeto, create_user):
        """O histórico já gravado também precisa aparecer.

        Ele existe desde a v1.13.0 e nunca foi desenhado — corrigir só o futuro
        deixaria meses de mudanças invisíveis para sempre.

        A regra é exercitada pela mesma função que a migração chama: o
        `pytest.ini` roda com `--nomigrations`, então regra escrita dentro da
        migração não é executada por teste nenhum.
        """
        from plane.utils.issue_properties import marcar_atividades_de_propriedade

        outro = Project.objects.create(
            name="Outro", identifier="OUT", workspace=workspace, created_by=create_user
        )
        canal = _propriedade(projeto, "Canal", "select")
        tarefa = _tarefa(projeto, create_user)

        # Como as linhas antigas estão no banco: verbo genérico, sem id.
        antiga = IssueActivity.objects.create(
            issue=tarefa, project=projeto, workspace=workspace, actor=create_user,
            verb="updated", field="Canal", old_value="", new_value="Indicação",
        )
        # Mesmo nome, OUTRO projeto: não é a mesma propriedade.
        de_outro_projeto = IssueActivity.objects.create(
            issue=tarefa, project=outro, workspace=workspace, actor=create_user,
            verb="updated", field="Canal", old_value="", new_value="Indicação",
        )
        # Campo do produto, que já tem dono e não pode ser tocado.
        de_estado = IssueActivity.objects.create(
            issue=tarefa, project=projeto, workspace=workspace, actor=create_user,
            verb="updated", field="state", old_value="A", new_value="B",
        )

        marcadas = marcar_atividades_de_propriedade(IssueActivity, IssueProperty)

        antiga.refresh_from_db()
        de_outro_projeto.refresh_from_db()
        de_estado.refresh_from_db()
        assert marcadas == 1
        assert (antiga.verb, antiga.new_identifier) == ("property_updated", canal.id)
        assert de_outro_projeto.verb == "updated"
        assert de_estado.verb == "updated"

    def test_the_backfill_does_not_touch_activities_that_carry_a_value_id(
        self, session_client, workspace, projeto, create_user
    ):
        """Nome de propriedade é livre, e pode colidir com campo do produto.

        Etiqueta, ciclo, módulo e responsável usam a MESMA coluna para o id do
        VALOR. Uma propriedade chamada "labels" faria o casamento por nome
        acertar a atividade de etiqueta — e reescrevê-la trocaria o significado
        de um dado alheio. Quem impede é a guarda do `new_identifier`, e é por
        isso que o cenário deste teste é justamente a colisão: sem ela, o
        casamento por nome já bastaria e a guarda não estaria sendo provada.
        """
        from plane.utils.issue_properties import marcar_atividades_de_propriedade

        _propriedade(projeto, "labels", "select")
        tarefa = _tarefa(projeto, create_user)
        etiqueta = IssueActivity.objects.create(
            issue=tarefa, project=projeto, workspace=workspace, actor=create_user,
            verb="updated", field="labels", new_value="Urgente", new_identifier=tarefa.id,
        )

        marcar_atividades_de_propriedade(IssueActivity, IssueProperty)

        etiqueta.refresh_from_db()
        assert etiqueta.verb == "updated"
        assert etiqueta.new_identifier == tarefa.id

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

    def test_the_public_api_carries_the_values(self, projeto, create_user):
        """A API pública é como o resto da operação lê a tarefa."""
        from plane.api.serializers.issue import IssueSerializer as PublicIssueSerializer

        texto = _propriedade(projeto, "Canal", "text")
        tarefa = _tarefa(projeto, create_user)
        IssuePropertyValue.objects.create(
            issue=tarefa,
            issue_property=texto,
            value_text="Indicação",
            project=projeto,
            workspace=projeto.workspace,
        )

        dados = PublicIssueSerializer(tarefa).data

        assert dados["property_values"] == {str(texto.id): "Indicação"}

    def test_the_webhook_payload_carries_the_values(self, projeto, create_user):
        """Mandar a tarefa sem o dado de negócio seria mandar meia tarefa."""
        from plane.api.serializers.issue import IssueExpandSerializer

        moeda = _propriedade(projeto, "Contrato", "currency", currency="BRL")
        tarefa = _tarefa(projeto, create_user)
        IssuePropertyValue.objects.create(
            issue=tarefa,
            issue_property=moeda,
            value_number="99.90",
            project=projeto,
            workspace=projeto.workspace,
        )

        dados = IssueExpandSerializer(tarefa).data

        assert dados["property_values"][str(moeda.id)].startswith("99.9")

    def test_the_public_api_can_read_values_in_bulk(self, projeto, create_user):
        """Sem o contexto, uma listagem pagaria uma consulta por linha."""
        from plane.api.serializers.issue import IssueSerializer as PublicIssueSerializer
        from plane.utils.issue_properties import valores_por_tarefa

        texto = _propriedade(projeto, "Canal", "text")
        tarefas = [_tarefa(projeto, create_user, nome=f"A{i}") for i in range(10)]
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
        em_bloco = valores_por_tarefa([t.id for t in tarefas])

        dados = PublicIssueSerializer(tarefas, many=True, context={"valores_de_propriedade": em_bloco}).data

        assert all(d["property_values"] == {str(texto.id): "x"} for d in dados)

    def test_currency_refuses_more_decimals_than_configured(self, session_client, workspace, projeto, create_user):
        """Precisão é RECUSADA, não arredondada.

        Arredondar dinheiro em silêncio troca o número que a pessoa digitou por
        outro, e ela só descobre no relatório — enquanto recusar acontece na
        frente dela, com o campo ainda aberto.
        """
        tarefa = _tarefa(projeto, create_user)
        url = VALORES_URL.format(slug=workspace.slug, project_id=projeto.id, issue_id=tarefa.id)
        duas = _propriedade(projeto, "Contrato", "currency", currency="BRL", decimal_places=2)
        zero = _propriedade(projeto, "Inteiro", "currency", currency="BRL", decimal_places=0)

        recusada = session_client.post(url, {"property": str(duas.id), "value": "1500.999"}, format="json")
        assert recusada.status_code == status.HTTP_400_BAD_REQUEST
        assert "2 casa" in str(recusada.data["value"])

        aceita = session_client.post(url, {"property": str(duas.id), "value": "1500.99"}, format="json")
        assert aceita.status_code == status.HTTP_200_OK

        sem_centavos = session_client.post(url, {"property": str(zero.id), "value": "1500.50"}, format="json")
        assert sem_centavos.status_code == status.HTTP_400_BAD_REQUEST

    def test_a_number_beyond_the_column_precision_is_refused(self, session_client, workspace, projeto, create_user):
        """Acima de 6 casas o Postgres arredondaria sozinho.

        Arredondamento silencioso é exatamente o que este caminho evita.
        """
        tarefa = _tarefa(projeto, create_user)
        numero = _propriedade(projeto, "Peso", "number")

        resposta = session_client.post(
            VALORES_URL.format(slug=workspace.slug, project_id=projeto.id, issue_id=tarefa.id),
            {"property": str(numero.id), "value": "1.1234567"},
            format="json",
        )

        assert resposta.status_code == status.HTTP_400_BAD_REQUEST

    def test_the_creation_path_validates_precision_too(self, session_client, workspace, projeto):
        """A criação grava valores pelo mesmo caminho — e a mesma trava vale."""
        moeda = _propriedade(projeto, "Contrato", "currency", currency="BRL", decimal_places=2)

        resposta = session_client.post(
            TAREFAS_URL.format(slug=workspace.slug, project_id=projeto.id),
            {"name": "Com centavo demais", "property_values": {str(moeda.id): "10.001"}},
            format="json",
        )

        assert resposta.status_code == status.HTTP_400_BAD_REQUEST
        assert "property_values" in resposta.data
        # E a tarefa NÃO ficou para trás: quem tentasse de novo criaria a
        # segunda, e a primeira seguiria no quadro sem o campo obrigatório.
        assert not Issue.objects.filter(name="Com centavo demais").exists()

    def test_reading_uses_the_configured_decimal_places(self, session_client, workspace, projeto, create_user):
        """A coluna guarda seis casas; a configuração pede outra coisa.

        Sem recortar na leitura, um campo de 2 casas devolvia "50.000000" — e o
        campo mostrava um número que ninguém escolheu.
        """
        tarefa = _tarefa(projeto, create_user)
        url = VALORES_URL.format(slug=workspace.slug, project_id=projeto.id, issue_id=tarefa.id)
        duas = _propriedade(projeto, "Contrato", "currency", currency="BRL", decimal_places=2)
        zero = _propriedade(projeto, "Inteiro", "currency", currency="BRL", decimal_places=0)
        numero = _propriedade(projeto, "Peso", "number")

        session_client.post(url, {"property": str(duas.id), "value": "50"}, format="json")
        session_client.post(url, {"property": str(zero.id), "value": "100"}, format="json")
        session_client.post(url, {"property": str(numero.id), "value": "100"}, format="json")

        lidos = session_client.get(url).data["values"]

        assert lidos[str(duas.id)] == "50.00"
        assert lidos[str(zero.id)] == "100"
        # Número redondo não pode virar notação científica ("1E+2").
        assert lidos[str(numero.id)] == "100"

    def test_the_export_also_uses_the_configured_places(self, projeto, create_user):
        """A exportação lê pelo mesmo caminho — e mostrava o número cru também."""
        from plane.db.models import Issue as IssueModel
        from plane.utils.porters.serializers.issue import IssueExportSerializer

        moeda = _propriedade(projeto, "Contrato", "currency", currency="BRL", decimal_places=2)
        tarefa = _tarefa(projeto, create_user)
        IssuePropertyValue.objects.create(
            issue=tarefa,
            issue_property=moeda,
            value_number="50",
            project=projeto,
            workspace=projeto.workspace,
        )

        dados = IssueExportSerializer(
            IssueModel.objects.filter(pk=tarefa.pk).select_related("project", "state"), many=True
        ).data

        assert dados[0]["Contrato"] == "BRL 50.00"

    def test_a_refused_write_never_destroys_the_stored_value(self, session_client, workspace, projeto, create_user):
        """Recusar não pode custar o valor que já estava lá.

        O caminho de escrita apagava as linhas antigas ANTES de converter, e a
        conversão é quem recusa — então a pessoa perdia o número novo E o
        antigo, com um erro falando de casas decimais sobre um campo vazio.
        """
        tarefa = _tarefa(projeto, create_user)
        url = VALORES_URL.format(slug=workspace.slug, project_id=projeto.id, issue_id=tarefa.id)
        moeda = _propriedade(projeto, "Contrato", "currency", currency="BRL", decimal_places=2)
        session_client.post(url, {"property": str(moeda.id), "value": "100"}, format="json")

        recusada = session_client.post(url, {"property": str(moeda.id), "value": "77.999"}, format="json")

        assert recusada.status_code == status.HTTP_400_BAD_REQUEST
        assert session_client.get(url).data["values"][str(moeda.id)] == "100.00"

    def test_a_refused_option_never_destroys_the_stored_value(self, session_client, workspace, projeto, create_user):
        """O mesmo para seleção: opção inválida não pode limpar a escolhida."""
        tarefa = _tarefa(projeto, create_user)
        url = VALORES_URL.format(slug=workspace.slug, project_id=projeto.id, issue_id=tarefa.id)
        canal = _propriedade(projeto, "Canal", "select")
        boa = _opcao(canal, "Indicação")
        outra = _propriedade(projeto, "Origem", "select")
        alheia = _opcao(outra, "Site")
        session_client.post(url, {"property": str(canal.id), "value": str(boa.id)}, format="json")

        recusada = session_client.post(url, {"property": str(canal.id), "value": str(alheia.id)}, format="json")

        assert recusada.status_code == status.HTTP_400_BAD_REQUEST
        assert session_client.get(url).data["values"][str(canal.id)] == str(boa.id)


@pytest.mark.contract
class TestDefinicoesNaSaida:
    """Os CAMPOS, e não só os valores (ADR 0011).

    `property_values` devolve `{"<uuid>": "<uuid>"}`. Sem o nome do campo e o
    rótulo da opção, quem integra recebe dois ids opacos: não sabe que aquilo é
    "Canal = Indicação". Estes testes cobrem os dois lugares onde a definição
    precisa chegar — o webhook, que não tem chamada de volta, e a API pública,
    que ganhou o endereço das definições.
    """

    @pytest.mark.django_db
    def test_the_webhook_payload_explains_itself(self, projeto, create_user):
        """O webhook não pode exigir uma segunda chamada para ser entendido."""
        from plane.api.serializers.issue import IssueExpandSerializer

        canal = _propriedade(projeto, "Canal", "select")
        indicacao = _opcao(canal, "Indicação")
        tarefa = _tarefa(projeto, create_user)
        IssuePropertyValue.objects.create(
            issue=tarefa,
            issue_property=canal,
            value_option=indicacao,
            project=projeto,
            workspace=projeto.workspace,
        )

        dados = IssueExpandSerializer(tarefa).data

        assert dados["property_values"] == {str(canal.id): str(indicacao.id)}
        definicao = next(d for d in dados["properties"] if d["id"] == str(canal.id))
        assert definicao["name"] == "Canal"
        assert definicao["property_type"] == "select"
        assert {"id": str(indicacao.id), "name": "Indicação", "color": indicacao.color} in definicao["options"]

    @pytest.mark.django_db
    def test_the_webhook_only_carries_what_the_work_item_uses(self, projeto, create_user):
        """Levar as 30 do projeto em toda tarefa seria pagar por todo mundo."""
        from plane.api.serializers.issue import IssueExpandSerializer

        usada = _propriedade(projeto, "Canal", "text")
        _propriedade(projeto, "Contrato", "currency", currency="BRL")
        tarefa = _tarefa(projeto, create_user)
        IssuePropertyValue.objects.create(
            issue=tarefa,
            issue_property=usada,
            value_text="Indicação",
            project=projeto,
            workspace=projeto.workspace,
        )

        dados = IssueExpandSerializer(tarefa).data

        assert [d["name"] for d in dados["properties"]] == ["Canal"]

    @pytest.mark.django_db
    def test_a_work_item_without_values_carries_no_definitions(self, projeto, create_user):
        from plane.api.serializers.issue import IssueExpandSerializer

        _propriedade(projeto, "Canal", "text")
        tarefa = _tarefa(projeto, create_user)

        dados = IssueExpandSerializer(tarefa).data

        assert dados["property_values"] == {}
        assert dados["properties"] == []

    @pytest.mark.django_db
    def test_the_webhook_reads_values_once_per_work_item(self, projeto, create_user, django_assert_max_num_queries):
        """Duas leituras do mesmo dado seriam duas consultas por evento."""
        from plane.api.serializers.issue import IssueExpandSerializer

        canal = _propriedade(projeto, "Canal", "text")
        tarefa = _tarefa(projeto, create_user)
        IssuePropertyValue.objects.create(
            issue=tarefa,
            issue_property=canal,
            value_text="Indicação",
            project=projeto,
            workspace=projeto.workspace,
        )

        with django_assert_max_num_queries(50) as captura:
            IssueExpandSerializer(tarefa).data

        de_valores = [q for q in captura.captured_queries if "issue_property_values" in q["sql"]]
        assert len(de_valores) == 1, de_valores

    @pytest.mark.django_db
    def test_the_public_api_serves_the_definitions(self, projeto, create_user, session_client, workspace):
        """O endereço que resolve os ids de `property_values`."""
        canal = _propriedade(projeto, "Canal", "select")
        indicacao = _opcao(canal, "Indicação")
        _propriedade(projeto, "Contrato", "currency", currency="BRL", decimal_places=2)

        url = f"/api/v1/workspaces/{workspace.slug}/projects/{projeto.id}/issue-properties/"
        resposta = session_client.get(url)

        assert resposta.status_code == status.HTTP_200_OK
        itens = resposta.data["results"] if isinstance(resposta.data, dict) else resposta.data
        por_nome = {i["name"]: i for i in itens}
        assert set(por_nome) == {"Canal", "Contrato"}
        assert por_nome["Canal"]["options"][0]["name"] == "Indicação"
        assert str(indicacao.id) == str(por_nome["Canal"]["options"][0]["id"])
        assert por_nome["Contrato"]["currency"] == "BRL"
        assert por_nome["Contrato"]["decimal_places"] == 2
        # Tipo que não é seleção não carrega lista de opções vazia por engano.
        assert por_nome["Contrato"]["options"] == []

    @pytest.mark.django_db
    def test_the_public_api_definitions_are_read_only(self, projeto, create_user, session_client, workspace):
        """Criar campo é configuração do projeto, e tem um caminho só."""
        url = f"/api/v1/workspaces/{workspace.slug}/projects/{projeto.id}/issue-properties/"

        resposta = session_client.post(url, {"name": "Novo", "property_type": "text"}, format="json")

        assert resposta.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    @pytest.mark.django_db
    def test_the_public_api_does_not_serve_another_project(self, projeto, create_user, session_client, workspace):
        """Propriedade é do projeto — e quem não é do projeto não a vê."""
        alheio = Project.objects.create(name="Alheio", identifier="ALH", workspace=workspace, created_by=create_user)
        _propriedade(alheio, "Secreta", "text")
        _propriedade(projeto, "Canal", "text")

        url = f"/api/v1/workspaces/{workspace.slug}/projects/{projeto.id}/issue-properties/"
        resposta = session_client.get(url)

        itens = resposta.data["results"] if isinstance(resposta.data, dict) else resposta.data
        assert [i["name"] for i in itens] == ["Canal"]

    @pytest.mark.django_db
    def test_each_work_item_gets_its_own_definitions(self, projeto, create_user):
        """O cache é por tarefa: em lote, a segunda não pode herdar a primeira."""
        from plane.api.serializers.issue import IssueExpandSerializer

        canal = _propriedade(projeto, "Canal", "text")
        contrato = _propriedade(projeto, "Contrato", "currency", currency="BRL")
        primeira = _tarefa(projeto, create_user, nome="Primeira")
        segunda = _tarefa(projeto, create_user, nome="Segunda")
        IssuePropertyValue.objects.create(
            issue=primeira,
            issue_property=canal,
            value_text="Indicação",
            project=projeto,
            workspace=projeto.workspace,
        )
        IssuePropertyValue.objects.create(
            issue=segunda,
            issue_property=contrato,
            value_number="10",
            project=projeto,
            workspace=projeto.workspace,
        )

        dados = IssueExpandSerializer([primeira, segunda], many=True).data

        por_tarefa = {d["name"]: [p["name"] for p in d["properties"]] for d in dados}
        assert por_tarefa == {"Primeira": ["Canal"], "Segunda": ["Contrato"]}

    @pytest.mark.django_db
    def test_a_deleted_property_stops_appearing(self, projeto, create_user):
        """Campo excluído não sai mais — nem como id órfão.

        A cascata que apaga os valores roda em tarefa assíncrona. Entre o
        clique e a tarefa — e para sempre, se ela falhar — o valor continuaria
        saindo com o id de um campo que não existe mais, e quem recebe não
        teria como resolvê-lo. Encontrado no `planedev`, com um valor vivo de
        uma propriedade já excluída.
        """
        from plane.api.serializers.issue import IssueExpandSerializer

        canal = _propriedade(projeto, "Canal", "text")
        tarefa = _tarefa(projeto, create_user)
        IssuePropertyValue.objects.create(
            issue=tarefa,
            issue_property=canal,
            value_text="Indicação",
            project=projeto,
            workspace=projeto.workspace,
        )
        # Exclusão lógica da propriedade, sem tocar no valor — exatamente o
        # estado em que o sistema fica antes de a cascata rodar.
        IssueProperty.objects.filter(pk=canal.id).update(deleted_at=timezone.now())

        dados = IssueExpandSerializer(tarefa).data

        assert dados["property_values"] == {}
        assert dados["properties"] == []


@pytest.mark.contract
class TestIcone:
    """O ícone do campo (ADR 0011).

    Antes, tudo aparecia com o mesmo desenho de etiqueta — um seletor onde
    todos os campos têm o mesmo ícone obriga a ler cada nome, que é justamente
    o trabalho que o ícone deveria poupar.
    """

    @pytest.mark.django_db
    def test_each_type_has_its_own_default(self, projeto, create_user):
        """Sem escolha nenhuma, dois tipos não podem sair iguais."""
        from plane.utils.issue_properties import icone_efetivo

        efetivos = {
            tipo: icone_efetivo(
                _propriedade(projeto, f"P {tipo}", tipo, **({"currency": "BRL"} if tipo == "currency" else {}))
            )
            for tipo in ("text", "number", "date", "select", "multi_select", "currency")
        }

        assert len(set(efetivos.values())) == len(efetivos), efetivos

    @pytest.mark.django_db
    def test_the_chosen_icon_wins_over_the_default(self, projeto, create_user):
        from plane.utils.issue_properties import icone_efetivo

        propriedade = _propriedade(projeto, "Contrato", "currency", currency="BRL", icon="briefcase")

        assert icone_efetivo(propriedade) == "briefcase"

    @pytest.mark.django_db
    def test_an_unknown_icon_is_refused(self, session_client, workspace, projeto):
        """Chave livre chegaria à tela como nome de componente."""
        url = f"/api/workspaces/{workspace.slug}/projects/{projeto.id}/issue-properties/"

        recusada = session_client.post(
            url, {"name": "Canal", "property_type": "text", "icon": "../../etc/passwd"}, format="json"
        )

        assert recusada.status_code == status.HTTP_400_BAD_REQUEST
        assert "icon" in recusada.data

    @pytest.mark.django_db
    def test_an_empty_icon_is_accepted_and_means_the_default(self, session_client, workspace, projeto):
        url = f"/api/workspaces/{workspace.slug}/projects/{projeto.id}/issue-properties/"

        criada = session_client.post(url, {"name": "Canal", "property_type": "date", "icon": ""}, format="json")

        assert criada.status_code == status.HTTP_201_CREATED
        assert IssueProperty.objects.get(pk=criada.data["id"]).icon == ""

    @pytest.mark.django_db
    def test_the_public_api_and_the_webhook_serve_the_effective_icon(self, projeto, create_user):
        """Quem integra não deve precisar conhecer a regra do padrão."""
        from plane.api.serializers.issue import IssueExpandSerializer
        from plane.utils.issue_properties import definicoes_das_propriedades

        moeda = _propriedade(projeto, "Contrato", "currency", currency="BRL")
        tarefa = _tarefa(projeto, create_user)
        IssuePropertyValue.objects.create(
            issue=tarefa,
            issue_property=moeda,
            value_number="10",
            project=projeto,
            workspace=projeto.workspace,
        )

        assert definicoes_das_propriedades([moeda.id])[0]["icon"] == "dollar-sign"
        assert IssueExpandSerializer(tarefa).data["properties"][0]["icon"] == "dollar-sign"

    @pytest.mark.django_db
    def test_every_default_icon_is_in_the_allowed_list(self):
        """O padrão de um tipo não pode ser um ícone que a escrita recusaria.

        A tela guarda o mesmo mapa para traduzir chave em desenho, e ele fica
        anotado em `icones.tsx`. Aqui só dá para provar o lado do servidor: um
        padrão fora da lista seria um campo que nasce com um ícone que ninguém
        consegue escolher de volta depois de trocar.
        """
        from plane.db.models import ICONES_DE_PROPRIEDADE, ICONE_PADRAO_POR_TIPO, PropertyType

        assert set(ICONE_PADRAO_POR_TIPO) == set(PropertyType)
        assert set(ICONE_PADRAO_POR_TIPO.values()) <= set(ICONES_DE_PROPRIEDADE)
