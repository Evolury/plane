# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""O relógio da régua — ver ADR 0021.

Roda uma vez por dia e não decide nada: pergunta a `regua.estado_de_hoje` qual é
o estado a partir de `pago_ate` e grava o que mudou. A régua calcula direto o
estado de hoje, e não um degrau por dia — se esta tarefa ficar uma semana fora
do ar, ninguém acorda "atrasado" quando já deveria estar bloqueado.

Dois efeitos que não são só mudança de palavra:

- **Encerrar cancela a cobrança no Asaas.** Deixar de honrar e continuar
  cobrando é a pior combinação possível, e a que gera estorno.
- **Remover apaga o espaço**, 90 dias depois de encerrar, pelo caminho de
  exclusão que já existe — o mesmo `delete()` que o produto usa, com a purga
  definitiva vindo depois. Antes disso há três avisos, e a exportação funciona
  até o último dia.
"""

import logging

from celery import shared_task
from django.utils import timezone

from plane.db.models import Assinatura, HistoricoDeAssinatura, Workspace
from plane.utils import regua
from plane.utils.asaas import ErroDoAsaas, cancelar_assinatura
from plane.utils.exception_logger import log_exception

registro = logging.getLogger("plane.faturamento")

# Quantos dias antes da remoção o espaço é avisado.
AVISOS_DE_REMOCAO = (30, 7, 1)


@shared_task
def avancar_regua():
    hoje = timezone.now().date()
    mudaram = 0

    for assinatura in Assinatura.objects.exclude(status__in=regua.PARADOS):
        atual = assinatura.status
        proximo = regua.estado_de_hoje(
            estado=atual,
            pago_ate=assinatura.pago_ate,
            hoje=hoje,
            encerrada_em=assinatura.encerrada_em,
        )
        if proximo == atual:
            continue

        _aplicar(assinatura, atual, proximo, hoje)
        mudaram += 1

    registro.info(f"Régua de faturamento: {mudaram} assinaturas mudaram de estado.")
    return {"mudaram": mudaram}


def _aplicar(assinatura, de, para, hoje):
    assinatura.status = para

    if para == regua.ENCERRADA:
        assinatura.encerrada_em = assinatura.encerrada_em or hoje
        assinatura.remover_dados_em = regua.data_de_remocao(assinatura.encerrada_em)
        _parar_de_cobrar(assinatura)

    assinatura.save()

    HistoricoDeAssinatura.objects.create(
        assinatura=assinatura,
        evento="regua",
        de=de,
        para=para,
        motivo=f"Régua diária a partir de pago_ate={assinatura.pago_ate}.",
    )

    if para == regua.REMOVIDA:
        _remover_o_espaco(assinatura)


def _parar_de_cobrar(assinatura):
    """Encerrou: a cobrança para junto.

    Falhar aqui não impede o encerramento — o acesso já acabou, e continuar
    tentando cancelar é assunto da conciliação. O que não pode é o encerramento
    depender de o Asaas estar de pé.
    """
    if not assinatura.asaas_subscription_id:
        return
    try:
        cancelar_assinatura(assinatura.asaas_subscription_id)
    except ErroDoAsaas as excecao:
        log_exception(excecao)


def _remover_o_espaco(assinatura):
    """Passados os 90 dias, o espaço vai pelo caminho de exclusão do produto."""
    espaco = Workspace.objects.filter(pk=assinatura.workspace_id, deleted_at__isnull=True).first()
    if espaco is None:
        return
    espaco.delete()
    registro.warning(f"Espaço {espaco.slug} removido: 90 dias após o encerramento do contrato.")


def dias_ate_a_remocao(assinatura, hoje) -> int | None:
    """Quantos dias faltam — é o que a faixa de aviso mostra."""
    if not assinatura.remover_dados_em:
        return None
    return (assinatura.remover_dados_em - hoje).days
