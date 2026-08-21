# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""A régua da assinatura — ver ADR 0021.

Tudo deriva de um campo só: `pago_ate`. O estado não é escrito por quem paga
nem por quem cobra; é **calculado** a partir da data até onde o ciclo está pago.

O cálculo vai direto ao estado de hoje, e não um degrau por dia. Se a rotina
diária ficar uma semana fora do ar, o espaço que estava atrasado acorda
bloqueado — e não atrasado, esperando seis execuções para chegar lá. Estado que
depende de a rotina ter rodado todo dia é estado que mente quando ela falha.

Nada aqui toca banco: são datas entrando e uma palavra saindo. É o que torna a
régua inteira testável sem migração e sem fixture.
"""

from datetime import date, timedelta
from typing import Optional

# Espaço sem assinatura nenhuma. Lê, não escreve.
SEM_ASSINATURA = "sem_assinatura"
# Acesso concedido por cupom de cortesia — e cortesia tem fim, como qualquer
# promoção (ADR 0021, decisão 10). Enquanto vale, comporta-se como `ativa`.
EM_CORTESIA = "em_cortesia"
ATIVA = "ativa"
# Venceu e não pagou. Não restringe nada: o Asaas ainda está tentando o cartão
# (cinco vezes em cerca de três dias), e restringir no primeiro dia puniria
# quem paga sozinho no segundo.
ATRASADA = "atrasada"
# Somente leitura. Degradar antes de suspender é o que mantém o dado à vista —
# e o dado à vista é o motivo de voltar.
RESTRITA = "restrita"
BLOQUEADA = "bloqueada"
# Cancelou. Mantém o acesso até o fim do ciclo já pago, e nem um dia a mais.
CANCELADA = "cancelada"
ENCERRADA = "encerrada"
REMOVIDA = "removida"

ESTADOS = (
    SEM_ASSINATURA,
    EM_CORTESIA,
    ATIVA,
    ATRASADA,
    RESTRITA,
    BLOQUEADA,
    CANCELADA,
    ENCERRADA,
    REMOVIDA,
)

ROTULOS = {
    SEM_ASSINATURA: "Sem assinatura",
    EM_CORTESIA: "Em cortesia",
    ATIVA: "Ativa",
    ATRASADA: "Atrasada",
    RESTRITA: "Restrita",
    BLOQUEADA: "Bloqueada",
    CANCELADA: "Cancelada",
    ENCERRADA: "Encerrada",
    REMOVIDA: "Removida",
}

ESCOLHAS = tuple((estado, ROTULOS[estado]) for estado in ESTADOS)

DIAS_ATE_RESTRINGIR = 7
DIAS_ATE_BLOQUEAR = 15
DIAS_ATE_ENCERRAR = 45
DIAS_DE_RETENCAO = 90

# Quem pode escrever. `cancelada` está aqui de propósito: cancelar não tira o
# que já foi pago.
PERMITEM_ESCRITA = frozenset({EM_CORTESIA, ATIVA, ATRASADA, CANCELADA})

# Quem pode ler. Restrito e bloqueado continuam lendo — e, principalmente,
# continuam **exportando**: é o que torna o bloqueio defensável.
PERMITEM_LEITURA = PERMITEM_ESCRITA | frozenset({SEM_ASSINATURA, RESTRITA, BLOQUEADA})

# Estados que a régua não move: não têm ciclo correndo.
PARADOS = frozenset({SEM_ASSINATURA, REMOVIDA})


def permite_escrita(estado: str) -> bool:
    return estado in PERMITEM_ESCRITA


def permite_leitura(estado: str) -> bool:
    return estado in PERMITEM_LEITURA


def dias_de_atraso(pago_ate: Optional[date], hoje: date) -> int:
    """Dias corridos desde o fim do ciclo pago. Zero enquanto estiver em dia."""
    if pago_ate is None or hoje <= pago_ate:
        return 0
    return (hoje - pago_ate).days


# Cortesia dada aos espaços que já existiam quando o faturamento entrou. Prazo,
# e não cortesia aberta: cortesia sem data é assinatura grátis para sempre, em
# silêncio. Com data, ela aparece no painel com um relógio correndo.
DIAS_DE_CORTESIA_DE_TRANSICAO = 90


def fim_da_cortesia_de_transicao(hoje: date) -> date:
    return hoje + timedelta(days=DIAS_DE_CORTESIA_DE_TRANSICAO)


def data_de_remocao(encerrada_em: date) -> date:
    """Quando os dados vão embora — 90 dias depois de encerrar o contrato.

    Outro relógio que o `HARD_DELETE_AFTER_DAYS`, que purga item excluído pelo
    usuário. Este encerra contrato.
    """
    return encerrada_em + timedelta(days=DIAS_DE_RETENCAO)


def estado_de_hoje(
    *,
    estado: str,
    pago_ate: Optional[date],
    hoje: date,
    encerrada_em: Optional[date] = None,
) -> str:
    """O estado que a assinatura tem hoje, calculado do zero.

    Recebe o estado atual só para saber de onde veio — cortesia continua
    cortesia enquanto vale, e cancelada continua cancelada até o ciclo acabar.
    O resto sai das datas.
    """
    if estado not in ESTADOS:
        raise ValueError(f"Estado desconhecido: {estado!r}. Conhecidos: {', '.join(ESTADOS)}")

    if estado in PARADOS:
        return estado

    if estado == ENCERRADA:
        if encerrada_em is not None and hoje >= data_de_remocao(encerrada_em):
            return REMOVIDA
        return ENCERRADA

    if estado == CANCELADA:
        # Sem data de fim, cancelar encerra na hora — não há ciclo pago a honrar.
        if pago_ate is None or hoje > pago_ate:
            return ENCERRADA
        return CANCELADA

    if pago_ate is None:
        # Assinatura ativa sem data até quando vale não é caso a adivinhar:
        # é dado incompleto, e a régua não inventa prazo.
        return estado

    atraso = dias_de_atraso(pago_ate, hoje)

    if atraso == 0:
        # Pagou: o ciclo andou para a frente. Cortesia volta a ser cortesia.
        return EM_CORTESIA if estado == EM_CORTESIA else ATIVA
    if atraso >= DIAS_ATE_ENCERRAR:
        return ENCERRADA
    if atraso >= DIAS_ATE_BLOQUEAR:
        return BLOQUEADA
    if atraso >= DIAS_ATE_RESTRINGIR:
        return RESTRITA
    return ATRASADA


def proximo_marco(*, estado: str, pago_ate: date, hoje: date):
    """O próximo aperto: `(data, estado)`, ou `None` se não houver mais nenhum.

    Dizer "somente leitura em 3 dias" é o aviso que recupera pagamento; "sua
    conta está irregular" é o que o cliente ignora.
    """
    if estado in PARADOS or estado in {ENCERRADA, CANCELADA} or pago_ate is None:
        return None

    for dias, destino in (
        (DIAS_ATE_RESTRINGIR, RESTRITA),
        (DIAS_ATE_BLOQUEAR, BLOQUEADA),
        (DIAS_ATE_ENCERRAR, ENCERRADA),
    ):
        marco = pago_ate + timedelta(days=dias)
        if marco > hoje:
            return marco, destino

    return None
