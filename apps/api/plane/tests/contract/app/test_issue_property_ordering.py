# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Ordenar por propriedade personalizada (ADR 0011, P4.3).

A allowlist de ordenação existe para que valor de quem chama nunca vire nome de
campo no ORM. Propriedade personalizada não cabe nela — o nome do campo é um id
que só existe em tempo de execução —, então ela entra por um prefixo próprio,
com o id validado como UUID antes de qualquer coisa. **É esse contorno que os
testes abaixo vigiam.**
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
from plane.utils.order_queryset import order_issue_queryset


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


def _tarefa(projeto, create_user, nome):
    return Issue.objects.create(
        name=nome, project=projeto, workspace=projeto.workspace, created_by=create_user
    )


def _valor(tarefa, propriedade, **campos):
    return IssuePropertyValue.objects.create(
        issue=tarefa,
        issue_property=propriedade,
        project=tarefa.project,
        workspace=tarefa.workspace,
        **campos,
    )


@pytest.mark.contract
class TestOrdenacao:
    @pytest.mark.django_db
    def test_number_sorts_as_number(self, projeto, create_user):
        """A coluna tipada é o que a escolha de modelo comprou.

        Numa coluna de texto, "10" viria antes de "9" — e o defeito seria
        invisível até alguém ter dois dígitos.
        """
        propriedade = IssueProperty.objects.create(
            name="Peso", property_type="number", project=projeto, workspace=projeto.workspace
        )
        for nome, valor in (("nove", "9"), ("dez", "10"), ("dois", "2")):
            _valor(_tarefa(projeto, create_user, nome), propriedade, value_number=valor)

        ordenado, _ = order_issue_queryset(
            Issue.issue_objects.filter(project=projeto), f"property__{propriedade.id}"
        )

        assert [t.name for t in ordenado] == ["dois", "nove", "dez"]

    @pytest.mark.django_db
    def test_work_items_without_value_go_last_in_both_directions(self, projeto, create_user):
        """Inverter a ordem não pode trazer para a frente quem não tem o dado.

        Sem `nulls_last`, descer a ordenação traria primeiro justamente as
        linhas que não têm o valor que a pessoa pediu para ordenar.
        """
        propriedade = IssueProperty.objects.create(
            name="Peso", property_type="number", project=projeto, workspace=projeto.workspace
        )
        _valor(_tarefa(projeto, create_user, "com"), propriedade, value_number="5")
        _tarefa(projeto, create_user, "sem")

        subindo, _ = order_issue_queryset(
            Issue.issue_objects.filter(project=projeto), f"property__{propriedade.id}"
        )
        descendo, _ = order_issue_queryset(
            Issue.issue_objects.filter(project=projeto), f"-property__{propriedade.id}"
        )

        assert [t.name for t in subindo][-1] == "sem"
        assert [t.name for t in descendo][-1] == "sem"

    @pytest.mark.django_db
    def test_select_sorts_by_the_configured_option_order(self, projeto, create_user):
        """Seleção ordena pela ordem das OPÇÕES, não pelo alfabeto.

        Quem arrastou "Urgente" para cima da lista espera que a coluna respeite
        isso; ordenar por nome devolveria a ordem que ninguém escolheu.
        """
        propriedade = IssueProperty.objects.create(
            name="Canal", property_type="select", project=projeto, workspace=projeto.workspace
        )
        primeira = IssuePropertyOption.objects.create(
            issue_property=propriedade, name="Zulu", sort_order=1,
            project=projeto, workspace=projeto.workspace,
        )
        segunda = IssuePropertyOption.objects.create(
            issue_property=propriedade, name="Alfa", sort_order=2,
            project=projeto, workspace=projeto.workspace,
        )
        _valor(_tarefa(projeto, create_user, "alfa"), propriedade, value_option=segunda)
        _valor(_tarefa(projeto, create_user, "zulu"), propriedade, value_option=primeira)

        ordenado, _ = order_issue_queryset(
            Issue.issue_objects.filter(project=projeto), f"property__{propriedade.id}"
        )

        assert [t.name for t in ordenado] == ["zulu", "alfa"]

    @pytest.mark.django_db
    def test_a_forged_order_by_falls_back_to_the_default(self, projeto, create_user):
        """O prefixo não pode virar porta para nome de campo arbitrário.

        A allowlist existe contra isso, e a propriedade contorna a allowlist —
        então o contorno valida UUID e a existência da propriedade antes de
        tocar no ORM.
        """
        _tarefa(projeto, create_user, "única")

        for forjado in (
            "property__../../etc",
            "property__nao-e-uuid",
            "property__00000000-0000-0000-0000-000000000000",
            "project__workspace__owner__password",
        ):
            ordenado, param = order_issue_queryset(Issue.issue_objects.filter(project=projeto), forjado)
            assert list(ordenado)  # não explode
            assert not param.lstrip("-").startswith("project__workspace")
