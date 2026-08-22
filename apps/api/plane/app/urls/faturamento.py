# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.urls import path

from plane.app.views.faturamento import PlanoDoEspacoEndpoint, webhook_do_asaas

urlpatterns = [
    path(
        "workspaces/<str:slug>/faturamento/plano/",
        PlanoDoEspacoEndpoint.as_view(),
        name="faturamento-plano",
    ),
    # Fora de `workspaces/` de propósito: quem chama é o Asaas, que não tem
    # sessão nem espaço de trabalho — e o middleware de faturamento só olha
    # caminhos de espaço, então esta rota nunca é travada por assinatura
    # nenhuma.
    path(
        "faturamento/asaas/webhook/",
        webhook_do_asaas,
        name="faturamento-webhook-asaas",
    ),
]
