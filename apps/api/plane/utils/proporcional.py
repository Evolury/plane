# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""A conta do meio do ciclo — ver ADR 0021.

O Asaas não calcula pró-rata. Quem sobe de plano no dia 10 de um ciclo de 30
dias já usou um terço do que pagou, e vai usar dois terços do plano novo. A
diferença entre esses dois pedaços é o que se cobra à parte, numa cobrança
avulsa — a assinatura só passa a valer o preço novo no ciclo seguinte.

**Downgrade não gera crédito.** Rebaixar no meio do ciclo e receber dinheiro de
volta seria um caminho fácil de arbitragem, e nenhum produto do mercado faz
isso: o plano menor vale a partir do próximo ciclo, e o dinheiro já pago compra
o que foi contratado. Por isso esta função só olha para cima.
"""

from datetime import date


def dias_restantes(hoje: date, fim_do_ciclo: date) -> int:
    """Quantos dias do ciclo ainda não foram usados. Nunca negativo."""
    return max((fim_do_ciclo - hoje).days, 0)


def diferenca_de_upgrade(*, valor_atual: int, valor_novo: int, hoje: date, inicio: date, fim: date) -> int:
    """O que se cobra hoje para subir de plano, em centavos.

    Proporcional ao que **resta** do ciclo, e sobre a diferença — não sobre o
    valor cheio do plano novo. Cobrar o plano novo inteiro no meio do ciclo
    seria cobrar duas vezes pelos dias que o cliente já pagou.

    Arredonda para baixo: numa disputa de centavo entre a casa e o cliente, a
    casa perde de propósito.
    """
    if valor_novo <= valor_atual:
        return 0

    total_de_dias = (fim - inicio).days
    if total_de_dias <= 0:
        return 0

    restantes = dias_restantes(hoje, fim)
    if restantes <= 0:
        return 0

    return (valor_novo - valor_atual) * restantes // total_de_dias
