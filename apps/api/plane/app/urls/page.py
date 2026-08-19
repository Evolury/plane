# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.urls import path


from plane.app.views import (
    PageViewSet,
    PageFavoriteViewSet,
    PagesDescriptionViewSet,
    PageVersionEndpoint,
    PageDuplicateEndpoint,
    PersonalPageViewSet,
    PersonalPageDescriptionViewSet,
    PersonalPageVersionEndpoint,
    PersonalPageDuplicateEndpoint,
    PersonalPageShareViewSet,
    SharedWithMeEndpoint,
)

urlpatterns = [
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/pages-summary/",
        PageViewSet.as_view({"get": "summary"}),
        name="project-pages-summary",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/pages/",
        PageViewSet.as_view({"get": "list", "post": "create"}),
        name="project-pages",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/pages/<uuid:page_id>/",
        PageViewSet.as_view({"get": "retrieve", "patch": "partial_update", "delete": "destroy"}),
        name="project-pages",
    ),
    # favorite pages
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/favorite-pages/<uuid:page_id>/",
        PageFavoriteViewSet.as_view({"post": "create", "delete": "destroy"}),
        name="user-favorite-pages",
    ),
    # archived pages
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/pages/<uuid:page_id>/archive/",
        PageViewSet.as_view({"post": "archive", "delete": "unarchive"}),
        name="project-page-archive-unarchive",
    ),
    # lock and unlock
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/pages/<uuid:page_id>/lock/",
        PageViewSet.as_view({"post": "lock", "delete": "unlock"}),
        name="project-pages-lock-unlock",
    ),
    # private and public page
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/pages/<uuid:page_id>/access/",
        PageViewSet.as_view({"post": "access"}),
        name="project-pages-access",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/pages/<uuid:page_id>/description/",
        PagesDescriptionViewSet.as_view({"get": "retrieve", "patch": "partial_update"}),
        name="page-description",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/pages/<uuid:page_id>/versions/",
        PageVersionEndpoint.as_view(),
        name="page-versions",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/pages/<uuid:page_id>/versions/<uuid:pk>/",
        PageVersionEndpoint.as_view(),
        name="page-versions",
    ),
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/pages/<uuid:page_id>/duplicate/",
        PageDuplicateEndpoint.as_view(),
        name="page-duplicate",
    ),

    # Evolury: páginas pessoais de "Minhas tarefas" — sem projeto na rota
    # porque não há projeto. Ver ADR 0015.
    path(
        "workspaces/<str:slug>/my-tasks/pages/",
        PersonalPageViewSet.as_view({"get": "list", "post": "create"}),
        name="personal-pages",
    ),
    path(
        "workspaces/<str:slug>/my-tasks/pages/<uuid:page_id>/",
        PersonalPageViewSet.as_view(
            {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
        ),
        name="personal-page",
    ),
    path(
        "workspaces/<str:slug>/my-tasks/pages/<uuid:page_id>/lock/",
        PersonalPageViewSet.as_view({"post": "lock", "delete": "unlock"}),
        name="personal-page-lock",
    ),
    path(
        "workspaces/<str:slug>/my-tasks/pages/<uuid:page_id>/archive/",
        PersonalPageViewSet.as_view({"post": "archive", "delete": "unarchive"}),
        name="personal-page-archive",
    ),
    path(
        "workspaces/<str:slug>/my-tasks/pages/<uuid:page_id>/description/",
        PersonalPageDescriptionViewSet.as_view({"get": "retrieve", "patch": "partial_update"}),
        name="personal-page-description",
    ),
    path(
        "workspaces/<str:slug>/my-tasks/pages/<uuid:page_id>/versions/",
        PersonalPageVersionEndpoint.as_view(),
        name="personal-page-versions",
    ),
    path(
        "workspaces/<str:slug>/my-tasks/pages/<uuid:page_id>/versions/<uuid:pk>/",
        PersonalPageVersionEndpoint.as_view(),
        name="personal-page-versions",
    ),
    path(
        "workspaces/<str:slug>/my-tasks/pages/<uuid:page_id>/duplicate/",
        PersonalPageDuplicateEndpoint.as_view(),
        name="personal-page-duplicate",
    ),
    path(
        "workspaces/<str:slug>/my-tasks/pages/<uuid:page_id>/shares/",
        PersonalPageShareViewSet.as_view({"get": "list", "post": "create"}),
        name="personal-page-shares",
    ),
    path(
        "workspaces/<str:slug>/my-tasks/pages/<uuid:page_id>/shares/<uuid:pk>/",
        PersonalPageShareViewSet.as_view({"delete": "destroy"}),
        name="personal-page-share",
    ),
    path(
        "workspaces/<str:slug>/my-tasks/shared-pages/",
        SharedWithMeEndpoint.as_view(),
        name="personal-pages-shared-with-me",
    ),
]
