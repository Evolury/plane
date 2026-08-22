# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""O que o espaço tem, em uma chamada só — ver ADR 0021.

A tela precisa saber três coisas ao mesmo tempo: qual plano, em que estado, e
quanto do teto já foi usado. Espalhar isso em três endpoints faria a interface
piscar em ordens diferentes a cada carregamento; juntar numa resposta faz o
front ter um retrato coerente ou nenhum.

Esta rota vive sob `faturamento/`, que é o prefixo que o middleware de somente
leitura deixa passar: **pagar não pode depender de estar pago**.
"""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from plane.app.permissions import WorkspaceViewerPermission
from plane.app.views.base import BaseAPIView
from plane.db.models import Assinatura
from plane.utils import direitos, planos, regua


class PlanoDoEspacoEndpoint(BaseAPIView):
    permission_classes = [IsAuthenticated, WorkspaceViewerPermission]

    def get(self, request, slug):
        retrato = direitos.dados(slug=slug)
        workspace_id = retrato["workspace_id"]
        chave = retrato["plano"]
        escolhido = planos.plano(chave) if chave else None

        assinatura = (
            Assinatura.objects.filter(workspace__slug=slug)
            .values("ciclo", "pago_ate", "proxima_cobranca_em", "assentos_extras", "promocao_termina_em")
            .first()
            or {}
        )

        marco = regua.proximo_marco(
            estado=retrato["status"],
            pago_ate=assinatura.get("pago_ate"),
            hoje=self._hoje(),
        )

        return Response(
            {
                "plano": chave,
                "nome": escolhido.nome if escolhido else "",
                "ciclo": assinatura.get("ciclo", ""),
                "status": retrato["status"],
                "pode_escrever": regua.permite_escrita(retrato["status"]),
                "pago_ate": assinatura.get("pago_ate"),
                "proxima_cobranca_em": assinatura.get("proxima_cobranca_em"),
                "promocao_termina_em": assinatura.get("promocao_termina_em"),
                "proximo_marco": {"data": marco[0], "estado": marco[1]} if marco else None,
                "recursos": {
                    recurso: bool(escolhido and escolhido.inclui(recurso)) for recurso in planos.RECURSOS
                },
                "limites": {
                    nome: direitos.limite(nome, slug=slug) for nome in planos.LIMITES
                },
                "assentos": {
                    "incluidos": retrato["assentos_incluidos"],
                    "extras": assinatura.get("assentos_extras", 0),
                    "usados": direitos.uso_de_assentos(workspace_id) if workspace_id else 0,
                },
                "convidados": {
                    "cota": direitos.cota_de_convidados(slug=slug),
                    "usados": direitos.uso_de_convidados(workspace_id) if workspace_id else 0,
                },
                "automacoes_ativas": direitos.uso_de_automacoes(workspace_id) if workspace_id else 0,
            },
            status=status.HTTP_200_OK,
        )

    def _hoje(self):
        from django.utils import timezone

        return timezone.now().date()
