# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Evolury: testes de contrato de "Minhas tarefas" — etapas pessoais, listagem
# anotada e movimento entre etapas.
# Regras em docs/evolury/funcionalidades/minhas-tarefas/ (ADRs 0001 e 0002).

from unittest import mock

from datetime import timedelta

import pytest

from plane.utils.etapas_por_vencimento import dia_local
from rest_framework import status
from rest_framework.test import APIClient

from plane.app.views.workspace.my_tasks import ensure_default_work_stages
from plane.db.models import (
    Issue,
    IssueActivity,
    IssueAssignee,
    Project,
    ProjectMember,
    State,
    User,
    WorkspaceMember,
    WorkStage,
    WorkStageIssue,
)

STAGES_URL = "/api/workspaces/{slug}/my-tasks/stages/"
STAGE_URL = "/api/workspaces/{slug}/my-tasks/stages/{pk}/"
MARK_DEFAULT_URL = "/api/workspaces/{slug}/my-tasks/stages/{pk}/mark-default/"
MARK_COMPLETION_URL = "/api/workspaces/{slug}/my-tasks/stages/{pk}/mark-completion/"
MARK_BUCKET_URL = "/api/workspaces/{slug}/my-tasks/stages/{pk}/mark-bucket/"
ISSUES_URL = "/api/workspaces/{slug}/my-tasks/issues/"
MOVE_URL = "/api/workspaces/{slug}/my-tasks/issues/{issue_id}/move/"
STAGE_URL_ISSUE = "/api/workspaces/{slug}/my-tasks/issues/{issue_id}/stage/"


@pytest.fixture
def project(db, workspace, create_user):
    """Projeto com o usuário como admin e um estado padrão."""
    project = Project.objects.create(
        name="Test Project",
        identifier="TP",
        workspace=workspace,
        created_by=create_user,
    )
    ProjectMember.objects.create(project=project, member=create_user, role=20, is_active=True)
    State.objects.create(
        name="Backlog",
        color="#000000",
        group="backlog",
        default=True,
        project=project,
        workspace=workspace,
        created_by=create_user,
    )
    return project


@pytest.fixture
def second_user(db, workspace):
    """Outro membro do workspace, para testes de isolamento."""
    user = User.objects.create(
        email="second@evolury.com.br",
        username="second-user",
        first_name="Second",
        last_name="User",
    )
    user.set_password("test-password")
    user.save()
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=15)
    return user


@pytest.fixture
def second_client(second_user):
    client = APIClient()
    client.force_authenticate(user=second_user)
    return client


@pytest.fixture
def assigned_issue(db, project, workspace, create_user):
    """Work item atribuído ao usuário principal."""
    issue = Issue.objects.create(
        name="Assigned Issue", project=project, workspace=workspace, created_by=create_user
    )
    IssueAssignee.objects.create(issue=issue, assignee=create_user, project=project, workspace=workspace)
    return issue


def seed_stages(workspace, user):
    ensure_default_work_stages(workspace, user)
    return {stage.name: stage for stage in WorkStage.objects.filter(workspace=workspace, owner=user)}


@pytest.mark.contract
class TestWorkStagesSeed:
    def test_first_list_seeds_default_stages(self, session_client, workspace):
        response = session_client.get(STAGES_URL.format(slug=workspace.slug))
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 8
        defaults = [stage for stage in response.data if stage["is_default"]]
        assert len(defaults) == 1
        assert defaults[0]["name"] == "Recentes"
        # Uma etapa de conclusão marcada, para o destino de concluir não
        # depender de ordenação (ADR 0009)
        completions = [stage for stage in response.data if stage["is_completion"]]
        assert len(completions) == 1
        assert completions[0]["name"] == "Concluídas"
        # Ordem do seed preservada pelo sort_order
        assert [stage["name"] for stage in response.data] == [
            "Recentes",
            "Em Andamento",
            "Para Hoje (fila)",
            "Pendências",
            "Para amanhã",
            "Para Depois",
            "Concluídas",
            "Cancelado",
        ]

    def test_seed_ja_nasce_com_a_varredura_configurada(self, session_client, workspace):
        """Conta nova organiza sozinha desde o primeiro dia (ADR 0014).

        Sem isto, o seed poderia perder as marcações numa edição futura e a
        varredura não moveria ninguém — sem erro em lugar nenhum, porque balde
        sem etapa marcada é caso legítimo.
        """
        response = session_client.get(STAGES_URL.format(slug=workspace.slug))
        por_marcacao = {
            marcacao: [s["name"] for s in response.data if s[marcacao]]
            for marcacao in ("is_due_today", "is_due_tomorrow", "is_due_later", "is_overdue")
        }

        assert por_marcacao == {
            "is_due_today": ["Para Hoje (fila)"],
            "is_due_tomorrow": ["Para amanhã"],
            "is_due_later": ["Para Depois"],
            "is_overdue": ["Pendências"],
        }

    def test_recentes_e_pendencias_nascem_fora_da_varredura(self, session_client, workspace):
        """Recentes é onde se toma conhecimento do que chegou — esvaziá-la toda
        madrugada a impediria de cumprir esse papel. Pendências costuma receber,
        à mão, coisa que a pessoa quer manter à vista mesmo com data futura."""
        response = session_client.get(STAGES_URL.format(slug=workspace.slug))

        travadas = sorted(s["name"] for s in response.data if s["automation_disabled"])
        assert travadas == ["Pendências", "Recentes"]

    def test_seed_is_idempotent(self, session_client, workspace):
        session_client.get(STAGES_URL.format(slug=workspace.slug))
        response = session_client.get(STAGES_URL.format(slug=workspace.slug))
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 8

    def test_seed_race_is_absorbed(self, db, workspace, create_user):
        """Se dois requests passam pelo exists() ao mesmo tempo, a segunda
        inserção viola a constraint de nome único e é absorvida em silêncio."""
        ensure_default_work_stages(workspace, create_user)
        with mock.patch(
            "plane.app.views.workspace.my_tasks.WorkStage.objects.filter"
        ) as mocked_filter:
            mocked_filter.return_value.exists.return_value = False
            ensure_default_work_stages(workspace, create_user)  # não levanta
        assert WorkStage.objects.filter(workspace=workspace, owner=create_user).count() == 8

    def test_seed_is_per_user(self, session_client, second_client, workspace, second_user, create_user):
        session_client.get(STAGES_URL.format(slug=workspace.slug))
        response = second_client.get(STAGES_URL.format(slug=workspace.slug))
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 8
        assert WorkStage.objects.filter(workspace=workspace).count() == 16
        first_ids = set(WorkStage.objects.filter(owner=create_user).values_list("id", flat=True))
        second_ids = {stage["id"] for stage in response.data}
        assert first_ids.isdisjoint(second_ids)


@pytest.mark.contract
class TestWorkStagesCrud:
    def test_create_stage(self, session_client, workspace):
        response = session_client.post(
            STAGES_URL.format(slug=workspace.slug),
            {"name": "Delegadas", "color": "#8B5CF6", "group": "started"},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["name"] == "Delegadas"
        assert response.data["is_default"] is False

    def test_create_duplicate_name_is_rejected(self, session_client, workspace, create_user):
        seed_stages(workspace, create_user)
        response = session_client.post(
            STAGES_URL.format(slug=workspace.slug),
            {"name": "Para Hoje (fila)", "color": "#000000", "group": "started"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_guest_cannot_access(self, db, workspace):
        guest = User.objects.create(email="guest@evolury.com.br", username="guest-user")
        WorkspaceMember.objects.create(workspace=workspace, member=guest, role=5)
        client = APIClient()
        client.force_authenticate(user=guest)
        response = client.get(STAGES_URL.format(slug=workspace.slug))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_unauthenticated_cannot_access(self, db, api_client, workspace):
        response = api_client.get(STAGES_URL.format(slug=workspace.slug))
        assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

    def test_patch_stage(self, session_client, workspace, create_user):
        stages = seed_stages(workspace, create_user)
        response = session_client.patch(
            STAGE_URL.format(slug=workspace.slug, pk=stages["Para Hoje (fila)"].id),
            {"name": "Agora", "color": "#FF0000"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "Agora"

    def test_patch_other_users_stage_is_not_found(self, second_client, workspace, create_user):
        stages = seed_stages(workspace, create_user)
        response = second_client.patch(
            STAGE_URL.format(slug=workspace.slug, pk=stages["Para Hoje (fila)"].id),
            {"name": "Invasão"},
            format="json",
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_destroy_default_is_rejected(self, session_client, workspace, create_user):
        stages = seed_stages(workspace, create_user)
        response = session_client.delete(
            STAGE_URL.format(slug=workspace.slug, pk=stages["Recentes"].id)
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_destroy_migrates_associations_to_default(
        self, session_client, workspace, create_user, assigned_issue
    ):
        stages = seed_stages(workspace, create_user)
        WorkStageIssue.objects.create(
            workspace=workspace, owner=create_user, stage=stages["Para Hoje (fila)"], issue=assigned_issue
        )
        response = session_client.delete(STAGE_URL.format(slug=workspace.slug, pk=stages["Para Hoje (fila)"].id))
        assert response.status_code == status.HTTP_204_NO_CONTENT
        association = WorkStageIssue.objects.get(owner=create_user, issue=assigned_issue)
        assert association.stage_id == stages["Recentes"].id

    def test_mark_completion_swaps(self, session_client, workspace, create_user):
        """Evolury: destino da conclusão entre as etapas do usuário (ADR 0009)."""
        stages = seed_stages(workspace, create_user)
        outra = WorkStage.objects.create(
            workspace=workspace, owner=create_user, name="Entregues", color="#000000",
            group="completed", sort_order=75000,
        )
        response = session_client.post(MARK_COMPLETION_URL.format(slug=workspace.slug, pk=outra.id))
        assert response.status_code == status.HTTP_204_NO_CONTENT
        outra.refresh_from_db()
        stages["Concluídas"].refresh_from_db()
        assert outra.is_completion is True
        assert stages["Concluídas"].is_completion is False

    def test_mark_completion_rejects_a_stage_outside_the_completed_group(
        self, session_client, workspace, create_user
    ):
        """Etapa de outro grupo não pode ser destino de conclusão."""
        stages = seed_stages(workspace, create_user)
        response = session_client.post(
            MARK_COMPLETION_URL.format(slug=workspace.slug, pk=stages["Para Hoje (fila)"].id)
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        stages["Para Hoje (fila)"].refresh_from_db()
        assert stages["Para Hoje (fila)"].is_completion is False

    def test_mark_default_swaps(self, session_client, workspace, create_user):
        stages = seed_stages(workspace, create_user)
        response = session_client.post(MARK_DEFAULT_URL.format(slug=workspace.slug, pk=stages["Para Hoje (fila)"].id))
        assert response.status_code == status.HTTP_204_NO_CONTENT
        defaults = WorkStage.objects.filter(workspace=workspace, owner=create_user, is_default=True)
        assert defaults.count() == 1
        assert defaults.first().id == stages["Para Hoje (fila)"].id


@pytest.mark.contract
class TestMyTasksIssues:
    def test_lists_only_assigned_issues(
        self, session_client, workspace, project, create_user, second_user, assigned_issue
    ):
        # Ruído que não deve aparecer: sem atribuição, atribuído a outro,
        # arquivado e rascunho.
        Issue.objects.create(name="Unassigned", project=project, workspace=workspace, created_by=create_user)
        other = Issue.objects.create(
            name="Someone else's", project=project, workspace=workspace, created_by=create_user
        )
        IssueAssignee.objects.create(issue=other, assignee=second_user, project=project, workspace=workspace)
        archived = Issue.objects.create(
            name="Archived",
            project=project,
            workspace=workspace,
            created_by=create_user,
            archived_at="2026-01-01",
        )
        IssueAssignee.objects.create(issue=archived, assignee=create_user, project=project, workspace=workspace)
        draft = Issue.objects.create(
            name="Draft", project=project, workspace=workspace, created_by=create_user, is_draft=True
        )
        IssueAssignee.objects.create(issue=draft, assignee=create_user, project=project, workspace=workspace)

        response = session_client.get(ISSUES_URL.format(slug=workspace.slug))
        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"]
        assert [item["id"] for item in results] == [assigned_issue.id]

    def test_unplaced_issue_is_annotated_with_default_stage(
        self, session_client, workspace, create_user, assigned_issue
    ):
        response = session_client.get(ISSUES_URL.format(slug=workspace.slug))
        assert response.status_code == status.HTTP_200_OK
        stages = {stage.name: stage for stage in WorkStage.objects.filter(workspace=workspace, owner=create_user)}
        result = response.data["results"][0]
        assert result["my_task_stage_id"] == stages["Recentes"].id

    def test_completed_issue_without_association_falls_into_the_completed_stage(
        self, session_client, workspace, project, create_user, assigned_issue
    ):
        """Concluída e sem associação, a tarefa pertence à etapa de concluídas.

        Vale para quem nunca moveu nada e para o que foi concluído antes de
        existirem etapas — por isso a regra é resolvida na listagem, e não só
        gravada na transição (ADR 0009).
        """
        stages = seed_stages(workspace, create_user)
        assigned_issue.state = State.objects.create(
            name="Concluído", color="#000000", group="completed", project=project, workspace=workspace
        )
        assigned_issue.save(update_fields=["state"])

        response = session_client.get(ISSUES_URL.format(slug=workspace.slug))
        result = response.data["results"][0]
        assert result["my_task_stage_id"] == stages["Concluídas"].id

    def test_moved_issue_is_annotated_with_its_stage(
        self, session_client, workspace, create_user, assigned_issue
    ):
        stages = seed_stages(workspace, create_user)
        WorkStageIssue.objects.create(
            workspace=workspace, owner=create_user, stage=stages["Para Hoje (fila)"], issue=assigned_issue
        )
        response = session_client.get(ISSUES_URL.format(slug=workspace.slug))
        result = response.data["results"][0]
        assert result["my_task_stage_id"] == stages["Para Hoje (fila)"].id

    def test_payload_sort_order_is_the_personal_one(
        self, session_client, workspace, create_user, assigned_issue
    ):
        """O sort_order serializado é o da associação (my_task_sort_order),
        não o do item — toda a ordenação manual da página é pessoal. O
        sort_order real do work item permanece intocado no banco."""
        stages = seed_stages(workspace, create_user)
        issue_sort_order_before = assigned_issue.sort_order
        WorkStageIssue.objects.create(
            workspace=workspace,
            owner=create_user,
            stage=stages["Para Hoje (fila)"],
            issue=assigned_issue,
            sort_order=111.0,
        )
        response = session_client.get(ISSUES_URL.format(slug=workspace.slug))
        result = response.data["results"][0]
        assert result["sort_order"] == 111.0
        assigned_issue.refresh_from_db()
        assert assigned_issue.sort_order == issue_sort_order_before

    def test_annotation_is_per_user(
        self, session_client, second_client, workspace, project, create_user, second_user, assigned_issue
    ):
        """O mesmo item aparece em etapas diferentes para usuários diferentes."""
        IssueAssignee.objects.create(
            issue=assigned_issue, assignee=second_user, project=project, workspace=workspace
        )
        ProjectMember.objects.create(project=project, member=second_user, role=15, is_active=True)
        first_stages = seed_stages(workspace, create_user)
        second_stages = seed_stages(workspace, second_user)
        WorkStageIssue.objects.create(
            workspace=workspace, owner=create_user, stage=first_stages["Para Hoje (fila)"], issue=assigned_issue
        )

        first = session_client.get(ISSUES_URL.format(slug=workspace.slug)).data["results"][0]
        second = second_client.get(ISSUES_URL.format(slug=workspace.slug)).data["results"][0]
        assert first["my_task_stage_id"] == first_stages["Para Hoje (fila)"].id
        assert second["my_task_stage_id"] == second_stages["Recentes"].id

    def test_grouped_by_stage(self, session_client, workspace, create_user, assigned_issue):
        stages = seed_stages(workspace, create_user)
        response = session_client.get(
            ISSUES_URL.format(slug=workspace.slug), {"group_by": "my_task_stage_id"}
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["grouped_by"] == "my_task_stage_id"
        results = response.data["results"]
        # Uma chave por etapa; o item não movido cai no grupo da padrão.
        assert set(results.keys()) == {str(stage.id) for stage in stages.values()}
        default_group = results[str(stages["Recentes"].id)]
        assert [item["id"] for item in default_group["results"]] == [assigned_issue.id]

    def test_grouped_response_always_carries_all_stage_keys(
        self, session_client, workspace, create_user
    ):
        """Mesmo sem nenhum item, a resposta agrupada traz todas as etapas
        com listas vazias — sem isso o front fica eternamente em
        "carregando" (groupedIssueIds nunca é populado)."""
        stages = seed_stages(workspace, create_user)
        response = session_client.get(
            ISSUES_URL.format(slug=workspace.slug), {"group_by": "my_task_stage_id"}
        )
        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"]
        assert set(results.keys()) == {str(stage.id) for stage in stages.values()}
        assert all(group["results"] == [] for group in results.values())

    def test_removed_project_member_issues_disappear(
        self, session_client, workspace, project, create_user, assigned_issue
    ):
        ProjectMember.objects.filter(project=project, member=create_user).update(is_active=False)
        response = session_client.get(ISSUES_URL.format(slug=workspace.slug))
        assert response.data["results"] == []


@pytest.mark.contract
class TestMyTasksIssueStage:
    def test_unplaced_issue_returns_default_stage(self, session_client, workspace, create_user, assigned_issue):
        response = session_client.get(STAGE_URL_ISSUE.format(slug=workspace.slug, issue_id=assigned_issue.id))
        assert response.status_code == status.HTTP_200_OK
        default = WorkStage.objects.get(workspace=workspace, owner=create_user, is_default=True)
        assert response.data["stage_id"] == str(default.id)

    def test_moved_issue_returns_its_stage(self, session_client, workspace, create_user, assigned_issue):
        stages = seed_stages(workspace, create_user)
        WorkStageIssue.objects.create(
            workspace=workspace, owner=create_user, stage=stages["Para Hoje (fila)"], issue=assigned_issue
        )
        response = session_client.get(STAGE_URL_ISSUE.format(slug=workspace.slug, issue_id=assigned_issue.id))
        assert response.data["stage_id"] == str(stages["Para Hoje (fila)"].id)

    def test_not_assigned_is_not_found(self, session_client, workspace, project, create_user):
        unassigned = Issue.objects.create(
            name="Unassigned", project=project, workspace=workspace, created_by=create_user
        )
        response = session_client.get(STAGE_URL_ISSUE.format(slug=workspace.slug, issue_id=unassigned.id))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_first_access_seeds_stages(self, session_client, workspace, create_user, assigned_issue):
        """O endpoint garante o seed: usuário que nunca abriu a página já
        recebe a etapa padrão pelo popover."""
        assert WorkStage.objects.filter(owner=create_user).count() == 0
        response = session_client.get(STAGE_URL_ISSUE.format(slug=workspace.slug, issue_id=assigned_issue.id))
        assert response.status_code == status.HTTP_200_OK
        assert WorkStage.objects.filter(owner=create_user).count() == 8
        assert response.data["stage_id"] is not None


@pytest.mark.contract
class TestMyTasksMove:
    def test_move_creates_association(self, session_client, workspace, create_user, assigned_issue):
        stages = seed_stages(workspace, create_user)
        response = session_client.post(
            MOVE_URL.format(slug=workspace.slug, issue_id=assigned_issue.id),
            {"stage_id": str(stages["Para Hoje (fila)"].id)},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        association = WorkStageIssue.objects.get(owner=create_user, issue=assigned_issue)
        assert association.stage_id == stages["Para Hoje (fila)"].id

    def test_move_again_updates_same_association(
        self, session_client, workspace, create_user, assigned_issue
    ):
        stages = seed_stages(workspace, create_user)
        url = MOVE_URL.format(slug=workspace.slug, issue_id=assigned_issue.id)
        session_client.post(url, {"stage_id": str(stages["Para Hoje (fila)"].id)}, format="json")
        session_client.post(url, {"stage_id": str(stages["Para Depois"].id)}, format="json")
        associations = WorkStageIssue.objects.filter(owner=create_user, issue=assigned_issue)
        assert associations.count() == 1
        assert associations.first().stage_id == stages["Para Depois"].id

    def test_move_persists_sort_order(self, session_client, workspace, create_user, assigned_issue):
        stages = seed_stages(workspace, create_user)
        response = session_client.post(
            MOVE_URL.format(slug=workspace.slug, issue_id=assigned_issue.id),
            {"stage_id": str(stages["Para Hoje (fila)"].id), "sort_order": 12345.0},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert WorkStageIssue.objects.get(owner=create_user, issue=assigned_issue).sort_order == 12345.0

    def test_move_requires_stage_id(self, session_client, workspace, assigned_issue):
        response = session_client.post(
            MOVE_URL.format(slug=workspace.slug, issue_id=assigned_issue.id), {}, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_move_unassigned_issue_is_not_found(self, session_client, workspace, project, create_user):
        seed = seed_stages(workspace, create_user)
        unassigned = Issue.objects.create(
            name="Unassigned", project=project, workspace=workspace, created_by=create_user
        )
        response = session_client.post(
            MOVE_URL.format(slug=workspace.slug, issue_id=unassigned.id),
            {"stage_id": str(seed["Para Hoje (fila)"].id)},
            format="json",
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_move_to_other_users_stage_is_not_found(
        self, session_client, workspace, create_user, second_user, assigned_issue
    ):
        other_stages = seed_stages(workspace, second_user)
        response = session_client.post(
            MOVE_URL.format(slug=workspace.slug, issue_id=assigned_issue.id),
            {"stage_id": str(other_stages["Para Hoje (fila)"].id)},
            format="json",
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_move_creates_no_issue_activity(self, session_client, workspace, create_user, assigned_issue):
        """Movimento pessoal é invisível no histórico do item (ADR 0001).
        Sem atividade também não há gatilho de webhook nem notificação."""
        stages = seed_stages(workspace, create_user)
        activity_count_before = IssueActivity.objects.filter(issue=assigned_issue).count()
        response = session_client.post(
            MOVE_URL.format(slug=workspace.slug, issue_id=assigned_issue.id),
            {"stage_id": str(stages["Concluídas"].id)},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert IssueActivity.objects.filter(issue=assigned_issue).count() == activity_count_before

    def test_move_to_a_completed_stage_does_not_change_the_issue_state(
        self, session_client, workspace, create_user, assigned_issue
    ):
        """A exceção do ADR 0009 é de MÃO ÚNICA.

        Concluir reposiciona a etapa pessoal; arrastar para a etapa de
        concluídas continua sem concluir nada no projeto.
        """
        stages = seed_stages(workspace, create_user)
        estado_antes = assigned_issue.state_id
        response = session_client.post(
            MOVE_URL.format(slug=workspace.slug, issue_id=assigned_issue.id),
            {"stage_id": str(stages["Concluídas"].id)},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assigned_issue.refresh_from_db()
        assert assigned_issue.state_id == estado_antes

    def test_hard_delete_cascades_association(self, session_client, workspace, create_user, assigned_issue):
        """Hard delete do work item remove a associação em cascata — sem
        linha órfã (linha 8 da matriz de compatibilidade)."""
        stages = seed_stages(workspace, create_user)
        session_client.post(
            MOVE_URL.format(slug=workspace.slug, issue_id=assigned_issue.id),
            {"stage_id": str(stages["Para Hoje (fila)"].id)},
            format="json",
        )
        assert WorkStageIssue.objects.filter(issue_id=assigned_issue.id).count() == 1
        assigned_issue.delete(soft=False)
        assert WorkStageIssue.all_objects.filter(issue_id=assigned_issue.id).count() == 0

    def test_reassignment_restores_previous_stage(
        self, session_client, workspace, project, create_user, assigned_issue
    ):
        """Desatribuído some da listagem; reatribuído volta à etapa em que
        estava — a associação sobrevive de propósito (linha 9 da matriz)."""
        stages = seed_stages(workspace, create_user)
        session_client.post(
            MOVE_URL.format(slug=workspace.slug, issue_id=assigned_issue.id),
            {"stage_id": str(stages["Para Hoje (fila)"].id)},
            format="json",
        )
        # desatribui
        IssueAssignee.objects.filter(issue=assigned_issue, assignee=create_user).delete()
        response = session_client.get(ISSUES_URL.format(slug=workspace.slug))
        assert response.data["results"] == []
        # reatribui
        IssueAssignee.objects.create(
            issue=assigned_issue, assignee=create_user, project=project, workspace=workspace
        )
        response = session_client.get(ISSUES_URL.format(slug=workspace.slug))
        result = response.data["results"][0]
        assert result["my_task_stage_id"] == stages["Para Hoje (fila)"].id

    def test_move_does_not_touch_issue_state(self, session_client, workspace, create_user, assigned_issue):
        """Overlay pessoal: mover para uma etapa do grupo "concluído" não muda
        o estado real do work item (ADR 0001)."""
        stages = seed_stages(workspace, create_user)
        state_before = assigned_issue.state_id
        session_client.post(
            MOVE_URL.format(slug=workspace.slug, issue_id=assigned_issue.id),
            {"stage_id": str(stages["Concluídas"].id)},
            format="json",
        )
        assigned_issue.refresh_from_db()
        assert assigned_issue.state_id == state_before


@pytest.mark.contract
class TestMarcarBaldeDeVencimento:
    """O endpoint que marca qual balde a etapa recebe (ADR 0014).

    Existe por si porque a constraint parcial exige soltar a antiga antes de
    marcar a nova — um PATCH comum estouraria com 500 em vez de trocar. E
    difere do `mark-default` num ponto: a etapa padrão é obrigatória e nunca se
    desliga; estas quatro são OPCIONAIS.
    """

    def test_marca_a_etapa_como_destino(self, session_client, workspace, create_user):
        stages = seed_stages(workspace, create_user)
        alvo = stages["Em Andamento"]

        response = session_client.post(
            MARK_BUCKET_URL.format(slug=workspace.slug, pk=alvo.id), {"balde": "hoje"}, format="json"
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        alvo.refresh_from_db()
        assert alvo.is_due_today is True

    def test_marcar_solta_a_anterior(self, session_client, workspace, create_user):
        """Sem soltar antes, a constraint estoura — e o 500 chegaria à tela."""
        stages = seed_stages(workspace, create_user)
        anterior = stages["Para Hoje (fila)"]

        response = session_client.post(
            MARK_BUCKET_URL.format(slug=workspace.slug, pk=stages["Em Andamento"].id),
            {"balde": "hoje"},
            format="json",
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        anterior.refresh_from_db()
        assert anterior.is_due_today is False

    def test_desligar_deixa_o_balde_SEM_destino(self, session_client, workspace, create_user):
        """A diferença para o mark-default: aqui a marcação é opcional.

        Balde sem destino é caso legítimo — a varredura simplesmente não move
        ninguém daquele grupo.
        """
        stages = seed_stages(workspace, create_user)
        alvo = stages["Para Hoje (fila)"]

        response = session_client.post(
            MARK_BUCKET_URL.format(slug=workspace.slug, pk=alvo.id),
            {"balde": "hoje", "ativo": False},
            format="json",
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        alvo.refresh_from_db()
        assert alvo.is_due_today is False
        assert not WorkStage.objects.filter(workspace=workspace, owner=create_user, is_due_today=True).exists()

    def test_uma_etapa_pode_receber_dois_baldes(self, session_client, workspace, create_user):
        stages = seed_stages(workspace, create_user)
        alvo = stages["Para amanhã"]

        session_client.post(
            MARK_BUCKET_URL.format(slug=workspace.slug, pk=alvo.id), {"balde": "depois"}, format="json"
        )

        alvo.refresh_from_db()
        assert alvo.is_due_tomorrow is True
        assert alvo.is_due_later is True

    def test_balde_desconhecido_e_recusado(self, session_client, workspace, create_user):
        """Recusa com a lista do que vale — recusar sem ensinar é falha barulhenta e inútil."""
        stages = seed_stages(workspace, create_user)

        response = session_client.post(
            MARK_BUCKET_URL.format(slug=workspace.slug, pk=stages["Em Andamento"].id),
            {"balde": "semana-que-vem"},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "hoje" in str(response.data)

    def test_etapa_de_outra_pessoa_nao_e_encontrada(self, session_client, workspace, create_user, django_user_model):
        outra = django_user_model.objects.create(email="outra-etapa@plane.so", username="outra_etapa")
        alheia = WorkStage.objects.create(
            workspace=workspace, owner=outra, name="Alheia", color="#000", group="backlog"
        )

        response = session_client.post(
            MARK_BUCKET_URL.format(slug=workspace.slug, pk=alheia.id), {"balde": "hoje"}, format="json"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_opt_out_muda_pelo_patch_comum(self, session_client, workspace, create_user):
        """`automation_disabled` não tem constraint, então não precisa de endpoint."""
        stages = seed_stages(workspace, create_user)
        alvo = stages["Em Andamento"]

        response = session_client.patch(
            STAGE_URL.format(slug=workspace.slug, pk=alvo.id), {"automation_disabled": True}, format="json"
        )

        assert response.status_code == status.HTTP_200_OK, response.data
        alvo.refresh_from_db()
        assert alvo.automation_disabled is True


@pytest.mark.contract
class TestArrastarReagenda:
    """Arrastar para hoje ou amanhã muda o vencimento (ADR 0014).

    É o que faz etapa e data concordarem: sem isto, a pessoa moveria a tarefa e
    a varredura a puxaria de volta na madrugada seguinte, porque a data
    continuaria dizendo outra coisa.

    Só essas duas etapas, e de propósito — "depois" é intervalo aberto e
    "vencidas" é passado; carimbar ali seria inventar informação.
    """

    def _mover(self, session_client, workspace, issue, stage):
        return session_client.post(
            MOVE_URL.format(slug=workspace.slug, issue_id=issue.id),
            {"stage_id": str(stage.id)},
            format="json",
        )

    def test_arrastar_para_hoje_marca_o_vencimento_de_hoje(
        self, session_client, workspace, create_user, assigned_issue
    ):
        stages = seed_stages(workspace, create_user)

        response = self._mover(session_client, workspace, assigned_issue, stages["Para Hoje (fila)"])

        assert response.status_code == status.HTTP_200_OK, response.data
        assigned_issue.refresh_from_db()
        # A data da PESSOA, e não a do servidor. Comparar com `timezone.now()`
        # passava o dia inteiro e quebrava entre a meia-noite de São Paulo e a
        # de Londres — três horas por dia em que a suíte acusaria um defeito que
        # não existe, e no resto do dia esconderia um que existisse.
        assert assigned_issue.target_date == dia_local(create_user.user_timezone)

    def test_arrastar_para_amanha_marca_o_vencimento_de_amanha(
        self, session_client, workspace, create_user, assigned_issue
    ):
        stages = seed_stages(workspace, create_user)

        self._mover(session_client, workspace, assigned_issue, stages["Para amanhã"])

        assigned_issue.refresh_from_db()
        assert assigned_issue.target_date == dia_local(create_user.user_timezone) + timedelta(days=1)

    @pytest.mark.parametrize("etapa", ["Para Depois", "Pendências", "Em Andamento"])
    def test_arrastar_para_as_outras_NAO_toca_na_data(
        self, session_client, workspace, create_user, assigned_issue, etapa
    ):
        """Sem isto, carimbar em toda etapa passaria nos dois testes acima."""
        stages = seed_stages(workspace, create_user)
        assigned_issue.target_date = dia_local(create_user.user_timezone) + timedelta(days=30)
        assigned_issue.save()

        self._mover(session_client, workspace, assigned_issue, stages[etapa])

        assigned_issue.refresh_from_db()
        assert assigned_issue.target_date == dia_local(create_user.user_timezone) + timedelta(days=30)

    def test_arrastar_para_hoje_uma_tarefa_que_ja_vence_hoje_nao_gera_ruido(
        self, session_client, workspace, create_user, assigned_issue
    ):
        """Regravar a mesma data encheria o histórico sem dizer nada."""
        stages = seed_stages(workspace, create_user)
        assigned_issue.target_date = dia_local(create_user.user_timezone)
        assigned_issue.save()
        antes = assigned_issue.updated_at

        self._mover(session_client, workspace, assigned_issue, stages["Para Hoje (fila)"])

        assigned_issue.refresh_from_db()
        assert assigned_issue.updated_at == antes


@pytest.mark.contract
class TestGrupoDeEncerramentoPrecisaDeDestino:
    """Concluir e cancelar procuram o destino DENTRO do grupo correspondente.

    Esvaziando o grupo, a tarefa concluída cai fora dele — na prática, vai
    parar junto das que acabaram de chegar. O prejuízo não aparece na hora da
    exclusão, e sim na próxima vez que alguém concluir alguma coisa: é o tipo
    de estrago que ninguém liga à causa.
    """

    @pytest.mark.parametrize("etapa", ["Concluídas", "Cancelado"])
    def test_a_ultima_do_grupo_nao_pode_ser_excluida(self, session_client, workspace, create_user, etapa):
        stages = seed_stages(workspace, create_user)

        response = session_client.delete(STAGE_URL.format(slug=workspace.slug, pk=stages[etapa].id))

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert WorkStage.objects.filter(pk=stages[etapa].id).exists()

    @pytest.mark.parametrize("grupo,nome", [("completed", "Concluídas"), ("cancelled", "Cancelado")])
    def test_com_duas_no_grupo_as_duas_podem(self, session_client, workspace, create_user, grupo, nome):
        """A regra é sobre a ÚLTIMA do grupo, e não sobre o grupo.

        Sem isto, proibir o grupo inteiro passaria no teste acima e travaria
        quem organiza a conclusão em mais de uma etapa.
        """
        stages = seed_stages(workspace, create_user)
        WorkStage.objects.create(
            workspace=workspace, owner=create_user, name=f"Outra {nome}", color="#000", group=grupo
        )

        response = session_client.delete(STAGE_URL.format(slug=workspace.slug, pk=stages[nome].id))

        assert response.status_code == status.HTTP_204_NO_CONTENT, response.data

    def test_etapa_comum_continua_excluivel(self, session_client, workspace, create_user):
        """Sem isto, proibir tudo passaria nos testes acima."""
        stages = seed_stages(workspace, create_user)

        response = session_client.delete(STAGE_URL.format(slug=workspace.slug, pk=stages["Para Depois"].id))

        assert response.status_code == status.HTTP_204_NO_CONTENT, response.data


@pytest.mark.contract
class TestEncerramentoNaoRecebeMarcacao:
    """Etapa de conclusão ou cancelamento não recebe balde nem vira entrada.

    Não é só falta de sentido — é dano. A varredura filtra pelo grupo do
    **estado da tarefa**, e não do da etapa: marcando "Concluídas" como destino
    de hoje, uma tarefa ABERTA que vencesse hoje seria jogada na coluna das
    concluídas, aberta, no meio do que já terminou.

    A entrada tem o problema simétrico: o que chega não chega pronto.
    """

    @pytest.mark.parametrize("etapa", ["Concluídas", "Cancelado"])
    @pytest.mark.parametrize("balde", ["hoje", "vencidas"])
    def test_nao_recebe_balde(self, session_client, workspace, create_user, etapa, balde):
        stages = seed_stages(workspace, create_user)

        response = session_client.post(
            MARK_BUCKET_URL.format(slug=workspace.slug, pk=stages[etapa].id), {"balde": balde}, format="json"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        stages[etapa].refresh_from_db()
        assert stages[etapa].is_due_today is False
        assert stages[etapa].is_overdue is False

    @pytest.mark.parametrize("etapa", ["Concluídas", "Cancelado"])
    def test_nao_vira_entrada(self, session_client, workspace, create_user, etapa):
        stages = seed_stages(workspace, create_user)

        response = session_client.post(MARK_DEFAULT_URL.format(slug=workspace.slug, pk=stages[etapa].id))

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        stages[etapa].refresh_from_db()
        assert stages[etapa].is_default is False

    def test_etapa_comum_continua_aceitando(self, session_client, workspace, create_user):
        """Sem isto, recusar tudo passaria nos testes acima."""
        stages = seed_stages(workspace, create_user)

        balde = session_client.post(
            MARK_BUCKET_URL.format(slug=workspace.slug, pk=stages["Em Andamento"].id),
            {"balde": "hoje"},
            format="json",
        )
        entrada = session_client.post(MARK_DEFAULT_URL.format(slug=workspace.slug, pk=stages["Em Andamento"].id))

        assert balde.status_code == status.HTTP_204_NO_CONTENT, balde.data
        assert entrada.status_code == status.HTTP_204_NO_CONTENT, entrada.data
