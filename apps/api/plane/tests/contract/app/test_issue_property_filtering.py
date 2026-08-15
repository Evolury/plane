# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Filtrar por propriedade personalizada (ADR 0011, P4.1).

O teste que mais importa aqui é o de DUAS propriedades ao mesmo tempo. Os
filtros do produto viram `kwargs` de uma única chamada de `.filter()`, e duas
condições sobre a mesma relação ali recairiam na mesma linha do join — o
resultado viria vazio para uma tarefa que tem as duas coisas, e ninguém
entenderia por quê.
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
from plane.utils.issue_properties import aplicar_filtros_de_propriedade


@pytest.fixture
def projeto(db, workspace, create_user):
    projeto = Project.objects.create(name="Projeto", identifier="PRJ", workspace=workspace, created_by=create_user)
    ProjectMember.objects.create(project=projeto, member=create_user, role=20, is_active=True)
    State.objects.filter(project=projeto).delete()
    State.objects.create(
        name="Pendente", group="backlog", project=projeto, workspace=workspace, color="#000", default=True
    )
    return projeto


def _prop(projeto, nome, tipo, **campos):
    return IssueProperty.objects.create(
        name=nome, property_type=tipo, project=projeto, workspace=projeto.workspace, **campos
    )


def _opcao(prop, nome):
    return IssuePropertyOption.objects.create(
        issue_property=prop, name=nome, project=prop.project, workspace=prop.workspace
    )


def _tarefa(projeto, create_user, nome):
    return Issue.objects.create(name=nome, project=projeto, workspace=projeto.workspace, created_by=create_user)


def _valor(tarefa, prop, **campos):
    return IssuePropertyValue.objects.create(
        issue=tarefa, issue_property=prop, project=tarefa.project, workspace=tarefa.workspace, **campos
    )


def _nomes(projeto, params):
    base = Issue.issue_objects.filter(project=projeto)
    return sorted(t.name for t in aplicar_filtros_de_propriedade(base, params))


@pytest.mark.contract
class TestFiltro:
    @pytest.mark.django_db
    def test_two_properties_at_once_do_not_collide(self, projeto, create_user):
        """A razão de o filtro devolver `Q` em vez de `kwargs`.

        Num `.filter()` só, a segunda condição recairia sobre a linha que a
        primeira escolheu, e a tarefa que tem AS DUAS coisas sumiria.
        """
        canal = _prop(projeto, "Canal", "select")
        tags = _prop(projeto, "Tags", "multi_select")
        indicacao, urgente = _opcao(canal, "Indicação"), _opcao(tags, "Urgente")

        as_duas = _tarefa(projeto, create_user, "as duas")
        _valor(as_duas, canal, value_option=indicacao)
        _valor(as_duas, tags, value_option=urgente)
        so_uma = _tarefa(projeto, create_user, "só uma")
        _valor(so_uma, canal, value_option=indicacao)

        achados = _nomes(
            projeto,
            {f"property_{canal.id}": str(indicacao.id), f"property_{tags.id}": str(urgente.id)},
        )

        assert achados == ["as duas"]

    @pytest.mark.django_db
    def test_select_matches_any_of_the_options(self, projeto, create_user):
        canal = _prop(projeto, "Canal", "select")
        a, b, c = _opcao(canal, "A"), _opcao(canal, "B"), _opcao(canal, "C")
        for nome, opcao in (("com a", a), ("com b", b), ("com c", c)):
            _valor(_tarefa(projeto, create_user, nome), canal, value_option=opcao)

        assert _nomes(projeto, {f"property_{canal.id}": f"{a.id},{b.id}"}) == ["com a", "com b"]

    @pytest.mark.django_db
    def test_text_matches_a_fragment(self, projeto, create_user):
        obs = _prop(projeto, "Observação", "text")
        _valor(_tarefa(projeto, create_user, "casa"), obs, value_text="Contrato assinado")
        _valor(_tarefa(projeto, create_user, "não casa"), obs, value_text="Aguardando")

        assert _nomes(projeto, {f"property_{obs.id}": "assinad"}) == ["casa"]

    @pytest.mark.django_db
    def test_number_and_date_match_a_range(self, projeto, create_user):
        peso = _prop(projeto, "Peso", "number")
        for nome, valor in (("baixo", "5"), ("meio", "50"), ("alto", "500")):
            _valor(_tarefa(projeto, create_user, nome), peso, value_number=valor)

        assert _nomes(projeto, {f"property_{peso.id}_gte": "10", f"property_{peso.id}_lte": "100"}) == ["meio"]

        aceite = _prop(projeto, "Aceite", "date")
        for nome, data in (("antes", "2026-01-01"), ("dentro", "2026-06-15"), ("depois", "2026-12-31")):
            _valor(_tarefa(projeto, create_user, f"d {nome}"), aceite, value_date=data)

        assert _nomes(
            projeto, {f"property_{aceite.id}_gte": "2026-05-01", f"property_{aceite.id}_lte": "2026-07-01"}
        ) == ["d dentro"]

    @pytest.mark.django_db
    def test_a_forged_filter_never_becomes_a_query(self, projeto, create_user):
        """Pedido malformado não vira consulta — nem ampla, nem erro de ORM."""
        _tarefa(projeto, create_user, "única")

        for params in (
            {"property_nao-e-uuid": "x"},
            {"property_../../etc": "x"},
            {"property_00000000-0000-0000-0000-000000000000": "x"},
            {"property_": "x"},
        ):
            assert _nomes(projeto, params) == ["única"], params

    @pytest.mark.django_db
    def test_an_invalid_option_id_is_ignored_instead_of_widening(self, projeto, create_user):
        """Opção inválida não pode alargar o filtro para tudo."""
        canal = _prop(projeto, "Canal", "select")
        a = _opcao(canal, "A")
        _valor(_tarefa(projeto, create_user, "com a"), canal, value_option=a)
        _tarefa(projeto, create_user, "sem valor")

        assert _nomes(projeto, {f"property_{canal.id}": "nao-e-uuid"}) == ["com a", "sem valor"]
        assert _nomes(projeto, {f"property_{canal.id}": f"nao-e-uuid,{a.id}"}) == ["com a"]
