# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""O que cada evento do Asaas faz com a assinatura — ver ADR 0021.

**O estado é montado a partir de cobrança, não de assinatura.** O Asaas não tem
webhook de assinatura para pagamento: o que chega é `PAYMENT_*`, e o campo
`subscription` do corpo é o que liga o evento ao espaço. `externalReference` é o
caminho reserva, com o prefixo `qoowork:` que separa o nosso do que pertence aos
outros negócios da mesma conta.

**Evento que não é nosso é ignorado, nunca é erro.** A distinção importa: erro
pede investigação, e a maior parte do que chega nesta porta é cobrança de outro
negócio da Evolury seguindo a vida dela.
"""

from datetime import date

from celery import shared_task
from django.utils import timezone

from plane.db.models import Assinatura, Cobranca, EventoAsaas, HistoricoDeAssinatura
from plane.utils import regua
from plane.utils.asaas import centavos, espaco_da_referencia
from plane.utils.exception_logger import log_exception
from plane.utils.planos import CICLO_MENSAL, fim_do_ciclo

APLICADO = "aplicado"
IGNORADO = "ignorado"
ERRO = "erro"

# De qual chave do corpo sai o objeto de cada família de evento.
CHAVE_DO_OBJETO = {"PAYMENT": "payment", "SUBSCRIPTION": "subscription", "CHECKOUT": "checkout"}

# Pagamento confirmado ou recebido: os dois valem como "pagou". `CONFIRMED` é o
# cartão aprovado antes de o dinheiro cair; esperar o `RECEIVED` deixaria o
# cliente esperando dias pelo acesso que ele já pagou.
PAGOU = {"PAYMENT_CONFIRMED", "PAYMENT_RECEIVED"}
DEVOLVEU = {"PAYMENT_REFUNDED", "PAYMENT_PARTIALLY_REFUNDED"}
ENCERROU_NO_ASAAS = {"SUBSCRIPTION_INACTIVATED", "SUBSCRIPTION_DELETED"}


def _objeto(payload, tipo):
    familia = (tipo or "").split("_")[0]
    return payload.get(CHAVE_DO_OBJETO.get(familia, ""), {}) or {}


def _assinatura_do(objeto):
    """Acha o espaço dono do evento, ou `None` quando ele não é nosso."""
    id_da_assinatura = objeto.get("subscription") or (
        objeto.get("id") if objeto.get("object") == "subscription" else None
    )
    if id_da_assinatura:
        encontrada = Assinatura.objects.filter(asaas_subscription_id=id_da_assinatura).first()
        if encontrada:
            return encontrada

    workspace_id = espaco_da_referencia(objeto.get("externalReference"))
    if workspace_id:
        return Assinatura.objects.filter(workspace_id=workspace_id).first()

    return None


def _data(valor):
    return date.fromisoformat(valor) if valor else None


def _registrar(assinatura, evento, de, para, motivo):
    HistoricoDeAssinatura.objects.create(
        assinatura=assinatura, evento=evento, de=de or "", para=para or "", motivo=motivo
    )


def _guardar_cobranca(assinatura, objeto):
    Cobranca.objects.update_or_create(
        asaas_payment_id=objeto.get("id"),
        defaults={
            "assinatura": assinatura,
            "status": objeto.get("status") or "",
            "forma": objeto.get("billingType") or "",
            "valor": centavos(objeto.get("value")),
            "vencimento": _data(objeto.get("dueDate")) or timezone.now().date(),
            "pago_em": _data(objeto.get("paymentDate") or objeto.get("confirmedDate")),
            "link": objeto.get("invoiceUrl") or "",
        },
    )


def aplicar(evento: EventoAsaas) -> str:
    tipo = evento.payload.get("event") or evento.tipo
    objeto = _objeto(evento.payload, tipo)

    assinatura = _assinatura_do(objeto)
    if assinatura is None:
        return IGNORADO

    if tipo.startswith("PAYMENT_") and objeto.get("id"):
        _guardar_cobranca(assinatura, objeto)

    anterior = assinatura.status

    if tipo in PAGOU:
        # Cancelada que paga a última cobrança continua cancelada: ela já disse
        # que não quer renovar, e o acesso vai até o fim do ciclo pago.
        if assinatura.status != regua.CANCELADA:
            assinatura.status = regua.ATIVA
        vencimento = _data(objeto.get("dueDate"))
        if vencimento:
            proximo = fim_do_ciclo(vencimento, assinatura.ciclo or CICLO_MENSAL)
            assinatura.pago_ate = proximo
            assinatura.proxima_cobranca_em = proximo
        assinatura.save()
        _registrar(assinatura, "pagamento_confirmado", anterior, assinatura.status, f"{tipo} do Asaas.")
        return APLICADO

    if tipo in DEVOLVEU:
        hoje = timezone.now().date()
        assinatura.status = regua.ENCERRADA
        assinatura.encerrada_em = hoje
        assinatura.remover_dados_em = regua.data_de_remocao(hoje)
        assinatura.save()
        _registrar(assinatura, "estorno", anterior, assinatura.status, f"{tipo} do Asaas.")
        return APLICADO

    if tipo in ENCERROU_NO_ASAAS:
        # Cancelar no Asaas não tira o acesso na hora: o ciclo pago é honrado, e
        # quem move para `encerrada` é a régua, quando `pago_ate` passar.
        if assinatura.status in (regua.ATIVA, regua.ATRASADA, regua.EM_CORTESIA):
            assinatura.status = regua.CANCELADA
            assinatura.cancelada_em = timezone.now().date()
            assinatura.save()
            _registrar(assinatura, "cancelamento", anterior, assinatura.status, f"{tipo} do Asaas.")
        return APLICADO

    if tipo.startswith("CHECKOUT_") and tipo == "CHECKOUT_PAID":
        # A assinatura nasce no Asaas quando o checkout é pago. Guardamos os
        # dois identificadores agora; o acesso é liberado pelo pagamento, que
        # chega logo atrás como `PAYMENT_CONFIRMED`.
        do_asaas = objeto.get("subscription") or {}
        cliente = objeto.get("customer") or {}
        assinatura.asaas_subscription_id = do_asaas.get("id") or assinatura.asaas_subscription_id
        assinatura.asaas_customer_id = cliente.get("id") or assinatura.asaas_customer_id
        assinatura.save()
        _registrar(assinatura, "checkout_pago", anterior, assinatura.status, "CHECKOUT_PAID do Asaas.")
        return APLICADO

    # Criado, atualizado, vencido, apagado: a cobrança já foi espelhada acima, e
    # o estado sai da régua, que lê `pago_ate`. Não há o que decidir aqui.
    return APLICADO


@shared_task
def processar_evento_do_asaas(evento_id):
    evento = EventoAsaas.objects.filter(pk=evento_id).first()
    if evento is None or evento.processado_em:
        return

    try:
        resultado = aplicar(evento)
        evento.resultado = resultado
        evento.erro = ""
    except Exception as excecao:  # noqa: BLE001
        # Falhar aqui não devolve erro ao Asaas: a resposta já foi 200. Fica
        # registrado, o reprocessamento é nosso, e a conciliação diária conserta
        # o estado mesmo que este evento nunca seja reprocessado.
        log_exception(excecao)
        evento.resultado = ERRO
        evento.erro = str(excecao)[:2000]
        evento.tentativas += 1
        evento.save(update_fields=["resultado", "erro", "tentativas", "updated_at"])
        return

    evento.processado_em = timezone.now()
    evento.save(update_fields=["resultado", "erro", "processado_em", "updated_at"])
    # O cache de direitos não é invalidado aqui: quem faz isso é o sinal de
    # `post_save` da assinatura, e por isso vale para toda escrita — inclusive
    # a da conciliação e a do bloqueio manual, que não passam por este arquivo.
