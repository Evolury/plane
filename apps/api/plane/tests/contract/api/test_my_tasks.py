# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Evolury: testes de contrato de "Minhas tarefas" — etapas pessoais, listagem
# anotada e movimento entre etapas.
# Regras em docs/evolury/funcionalidades/minhas-tarefas/ (ADRs 0001 e 0002).

from unittest import mock

import pytest
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
ISSUES_URL = "/api/workspaces/{slug}/my-tasks/issues/"
MOVE_URL = "/api/workspaces/{slug}/my-tasks/issues/{issue_id}/move/"


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
        assert len(response.data) == 5
        defaults = [stage for stage in response.data if stage["is_default"]]
        assert len(defaults) == 1
        assert defaults[0]["name"] == "Recém-atribuídas"
        # Ordem do seed preservada pelo sort_order
        assert [stage["name"] for stage in response.data] == [
            "Recém-atribuídas",
            "Hoje",
            "Em breve",
            "Depois",
            "Concluídas",
        ]

    def test_seed_is_idempotent(self, session_client, workspace):
        session_client.get(STAGES_URL.format(slug=workspace.slug))
        response = session_client.get(STAGES_URL.format(slug=workspace.slug))
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 5

    def test_seed_race_is_absorbed(self, db, workspace, create_user):
        """Se dois requests passam pelo exists() ao mesmo tempo, a segunda
        inserção viola a constraint de nome único e é absorvida em silêncio."""
        ensure_default_work_stages(workspace, create_user)
        with mock.patch(
            "plane.app.views.workspace.my_tasks.WorkStage.objects.filter"
        ) as mocked_filter:
            mocked_filter.return_value.exists.return_value = False
            ensure_default_work_stages(workspace, create_user)  # não levanta
        assert WorkStage.objects.filter(workspace=workspace, owner=create_user).count() == 5

    def test_seed_is_per_user(self, session_client, second_client, workspace, second_user, create_user):
        session_client.get(STAGES_URL.format(slug=workspace.slug))
        response = second_client.get(STAGES_URL.format(slug=workspace.slug))
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 5
        assert WorkStage.objects.filter(workspace=workspace).count() == 10
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
            {"name": "Hoje", "color": "#000000", "group": "started"},
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
            STAGE_URL.format(slug=workspace.slug, pk=stages["Hoje"].id),
            {"name": "Agora", "color": "#FF0000"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "Agora"

    def test_patch_other_users_stage_is_not_found(self, second_client, workspace, create_user):
        stages = seed_stages(workspace, create_user)
        response = second_client.patch(
            STAGE_URL.format(slug=workspace.slug, pk=stages["Hoje"].id),
            {"name": "Invasão"},
            format="json",
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_destroy_default_is_rejected(self, session_client, workspace, create_user):
        stages = seed_stages(workspace, create_user)
        response = session_client.delete(
            STAGE_URL.format(slug=workspace.slug, pk=stages["Recém-atribuídas"].id)
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_destroy_migrates_associations_to_default(
        self, session_client, workspace, create_user, assigned_issue
    ):
        stages = seed_stages(workspace, create_user)
        WorkStageIssue.objects.create(
            workspace=workspace, owner=create_user, stage=stages["Hoje"], issue=assigned_issue
        )
        response = session_client.delete(STAGE_URL.format(slug=workspace.slug, pk=stages["Hoje"].id))
        assert response.status_code == status.HTTP_204_NO_CONTENT
        association = WorkStageIssue.objects.get(owner=create_user, issue=assigned_issue)
        assert association.stage_id == stages["Recém-atribuídas"].id

    def test_mark_default_swaps(self, session_client, workspace, create_user):
        stages = seed_stages(workspace, create_user)
        response = session_client.post(MARK_DEFAULT_URL.format(slug=workspace.slug, pk=stages["Hoje"].id))
        assert response.status_code == status.HTTP_204_NO_CONTENT
        defaults = WorkStage.objects.filter(workspace=workspace, owner=create_user, is_default=True)
        assert defaults.count() == 1
        assert defaults.first().id == stages["Hoje"].id


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
        assert result["my_task_stage_id"] == stages["Recém-atribuídas"].id

    def test_moved_issue_is_annotated_with_its_stage(
        self, session_client, workspace, create_user, assigned_issue
    ):
        stages = seed_stages(workspace, create_user)
        WorkStageIssue.objects.create(
            workspace=workspace, owner=create_user, stage=stages["Hoje"], issue=assigned_issue
        )
        response = session_client.get(ISSUES_URL.format(slug=workspace.slug))
        result = response.data["results"][0]
        assert result["my_task_stage_id"] == stages["Hoje"].id

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
            stage=stages["Hoje"],
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
            workspace=workspace, owner=create_user, stage=first_stages["Hoje"], issue=assigned_issue
        )

        first = session_client.get(ISSUES_URL.format(slug=workspace.slug)).data["results"][0]
        second = second_client.get(ISSUES_URL.format(slug=workspace.slug)).data["results"][0]
        assert first["my_task_stage_id"] == first_stages["Hoje"].id
        assert second["my_task_stage_id"] == second_stages["Recém-atribuídas"].id

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
        default_group = results[str(stages["Recém-atribuídas"].id)]
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
class TestMyTasksMove:
    def test_move_creates_association(self, session_client, workspace, create_user, assigned_issue):
        stages = seed_stages(workspace, create_user)
        response = session_client.post(
            MOVE_URL.format(slug=workspace.slug, issue_id=assigned_issue.id),
            {"stage_id": str(stages["Hoje"].id)},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        association = WorkStageIssue.objects.get(owner=create_user, issue=assigned_issue)
        assert association.stage_id == stages["Hoje"].id

    def test_move_again_updates_same_association(
        self, session_client, workspace, create_user, assigned_issue
    ):
        stages = seed_stages(workspace, create_user)
        url = MOVE_URL.format(slug=workspace.slug, issue_id=assigned_issue.id)
        session_client.post(url, {"stage_id": str(stages["Hoje"].id)}, format="json")
        session_client.post(url, {"stage_id": str(stages["Depois"].id)}, format="json")
        associations = WorkStageIssue.objects.filter(owner=create_user, issue=assigned_issue)
        assert associations.count() == 1
        assert associations.first().stage_id == stages["Depois"].id

    def test_move_persists_sort_order(self, session_client, workspace, create_user, assigned_issue):
        stages = seed_stages(workspace, create_user)
        response = session_client.post(
            MOVE_URL.format(slug=workspace.slug, issue_id=assigned_issue.id),
            {"stage_id": str(stages["Hoje"].id), "sort_order": 12345.0},
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
            {"stage_id": str(seed["Hoje"].id)},
            format="json",
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_move_to_other_users_stage_is_not_found(
        self, session_client, workspace, create_user, second_user, assigned_issue
    ):
        other_stages = seed_stages(workspace, second_user)
        response = session_client.post(
            MOVE_URL.format(slug=workspace.slug, issue_id=assigned_issue.id),
            {"stage_id": str(other_stages["Hoje"].id)},
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

    def test_hard_delete_cascades_association(self, session_client, workspace, create_user, assigned_issue):
        """Hard delete do work item remove a associação em cascata — sem
        linha órfã (linha 8 da matriz de compatibilidade)."""
        stages = seed_stages(workspace, create_user)
        session_client.post(
            MOVE_URL.format(slug=workspace.slug, issue_id=assigned_issue.id),
            {"stage_id": str(stages["Hoje"].id)},
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
            {"stage_id": str(stages["Hoje"].id)},
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
        assert result["my_task_stage_id"] == stages["Hoje"].id

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
