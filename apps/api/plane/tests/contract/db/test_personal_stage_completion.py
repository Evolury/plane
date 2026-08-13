# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Reflexo da conclusão nas etapas pessoais (ADR 0009).

O ADR 0001 fixou que etapa pessoal e estado real não se afetam. Concluir é a
exceção, e de mão única: entrar no grupo concluído reposiciona a associação
pessoal de cada responsável; o caminho contrário continua isolado.
"""

import pytest

from plane.db.models import (
    Issue,
    IssueAssignee,
    Project,
    ProjectMember,
    State,
    StateGroup,
    WorkStage,
    WorkStageIssue,
)
from plane.utils.personal_stage import sync_personal_stages_on_completion


@pytest.fixture
def projeto(db, workspace, create_user):
    projeto = Project.objects.create(
        name="Projeto", identifier="PRJ", workspace=workspace, created_by=create_user
    )
    ProjectMember.objects.create(project=projeto, member=create_user, role=20, is_active=True)
    return projeto


@pytest.fixture
def estados(db, projeto, workspace):
    State.objects.filter(project=projeto).delete()
    return {
        "aberto": State.objects.create(
            name="A fazer", group=StateGroup.UNSTARTED.value, project=projeto, workspace=workspace, color="#000"
        ),
        "concluido": State.objects.create(
            name="Concluído", group=StateGroup.COMPLETED.value, project=projeto, workspace=workspace, color="#000"
        ),
    }


@pytest.fixture
def tarefa(db, projeto, workspace, create_user, estados):
    tarefa = Issue.objects.create(
        name="Tarefa", project=projeto, workspace=workspace, state=estados["aberto"], created_by=create_user
    )
    IssueAssignee.objects.create(issue=tarefa, assignee=create_user, project=projeto, workspace=workspace)
    return tarefa


@pytest.fixture
def etapas(db, workspace, create_user):
    return {
        "hoje": WorkStage.objects.create(
            workspace=workspace, owner=create_user, name="Hoje", color="#000",
            group=StateGroup.STARTED.value, sort_order=15000, is_default=True,
        ),
        "concluidas": WorkStage.objects.create(
            workspace=workspace, owner=create_user, name="Concluídas", color="#000",
            group=StateGroup.COMPLETED.value, sort_order=25000,
        ),
    }


@pytest.mark.contract
class TestPersonalStageOnCompletion:
    @pytest.mark.django_db
    def test_creates_association_in_the_completed_stage(self, tarefa, estados, etapas, create_user):
        """Sem associação nenhuma, concluir cria uma na etapa de concluídas."""
        assert sync_personal_stages_on_completion(tarefa.id, estados["aberto"].id, estados["concluido"].id) == 1

        associacao = WorkStageIssue.objects.get(owner=create_user, issue=tarefa)
        assert associacao.stage_id == etapas["concluidas"].id

    @pytest.mark.django_db
    def test_accepts_ids_as_text(self, tarefa, estados, etapas, create_user):
        """Os ids chegam como TEXTO da tarefa em segundo plano (payload JSON).

        Com UUID de um lado e texto do outro, a comparação de grupo dava
        sempre "nada mudou" e nada era reposicionado — foi assim que a
        funcionalidade passou nos testes e falhou na tela.
        """
        movidas = sync_personal_stages_on_completion(
            str(tarefa.id), str(estados["aberto"].id), str(estados["concluido"].id)
        )

        assert movidas == 1
        assert WorkStageIssue.objects.get(owner=create_user, issue=tarefa).stage_id == etapas["concluidas"].id

    @pytest.mark.django_db
    def test_moves_existing_association(self, tarefa, estados, etapas, workspace, create_user):
        """Quem estava em "Hoje" vai para concluídas — o motivo da exceção."""
        WorkStageIssue.objects.create(
            workspace=workspace, owner=create_user, issue=tarefa, stage=etapas["hoje"]
        )

        assert sync_personal_stages_on_completion(tarefa.id, estados["aberto"].id, estados["concluido"].id) == 1
        assert WorkStageIssue.objects.get(owner=create_user, issue=tarefa).stage_id == etapas["concluidas"].id

    @pytest.mark.django_db
    def test_preserves_a_stage_already_in_the_completed_group(
        self, tarefa, estados, etapas, workspace, create_user
    ):
        """Etapa de concluídas escolhida pela pessoa não é reposicionada."""
        outra = WorkStage.objects.create(
            workspace=workspace, owner=create_user, name="Entregues", color="#000",
            group=StateGroup.COMPLETED.value, sort_order=35000,
        )
        WorkStageIssue.objects.create(workspace=workspace, owner=create_user, issue=tarefa, stage=outra)

        assert sync_personal_stages_on_completion(tarefa.id, estados["aberto"].id, estados["concluido"].id) == 0
        assert WorkStageIssue.objects.get(owner=create_user, issue=tarefa).stage_id == outra.id

    @pytest.mark.django_db
    def test_ignores_updates_that_do_not_enter_the_completed_group(self, tarefa, estados, etapas, create_user):
        """Mudança entre estados abertos não mexe em etapa pessoal."""
        outro_aberto = State.objects.create(
            name="Em andamento", group=StateGroup.STARTED.value,
            project=tarefa.project, workspace=tarefa.workspace, color="#000",
        )

        assert sync_personal_stages_on_completion(tarefa.id, estados["aberto"].id, outro_aberto.id) == 0
        assert not WorkStageIssue.objects.filter(owner=create_user, issue=tarefa).exists()

    @pytest.mark.django_db
    def test_ignores_moves_within_the_completed_group(self, tarefa, estados, etapas, workspace, create_user):
        """Já concluída, trocar de estado concluído não reposiciona ninguém.

        Protege a escolha de quem tinha arrastado a tarefa depois de concluída.
        """
        entregue = State.objects.create(
            name="Entregue", group=StateGroup.COMPLETED.value,
            project=tarefa.project, workspace=tarefa.workspace, color="#000",
        )
        WorkStageIssue.objects.create(
            workspace=workspace, owner=create_user, issue=tarefa, stage=etapas["hoje"]
        )

        assert sync_personal_stages_on_completion(tarefa.id, estados["concluido"].id, entregue.id) == 0
        assert WorkStageIssue.objects.get(owner=create_user, issue=tarefa).stage_id == etapas["hoje"].id

    @pytest.mark.django_db
    def test_skips_users_without_a_completed_stage(self, tarefa, estados, workspace, create_user):
        """Sem etapa no grupo concluído não há destino — e nada é inventado.

        Quem nunca abriu "Minhas tarefas" não tem etapas semeadas; a listagem
        resolve o implícito quando ele abrir.
        """
        WorkStage.objects.create(
            workspace=workspace, owner=create_user, name="Hoje", color="#000",
            group=StateGroup.STARTED.value, sort_order=15000, is_default=True,
        )

        assert sync_personal_stages_on_completion(tarefa.id, estados["aberto"].id, estados["concluido"].id) == 0
        assert not WorkStageIssue.objects.filter(owner=create_user, issue=tarefa).exists()
