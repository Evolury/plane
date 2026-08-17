# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Propriedade de seleção aceita `"id"` e `["id"]` — a conferência e a gravação
fazem a mesma pergunta.

O tipo que a tela usa é `string | string[]` (`TPropertyValue`), e o multi-select
sempre aceitou os dois formatos. O select simples não: a gravação fazia
`[valor]` sem normalizar, então uma lista virava lista dentro de lista, o
`id__in` recebia `[["..."]]` e o Django levantava `ValidationError`.

O que chegava na tela era `{"error": "Please provide valid detail"}` — uma frase
que não diz nada a quem preencheu o campo. Criar tarefa com a propriedade
preenchida falhava, e o motivo ficava escondido.

Pior que o formato: **a conferência e a gravação discordavam**. `validar_valores`
aceitava a lista e `gravar_valor` recusava depois — e essa função existe
justamente para que valor recusado não deixe a tarefa criada pela metade.

Medido antes da correção, com uma propriedade de seleção obrigatória:

    property_values: {id: "opcao"}     -> 201
    property_values: {id: ["opcao"]}   -> 400  {"error": "Please provide valid detail"}
"""

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from plane.db.models import IssueProperty, IssuePropertyOption, IssuePropertyValue, Project, ProjectMember


@pytest.fixture
def projeto(db, workspace, create_user):
    p = Project.objects.create(name="Seleção", identifier="SEL", workspace=workspace)
    ProjectMember.objects.create(project=p, member=create_user, workspace=workspace, role=20)
    return p


@pytest.fixture
def propriedade(db, workspace, projeto):
    prop = IssueProperty.objects.create(
        name="Origem",
        project=projeto,
        workspace=workspace,
        property_type="select",
        is_required=False,
        is_active=True,
    )
    opcoes = [
        IssuePropertyOption.objects.create(issue_property=prop, name=nome, project=projeto, workspace=workspace)
        for nome in ("Site", "Feira")
    ]
    return prop, opcoes


@pytest.fixture
def cliente(db, create_user):
    c = APIClient()
    c.force_authenticate(user=create_user)
    return c


def criar(cliente, workspace, projeto, valor, nome="Tarefa"):
    return cliente.post(
        f"/api/workspaces/{workspace.slug}/projects/{projeto.id}/issues/",
        {"name": nome, "property_values": valor},
        format="json",
    )


@pytest.mark.contract
class TestValorDeSelecao:
    @pytest.mark.django_db
    def test_aceita_o_id_dentro_de_uma_lista(self, cliente, workspace, projeto, propriedade):
        """O caso medido: falhava com 400 e mensagem que não explicava nada."""
        prop, opcoes = propriedade

        resposta = criar(cliente, workspace, projeto, {str(prop.id): [str(opcoes[0].id)]})

        assert resposta.status_code == status.HTTP_201_CREATED, resposta.data
        gravado = IssuePropertyValue.objects.get(issue_id=resposta.data["id"], issue_property=prop)
        assert gravado.value_option_id == opcoes[0].id

    @pytest.mark.django_db
    def test_aceita_o_id_solto(self, cliente, workspace, projeto, propriedade):
        """O formato que já funcionava continua funcionando."""
        prop, opcoes = propriedade

        resposta = criar(cliente, workspace, projeto, {str(prop.id): str(opcoes[1].id)}, nome="Solta")

        assert resposta.status_code == status.HTTP_201_CREATED, resposta.data
        gravado = IssuePropertyValue.objects.get(issue_id=resposta.data["id"], issue_property=prop)
        assert gravado.value_option_id == opcoes[1].id

    @pytest.mark.django_db
    def test_duas_opcoes_num_select_simples_e_recusado_com_frase(self, cliente, workspace, projeto, propriedade):
        """Recusa antes de criar a tarefa, e dizendo o nome da propriedade."""
        prop, opcoes = propriedade

        resposta = criar(cliente, workspace, projeto, {str(prop.id): [str(o.id) for o in opcoes]}, nome="Duas")

        assert resposta.status_code == status.HTTP_400_BAD_REQUEST
        assert "Origem" in str(resposta.data["property_values"])
        assert "uma opção" in str(resposta.data["property_values"])

    @pytest.mark.django_db
    def test_lixo_no_lugar_do_id_vira_frase_e_nao_erro_generico(self, cliente, workspace, projeto, propriedade):
        """`id__in` com algo que não é UUID estourava `ValidationError` do Django.

        Aquilo subia como "Please provide valid detail", que é o mesmo texto de
        qualquer outro erro — impossível de agir sobre.
        """
        prop, _ = propriedade

        resposta = criar(cliente, workspace, projeto, {str(prop.id): "isto-não-é-uuid"}, nome="Lixo")

        assert resposta.status_code == status.HTTP_400_BAD_REQUEST
        assert "Origem" in str(resposta.data.get("property_values", resposta.data))

    @pytest.mark.django_db
    def test_a_tarefa_nao_nasce_quando_o_valor_e_recusado(self, cliente, workspace, projeto, propriedade):
        """A razão de `validar_valores` existir, trancada por teste.

        Antes, conferência e gravação discordavam sobre a lista: a primeira
        aceitava, a segunda recusava — e a tarefa já estava criada.
        """
        from plane.db.models import Issue

        prop, opcoes = propriedade
        criar(cliente, workspace, projeto, {str(prop.id): [str(o.id) for o in opcoes]}, nome="Não deve existir")

        assert not Issue.objects.filter(project=projeto, name="Não deve existir").exists()
