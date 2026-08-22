# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Cancelar, reativar e pedir reembolso — ver ADR 0021.

Três atos que o cliente faz sozinho, e que o produto precisa deixar fáceis:
prender quem quer sair é o caminho mais rápido para um estorno, que custa mais
que a mensalidade perdida.

**Cancelar não corta na hora.** O acesso vai até o fim do ciclo já pago, e nem
um dia a mais. O dinheiro pago comprou aquele período; devolvê-lo pela metade
seria cobrar por algo que não foi entregue.

**Reativar recupera a mesma assinatura** enquanto os dados existirem — dentro
dos 90 dias de retenção. Depois disso não há o que recuperar, e a tela diz
exatamente isso em vez de tentar.

**Reembolso é pedido, não botão de estorno.** Quem processa é o financeiro, no
painel do Asaas; o que o produto faz é registrar o pedido com data e motivo. O
estorno volta pelo webhook e encerra o espaço na hora (ADR 0021, decisão 14).
"""

from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response

from plane.app.permissions import ROLE, allow_permission
from plane.app.views.base import BaseAPIView
from plane.db.models import Assinatura, HistoricoDeAssinatura
from plane.utils import regua
from plane.utils.asaas import ErroDoAsaas, cancelar_assinatura
from plane.utils.error_codes import ERROR_CODES
from plane.utils.exception_logger import log_exception

# Quanto tempo o cliente tem para pedir o dinheiro de volta.
DIAS_DE_GARANTIA = 30


def _assinatura(slug):
    return Assinatura.objects.filter(workspace__slug=slug).first()


def _erro(codigo, **extras):
    return Response({"error_code": ERROR_CODES.get(codigo, 0), "error_message": codigo, **extras}, status=400)


class CancelarEndpoint(BaseAPIView):
    @allow_permission(allowed_roles=[ROLE.ADMIN], level="WORKSPACE")
    def post(self, request, slug):
        assinatura = _assinatura(slug)
        if assinatura is None or assinatura.status in (regua.ENCERRADA, regua.REMOVIDA):
            return _erro("SEM_ASSINATURA")
        if assinatura.status == regua.CANCELADA:
            return _erro("JA_CANCELADA")

        de = assinatura.status
        hoje = timezone.now().date()

        # Parar de cobrar é a primeira coisa. Se o Asaas estiver fora do ar, o
        # cancelamento **não** acontece — cancelar aqui e continuar cobrando lá
        # é o defeito que vira estorno.
        if assinatura.asaas_subscription_id:
            try:
                cancelar_assinatura(assinatura.asaas_subscription_id)
            except ErroDoAsaas as erro:
                log_exception(erro)
                return Response(
                    {"error_message": "ASAAS_RECUSOU", "detalhe": erro.corpo or str(erro)},
                    status=status.HTTP_502_BAD_GATEWAY,
                )

        assinatura.status = regua.CANCELADA
        assinatura.cancelada_em = hoje
        assinatura.save()

        HistoricoDeAssinatura.objects.create(
            assinatura=assinatura,
            evento="cancelamento",
            de=de,
            para=regua.CANCELADA,
            motivo=(request.data.get("motivo") or "").strip()[:500],
        )

        return Response(
            {"status": assinatura.status, "acesso_ate": assinatura.pago_ate},
            status=status.HTTP_200_OK,
        )


class ReativarEndpoint(BaseAPIView):
    @allow_permission(allowed_roles=[ROLE.ADMIN], level="WORKSPACE")
    def post(self, request, slug):
        assinatura = _assinatura(slug)
        if assinatura is None:
            return _erro("SEM_ASSINATURA")
        if assinatura.status == regua.REMOVIDA:
            # Não há o que recuperar. Dizer isso é melhor que tentar e falhar.
            return _erro("DADOS_REMOVIDOS")
        if assinatura.status not in (regua.CANCELADA, regua.ENCERRADA):
            return _erro("NAO_ESTA_CANCELADA")

        de = assinatura.status
        assinatura.cancelada_em = None
        assinatura.encerrada_em = None
        assinatura.remover_dados_em = None

        # Volta para onde a régua disser, a partir do que está pago: quem
        # cancelou dentro do ciclo volta ativo, e reativar não perdoa dívida.
        voltou_para = regua.estado_de_hoje(
            estado=regua.ATIVA, pago_ate=assinatura.pago_ate, hoje=timezone.now().date()
        )
        # Com uma trava: quem encerrou há muito tempo cairia direto em
        # `encerrada` de novo, e o botão de reativar não faria nada. O piso é
        # `restrita` — lê os próprios dados, exporta, e tem por onde pagar.
        if voltou_para in (regua.ENCERRADA, regua.REMOVIDA):
            voltou_para = regua.RESTRITA
        assinatura.status = voltou_para
        assinatura.save()

        HistoricoDeAssinatura.objects.create(
            assinatura=assinatura,
            evento="reativacao",
            de=de,
            para=assinatura.status,
            motivo="Reativada pelo administrador do espaço.",
        )

        return Response(
            {"status": assinatura.status, "precisa_contratar": not assinatura.asaas_subscription_id},
            status=status.HTTP_200_OK,
        )


class ReembolsoEndpoint(BaseAPIView):
    @allow_permission(allowed_roles=[ROLE.ADMIN], level="WORKSPACE")
    def post(self, request, slug):
        assinatura = _assinatura(slug)
        if assinatura is None:
            return _erro("SEM_ASSINATURA")

        motivo = (request.data.get("motivo") or "").strip()
        if not motivo:
            return _erro("MOTIVO_OBRIGATORIO")

        HistoricoDeAssinatura.objects.create(
            assinatura=assinatura,
            evento="pedido_de_reembolso",
            de=assinatura.status,
            para=assinatura.status,
            motivo=motivo[:500],
        )

        return Response(
            {
                "registrado": True,
                # O prazo é dito de volta para que a expectativa não dependa de
                # o cliente lembrar do que leu na contratação.
                "dias_de_garantia": DIAS_DE_GARANTIA,
            },
            status=status.HTTP_200_OK,
        )
