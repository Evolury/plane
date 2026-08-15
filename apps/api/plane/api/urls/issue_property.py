# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Evolury: definições de propriedade na API pública (ADR 0011).

from django.urls import path

from plane.api.views import IssuePropertyListAPIEndpoint


urlpatterns = [
    path(
        "workspaces/<str:slug>/projects/<uuid:project_id>/issue-properties/",
        IssuePropertyListAPIEndpoint.as_view(http_method_names=["get"]),
        name="issue-property",
    ),
]
