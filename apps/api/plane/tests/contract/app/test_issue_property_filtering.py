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


@pytest.mark.contract
class TestArvoreDeFiltrosRicos:
    """A segunda porta: a árvore JSON que a tela manda em `filters`.

    A tela não manda mais um parâmetro por filtro — manda a árvore inteira, e
    ela vira UM `Q` aplicado numa chamada de `.filter()` só. É exatamente a
    situação em que um join colidiria consigo mesmo, e é por isso que a
    condição de propriedade nasce como subconsulta.
    """

    def _backend(self):
        from plane.utils.filters import FiltroComPropriedades, IssueFilterSet

        class _View:
            filterset_class = IssueFilterSet

        return FiltroComPropriedades(), _View()

    def _filtrar(self, projeto, arvore):
        backend, view = self._backend()
        base = Issue.issue_objects.filter(project=projeto)
        return sorted(t.name for t in backend._apply_json_filter(base, arvore, view))

    @pytest.mark.django_db
    def test_two_properties_in_one_and_node(self, projeto, create_user):
        canal = _prop(projeto, "Canal", "select")
        indicacao = _opcao(canal, "Indicação")
        etiqueta = _prop(projeto, "Etiqueta", "multi_select")
        urgente = _opcao(etiqueta, "Urgente")

        tem_as_duas = _tarefa(projeto, create_user, "tem as duas")
        _valor(tem_as_duas, canal, value_option=indicacao)
        _valor(tem_as_duas, etiqueta, value_option=urgente)

        so_uma = _tarefa(projeto, create_user, "só o canal")
        _valor(so_uma, canal, value_option=indicacao)

        arvore = {
            "and": [
                {f"property_{canal.id}__in": [str(indicacao.id)]},
                {f"property_{etiqueta.id}__in": [str(urgente.id)]},
            ]
        }
        assert self._filtrar(projeto, arvore) == ["tem as duas"]

    @pytest.mark.django_db
    def test_or_and_not_compose(self, projeto, create_user):
        canal = _prop(projeto, "Canal", "select")
        indicacao = _opcao(canal, "Indicação")
        anuncio = _opcao(canal, "Anúncio")

        a = _tarefa(projeto, create_user, "indicação")
        _valor(a, canal, value_option=indicacao)
        b = _tarefa(projeto, create_user, "anúncio")
        _valor(b, canal, value_option=anuncio)
        _tarefa(projeto, create_user, "sem canal")

        ou = {
            "or": [
                {f"property_{canal.id}__in": [str(indicacao.id)]},
                {f"property_{canal.id}__in": [str(anuncio.id)]},
            ]
        }
        assert self._filtrar(projeto, ou) == ["anúncio", "indicação"]

        nao = {"not": {f"property_{canal.id}__in": [str(indicacao.id)]}}
        assert self._filtrar(projeto, nao) == ["anúncio", "sem canal"]

    @pytest.mark.django_db
    def test_property_condition_combines_with_a_product_filter(self, projeto, create_user):
        canal = _prop(projeto, "Canal", "select")
        indicacao = _opcao(canal, "Indicação")

        urgente = _tarefa(projeto, create_user, "urgente")
        urgente.priority = "urgent"
        urgente.save()
        _valor(urgente, canal, value_option=indicacao)

        baixa = _tarefa(projeto, create_user, "baixa")
        baixa.priority = "low"
        baixa.save()
        _valor(baixa, canal, value_option=indicacao)

        arvore = {"and": [{f"property_{canal.id}__in": [str(indicacao.id)]}, {"priority__in": ["urgent"]}]}
        assert self._filtrar(projeto, arvore) == ["urgente"]

    @pytest.mark.django_db
    def test_forged_field_name_is_rejected(self, projeto, create_user):
        """A allowlist continua sendo allowlist: só passa UUID de propriedade."""
        from rest_framework.exceptions import ValidationError

        _tarefa(projeto, create_user, "qualquer")
        for forjado in (
            "property_workspace__slug",
            "property_../../etc",
            "property_1; drop table",
            "property_created_by__email",
        ):
            with pytest.raises(ValidationError):
                self._filtrar(projeto, {forjado: ["x"]})

    @pytest.mark.django_db
    def test_inactive_property_filters_nothing_instead_of_breaking(self, projeto, create_user):
        """Visão salva com propriedade desligada não pode derrubar a tela."""
        canal = _prop(projeto, "Canal", "select", is_active=False)
        indicacao = _opcao(canal, "Indicação")
        tarefa = _tarefa(projeto, create_user, "tem o valor")
        _valor(tarefa, canal, value_option=indicacao)
        _tarefa(projeto, create_user, "não tem")

        # As duas voltam: a condição foi descartada, e não aplicada.
        assert self._filtrar(projeto, {f"property_{canal.id}__in": [str(indicacao.id)]}) == [
            "não tem",
            "tem o valor",
        ]

    @pytest.mark.django_db
    def test_deleted_value_stops_counting(self, projeto, create_user):
        """O join não passava pelo gerente do modelo; a subconsulta passa."""
        canal = _prop(projeto, "Canal", "select")
        indicacao = _opcao(canal, "Indicação")
        tarefa = _tarefa(projeto, create_user, "teve canal")
        valor = _valor(tarefa, canal, value_option=indicacao)
        valor.delete()

        assert self._filtrar(projeto, {f"property_{canal.id}__in": [str(indicacao.id)]}) == []


@pytest.mark.contract
class TestOperadoresDaTela:
    """`exact` e `range`, que são o que o seletor visual emite.

    A tela de filtros ricos oferece "é" e "entre", e serializa como
    `property_<id>__exact` e `property_<id>__range` com "início,fim". O caminho
    por parâmetro de consulta já falava `_gte`/`_lte`; estes traduzem para o
    mesmo lugar, para não existirem dois formatos de faixa no backend.
    """

    def _filtrar(self, projeto, arvore):
        from plane.utils.filters import FiltroComPropriedades, IssueFilterSet

        class _View:
            filterset_class = IssueFilterSet

        base = Issue.issue_objects.filter(project=projeto)
        return sorted(t.name for t in FiltroComPropriedades()._apply_json_filter(base, arvore, _View()))

    @pytest.mark.django_db
    def test_exact_on_a_date(self, projeto, create_user):
        aceite = _prop(projeto, "Aceite", "date")
        no_dia = _tarefa(projeto, create_user, "no dia")
        _valor(no_dia, aceite, value_date="2026-08-20")
        outro = _tarefa(projeto, create_user, "outro dia")
        _valor(outro, aceite, value_date="2026-08-21")

        assert self._filtrar(projeto, {f"property_{aceite.id}__exact": "2026-08-20"}) == ["no dia"]

    @pytest.mark.django_db
    def test_range_on_a_date(self, projeto, create_user):
        aceite = _prop(projeto, "Aceite", "date")
        for nome, dia in (("antes", "2026-08-01"), ("dentro", "2026-08-15"), ("depois", "2026-09-01")):
            _valor(_tarefa(projeto, create_user, nome), aceite, value_date=dia)

        assert self._filtrar(projeto, {f"property_{aceite.id}__range": "2026-08-10,2026-08-20"}) == ["dentro"]

    @pytest.mark.django_db
    def test_range_on_a_number(self, projeto, create_user):
        peso = _prop(projeto, "Peso", "number")
        for nome, valor in (("leve", "1"), ("medio", "10"), ("pesado", "100")):
            _valor(_tarefa(projeto, create_user, nome), peso, value_number=valor)

        assert self._filtrar(projeto, {f"property_{peso.id}__range": "5,50"}) == ["medio"]

    @pytest.mark.django_db
    def test_exact_on_currency_respects_the_value(self, projeto, create_user):
        contrato = _prop(projeto, "Contrato", "currency", currency="BRL")
        certo = _tarefa(projeto, create_user, "certo")
        _valor(certo, contrato, value_number="1999.90")
        _valor(_tarefa(projeto, create_user, "errado"), contrato, value_number="1999.91")

        assert self._filtrar(projeto, {f"property_{contrato.id}__exact": "1999.90"}) == ["certo"]

    @pytest.mark.django_db
    def test_a_malformed_range_does_not_filter_at_all(self, projeto, create_user):
        """Faixa quebrada não pode virar consulta ampla nem erro de ORM."""
        peso = _prop(projeto, "Peso", "number")
        _valor(_tarefa(projeto, create_user, "uma"), peso, value_number="10")
        _tarefa(projeto, create_user, "outra")

        for quebrada in ("5", "5,10,20", "abc,def", ""):
            assert self._filtrar(projeto, {f"property_{peso.id}__range": quebrada}) == ["outra", "uma"], quebrada

    @pytest.mark.django_db
    def test_text_keeps_answering_contains(self, projeto, create_user):
        """A tela manda `__contains`; o backend já traduzia para `icontains`."""
        obs = _prop(projeto, "Observação", "text")
        _valor(_tarefa(projeto, create_user, "com trecho"), obs, value_text="entrega em SP")
        _valor(_tarefa(projeto, create_user, "sem trecho"), obs, value_text="entrega em RJ")

        assert self._filtrar(projeto, {f"property_{obs.id}__contains": "SP"}) == ["com trecho"]
