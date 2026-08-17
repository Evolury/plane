# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""O tamanho da página é o número validado, e não o que vem no cursor.

Defeito da revisão do upstream (branch `secur-236`): `get_per_page` recusa
`per_page` acima de `max_per_page`, mas nos paginadores **agrupados** quem
decidia o tamanho da página era o `cursor.value` — que vem do cliente e não
passava por limite nenhum.

Medido antes da correção contra a pilha de desenvolvimento, com `per_page=3` e
30 tarefas num grupo:

    cursor=3:0:0       ->  3 linhas   (o teto pedido)
    cursor=100:0:0     -> 30 linhas   (dez vezes o teto)
    cursor=100000:0:0  -> 30 linhas   (tudo o que havia)

A fixture aqui cria doze, e não trinta: basta passar do teto de três para a
diferença aparecer, e menos linha é teste mais rápido.

Duas divergências do aviso deles, as duas por medição:

* Eles descrevem também **500 por índice negativo**. Aqui não acontece: o
  paginador agrupado FILTRA por `row_number`, não fatia queryset, então `-5`
  devolvia página vazia com 200. Passou a ser 400.

* Eles apenas limitam o `cursor.value` ao teto. Limitar resolve o caso extremo e
  deixa `per_page=3` com `cursor=100` devolvendo 100. A correção aqui vai à
  causa: os agrupados passam a usar o `limit`, como o `OffsetPaginator` sempre
  fez. Não custa nada a fluxo real — **todo cursor que o servidor emite já
  carrega `limit` como valor**, então só um cursor forjado à mão diverge.
"""

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from plane.db.models import Issue, Project, ProjectMember, State

TETO_DE_PAGINA = 3
QUANTAS_TAREFAS = 12


def url(slug, project_id):
    return f"/api/workspaces/{slug}/projects/{project_id}/issues/"


@pytest.fixture
def projeto_cheio(db, workspace, create_user):
    """Um grupo com mais tarefas do que uma página cabe."""
    p = Project.objects.create(name="Paginação", identifier="PAG", workspace=workspace)
    ProjectMember.objects.create(project=p, member=create_user, workspace=workspace, role=20)
    estado = State.objects.create(name="A fazer", project=p, workspace=workspace, group="unstarted")
    Issue.objects.bulk_create(
        [
            Issue(
                name=f"Tarefa {i}",
                project=p,
                workspace=workspace,
                state=estado,
                priority="urgent",
                sequence_id=i + 1,
            )
            for i in range(QUANTAS_TAREFAS)
        ]
    )
    return p


@pytest.fixture
def cliente(db, create_user):
    c = APIClient()
    c.force_authenticate(user=create_user)
    return c


def linhas_do_grupo(resposta, grupo="urgent"):
    return len(resposta.data.get("results", {}).get(grupo, {}).get("results", []))


@pytest.mark.contract
class TestTetoDaPagina:
    @pytest.mark.django_db
    def test_cursor_inflado_nao_aumenta_a_pagina(self, cliente, workspace, projeto_cheio):
        """O caso medido: `cursor=100` com `per_page=3` devolvia 30 linhas."""
        resposta = cliente.get(
            url(workspace.slug, projeto_cheio.id),
            {"group_by": "priority", "per_page": TETO_DE_PAGINA, "cursor": "100:0:0"},
        )
        assert resposta.status_code == status.HTTP_200_OK, resposta.data
        assert linhas_do_grupo(resposta) == TETO_DE_PAGINA

    @pytest.mark.django_db
    def test_cursor_acima_do_teto_global_e_recusado(self, cliente, workspace, projeto_cheio):
        resposta = cliente.get(
            url(workspace.slug, projeto_cheio.id),
            {"group_by": "priority", "per_page": TETO_DE_PAGINA, "cursor": "100000:0:0"},
        )
        assert resposta.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_cursor_negativo_e_recusado_em_vez_de_devolver_pagina_vazia(self, cliente, workspace, projeto_cheio):
        """Antes: 200 com zero linhas — uma recusa disfarçada de resposta."""
        resposta = cliente.get(
            url(workspace.slug, projeto_cheio.id),
            {"group_by": "priority", "per_page": TETO_DE_PAGINA, "cursor": "-5:0:0"},
        )
        assert resposta.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.django_db
    def test_pagina_negativa_e_recusada(self, cliente, workspace, projeto_cheio):
        resposta = cliente.get(
            url(workspace.slug, projeto_cheio.id),
            {"group_by": "priority", "per_page": TETO_DE_PAGINA, "cursor": "3:-1:0"},
        )
        assert resposta.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.contract
class TestAPaginacaoContinuaFuncionando:
    """Sem isto, recusar tudo passaria em todos os testes de cima."""

    @pytest.mark.django_db
    def test_primeira_pagina_traz_o_teto_pedido(self, cliente, workspace, projeto_cheio):
        resposta = cliente.get(
            url(workspace.slug, projeto_cheio.id),
            {"group_by": "priority", "per_page": TETO_DE_PAGINA, "cursor": f"{TETO_DE_PAGINA}:0:0"},
        )
        assert resposta.status_code == status.HTTP_200_OK, resposta.data
        assert linhas_do_grupo(resposta) == TETO_DE_PAGINA

    @pytest.mark.django_db
    def test_as_paginas_avancam_e_nao_se_repetem(self, cliente, workspace, projeto_cheio):
        """A prova de que trocar `cursor.value` por `limit` não travou o avanço.

        Duas páginas seguidas têm de trazer tarefas DIFERENTES — se o `offset`
        tivesse ficado errado, a segunda página repetiria a primeira e o teste de
        contagem acima continuaria verde.
        """
        vistas = []
        for pagina in (0, 1):
            resposta = cliente.get(
                url(workspace.slug, projeto_cheio.id),
                {"group_by": "priority", "per_page": TETO_DE_PAGINA, "cursor": f"{TETO_DE_PAGINA}:{pagina}:0"},
            )
            assert resposta.status_code == status.HTTP_200_OK, resposta.data
            vistas.append({item["id"] for item in resposta.data["results"]["urgent"]["results"]})

        assert len(vistas[0]) == TETO_DE_PAGINA
        assert len(vistas[1]) == TETO_DE_PAGINA
        assert not (vistas[0] & vistas[1]), "a segunda página repetiu a primeira"
