# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""O que conserta o que o webhook não entregou — ver ADR 0021.

Webhook é entrega otimista: chega quase sempre, e "quase" é o problema. Duas
rotinas cobrem os dois modos de falha:

- **Conciliação**: pergunta ao Asaas o estado de cada assinatura que
  conhecemos e corrige o espelho. Roda todo dia, e é ela que faz um evento
  perdido custar horas em vez de um mês.
- **Alarme**: fila interrompida é silenciosa por natureza — quinze falhas
  seguidas e o Asaas simplesmente para de mandar. Sem alguém olhando o relógio,
  quem descobre é o cliente que não conseguiu pagar.

Nenhuma das duas escreve no Asaas. Consertar o nosso lado é seguro; escrever do
lado do dinheiro por conta de uma divergência que ninguém leu, não.
"""

import logging
from datetime import date, timedelta

from celery import shared_task
from django.core.cache import cache
from django.utils import timezone

from plane.db.models import Assinatura, HistoricoDeAssinatura
from plane.utils import regua
from plane.utils.asaas import ErroDoAsaas, buscar_assinatura, centavos
from plane.utils.exception_logger import log_exception

# Quantas horas de silêncio já são suspeitas. O Asaas manda evento a cada
# cobrança criada, atualizada, vencida ou paga; com assinatura ativa na casa,
# um dia inteiro calado é sinal de fila interrompida, não de calmaria.
HORAS_DE_SILENCIO_ACEITAS = 24

registro = logging.getLogger("plane.faturamento")

CHAVE_DO_ULTIMO_EVENTO = "faturamento:ultimo_evento_em"
CHAVE_DO_ALARME = "faturamento:alarme_de_silencio"

# Como o Asaas chama cada estado de assinatura.
ATIVA_NO_ASAAS = "ACTIVE"


@shared_task
def conciliar_assinaturas():
    """Compara o espelho com o Asaas, assinatura por assinatura."""
    assinaturas = Assinatura.objects.exclude(asaas_subscription_id="").exclude(
        status__in=[regua.REMOVIDA, regua.ENCERRADA]
    )

    conferidas = 0
    corrigidas = 0

    for assinatura in assinaturas:
        try:
            do_asaas = buscar_assinatura(assinatura.asaas_subscription_id)
        except ErroDoAsaas as excecao:
            log_exception(excecao)
            continue

        conferidas += 1
        divergencias = _divergencias(assinatura, do_asaas)
        if not divergencias:
            continue

        for campo, valor in divergencias.items():
            setattr(assinatura, campo, valor)
        assinatura.save()
        corrigidas += 1

        HistoricoDeAssinatura.objects.create(
            assinatura=assinatura,
            evento="conciliacao",
            motivo="Divergências corrigidas a partir do Asaas: "
            + ", ".join(f"{campo}={valor}" for campo, valor in divergencias.items()),
        )

    registro.info(f"Conciliação de faturamento: {conferidas} conferidas, {corrigidas} corrigidas.")
    return {"conferidas": conferidas, "corrigidas": corrigidas}


def _divergencias(assinatura, do_asaas) -> dict:
    """O que o Asaas diz e o nosso banco não sabe.

    Só datas e valores. O **estado** é nosso: a régua deriva de `pago_ate`, e
    "ACTIVE" no Asaas quer dizer "a assinatura existe", não "o cliente está em
    dia". Sobrescrever o nosso estado com o dele devolveria acesso a quem não
    pagou.
    """
    achadas = {}

    proximo = do_asaas.get("nextDueDate")
    if proximo:
        proximo = date.fromisoformat(proximo)
        if assinatura.proxima_cobranca_em != proximo:
            achadas["proxima_cobranca_em"] = proximo

    valor = do_asaas.get("value")
    if valor is not None:
        # O valor conferido é o da base, sem os assentos extras — que existem só
        # do nosso lado até a E7 empurrá-los para o Asaas.
        esperado = assinatura.valor_base + assinatura.valor_por_assento * assinatura.assentos_extras
        if centavos(valor) != esperado and assinatura.valor_base:
            achadas["valor_base"] = centavos(valor) - assinatura.valor_por_assento * assinatura.assentos_extras

    if do_asaas.get("status") and do_asaas["status"] != ATIVA_NO_ASAAS:
        # Inativada lá e ativa aqui: alguém mexeu pelo painel do Asaas. Vira
        # cancelada, que honra o ciclo pago em vez de cortar na hora.
        if assinatura.status in (regua.ATIVA, regua.ATRASADA, regua.EM_CORTESIA):
            achadas["status"] = regua.CANCELADA
            achadas["cancelada_em"] = timezone.now().date()

    return achadas


@shared_task
def alarme_de_silencio_do_asaas():
    """Acende o aviso quando nenhum evento chega há tempo demais."""
    tem_assinatura_viva = (
        Assinatura.objects.exclude(asaas_subscription_id="")
        .filter(status__in=[regua.ATIVA, regua.ATRASADA, regua.RESTRITA, regua.BLOQUEADA])
        .exists()
    )
    if not tem_assinatura_viva:
        cache.delete(CHAVE_DO_ALARME)
        return {"alarme": False, "motivo": "nenhuma assinatura viva"}

    ultimo = cache.get(CHAVE_DO_ULTIMO_EVENTO)
    limite = timezone.now() - timedelta(hours=HORAS_DE_SILENCIO_ACEITAS)

    calado = True
    if ultimo:
        try:
            calado = timezone.datetime.fromisoformat(ultimo) < limite
        except ValueError:
            calado = True

    if calado:
        aviso = (
            f"Nenhum evento do Asaas há mais de {HORAS_DE_SILENCIO_ACEITAS}h com assinatura ativa. "
            "Fila de webhook possivelmente interrompida — o Asaas para depois de 15 falhas seguidas."
        )
        cache.set(CHAVE_DO_ALARME, aviso, None)
        registro.warning(aviso)
        return {"alarme": True, "desde": ultimo}

    cache.delete(CHAVE_DO_ALARME)
    return {"alarme": False, "desde": ultimo}
