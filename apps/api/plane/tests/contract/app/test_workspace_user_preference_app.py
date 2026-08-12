# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from plane.db.models import User, WorkspaceMember
from plane.db.models.workspace import WorkspaceUserPreference


@pytest.mark.contract
class TestWorkspaceUserPreferencePatch:
    """Contract tests for the sidebar preference PATCH endpoint.

    Regression coverage for #9260: ``patch`` filtered ``WorkspaceUserPreference``
    by ``key``/``workspace__slug`` only, so in a workspace with multiple members
    ``.first()`` (ordered by ``-created_at``) could return — and mutate — another
    member's preference row instead of the requesting user's.
    """

    KEY = WorkspaceUserPreference.UserPreferenceKeys.ANALYTICS.value

    @pytest.mark.django_db
    def test_patch_only_updates_requesting_users_preference(self, session_client, create_user, workspace):
        """A member's PATCH must update only their own preference, never another member's."""
        # A second, more-recently-active member of the same workspace.
        other_user = User.objects.create(
            email="other@plane.so", username="other_user", first_name="Other", last_name="User"
        )
        WorkspaceMember.objects.create(workspace=workspace, member=other_user, role=15)

        own_pref = WorkspaceUserPreference.objects.create(
            workspace=workspace, user=create_user, key=self.KEY, is_pinned=False, sort_order=100
        )
        other_pref = WorkspaceUserPreference.objects.create(
            workspace=workspace, user=other_user, key=self.KEY, is_pinned=False, sort_order=200
        )

        # Force the other member's row to sort first under the model's ``-created_at``
        # ordering, so an unscoped ``.first()`` would deterministically pick it.
        now = timezone.now()
        WorkspaceUserPreference.objects.filter(pk=own_pref.pk).update(created_at=now)
        WorkspaceUserPreference.objects.filter(pk=other_pref.pk).update(created_at=now + timedelta(minutes=1))

        url = reverse("workspace-user-preference", kwargs={"slug": workspace.slug})
        response = session_client.patch(
            url, [{"key": self.KEY, "is_pinned": True, "sort_order": 999}], format="json"
        )

        assert response.status_code == status.HTTP_200_OK

        own_pref.refresh_from_db()
        other_pref.refresh_from_db()

        # The requesting user's preference is updated...
        assert own_pref.is_pinned is True
        assert own_pref.sort_order == 999
        # ...and the other member's preference is left untouched.
        assert other_pref.is_pinned is False
        assert other_pref.sort_order == 200

    @pytest.mark.django_db
    def test_patch_updates_own_preference(self, session_client, create_user, workspace):
        """Baseline: a member's PATCH persists changes to their own preference row."""
        preference = WorkspaceUserPreference.objects.create(
            workspace=workspace, user=create_user, key=self.KEY, is_pinned=False, sort_order=100
        )

        url = reverse("workspace-user-preference", kwargs={"slug": workspace.slug})
        response = session_client.patch(
            url, [{"key": self.KEY, "is_pinned": True, "sort_order": 42}], format="json"
        )

        assert response.status_code == status.HTTP_200_OK

        preference.refresh_from_db()
        assert preference.is_pinned is True
        assert preference.sort_order == 42


# Evolury: "Minhas tarefas" fica acima de "Minhas atividades" (your_work) na
# sidebar — cobre o default de usuário novo, a âncora do caminho de upgrade
# (linhas pré-existentes sem my_tasks) e a troca da migração 0126.
@pytest.mark.contract
class TestWorkspaceUserPreferenceOrdering:
    MY_TASKS = WorkspaceUserPreference.UserPreferenceKeys.MY_TASKS.value
    YOUR_WORK = WorkspaceUserPreference.UserPreferenceKeys.YOUR_WORK.value

    @pytest.mark.django_db
    def test_fresh_user_gets_my_tasks_above_your_work(self, session_client, create_user, workspace):
        """Sem linha alguma, o GET semeia todas as chaves com my_tasks acima."""
        url = reverse("workspace-user-preference", kwargs={"slug": workspace.slug})
        response = session_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        preferences = response.json()
        assert preferences[self.MY_TASKS]["sort_order"] < preferences[self.YOUR_WORK]["sort_order"]

    @pytest.mark.django_db
    def test_upgrade_anchors_my_tasks_right_above_your_work(self, session_client, create_user, workspace):
        """Com your_work já criada, my_tasks nasce ancorada 5000 acima dela."""
        WorkspaceUserPreference.objects.create(
            workspace=workspace, user=create_user, key=self.YOUR_WORK, is_pinned=True, sort_order=75535
        )

        url = reverse("workspace-user-preference", kwargs={"slug": workspace.slug})
        response = session_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        preferences = response.json()
        assert preferences[self.MY_TASKS]["sort_order"] == 75535 - 5000
        assert preferences[self.YOUR_WORK]["sort_order"] == 75535

    @pytest.mark.django_db
    def test_migration_swaps_only_inverted_pairs(self, create_user, workspace):
        """A troca da 0126 inverte pares my_tasks>your_work e preserva os demais."""
        import importlib

        from django.apps import apps as django_apps

        inverted_my_tasks = WorkspaceUserPreference.objects.create(
            workspace=workspace, user=create_user, key=self.MY_TASKS, is_pinned=True, sort_order=70535
        )
        inverted_your_work = WorkspaceUserPreference.objects.create(
            workspace=workspace, user=create_user, key=self.YOUR_WORK, is_pinned=True, sort_order=65535
        )

        # Um segundo membro já com a ordem nova (ex.: reordenou manualmente).
        other_user = User.objects.create(
            email="ordered@plane.so", username="ordered_user", first_name="Ordered", last_name="User"
        )
        WorkspaceMember.objects.create(workspace=workspace, member=other_user, role=15)
        ordered_my_tasks = WorkspaceUserPreference.objects.create(
            workspace=workspace, user=other_user, key=self.MY_TASKS, is_pinned=True, sort_order=1000
        )
        ordered_your_work = WorkspaceUserPreference.objects.create(
            workspace=workspace, user=other_user, key=self.YOUR_WORK, is_pinned=True, sort_order=2000
        )

        migration = importlib.import_module("plane.db.migrations.0126_evolury_my_tasks_above_your_work")
        migration.swap_my_tasks_above_your_work(django_apps, None)

        inverted_my_tasks.refresh_from_db()
        inverted_your_work.refresh_from_db()
        ordered_my_tasks.refresh_from_db()
        ordered_your_work.refresh_from_db()

        # O par invertido troca de posição entre si...
        assert inverted_my_tasks.sort_order == 65535
        assert inverted_your_work.sort_order == 70535
        # ...e o par que já estava na ordem nova permanece intacto.
        assert ordered_my_tasks.sort_order == 1000
        assert ordered_your_work.sort_order == 2000
