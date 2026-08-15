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
