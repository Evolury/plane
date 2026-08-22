# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""O catálogo de planos — ver ADR 0021.

Mora em código, e não em banco, por dois motivos. São três planos que mudam
raro, e uma tela de administração para eles custaria mais do que economiza. E,
principalmente, é aqui que a **coerência entre os planos** pode ser testada:
tabela de preço incoerente, quando não é testada, só aparece em reunião
comercial.

Dinheiro é inteiro, em centavos. `0.1 + 0.2` não é `0.3`, e cobrança é o último
lugar onde se quer descobrir isso.

O que a assinatura guarda é **cópia** destes números, não referência: reajustar
a tabela não pode reescrever o que o cliente já contratou.
"""

from dataclasses import dataclass
from datetime import date
from typing import Optional

from dateutil.relativedelta import relativedelta

# Ciclos aceitos. O anual custa dez mensalidades — dois meses grátis, que é a
# âncora reconhecida no mercado brasileiro.
CICLO_MENSAL = "mensal"
CICLO_ANUAL = "anual"
CICLOS = (CICLO_MENSAL, CICLO_ANUAL)

MESES_DO_CICLO_ANUAL = 10

# Como cada ciclo se chama do lado do Asaas.
CICLOS_DO_ASAAS = {CICLO_MENSAL: "MONTHLY", CICLO_ANUAL: "YEARLY"}


def fim_do_ciclo(vencimento: date, ciclo: str) -> date:
    """O vencimento seguinte, que é também o `pago_ate` do ciclo pago.

    Uma data só para as duas coisas, de propósito: se a próxima cobrança vence
    em 22/09, o cliente está em dia até 22/09 — vencer hoje ainda não é atraso
    (a régua conta a partir do dia seguinte). Guardar "último dia coberto" e
    "próximo vencimento" separados criaria um erro de um dia esperando
    acontecer.

    `relativedelta` e não trinta dias: 31/01 mais um mês é 28/02, e somar dias
    faria a cobrança andar para trás no calendário a cada ano.
    """
    if ciclo == CICLO_ANUAL:
        return vencimento + relativedelta(years=1)
    if ciclo == CICLO_MENSAL:
        return vencimento + relativedelta(months=1)
    raise ValueError(f"Ciclo desconhecido: {ciclo!r}. Conhecidos: {', '.join(CICLOS)}")

# Recursos são booleanos: o plano inclui ou não inclui.
RECURSO_ANALYTICS = "analytics"
RECURSO_API_PUBLICA = "api_publica"
RECURSO_WEBHOOKS = "webhooks"
RECURSOS = (RECURSO_ANALYTICS, RECURSO_API_PUBLICA, RECURSO_WEBHOOKS)

# Limites são quantidade. `None` é "sem teto" — nunca zero, que significa
# "nenhum" e é outra coisa.
LIMITE_PROPRIEDADES = "propriedades_por_projeto"
LIMITE_AUTOMACOES = "automacoes_ativas"
LIMITES = (LIMITE_PROPRIEDADES, LIMITE_AUTOMACOES)


@dataclass(frozen=True)
class Plano:
    chave: str
    nome: str
    assentos: int
    mensal: int
    adicional_mensal: int
    convidados_por_assento: int
    recursos: dict
    limites: dict

    @property
    def anual(self) -> int:
        return self.mensal * MESES_DO_CICLO_ANUAL

    @property
    def adicional_anual(self) -> int:
        return self.adicional_mensal * MESES_DO_CICLO_ANUAL

    @property
    def por_assento(self) -> int:
        """Preço efetivo do assento incluído, para comparar planos."""
        return self.mensal // self.assentos

    def preco(self, ciclo: str) -> int:
        return self.anual if ciclo == CICLO_ANUAL else self.mensal

    def adicional(self, ciclo: str) -> int:
        return self.adicional_anual if ciclo == CICLO_ANUAL else self.adicional_mensal

    def inclui(self, recurso: str) -> bool:
        return bool(self.recursos.get(recurso, False))

    def teto(self, limite: str) -> Optional[int]:
        return self.limites.get(limite)


ESSENCIAL = "essencial"
PROFISSIONAL = "profissional"
AVANCADO = "avancado"

# A ordem é a régua: cada plano só é comparado com o seguinte.
ORDEM = (ESSENCIAL, PROFISSIONAL, AVANCADO)

PLANOS = {
    ESSENCIAL: Plano(
        chave=ESSENCIAL,
        nome="Essencial",
        assentos=3,
        mensal=29000,
        adicional_mensal=9000,
        # Zero convidado é deliberado: mostrar trabalho para quem está de fora é
        # o motivo mais comum de subir de plano, e é aqui que isso se compra.
        convidados_por_assento=0,
        recursos={RECURSO_ANALYTICS: False, RECURSO_API_PUBLICA: False, RECURSO_WEBHOOKS: False},
        limites={LIMITE_PROPRIEDADES: 5, LIMITE_AUTOMACOES: 2},
    ),
    PROFISSIONAL: Plano(
        chave=PROFISSIONAL,
        nome="Profissional",
        assentos=10,
        mensal=69000,
        adicional_mensal=6500,
        convidados_por_assento=2,
        recursos={RECURSO_ANALYTICS: True, RECURSO_API_PUBLICA: True, RECURSO_WEBHOOKS: True},
        limites={LIMITE_PROPRIEDADES: 30, LIMITE_AUTOMACOES: None},
    ),
    AVANCADO: Plano(
        chave=AVANCADO,
        nome="Avançado",
        assentos=30,
        mensal=159000,
        adicional_mensal=4900,
        convidados_por_assento=5,
        # O Avançado vende escala, não funcionalidade: libera o mesmo que o
        # Profissional. Espremer um recurso aqui só para justificá-lo tiraria
        # valor do plano do meio, que é o alvo. Ver ADR 0021.
        recursos={RECURSO_ANALYTICS: True, RECURSO_API_PUBLICA: True, RECURSO_WEBHOOKS: True},
        limites={LIMITE_PROPRIEDADES: 30, LIMITE_AUTOMACOES: None},
    ),
}

CHAVES = tuple(PLANOS)


def plano(chave: str) -> Plano:
    try:
        return PLANOS[chave]
    except KeyError:
        raise ValueError(f"Plano desconhecido: {chave!r}. Conhecidos: {', '.join(CHAVES)}") from None


def existe(chave: str) -> bool:
    return chave in PLANOS


def seguinte(chave: str) -> Optional[Plano]:
    """O próximo degrau da régua, ou `None` no topo."""
    posicao = ORDEM.index(plano(chave).chave)
    if posicao + 1 >= len(ORDEM):
        return None
    return PLANOS[ORDEM[posicao + 1]]


def planos_com(recurso: str) -> tuple:
    """Quais planos liberam o recurso — é o que a recusa devolve ao cliente.

    Recusar sem dizer onde está o que ele quer transforma a trava em parede.
    """
    if recurso not in RECURSOS:
        raise ValueError(f"Recurso desconhecido: {recurso!r}. Conhecidos: {', '.join(RECURSOS)}")
    return tuple(chave for chave in ORDEM if PLANOS[chave].inclui(recurso))


def valor_do_ciclo(chave: str, ciclo: str, assentos_extras: int = 0) -> int:
    """O que se cobra num ciclo: a base mais os assentos que passaram do teto."""
    if ciclo not in CICLOS:
        raise ValueError(f"Ciclo desconhecido: {ciclo!r}. Conhecidos: {', '.join(CICLOS)}")
    if assentos_extras < 0:
        raise ValueError("Assentos extras não podem ser negativos")
    escolhido = plano(chave)
    return escolhido.preco(ciclo) + escolhido.adicional(ciclo) * assentos_extras


def convidados_permitidos(chave: str, assentos_pagos: int) -> int:
    """Cota de convidado: múltiplo dos assentos pagos, incluídos e extras."""
    if assentos_pagos < 0:
        raise ValueError("Assentos pagos não podem ser negativos")
    return plano(chave).convidados_por_assento * assentos_pagos


def copia_para_contrato(chave: str, ciclo: str, gratuita: bool = False) -> dict:
    """Os campos que a assinatura guarda como **cópia** do catálogo.

    Reajustar a tabela não pode reescrever contrato assinado (ADR 0021, decisão
    11), então o que vale para o cliente é o que foi copiado no dia em que ele
    contratou — não o que este arquivo diz hoje.

    `gratuita` zera o preço e mantém a capacidade: é a forma da cortesia, que
    não cobra mas precisa saber quantos assentos e quantos convidados libera.
    """
    escolhido = plano(chave)
    if ciclo not in CICLOS:
        raise ValueError(f"Ciclo desconhecido: {ciclo!r}. Conhecidos: {', '.join(CICLOS)}")
    return {
        "plano": escolhido.chave,
        "ciclo": ciclo,
        "assentos_incluidos": escolhido.assentos,
        "convidados_por_assento": escolhido.convidados_por_assento,
        "valor_base": 0 if gratuita else escolhido.preco(ciclo),
        "valor_por_assento": 0 if gratuita else escolhido.adicional(ciclo),
    }


def incoerencias() -> list:
    """As duas regras que o catálogo tem de obedecer, em forma de conferência.

    Existe para ser chamada pelo teste. É a razão de o catálogo morar em código:
    trocar um número e quebrar a régua reprova a suíte, em vez de virar tabela
    publicada.

    1. **Acumular excedente tem de custar mais que subir de plano.** Sem isso a
       régua de três níveis vira decoração: ninguém sobe, todo mundo estica.
    2. **Preço por assento e adicional caem a cada nível.** É o que faz o plano
       maior ser vantagem, e não só um teto mais alto pelo mesmo preço.
    """
    problemas = []

    for chave in ORDEM:
        atual = PLANOS[chave]
        proximo = seguinte(chave)
        if proximo is None:
            continue

        esticado = atual.mensal + atual.adicional_mensal * (proximo.assentos - atual.assentos)
        if esticado <= proximo.mensal:
            problemas.append(
                f"{atual.nome} esticado até {proximo.assentos} assentos custa {esticado} centavos, "
                f"e {proximo.nome} custa {proximo.mensal}: acumular excedente ficou mais barato que subir"
            )

        if proximo.por_assento >= atual.por_assento:
            problemas.append(
                f"O assento do {proximo.nome} ({proximo.por_assento}) não é mais barato "
                f"que o do {atual.nome} ({atual.por_assento})"
            )

        if proximo.adicional_mensal >= atual.adicional_mensal:
            problemas.append(
                f"O adicional do {proximo.nome} ({proximo.adicional_mensal}) não é mais barato "
                f"que o do {atual.nome} ({atual.adicional_mensal})"
            )

    return problemas
