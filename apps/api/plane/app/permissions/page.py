# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.db.models import Exists, OuterRef

from plane.db.models import ProjectMember, ProjectPage, Page, PageShare, WorkspaceMember
from plane.app.permissions import ROLE


from rest_framework.exceptions import NotFound
from rest_framework.permissions import BasePermission, SAFE_METHODS


# Permission Mappings for workspace members
ADMIN = ROLE.ADMIN.value
MEMBER = ROLE.MEMBER.value
GUEST = ROLE.GUEST.value


class ProjectPagePermission(BasePermission):
    """
    Custom permission to control access to pages within a workspace
    based on user roles, page visibility (public/private), and feature flags.
    """

    def has_permission(self, request, view):
        """
        Check basic project-level permissions before checking object-level permissions.
        """
        if request.user.is_anonymous:
            return False

        user_id = request.user.id
        slug = view.kwargs.get("slug")
        page_id = view.kwargs.get("page_id")
        project_id = view.kwargs.get("project_id")

        # Hook for extended validation
        extended_access, role = self._check_access_and_get_role(request, slug, project_id)
        if extended_access is False:
            return False

        if page_id:
            # Scope the page to the project in the URL. Resolving the page by
            # workspace + page_id alone allowed a member of one project to read
            # pages belonging to another project in the same workspace
            # (GHSA-g49r / GHSA-ghcr). Require an *active* ProjectPage link (both
            # conditions on the same relation so they match one row) so a page
            # removed from the project (soft-deleted link) is also denied.
            page = Page.objects.filter(
                id=page_id,
                workspace__slug=slug,
                project_pages__project_id=project_id,
                project_pages__deleted_at__isnull=True,
            ).first()
            if page is None:
                return False

            # Allow access if the user is the owner of the page
            if page.owned_by_id == user_id:
                return True

            # Handle private page access
            if page.access == Page.PRIVATE_ACCESS:
                return self._has_private_page_action_access(request, slug, page, project_id)

        # Handle public page access
        return self._has_public_page_action_access(request, role)

    def _check_project_member_access(self, request, slug, project_id):
        """
        Check if the user is a project member.
        """
        return (
            ProjectMember.objects.filter(
                member=request.user,
                workspace__slug=slug,
                is_active=True,
                project_id=project_id,
            )
            .values_list("role", flat=True)
            .first()
        )

    def _check_access_and_get_role(self, request, slug, project_id):
        """
        Hook for extended access checking
        Returns: True (allow), False (deny), None (continue with normal flow)
        """
        role = self._check_project_member_access(request, slug, project_id)
        if not role:
            return False, None
        return True, role

    def _has_private_page_action_access(self, request, slug, page, project_id):
        """
        Check access to private pages. Override for feature flag logic.
        """
        # Base implementation: only owner can access private pages
        return False

    def _check_project_action_access(self, request, role):
        method = request.method

        # Only admins can create (POST) pages
        if method == "POST":
            if role in [ADMIN, MEMBER]:
                return True
            return False

        # Safe methods (GET, HEAD, OPTIONS) allowed for all active roles
        if method in SAFE_METHODS:
            if role in [ADMIN, MEMBER, GUEST]:
                return True
            return False

        # PUT/PATCH: Admins and members can update
        if method in ["PUT", "PATCH"]:
            if role in [ADMIN, MEMBER]:
                return True
            return False

        # DELETE: Only admins can delete
        if method == "DELETE":
            if role in [ADMIN]:
                return True
            return False

        # Deny by default
        return False

    def _has_public_page_action_access(self, request, role):
        """
        Check if the user has permission to access a public page
        and can perform operations on the page.
        """
        project_member_exists = self._check_project_action_access(request, role)
        if not project_member_exists:
            return False
        return True


class PersonalPagePermission(BasePermission):
    """
    Evolury — página pessoal: mora no workspace e não pertence a projeto nenhum.

    O acesso tem duas fontes e só duas: ser o dono, ou ter uma linha em
    `PageShare`. Papel de projeto não existe (não há projeto) e papel de
    workspace não vale — administrador de workspace não lê o caderno pessoal de
    ninguém. Quem não tem nenhuma das duas recebe 404 e não 403: 403 confirmaria
    que a página existe.

    O método diz o que a pessoa está tentando fazer, e é por ele que o papel
    decide:

    | método      | dono | pode editar | pode ler |
    | ----------- | ---- | ----------- | -------- |
    | GET         | sim  | sim         | sim      |
    | PATCH       | sim  | sim         | não      |
    | POST/DELETE | sim  | não         | não      |

    POST e DELETE nesta API são bloquear, arquivar, duplicar e excluir — todos
    privilégio do dono, mesmo para quem pode editar. Ver ADR 0015.
    """

    def has_permission(self, request, view):
        if request.user.is_anonymous:
            return False

        slug = view.kwargs.get("slug")
        if not WorkspaceMember.objects.filter(
            workspace__slug=slug, member=request.user, is_active=True
        ).exists():
            return False

        page_id = view.kwargs.get("page_id")
        if not page_id:
            # Listar e criar não têm alvo: o queryset da view já se restringe
            # ao dono.
            return True

        page = (
            Page.objects.filter(id=page_id, workspace__slug=slug)
            .annotate(em_projeto=Exists(ProjectPage.objects.filter(page_id=OuterRef("pk"))))
            .filter(em_projeto=False)
            .first()
        )
        # 404 e não 403 de propósito: negar com 403 responde "existe, mas não é
        # sua", que é informação sobre a página de outra pessoa.
        if page is None:
            raise NotFound()

        # Guardado para a view não repetir a consulta.
        request.pagina_pessoal = page

        if page.owned_by_id == request.user.id:
            request.papel_na_pagina = "dono"
            return True

        compartilhamento = PageShare.objects.filter(page_id=page.id, shared_with=request.user).first()
        if compartilhamento is None:
            raise NotFound()

        request.papel_na_pagina = compartilhamento.role
        if request.method in SAFE_METHODS:
            return True
        if request.method in ("PUT", "PATCH"):
            return compartilhamento.role >= PageShare.WRITE
        return False
