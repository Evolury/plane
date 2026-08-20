# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Agrupar o quadro por propriedade de seleção (ADR 0011, P4.2).

O agrupamento cabe no maquinário existente porque o paginador resolve o nome do
campo em `F()`, em `values()` e na partição de janela — e anotação atende os
três. O que estes testes vigiam é o contorno: como na ordenação, o valor de
quem chama não pode virar nome de campo.
"""

import pytest

from plane.db.models import (
    Issue,
    IssueProperty,
    IssuePropertyOption,
    IssuePropertyValue,
    Project,
    ProjectMember,
    State,
)
from plane.utils.grouper import issue_group_values, issue_on_results, issue_queryset_grouper
from plane.utils.issue_properties import alias_de_agrupamento


@pytest.fixture
def projeto(db, workspace, create_user):
    projeto = Project.objects.create(name="Projeto", identifier="PRJ", workspace=workspace, created_by=create_user)
    ProjectMember.objects.create(project=projeto, member=create_user, role=20, is_active=True)
    State.objects.filter(project=projeto).delete()
    State.objects.create(
        name="Pendente", group="backlog", project=projeto, workspace=workspace, color="#000", default=True
    )
    return projeto


def _select(projeto, nome="Canal"):
    return IssueProperty.objects.create(name=nome, property_type="select", project=projeto, workspace=projeto.workspace)


def _opcao(prop, nome, ordem):
    return IssuePropertyOption.objects.create(
        issue_property=prop,
        name=nome,
        sort_order=ordem,
        project=prop.project,
        workspace=prop.workspace,
    )


def _tarefa(projeto, create_user, nome):
    return Issue.objects.create(name=nome, project=projeto, workspace=projeto.workspace, created_by=create_user)


def _como_a_view(projeto):
    """A listagem anota estes quatro campos ANTES de agrupar.

    O agrupador não os cria, e `issue_on_results` os exige — reproduzi-los aqui
    é o que faz o teste exercitar o caminho real em vez de um recorte dele.
    """
    from django.db.models import IntegerField, UUIDField, Value

    return (
        Issue.issue_objects.filter(project=projeto)
        .annotate(cycle_id=Value(None, output_field=UUIDField()))
        .annotate(link_count=Value(0, output_field=IntegerField()))
        .annotate(attachment_count=Value(0, output_field=IntegerField()))
        .annotate(sub_issues_count=Value(0, output_field=IntegerField()))
    )


@pytest.mark.contract
class TestAgrupamento:
    @pytest.mark.django_db
    def test_the_annotation_reaches_the_response(self, projeto, create_user):
        """Sem entrar no `values()`, o agrupamento existe na consulta e some
        da resposta — o quadro voltaria uma coluna só."""
        canal = _select(projeto)
        opcao = _opcao(canal, "Indicação", 1)
        tarefa = _tarefa(projeto, create_user, "com canal")
        IssuePropertyValue.objects.create(
            issue=tarefa,
            issue_property=canal,
            value_option=opcao,
            project=projeto,
            workspace=projeto.workspace,
        )
        chave = f"property_{canal.id}"

        agrupado = issue_queryset_grouper(_como_a_view(projeto), chave, None)
        linhas = issue_on_results(agrupado, chave, None)

        assert linhas[0][chave] == opcao.id

    @pytest.mark.django_db
    def test_the_columns_follow_the_configured_option_order(self, projeto, create_user):
        """Quem arrastou a opção para o topo espera a coluna no topo.

        E `"None"` no fim porque tarefa sem valor precisa de uma coluna onde
        caber — sem ela, agrupar esconderia trabalho.
        """
        canal = _select(projeto)
        zulu = _opcao(canal, "Zulu", 1)
        alfa = _opcao(canal, "Alfa", 2)

        colunas = issue_group_values(f"property_{canal.id}", projeto.workspace.slug, str(projeto.id))

        assert colunas == [zulu.id, alfa.id, "None"]

    @pytest.mark.django_db
    def test_only_single_select_groups(self, projeto, create_user):
        """Texto ou moeda dariam uma coluna por valor distinto — ruído, e não
        organização (ADR 0011)."""
        for tipo in ("text", "number", "currency", "date", "multi_select"):
            propriedade = IssueProperty.objects.create(
                name=f"P {tipo}", property_type=tipo, project=projeto, workspace=projeto.workspace
            )
            assert alias_de_agrupamento(f"property_{propriedade.id}") is None, tipo

        agrupavel = _select(projeto, "Agrupável")
        assert alias_de_agrupamento(f"property_{agrupavel.id}") == agrupavel.id

    @pytest.mark.django_db
    def test_a_forged_group_by_is_ignored(self, projeto, create_user):
        """Como na ordenação: valor de quem chama não vira nome de campo."""
        for forjado in (
            "property_nao-e-uuid",
            "property_../../etc",
            "property_00000000-0000-0000-0000-000000000000",
            "state_id",
            None,
        ):
            assert alias_de_agrupamento(forjado) is None, forjado

    @pytest.mark.django_db
    def test_grouping_does_not_break_the_other_group_bys(self, projeto, create_user):
        """O caminho novo não pode custar nada ao que já existia."""
        _tarefa(projeto, create_user, "uma")

        agrupado = issue_queryset_grouper(_como_a_view(projeto), "state_id", None)
        linhas = issue_on_results(agrupado, "state_id", None)

        assert len(linhas) == 1
        assert "label_ids" in linhas[0]

    @pytest.mark.django_db
    def test_the_paginator_guard_still_refuses_arbitrary_fields(self, projeto, create_user):
        """A allowlist do paginador existe contra injeção de nome de campo
        (GHSA-wwgj-929g-42cm), e a propriedade a contorna — então a prova dela
        precisa ser igualmente rígida.

        Este teste exercita a MESMA função que o paginador consulta.
        """
        canal = _select(projeto)

        # Passa: propriedade de seleção existente.
        assert alias_de_agrupamento(f"property_{canal.id}") is not None

        # Não passa: nada que não seja exatamente isso.
        for forjado in (
            "property_state__group",
            "property_project__workspace__owner__password",
            "property_' OR 1=1--",
            f"property_{canal.id}__extra",
            "propertyx_" + str(canal.id),
        ):
            assert alias_de_agrupamento(forjado) is None, forjado


class _PaginadorDeMentira:
    """Dublê do paginador agrupado.

    A prova mora em `BasePaginator.paginate()`, antes de o nome do campo tocar
    o ORM — instanciar o paginador de verdade só traria consulta para dentro de
    um teste que não é sobre consulta. Mesmo dublê de
    `tests/unit/utils/test_paginator.py`.
    """

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def get_result(self, limit, cursor):
        from plane.utils.paginator import Cursor, CursorResult

        return CursorResult(
            results=[],
            next=Cursor(limit, 1, False, False),
            prev=Cursor(limit, -1, True, False),
            hits=0,
            max_hits=0,
        )

    def process_results(self, results):
        return results


@pytest.mark.contract
class TestEscolhaDeAgrupar:
    """Agrupar por propriedade é opt-in da definição (ADR 0011).

    A marca é honrada AQUI, e não só no menu, porque `alias_de_agrupamento` é a
    mesma função que a allowlist do paginador consulta
    (GHSA-wwgj-929g-42cm): desmarcar deixa de ser sugestão de tela e vira
    recusa da consulta, venha ela da tela, da URL ou de um script.
    """

    @pytest.mark.django_db
    def test_an_unmarked_property_does_not_group(self, projeto, create_user):
        canal = _select(projeto)
        canal.show_in_grouping = False
        canal.save(update_fields=["show_in_grouping"])

        assert alias_de_agrupamento(f"property_{canal.id}") is None

    @pytest.mark.django_db
    def test_an_unmarked_property_is_refused_by_the_paginator(self, projeto, create_user):
        """A recusa chega ao pedido, e não fica na tela.

        `BasePaginator.paginate` é o funil por onde passam os seis endpoints
        que aceitam `group_by`. Este teste exercita o funil de verdade — com a
        propriedade marcada e com ela desmarcada — porque é ele que transforma
        a marca em 400.
        """
        from django.test import RequestFactory
        from rest_framework.exceptions import ParseError
        from rest_framework.request import Request

        from plane.utils.paginator import BasePaginator

        canal = _select(projeto)
        _opcao(canal, "Indicação", 1)
        chave = f"property_{canal.id}"

        def paginar():
            pedido = Request(RequestFactory().get("/fake-url/", data={"group_by": chave}))
            return BasePaginator().paginate(
                request=pedido,
                queryset=_como_a_view(projeto),
                paginator_cls=_PaginadorDeMentira,
                group_by_field_name=chave,
                group_by_fields=[],
            )

        # Marcada: passa.
        paginar()

        canal.show_in_grouping = False
        canal.save(update_fields=["show_in_grouping"])

        with pytest.raises(ParseError):
            paginar()

    @pytest.mark.django_db
    def test_a_property_is_groupable_by_default(self, projeto, create_user):
        """Nasce ligada, ao contrário de `show_on_card`.

        É também o que a migração faz com as que já existiam: antes do campo,
        toda seleção única aparecia em "agrupar por", e nascer desligada faria
        sumir do menu um agrupamento em uso.
        """
        canal = _select(projeto)

        assert canal.show_in_grouping is True
        assert alias_de_agrupamento(f"property_{canal.id}") == canal.id
