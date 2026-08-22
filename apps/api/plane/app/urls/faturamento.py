# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.urls import path

from plane.app.views.faturamento import (
    CancelarEndpoint,
    CobrancasEndpoint,
    ConferirCupomEndpoint,
    ContratarEndpoint,
    DadosDeCobrancaEndpoint,
    PlanoDoEspacoEndpoint,
    ReativarEndpoint,
    ReembolsoEndpoint,
    TrocarPlanoEndpoint,
    webhook_do_asaas,
)

urlpatterns = [
    path(
        "workspaces/<str:slug>/faturamento/plano/",
        PlanoDoEspacoEndpoint.as_view(),
        name="faturamento-plano",
    ),
    path(
        "workspaces/<str:slug>/faturamento/dados-de-cobranca/",
        DadosDeCobrancaEndpoint.as_view(),
        name="faturamento-dados-de-cobranca",
    ),
    path(
        "workspaces/<str:slug>/faturamento/cupom/",
        ConferirCupomEndpoint.as_view(),
        name="faturamento-cupom",
    ),
    path(
        "workspaces/<str:slug>/faturamento/contratar/",
        ContratarEndpoint.as_view(),
        name="faturamento-contratar",
    ),
    path(
        "workspaces/<str:slug>/faturamento/trocar-plano/",
        TrocarPlanoEndpoint.as_view(),
        name="faturamento-trocar-plano",
    ),
    path(
        "workspaces/<str:slug>/faturamento/cobrancas/",
        CobrancasEndpoint.as_view(),
        name="faturamento-cobrancas",
    ),
    path(
        "workspaces/<str:slug>/faturamento/cancelar/",
        CancelarEndpoint.as_view(),
        name="faturamento-cancelar",
    ),
    path(
        "workspaces/<str:slug>/faturamento/reativar/",
        ReativarEndpoint.as_view(),
        name="faturamento-reativar",
    ),
    path(
        "workspaces/<str:slug>/faturamento/reembolso/",
        ReembolsoEndpoint.as_view(),
        name="faturamento-reembolso",
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
