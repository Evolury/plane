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
            name="A fazer", group=StateGroup.UNSTARTED.value, project=projeto, workspace=workspace,
            color="#000", default=True,
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
        "recem": WorkStage.objects.create(
            workspace=workspace, owner=create_user, name="Recém-atribuídas", color="#000",
            group=StateGroup.UNSTARTED.value, sort_order=5000, is_default=True,
        ),
        "hoje": WorkStage.objects.create(
            workspace=workspace, owner=create_user, name="Hoje", color="#000",
            group=StateGroup.STARTED.value, sort_order=15000,
        ),
        "concluidas": WorkStage.objects.create(
            workspace=workspace, owner=create_user, name="Concluídas", color="#000",
            group=StateGroup.COMPLETED.value, sort_order=25000,
        ),
        "canceladas": WorkStage.objects.create(
            workspace=workspace, owner=create_user, name="Canceladas", color="#000",
            group=StateGroup.CANCELLED.value, sort_order=35000,
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

    @pytest.mark.django_db
    def test_uses_the_stage_marked_as_completion(self, tarefa, estados, etapas, workspace, create_user):
        """A etapa marcada ganha da primeira do grupo."""
        entregues = WorkStage.objects.create(
            workspace=workspace, owner=create_user, name="Entregues", color="#000",
            group=StateGroup.COMPLETED.value, sort_order=45000, is_completion=True,
        )

        assert sync_personal_stages_on_completion(tarefa.id, estados["aberto"].id, estados["concluido"].id) == 1
        assert WorkStageIssue.objects.get(owner=create_user, issue=tarefa).stage_id == entregues.id

    @pytest.mark.django_db
    def test_reopening_returns_to_the_default_stage(self, tarefa, estados, etapas, workspace, create_user):
        """Desconcluir devolve a tarefa à etapa padrão, como uma recém-atribuída."""
        WorkStageIssue.objects.create(
            workspace=workspace, owner=create_user, issue=tarefa, stage=etapas["concluidas"]
        )

        movidas = sync_personal_stages_on_completion(tarefa.id, estados["concluido"].id, estados["aberto"].id)

        assert movidas == 1
        assert WorkStageIssue.objects.get(owner=create_user, issue=tarefa).stage_id == etapas["recem"].id

    @pytest.mark.django_db
    def test_cancelling_moves_to_the_cancelled_stage(self, tarefa, estados, etapas, workspace, create_user):
        """Cancelar tem o mesmo tratamento de concluir, com outro destino."""
        cancelado = State.objects.create(
            name="Cancelado", group=StateGroup.CANCELLED.value,
            project=tarefa.project, workspace=tarefa.workspace, color="#000",
        )
        WorkStageIssue.objects.create(
            workspace=workspace, owner=create_user, issue=tarefa, stage=etapas["hoje"]
        )

        assert sync_personal_stages_on_completion(tarefa.id, estados["aberto"].id, cancelado.id) == 1
        assert WorkStageIssue.objects.get(owner=create_user, issue=tarefa).stage_id == etapas["canceladas"].id

    @pytest.mark.django_db
    def test_moving_between_open_groups_does_nothing(self, tarefa, estados, etapas, workspace, create_user):
        """Andar entre estados abertos é fluxo do projeto, não da pessoa.

        Quem organizou a tarefa em "Hoje" não a perde porque o time moveu o
        estado de "A fazer" para "Em andamento".
        """
        em_andamento = State.objects.create(
            name="Em andamento", group=StateGroup.STARTED.value,
            project=tarefa.project, workspace=tarefa.workspace, color="#000",
        )
        WorkStageIssue.objects.create(
            workspace=workspace, owner=create_user, issue=tarefa, stage=etapas["hoje"]
        )

        assert sync_personal_stages_on_completion(tarefa.id, estados["aberto"].id, em_andamento.id) == 0
        assert WorkStageIssue.objects.get(owner=create_user, issue=tarefa).stage_id == etapas["hoje"].id

    @pytest.mark.django_db
    def test_reopening_by_the_state_field_follows_the_chosen_state(
        self, tarefa, estados, etapas, workspace, create_user
    ):
        """Reabrir escolhendo "Em andamento" leva à etapa daquele grupo.

        O botão de reabrir manda a tarefa para o estado PADRÃO, e ali "de volta
        ao começo" é a resposta certa. Quem escolhe o estado no campo está
        dizendo onde a tarefa está — a etapa pessoal segue a escolha.
        """
        em_andamento = State.objects.create(
            name="Em andamento", group=StateGroup.STARTED.value,
            project=tarefa.project, workspace=tarefa.workspace, color="#000",
        )
        WorkStageIssue.objects.create(
            workspace=workspace, owner=create_user, issue=tarefa, stage=etapas["concluidas"]
        )

        movidas = sync_personal_stages_on_completion(tarefa.id, estados["concluido"].id, em_andamento.id)

        assert movidas == 1
        assert WorkStageIssue.objects.get(owner=create_user, issue=tarefa).stage_id == etapas["hoje"].id

    @pytest.mark.django_db
    def test_reopening_falls_back_to_the_default_stage_without_a_stage_in_the_group(
        self, tarefa, estados, etapas, workspace, create_user
    ):
        """Sem etapa no grupo escolhido, a padrão é o recuo — nada some da tela."""
        etapas["hoje"].delete()
        em_andamento = State.objects.create(
            name="Em andamento", group=StateGroup.STARTED.value,
            project=tarefa.project, workspace=tarefa.workspace, color="#000",
        )
        WorkStageIssue.objects.create(
            workspace=workspace, owner=create_user, issue=tarefa, stage=etapas["concluidas"]
        )

        assert sync_personal_stages_on_completion(tarefa.id, estados["concluido"].id, em_andamento.id) == 1
        assert WorkStageIssue.objects.get(owner=create_user, issue=tarefa).stage_id == etapas["recem"].id
