# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Cupom e cortesia são o mesmo objeto — ver ADR 0021.

O comercial pediu duas coisas — código de teste e desconto — e elas são um
objeto com dois tipos:

- **percentual**: de 1% a 100%, por N ciclos ou permanente;
- **cortesia**: N dias de acesso sem cobrança.

O Checkout do Asaas **não tem campo de cupom**: o desconto é aplicado no valor
que enviamos. Isso põe uma responsabilidade aqui que em outros produtos é do
gateway — **toda promoção precisa de fim registrado**. Um cupom de 100% sem
prazo não é um desconto generoso; é uma assinatura grátis para sempre, em
silêncio, que ninguém descobre até alguém somar a receita à mão.
"""

from datetime import date, timedelta
from typing import Optional

PERCENTUAL = "percentual"
CORTESIA = "cortesia"
TIPOS = (PERCENTUAL, CORTESIA)

INVALIDO = "CUPOM_INVALIDO"
VENCIDO = "CUPOM_VENCIDO"
ESGOTADO = "CUPOM_ESGOTADO"


class CupomRecusado(Exception):
    def __init__(self, motivo):
        super().__init__(motivo)
        self.motivo = motivo


def conferir(cupom, hoje: date):
    """Recusa com motivo, em vez de devolver `None` e deixar quem chamou adivinhar."""
    if cupom is None:
        raise CupomRecusado(INVALIDO)
    if cupom.validade and cupom.validade < hoje:
        raise CupomRecusado(VENCIDO)
    if cupom.usos_max is not None and cupom.usos >= cupom.usos_max:
        raise CupomRecusado(ESGOTADO)
    return cupom


def valor_com_desconto(cupom, valor: int) -> int:
    """O valor que vai para o Asaas, em centavos.

    Cortesia zera: durante os dias dela não há cobrança nenhuma. Percentual
    desconta e **arredonda para baixo**, pelo mesmo motivo do pró-rata.
    """
    if cupom is None:
        return valor
    if cupom.tipo == CORTESIA:
        return 0
    desconto = valor * min(cupom.valor, 100) // 100
    return max(valor - desconto, 0)


def fim_da_promocao(cupom, hoje: date, fim_do_ciclo, ciclo: str) -> Optional[date]:
    """Quando o preço cheio volta. `None` só para desconto permanente.

    `fim_do_ciclo` vem por parâmetro para que este módulo siga sem saber de
    catálogo — testável com um cupom de mentira e nada mais. `ciclo` é o da
    assinatura: "três ciclos" de um contrato anual são três anos, não três
    meses, e confundir os dois daria desconto por engano.
    """
    if cupom is None:
        return None
    if cupom.tipo == CORTESIA:
        return hoje + timedelta(days=cupom.valor)
    if not cupom.ciclos:
        # Permanente é decisão, e fica registrada pela ausência de data.
        return None

    fim = hoje
    for _ in range(cupom.ciclos):
        fim = fim_do_ciclo(fim, ciclo)
    return fim


def primeira_cobranca(cupom, hoje: date) -> date:
    """Quando a primeira cobrança vence.

    Cortesia empurra: o cliente entra hoje e paga quando ela acabar. Sem
    cortesia, a cobrança é hoje — quem contrata, contrata pagando.
    """
    if cupom is not None and cupom.tipo == CORTESIA:
        return hoje + timedelta(days=cupom.valor)
    return hoje
