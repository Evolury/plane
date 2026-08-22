# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Toda promoção acaba — ver ADR 0021.

O Checkout do Asaas não tem campo de cupom: o desconto é aplicado no valor que
**nós** enviamos. Isso põe aqui uma responsabilidade que em outros produtos é do
gateway — sem esta rotina, um cupom de 100% não é um desconto generoso, é uma
assinatura grátis para sempre que ninguém descobre até alguém somar a receita à
mão.

O aviso vem antes: a tela de faturamento mostra a data de fim desde o dia em que
o cupom é aplicado, e a faixa aparece na semana final. O preço cheio nunca chega
como surpresa na fatura.
"""

import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from plane.db.models import Assinatura, HistoricoDeAssinatura
from plane.utils import planos
from plane.utils.asaas import ErroDoAsaas, atualizar_assinatura, reais
from plane.utils.exception_logger import log_exception

registro = logging.getLogger("plane.faturamento")

# Quantos dias antes o fim da promoção é anunciado na tela.
DIAS_DE_AVISO = 7


@shared_task
def encerrar_promocoes():
    hoje = timezone.now().date()
    encerradas = 0

    vencidas = Assinatura.objects.filter(promocao_termina_em__lte=hoje).exclude(plano="")

    for assinatura in vencidas:
        de = assinatura.valor_base
        cheio = planos.copia_para_contrato(assinatura.plano, assinatura.ciclo or planos.CICLO_MENSAL)

        assinatura.valor_base = cheio["valor_base"]
        assinatura.valor_por_assento = cheio["valor_por_assento"]
        assinatura.promocao_termina_em = None
        assinatura.cupom = None
        assinatura.save()
        encerradas += 1

        _avisar_o_asaas(assinatura)

        HistoricoDeAssinatura.objects.create(
            assinatura=assinatura,
            evento="fim_da_promocao",
            de=str(de),
            para=str(assinatura.valor_base),
            motivo=f"Promoção encerrada em {hoje.isoformat()}. Preço cheio de volta.",
        )

    registro.info(f"Promoções de faturamento: {encerradas} voltaram ao preço cheio.")
    return {"encerradas": encerradas}


def promocoes_a_vencer(hoje):
    """Quem precisa ser avisado nesta semana — é o que a tela destaca."""
    return Assinatura.objects.filter(
        promocao_termina_em__gt=hoje, promocao_termina_em__lte=hoje + timedelta(days=DIAS_DE_AVISO)
    )


def _avisar_o_asaas(assinatura):
    if not assinatura.asaas_subscription_id:
        return
    total = assinatura.valor_base + assinatura.valor_por_assento * assinatura.assentos_extras
    try:
        atualizar_assinatura(assinatura.asaas_subscription_id, value=reais(total))
    except ErroDoAsaas as excecao:
        # A conciliação diária compara os dois lados e volta a tentar.
        log_exception(excecao)
