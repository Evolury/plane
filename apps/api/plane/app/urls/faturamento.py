# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.urls import path

from plane.app.views.faturamento import PlanoDoEspacoEndpoint

urlpatterns = [
    path(
        "workspaces/<str:slug>/faturamento/plano/",
        PlanoDoEspacoEndpoint.as_view(),
        name="faturamento-plano",
    ),
]
