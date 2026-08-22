# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Assento a mais entra no ciclo seguinte — ver ADR 0021.

Convidar nunca é bloqueado: quem precisa de mais gente coloca mais gente, e a
conta acerta depois. Bloquear o convite seria atrito que gera suporte e não gera
receita.

**O ajuste é para o ciclo seguinte, nunca para a cobrança já gerada.** É por isso
que a atualização no Asaas não leva `updatePendingPayments`: mudar o valor de
uma cobrança que o cliente já recebeu — e talvez já tenha agendado no banco — é
o tipo de surpresa que vira contestação.

**A conta é refeita do zero a cada dia**, e não incrementada: `extras = usados −
incluídos`. Quem tirou gente do espaço vê a conta cair na mesma rotina, sem
ninguém precisar lembrar de desfazer nada. Contador que só sobe é contador que
cobra a mais.
"""

import logging

from celery import shared_task

from plane.db.models import Assinatura, HistoricoDeAssinatura
from plane.utils import direitos, regua
from plane.utils.asaas import ErroDoAsaas, atualizar_assinatura, reais
from plane.utils.exception_logger import log_exception

registro = logging.getLogger("plane.faturamento")

# Só quem tem contrato de pé. Cortesia não gera excedente: ela não cobra nada, e
# cobrar assento extra de quem não paga assento nenhum não faz sentido.
ESTADOS_QUE_COBRAM = (regua.ATIVA, regua.ATRASADA, regua.RESTRITA, regua.BLOQUEADA)


@shared_task
def ajustar_excedentes():
    ajustadas = 0

    for assinatura in Assinatura.objects.filter(status__in=ESTADOS_QUE_COBRAM).exclude(plano=""):
        usados = direitos.uso_de_assentos(assinatura.workspace_id)
        extras = max(usados - assinatura.assentos_incluidos, 0)
        if extras == assinatura.assentos_extras:
            continue

        de = assinatura.assentos_extras
        assinatura.assentos_extras = extras
        assinatura.save()
        ajustadas += 1

        _avisar_o_asaas(assinatura)

        HistoricoDeAssinatura.objects.create(
            assinatura=assinatura,
            evento="excedente",
            de=str(de),
            para=str(extras),
            motivo=(
                f"{usados} membros para {assinatura.assentos_incluidos} assentos incluídos. "
                f"Novo valor do ciclo: {reais(assinatura.valor_base + assinatura.valor_por_assento * extras)}."
            ),
        )

    registro.info(f"Excedentes de faturamento: {ajustadas} assinaturas ajustadas.")
    return {"ajustadas": ajustadas}


def _avisar_o_asaas(assinatura):
    """O valor novo vale do próximo vencimento em diante.

    Falhar aqui não desfaz o ajuste local: a conciliação diária compara os dois
    lados e volta a tentar. O contrário — desistir do ajuste porque o Asaas
    piscou — deixaria de cobrar assento que está sendo usado.
    """
    if not assinatura.asaas_subscription_id:
        return
    total = assinatura.valor_base + assinatura.valor_por_assento * assinatura.assentos_extras
    try:
        atualizar_assinatura(assinatura.asaas_subscription_id, value=reais(total))
    except ErroDoAsaas as excecao:
        log_exception(excecao)
