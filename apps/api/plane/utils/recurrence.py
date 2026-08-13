# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Cálculo das datas de uma tarefa recorrente (ADR 0010).

A agenda mora em campos legíveis no modelo e vira data aqui. Duas ferramentas,
cada uma onde é melhor:

- `dateutil.rrule` para o que é padrão de calendário — semanal com vários dias,
  "última sexta do mês";
- `relativedelta` para o mensal e o anual por dia fixo, porque ele **encurta**
  a data em vez de descartá-la: 31 de janeiro mais um mês é 28 de fevereiro.

Essa diferença é a decisão do ADR 0010. A RFC 5545 manda ignorar data inválida,
então `BYMONTHDAY=31` pula fevereiro, abril, junho, setembro e novembro —
correto para calendário, errado para tarefa: quem pede "todo dia 31" quer dizer
"todo fim de mês", e um silêncio de cinco meses no ano é um defeito que ninguém
relaciona à causa.

Todo cálculo acontece no **fuso do projeto** e sai em UTC, porque "toda segunda
às 8h" não significa nada sem fuso (ADR 0006).
"""

# Python imports
import calendar
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

# Third party imports
from dateutil.relativedelta import relativedelta
from dateutil.rrule import DAILY, FR, MO, MONTHLY, SA, SU, TH, TU, WE, WEEKLY, rrule

# Module imports
from plane.db.models.recurring_work_item import (
    GenerationMode,
    MonthlyMode,
    RecurrenceEndMode,
    RecurrenceFrequency,
)

# O produto conta a semana a partir do domingo (ADR 0005); o dateutil conta a
# partir da segunda. Este mapa é a tradução, e mora em um lugar só.
DIAS_DA_SEMANA = [SU, MO, TU, WE, TH, FR, SA]

LIMITE_DE_BUSCA = 500


def _fuso(regra):
    return ZoneInfo(regra.project.timezone or "America/Sao_Paulo")


def _com_horario(dia: date, regra, fuso) -> datetime:
    return datetime.combine(dia, regra.time_of_day, tzinfo=fuso)


def _dia_valido_no_mes(ano: int, mes: int, dia: int) -> int:
    """Encurta o dia até o último do mês, em vez de descartar a data."""
    return min(dia, calendar.monthrange(ano, mes)[1])


def _datas_por_dia_fixo(regra, fuso, depois_de: datetime):
    """Mensal e anual por dia do mês, com encurtamento.

    Cada ocorrência é calculada a partir da data de início, e não da anterior:
    somar mês a mês faria 31/01 virar 28/02 e depois 28/03, perdendo o 31 que a
    pessoa pediu.
    """
    mensal = regra.frequency == RecurrenceFrequency.MONTHLY
    passo = relativedelta(months=regra.interval) if mensal else relativedelta(years=regra.interval)
    # "Último dia" é dia 31 com o encurtamento que já existe — 31 nunca passa
    # do fim do mês, seja ele 28, 29, 30 ou 31.
    dia_pedido = 31 if regra.monthly_mode == MonthlyMode.LAST_DAY else (regra.day_of_month or regra.start_date.day)
    mes_base = (
        regra.start_date.replace(day=1)
        if mensal
        else regra.start_date.replace(day=1, month=regra.month_of_year or regra.start_date.month)
    )

    for n in range(LIMITE_DE_BUSCA):
        referencia = mes_base + (passo * n)
        dia = _dia_valido_no_mes(referencia.year, referencia.month, dia_pedido)
        momento = _com_horario(date(referencia.year, referencia.month, dia), regra, fuso)
        if momento > depois_de:
            yield momento


def _datas_por_rrule(regra, fuso, depois_de: datetime):
    """O que é padrão de calendário fica com o dateutil."""
    inicio = _com_horario(regra.start_date, regra, fuso)

    if regra.frequency == RecurrenceFrequency.DAILY:
        regra_dateutil = rrule(DAILY, interval=regra.interval, dtstart=inicio)
    elif regra.frequency == RecurrenceFrequency.WEEKLY:
        # `weekday()` do Python conta a partir da segunda; o produto, a partir
        # do domingo. Sem a conversão, uma regra sem dias escolhidos cairia no
        # dia errado.
        padrao = [(regra.start_date.weekday() + 1) % 7]
        dias = [DIAS_DA_SEMANA[d] for d in (regra.weekdays or padrao)]
        regra_dateutil = rrule(WEEKLY, interval=regra.interval, byweekday=dias, dtstart=inicio)
    else:
        # Mensal por posição: "primeira segunda", "última sexta".
        dia = DIAS_DA_SEMANA[regra.weekday_of_month or 0]
        regra_dateutil = rrule(
            MONTHLY,
            interval=regra.interval,
            byweekday=dia(regra.week_of_month or 1),
            dtstart=inicio,
        )

    for momento in regra_dateutil:
        if momento > depois_de:
            yield momento


def _candidatas(regra, depois_de: datetime):
    fuso = _fuso(regra)
    depois_de_local = depois_de.astimezone(fuso)

    por_dia_fixo = regra.frequency == RecurrenceFrequency.YEARLY or (
        regra.frequency == RecurrenceFrequency.MONTHLY and regra.monthly_mode != MonthlyMode.WEEKDAY_OF_MONTH
    )
    gerador = _datas_por_dia_fixo if por_dia_fixo else _datas_por_rrule
    # Uma regra nunca gera antes da própria data de início.
    inicio = _com_horario(regra.start_date, regra, fuso)
    return (momento for momento in gerador(regra, fuso, depois_de_local) if momento >= inicio)


def alcancou_o_fim(regra, momento: datetime) -> bool:
    """A recorrência acabou — por data ou por contagem."""
    if regra.end_mode == RecurrenceEndMode.ON_DATE and regra.end_date:
        return momento.astimezone(_fuso(regra)).date() > regra.end_date
    if regra.end_mode == RecurrenceEndMode.AFTER_COUNT and regra.end_after_count:
        return regra.occurrences_created >= regra.end_after_count
    return False


def proxima_data(regra, depois_de: datetime) -> datetime | None:
    """A próxima data prevista depois de `depois_de`, em UTC.

    No modo "após a conclusão" não existe agenda: a data sai da conclusão da
    ocorrência anterior, e quem sabe disso é quem trata a conclusão.
    """
    if regra.generation_mode == GenerationMode.AFTER_COMPLETION:
        return None
    if alcancou_o_fim(regra, depois_de):
        return None

    for momento in _candidatas(regra, depois_de):
        if alcancou_o_fim(regra, momento):
            return None
        return momento.astimezone(ZoneInfo("UTC"))
    return None


def proximas_datas(regra, depois_de: datetime, quantidade: int = 3) -> list[datetime]:
    """Pré-visualização: as próximas N datas, em UTC.

    É o que torna uma regra complexa confiável na tela — "próximas: 18/08,
    25/08, 01/09" diz mais do que qualquer rótulo de frequência.
    """
    if regra.generation_mode == GenerationMode.AFTER_COMPLETION:
        return []

    datas = []
    for momento in _candidatas(regra, depois_de):
        if alcancou_o_fim(regra, momento):
            break
        datas.append(momento.astimezone(ZoneInfo("UTC")))
        if len(datas) >= quantidade:
            break
    return datas


def data_apos_conclusao(regra, concluida_em: datetime) -> datetime | None:
    """No modo "após a conclusão", a próxima data conta a partir da conclusão."""
    if regra.generation_mode != GenerationMode.AFTER_COMPLETION:
        return None
    dias = regra.days_after_completion or 1
    fuso = _fuso(regra)
    alvo = concluida_em.astimezone(fuso) + timedelta(days=dias)
    momento = _com_horario(alvo.date(), regra, fuso)
    if alcancou_o_fim(regra, momento):
        return None
    return momento.astimezone(ZoneInfo("UTC"))
