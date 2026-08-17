# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""A tarefa nomeada na URL tem de ser do projeto nomeado na URL.

Defeito da revisão do upstream (SECUR-243): as rotas de sub-recurso de tarefa
trazem projeto **e** tarefa no caminho, e nada amarrava um ao outro. A
permissão dizia "sim" porque quem pediu é membro do projeto A; a ação então
trabalhava sobre uma tarefa do projeto B, porque ninguém perguntou de que
projeto ela era.

Medido antes da correção, como membro de A apontando para uma tarefa de B:

* comentário, link, reação, inscrição e relação **criados** na tarefa alheia;
* relação alheia **apagada**;
* lista de subtarefas de B **devolvida na íntegra** (as demais leituras já
  filtravam por projeto e voltavam vazias — o furo de leitura era esse um).

E a mesma coisa pela API pública, com token: comentário e link criados na
tarefa alheia.

A correção é um `initial` no mixin compartilhado pelas duas APIs, então este
arquivo não testa uma rota: testa a regra. Os casos abaixo cobrem as duas
portas e as duas naturezas — o que se lê e o que se escreve — e terminam com
os controles positivos, porque um 404 chapado passaria em tudo o que vem antes.
"""

from uuid import uuid4

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from plane.db.models import (
    Issue,
    IssueComment,
    IssueLink,
    IssueReaction,
    IssueSubscriber,
    Project,
    ProjectMember,
    State,
    User,
    WorkspaceMember,
)


@pytest.fixture
def dois_projetos(db, workspace, create_user):
    """A: quem testa é membro. B: alheio, com uma tarefa e conteúdo dentro."""
    a = Project.objects.create(name="A", identifier="AAA", workspace=workspace, created_by=create_user)
    ProjectMember.objects.create(project=a, member=create_user, workspace=workspace, role=20)
    estado_a = State.objects.create(name="A fazer", project=a, workspace=workspace, group="unstarted")
    minha = Issue.objects.create(name="Minha de A", project=a, workspace=workspace, state=estado_a)

    marca = uuid4().hex[:8]
    dono = User.objects.create(email=f"dono-{marca}@plane.so", username=f"dono_{marca}")
    dono.set_password("test-password")
    dono.save()
    WorkspaceMember.objects.create(workspace=workspace, member=dono, role=20)
    b = Project.objects.create(name="B", identifier="BBB", workspace=workspace, created_by=dono)
    ProjectMember.objects.create(project=b, member=dono, workspace=workspace, role=20)
    estado_b = State.objects.create(name="A fazer", project=b, workspace=workspace, group="unstarted")
    alheia = Issue.objects.create(name="Segredo de B", project=b, workspace=workspace, state=estado_b)
    Issue.objects.create(name="Subtarefa secreta de B", project=b, workspace=workspace, state=estado_b, parent=alheia)

    return {"a": a, "b": b, "minha": minha, "alheia": alheia, "slug": workspace.slug}


@pytest.fixture
def cliente(db, create_user):
    cli = APIClient()
    cli.force_authenticate(user=create_user)
    return cli


@pytest.mark.contract
class TestLeitura:
    @pytest.mark.django_db
    def test_nao_lista_as_subtarefas_da_tarefa_alheia(self, cliente, dois_projetos):
        """O único furo de LEITURA medido: as subtarefas vinham inteiras."""
        url = (
            f"/api/workspaces/{dois_projetos['slug']}/projects/{dois_projetos['a'].id}"
            f"/issues/{dois_projetos['alheia'].id}/sub-issues/"
        )
        resposta = cliente.get(url)

        assert resposta.status_code == status.HTTP_404_NOT_FOUND
        assert "Subtarefa secreta de B" not in str(resposta.data)

    @pytest.mark.django_db
    def test_a_recusa_e_404_e_nao_403(self, cliente, dois_projetos):
        """403 confirmaria que a tarefa existe em algum lugar. 404 não conta nada."""
        url = (
            f"/api/workspaces/{dois_projetos['slug']}/projects/{dois_projetos['a'].id}"
            f"/issues/{dois_projetos['alheia'].id}/comments/"
        )
        assert cliente.get(url).status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.contract
class TestEscrita:
    """Cada um destes criava ou apagava linha na tarefa de outro projeto."""

    @pytest.mark.django_db
    def test_nao_comenta_na_tarefa_alheia(self, cliente, dois_projetos, create_user):
        url = (
            f"/api/workspaces/{dois_projetos['slug']}/projects/{dois_projetos['a'].id}"
            f"/issues/{dois_projetos['alheia'].id}/comments/"
        )
        resposta = cliente.post(url, {"comment_html": "<p>invadi</p>"}, format="json")

        assert resposta.status_code == status.HTTP_404_NOT_FOUND
        assert not IssueComment.objects.filter(issue=dois_projetos["alheia"], actor=create_user).exists()

    @pytest.mark.django_db
    def test_nao_anexa_link_na_tarefa_alheia(self, cliente, dois_projetos, create_user):
        url = (
            f"/api/workspaces/{dois_projetos['slug']}/projects/{dois_projetos['a'].id}"
            f"/issues/{dois_projetos['alheia'].id}/issue-links/"
        )
        resposta = cliente.post(url, {"url": "https://exemplo.com"}, format="json")

        assert resposta.status_code == status.HTTP_404_NOT_FOUND
        assert not IssueLink.objects.filter(issue=dois_projetos["alheia"], created_by=create_user).exists()

    @pytest.mark.django_db
    def test_nao_reage_na_tarefa_alheia(self, cliente, dois_projetos, create_user):
        url = (
            f"/api/workspaces/{dois_projetos['slug']}/projects/{dois_projetos['a'].id}"
            f"/issues/{dois_projetos['alheia'].id}/reactions/"
        )
        resposta = cliente.post(url, {"reaction": "128077"}, format="json")

        assert resposta.status_code == status.HTTP_404_NOT_FOUND
        assert not IssueReaction.objects.filter(issue=dois_projetos["alheia"], actor=create_user).exists()

    @pytest.mark.django_db
    def test_nao_se_inscreve_na_tarefa_alheia(self, cliente, dois_projetos, create_user):
        url = (
            f"/api/workspaces/{dois_projetos['slug']}/projects/{dois_projetos['a'].id}"
            f"/issues/{dois_projetos['alheia'].id}/subscribe/"
        )
        resposta = cliente.post(url, {}, format="json")

        assert resposta.status_code == status.HTTP_404_NOT_FOUND
        assert not IssueSubscriber.objects.filter(issue=dois_projetos["alheia"], subscriber=create_user).exists()

    @pytest.mark.django_db
    def test_nao_relaciona_a_partir_da_tarefa_alheia(self, cliente, dois_projetos):
        from plane.db.models import IssueRelation

        url = (
            f"/api/workspaces/{dois_projetos['slug']}/projects/{dois_projetos['a'].id}"
            f"/issues/{dois_projetos['alheia'].id}/issue-relation/"
        )
        resposta = cliente.post(
            url, {"relation_type": "relates_to", "issues": [str(dois_projetos["minha"].id)]}, format="json"
        )

        assert resposta.status_code == status.HTTP_404_NOT_FOUND
        assert not IssueRelation.objects.filter(issue=dois_projetos["alheia"]).exists()
        assert not IssueRelation.objects.filter(related_issue=dois_projetos["alheia"]).exists()


@pytest.mark.contract
class TestApiPublica:
    """A mesma falha pela outra porta, com token em vez de sessão."""

    @pytest.mark.django_db
    def test_nao_comenta_na_tarefa_alheia(self, api_key_client, dois_projetos, create_user):
        url = (
            f"/api/v1/workspaces/{dois_projetos['slug']}/projects/{dois_projetos['a'].id}"
            f"/issues/{dois_projetos['alheia'].id}/comments/"
        )
        resposta = api_key_client.post(url, {"comment_html": "<p>invadi</p>"}, format="json")

        assert resposta.status_code == status.HTTP_404_NOT_FOUND
        assert not IssueComment.objects.filter(issue=dois_projetos["alheia"], actor=create_user).exists()

    @pytest.mark.django_db
    def test_nao_anexa_link_na_tarefa_alheia(self, api_key_client, dois_projetos, create_user):
        url = (
            f"/api/v1/workspaces/{dois_projetos['slug']}/projects/{dois_projetos['a'].id}"
            f"/issues/{dois_projetos['alheia'].id}/links/"
        )
        resposta = api_key_client.post(url, {"url": "https://exemplo.com"}, format="json")

        assert resposta.status_code == status.HTTP_404_NOT_FOUND
        assert not IssueLink.objects.filter(issue=dois_projetos["alheia"], created_by=create_user).exists()


@pytest.mark.contract
class TestOQueTemDeContinuarFuncionando:
    """Sem estes, um 404 chapado passaria em todo o resto do arquivo."""

    @pytest.mark.django_db
    def test_comenta_na_propria_tarefa(self, cliente, dois_projetos):
        url = (
            f"/api/workspaces/{dois_projetos['slug']}/projects/{dois_projetos['a'].id}"
            f"/issues/{dois_projetos['minha'].id}/comments/"
        )
        resposta = cliente.post(url, {"comment_html": "<p>meu comentário</p>"}, format="json")

        assert resposta.status_code == status.HTTP_201_CREATED, resposta.data
        assert IssueComment.objects.filter(issue=dois_projetos["minha"]).exists()

    @pytest.mark.django_db
    def test_le_a_propria_tarefa(self, cliente, dois_projetos):
        url = (
            f"/api/workspaces/{dois_projetos['slug']}/projects/{dois_projetos['a'].id}"
            f"/issues/{dois_projetos['minha'].id}/sub-issues/"
        )
        assert cliente.get(url).status_code == status.HTTP_200_OK

    @pytest.mark.django_db
    def test_rota_sem_projeto_no_caminho_nao_e_afetada(self, cliente, dois_projetos):
        """`my-tasks` é rota de workspace: não há projeto na URL a amarrar.

        Se o guarda tentasse agir aqui, a etapa pessoal quebraria para todo
        mundo — e nenhum dos testes de recusa acima notaria.
        """
        url = f"/api/workspaces/{dois_projetos['slug']}/my-tasks/issues/{dois_projetos['minha'].id}/stage/"
        assert cliente.post(url, {"stage": "today"}, format="json").status_code != status.HTTP_404_NOT_FOUND
