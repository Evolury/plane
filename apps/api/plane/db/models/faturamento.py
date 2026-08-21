# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Evolury: assinatura por espaço de trabalho (ADR 0021).
#
# Domínio inteiramente nosso — nenhum modelo herdado é alterado aqui.
# Especificação e arquitetura em docs/evolury/funcionalidades/faturamento/.
#
# Duas escolhas estruturais que o resto do módulo assume:
#
# 1. **O Asaas é a autoridade do dinheiro; este banco é a autoridade do
#    acesso.** A tela nunca pergunta ao Asaas se o cliente pagou — ela lê este
#    espelho, alimentado por webhook e corrigido por conciliação diária. Se o
#    Asaas cair, ninguém é bloqueado: sem evento, o estado não muda.
#
# 2. **O preço é cópia, não referência.** `valor_base` e `valor_por_assento`
#    guardam o que o cliente contratou no dia em que contratou. Reajustar a
#    tabela em plane/utils/planos.py não pode reescrever contrato assinado.

# Django imports
from django.db import models

# Module imports
from plane.utils import regua
from plane.utils.planos import CICLOS, CHAVES

from .base import BaseModel

ESCOLHAS_DE_PLANO = tuple((chave, chave.capitalize()) for chave in CHAVES)
ESCOLHAS_DE_CICLO = tuple((ciclo, ciclo.capitalize()) for ciclo in CICLOS)

TIPO_PERCENTUAL = "percentual"
TIPO_CORTESIA = "cortesia"
ESCOLHAS_DE_CUPOM = ((TIPO_PERCENTUAL, "Percentual"), (TIPO_CORTESIA, "Cortesia"))


class Cupom(BaseModel):
    """Um código, dois tipos — e todo cupom tem fim.

    O Checkout do Asaas não tem campo de cupom: o desconto é aplicado no valor
    que enviamos. Sem `validade` e sem `ciclos`, um cupom de 100% viraria
    assinatura grátis para sempre, em silêncio (ADR 0021, decisão 10).
    """

    codigo = models.CharField(max_length=32, unique=True)
    tipo = models.CharField(max_length=16, choices=ESCOLHAS_DE_CUPOM)
    # Percentual: 1 a 100. Cortesia: dias de acesso sem cobrança.
    valor = models.PositiveIntegerField()
    # Só para percentual: por quantos ciclos vale. Nulo é permanente — e
    # permanente é decisão, não descuido, por isso precisa ser escrita.
    ciclos = models.PositiveIntegerField(null=True, blank=True)
    validade = models.DateField(null=True, blank=True)
    usos_max = models.PositiveIntegerField(null=True, blank=True)
    usos = models.PositiveIntegerField(default=0)
    descricao = models.TextField(blank=True, default="")

    class Meta:
        verbose_name = "Cupom"
        verbose_name_plural = "Cupons"
        db_table = "cupons"
        ordering = ("-created_at",)

    def __str__(self):
        return self.codigo


class Assinatura(BaseModel):
    """Uma por espaço de trabalho. O relógio de tudo é `pago_ate`."""

    workspace = models.OneToOneField("db.Workspace", on_delete=models.CASCADE, related_name="assinatura")

    # Vazio enquanto o espaço não contratou nada — é o par de `sem_assinatura`.
    plano = models.CharField(max_length=32, choices=ESCOLHAS_DE_PLANO, blank=True, default="")
    ciclo = models.CharField(max_length=16, choices=ESCOLHAS_DE_CICLO, blank=True, default="")
    status = models.CharField(
        max_length=24,
        choices=regua.ESCOLHAS,
        default=regua.SEM_ASSINATURA,
        db_index=True,
    )

    # Até onde o ciclo está pago. Toda a régua sai daqui.
    pago_ate = models.DateField(null=True, blank=True, db_index=True)
    proxima_cobranca_em = models.DateField(null=True, blank=True)

    # Cópia do catálogo no ato da contratação — ver o cabeçalho deste arquivo.
    assentos_incluidos = models.PositiveIntegerField(default=0)
    assentos_extras = models.PositiveIntegerField(default=0)
    convidados_por_assento = models.PositiveIntegerField(default=0)
    valor_base = models.PositiveIntegerField(default=0)
    valor_por_assento = models.PositiveIntegerField(default=0)

    asaas_customer_id = models.CharField(max_length=64, blank=True, default="", db_index=True)
    asaas_subscription_id = models.CharField(max_length=64, blank=True, default="", db_index=True)
    asaas_checkout_id = models.CharField(max_length=64, blank=True, default="")

    cupom = models.ForeignKey(Cupom, on_delete=models.SET_NULL, null=True, blank=True, related_name="assinaturas")
    promocao_termina_em = models.DateField(null=True, blank=True)

    cancelada_em = models.DateField(null=True, blank=True)
    encerrada_em = models.DateField(null=True, blank=True)
    # Preenchida quando encerra. É o que a rotina de remoção lê — guardar a
    # data em vez de recalculá-la deixa a prorrogação ser um `UPDATE`.
    remover_dados_em = models.DateField(null=True, blank=True, db_index=True)

    class Meta:
        verbose_name = "Assinatura"
        verbose_name_plural = "Assinaturas"
        db_table = "assinaturas"
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.workspace_id} · {self.plano or 'sem plano'} · {self.status}"

    @property
    def assentos_pagos(self) -> int:
        return self.assentos_incluidos + self.assentos_extras

    def permite_escrita(self) -> bool:
        return regua.permite_escrita(self.status)

    def permite_leitura(self) -> bool:
        return regua.permite_leitura(self.status)


class Cobranca(BaseModel):
    """Espelho de cada cobrança do Asaas — é o histórico que a tela mostra.

    Não existe webhook de assinatura para pagamento: o que chega é evento de
    cobrança, e é daqui que o estado da assinatura é montado.
    """

    assinatura = models.ForeignKey(Assinatura, on_delete=models.CASCADE, related_name="cobrancas")
    asaas_payment_id = models.CharField(max_length=64, unique=True)
    status = models.CharField(max_length=32, db_index=True)
    forma = models.CharField(max_length=32, blank=True, default="")
    valor = models.PositiveIntegerField()
    vencimento = models.DateField(db_index=True)
    pago_em = models.DateField(null=True, blank=True)
    link = models.TextField(blank=True, default="")

    class Meta:
        verbose_name = "Cobrança"
        verbose_name_plural = "Cobranças"
        db_table = "cobrancas"
        ordering = ("-vencimento",)

    def __str__(self):
        return f"{self.asaas_payment_id} · {self.status}"


class EventoAsaas(BaseModel):
    """Todo evento recebido, gravado antes de ser processado.

    `asaas_event_id` é único **sem condição de exclusão**: idempotência não pode
    depender de o registro não ter sido apagado. O Asaas entrega *at-least-once*
    e reenvia a fila inteira quando ela é reativada — chegar duas vezes é o
    caso normal, não a exceção.

    O `payload` cru fica guardado porque reprocessar não pode exigir pedir nada
    de volta ao Asaas.
    """

    asaas_event_id = models.CharField(max_length=64, unique=True)
    tipo = models.CharField(max_length=64, db_index=True)
    payload = models.JSONField(default=dict)
    processado_em = models.DateTimeField(null=True, blank=True, db_index=True)
    tentativas = models.PositiveIntegerField(default=0)
    erro = models.TextField(blank=True, default="")

    class Meta:
        verbose_name = "Evento do Asaas"
        verbose_name_plural = "Eventos do Asaas"
        db_table = "eventos_asaas"
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.tipo} · {self.asaas_event_id}"


class HistoricoDeAssinatura(BaseModel):
    """Quem mudou o quê, quando e por quê — inclusive pelo god-mode.

    Bloqueio manual, cortesia concedida e troca de plano são atos com
    consequência financeira. Ato administrativo nunca é silencioso.
    """

    assinatura = models.ForeignKey(Assinatura, on_delete=models.CASCADE, related_name="historico")
    evento = models.CharField(max_length=48, db_index=True)
    de = models.CharField(max_length=48, blank=True, default="")
    para = models.CharField(max_length=48, blank=True, default="")
    motivo = models.TextField(blank=True, default="")

    class Meta:
        verbose_name = "Histórico de assinatura"
        verbose_name_plural = "Históricos de assinatura"
        db_table = "historicos_de_assinatura"
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.evento}: {self.de or '—'} → {self.para or '—'}"
