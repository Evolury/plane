# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Excluir muitas tarefas, e desfazer (ADR 0018).

O endpoint já existia e não fazia o que a exclusão de UMA tarefa faz: marcava
`deleted_at` só nas tarefas. A subtarefa continuava viva apontando para um pai
excluído, o histórico não registrava nada, e só administrador podia — enquanto
no singular quem criou também pode.

O que estes testes fixam é isso, e mais uma coisa que só aparece com o desfazer:
**restaurar devolve o lote, e apenas o lote**. Uma tarefa excluída ontem não
pode voltar de carona.
"""

from unittest.mock import patch

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from plane.db.models import Issue, IssueComment, Project, ProjectMember, User, WorkspaceMember

EXCLUIR = "/api/workspaces/{slug}/projects/{pid}/bulk-delete-issues/"
RESTAURAR = "/api/workspaces/{slug}/projects/{pid}/bulk-restore-issues/"

TAREFA = "plane.app.views.issue.base.registrar_exclusao_em_massa"


@pytest.fixture
def projeto(db, workspace, create_user):
    projeto = Project.objects.create(name="Projeto", identifier="PRJ", workspace=workspace, created_by=create_user)
    ProjectMember.objects.create(project=projeto, member=create_user, role=20, is_active=True)
    return projeto


@pytest.fixture
def membro(db, workspace, projeto):
    """Alguém que participa do projeto, mas não é administrador."""
    outro = User.objects.create(email="membro@evolury.com.br", username="membro", first_name="Membro")
    WorkspaceMember.objects.create(workspace=workspace, member=outro, role=15)
    ProjectMember.objects.create(project=projeto, member=outro, role=15, is_active=True)
    return outro


@pytest.fixture
def cliente_do_membro(membro):
    """Cliente PRÓPRIO, e não o `api_client` compartilhado.

    `session_client` e este autenticam a mesma instância quando compartilham a
    fixture, e o último a resolver vence — o teste que usa os dois acabaria
    fazendo tudo com um usuário só, e passaria dizendo o contrário.
    """
    cliente = APIClient()
    cliente.force_authenticate(user=membro)
    return cliente


def nova_tarefa(projeto, workspace, autor, nome="Tarefa", pai=None):
    """`created_by` entra por `update`, e não por `create`.

    O `save()` da base sobrescreve o campo com o usuário do PEDIDO — e, sem
    pedido, com `None` (`plane/db/models/base.py`). É a guarda que impede o
    cliente de dizer quem criou o quê; aqui ela precisa ser contornada, porque
    o que se está testando é justamente a regra de "quem criou pode excluir".
    """
    tarefa = Issue.objects.create(name=nome, project=projeto, workspace=workspace, parent=pai)
    Issue.objects.filter(pk=tarefa.pk).update(created_by=autor)
    tarefa.refresh_from_db()
    return tarefa


@pytest.mark.contract
class TestExclusaoEmMassa:
    def test_deletes_the_selected_work_items(self, session_client, workspace, projeto, create_user):
        tarefas = [nova_tarefa(projeto, workspace, create_user, f"T{i}") for i in range(3)]

        with patch(TAREFA):
            resposta = session_client.delete(
                EXCLUIR.format(slug=workspace.slug, pid=projeto.id),
                {"issue_ids": [str(t.id) for t in tarefas]},
                format="json",
            )

        assert resposta.status_code == status.HTTP_200_OK
        assert resposta.data["deleted"] == 3
        assert Issue.issue_objects.filter(project=projeto).count() == 0

    def test_the_cascade_takes_sub_items_and_comments(self, session_client, workspace, projeto, create_user):
        """O buraco do endpoint antigo: a subtarefa ficava viva, órfã de um pai
        que não existe mais."""
        pai = nova_tarefa(projeto, workspace, create_user, "Pai")
        filha = nova_tarefa(projeto, workspace, create_user, "Filha", pai=pai)
        comentario = IssueComment.objects.create(
            issue=pai, project=projeto, workspace=workspace, comment_html="<p>oi</p>", actor=create_user
        )

        with patch(TAREFA):
            session_client.delete(
                EXCLUIR.format(slug=workspace.slug, pid=projeto.id),
                {"issue_ids": [str(pai.id)]},
                format="json",
            )

        filha.refresh_from_db()
        comentario.refresh_from_db()
        assert filha.deleted_at is not None
        assert comentario.deleted_at is not None

    def test_the_whole_batch_shares_one_instant(self, session_client, workspace, projeto, create_user):
        """O instante é a identidade do lote — é por ele que o desfazer acha o
        que devolver. Se cada linha levasse o seu, não haveria lote nenhum."""
        pai = nova_tarefa(projeto, workspace, create_user, "Pai")
        filha = nova_tarefa(projeto, workspace, create_user, "Filha", pai=pai)

        with patch(TAREFA):
            resposta = session_client.delete(
                EXCLUIR.format(slug=workspace.slug, pid=projeto.id),
                {"issue_ids": [str(pai.id)]},
                format="json",
            )

        pai.refresh_from_db()
        filha.refresh_from_db()
        assert pai.deleted_at == filha.deleted_at
        assert resposta.data["batch"] == pai.deleted_at.isoformat()

    def test_records_history_for_every_item(self, session_client, workspace, projeto, create_user):
        tarefas = [nova_tarefa(projeto, workspace, create_user, f"T{i}") for i in range(2)]

        with patch(TAREFA) as tarefa:
            session_client.delete(
                EXCLUIR.format(slug=workspace.slug, pid=projeto.id),
                {"issue_ids": [str(t.id) for t in tarefas]},
                format="json",
            )

        argumentos = tarefa.delay.call_args.kwargs
        assert argumentos["verbo"] == "deleted"
        assert sorted(argumentos["issue_ids"]) == sorted(str(t.id) for t in tarefas)

    def test_a_member_may_delete_what_they_created(self, cliente_do_membro, workspace, projeto, membro):
        """A mesma regra do singular: administrador OU quem criou."""
        minhas = [nova_tarefa(projeto, workspace, membro, f"T{i}") for i in range(2)]

        with patch(TAREFA):
            resposta = cliente_do_membro.delete(
                EXCLUIR.format(slug=workspace.slug, pid=projeto.id),
                {"issue_ids": [str(t.id) for t in minhas]},
                format="json",
            )

        assert resposta.status_code == status.HTTP_200_OK
        assert Issue.issue_objects.filter(project=projeto).count() == 0

    def test_refuses_the_whole_request_when_one_item_is_not_theirs(
        self, cliente_do_membro, workspace, projeto, membro, create_user
    ):
        """Excluir 8 de 10 sem dizer quais ficaram é pior que não excluir nada."""
        minha = nova_tarefa(projeto, workspace, membro, "Minha")
        alheia = nova_tarefa(projeto, workspace, create_user, "Alheia")

        with patch(TAREFA):
            resposta = cliente_do_membro.delete(
                EXCLUIR.format(slug=workspace.slug, pid=projeto.id),
                {"issue_ids": [str(minha.id), str(alheia.id)]},
                format="json",
            )

        assert resposta.status_code == status.HTTP_403_FORBIDDEN
        assert resposta.data["error"] == "NOT_ALLOWED_FOR_SOME"
        assert Issue.issue_objects.filter(project=projeto).count() == 2

    def test_refuses_more_than_the_ceiling(self, session_client, workspace, projeto):
        ids = [str(numero) for numero in range(501)]

        resposta = session_client.delete(
            EXCLUIR.format(slug=workspace.slug, pid=projeto.id), {"issue_ids": ids}, format="json"
        )

        assert resposta.status_code == status.HTTP_400_BAD_REQUEST
        assert resposta.data["error"] == "TOO_MANY_ISSUES"

    def test_does_not_reach_another_project(self, session_client, workspace, projeto, create_user):
        vizinho = Project.objects.create(
            name="Vizinho", identifier="VIZ", workspace=workspace, created_by=create_user
        )
        ProjectMember.objects.create(project=vizinho, member=create_user, role=20, is_active=True)
        de_fora = nova_tarefa(vizinho, workspace, create_user, "De fora")

        resposta = session_client.delete(
            EXCLUIR.format(slug=workspace.slug, pid=projeto.id),
            {"issue_ids": [str(de_fora.id)]},
            format="json",
        )

        assert resposta.status_code == status.HTTP_400_BAD_REQUEST
        de_fora.refresh_from_db()
        assert de_fora.deleted_at is None


@pytest.mark.contract
class TestDesfazer:
    def _excluir(self, cliente, workspace, projeto, tarefas):
        with patch(TAREFA):
            resposta = cliente.delete(
                EXCLUIR.format(slug=workspace.slug, pid=projeto.id),
                {"issue_ids": [str(t.id) for t in tarefas]},
                format="json",
            )
        return resposta.data["batch"]

    def test_brings_the_batch_back(self, session_client, workspace, projeto, create_user):
        tarefas = [nova_tarefa(projeto, workspace, create_user, f"T{i}") for i in range(3)]
        lote = self._excluir(session_client, workspace, projeto, tarefas)

        with patch(TAREFA) as tarefa:
            resposta = session_client.post(
                RESTAURAR.format(slug=workspace.slug, pid=projeto.id), {"batch": lote}, format="json"
            )

        assert resposta.status_code == status.HTTP_200_OK
        assert resposta.data["restored"] == 3
        assert Issue.issue_objects.filter(project=projeto).count() == 3
        assert tarefa.delay.call_args.kwargs["verbo"] == "restored"

    def test_brings_back_what_fell_with_it(self, session_client, workspace, projeto, create_user):
        pai = nova_tarefa(projeto, workspace, create_user, "Pai")
        filha = nova_tarefa(projeto, workspace, create_user, "Filha", pai=pai)
        comentario = IssueComment.objects.create(
            issue=pai, project=projeto, workspace=workspace, comment_html="<p>oi</p>", actor=create_user
        )
        lote = self._excluir(session_client, workspace, projeto, [pai])

        with patch(TAREFA):
            session_client.post(
                RESTAURAR.format(slug=workspace.slug, pid=projeto.id), {"batch": lote}, format="json"
            )

        filha.refresh_from_db()
        comentario.refresh_from_db()
        assert filha.deleted_at is None
        assert comentario.deleted_at is None

    def test_does_not_resurrect_what_was_deleted_before(self, session_client, workspace, projeto, create_user):
        """O ponto do lote: desfazer devolve o que ESTA exclusão levou, e nada
        do que já estava excluído antes."""
        antiga = nova_tarefa(projeto, workspace, create_user, "Antiga")
        antiga.delete()
        assert antiga.deleted_at is not None

        nova = nova_tarefa(projeto, workspace, create_user, "Nova")
        lote = self._excluir(session_client, workspace, projeto, [nova])

        with patch(TAREFA):
            session_client.post(
                RESTAURAR.format(slug=workspace.slug, pid=projeto.id), {"batch": lote}, format="json"
            )

        antiga.refresh_from_db()
        assert antiga.deleted_at is not None
        assert Issue.issue_objects.filter(project=projeto, name="Nova").exists()

    def test_refuses_a_batch_that_is_not_theirs(
        self, session_client, cliente_do_membro, workspace, projeto, create_user
    ):
        alheia = nova_tarefa(projeto, workspace, create_user, "Alheia")
        lote = self._excluir(session_client, workspace, projeto, [alheia])

        resposta = cliente_do_membro.post(
            RESTAURAR.format(slug=workspace.slug, pid=projeto.id), {"batch": lote}, format="json"
        )

        assert resposta.status_code == status.HTTP_403_FORBIDDEN
        alheia.refresh_from_db()
        assert alheia.deleted_at is not None

    def test_refuses_an_unknown_batch(self, session_client, workspace, projeto):
        resposta = session_client.post(
            RESTAURAR.format(slug=workspace.slug, pid=projeto.id),
            {"batch": "2020-01-01T00:00:00.000001+00:00"},
            format="json",
        )

        assert resposta.status_code == status.HTTP_400_BAD_REQUEST
        assert resposta.data["error"] == "NOTHING_TO_RESTORE"
