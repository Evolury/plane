# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""O relógio da regra agendada (ADR 0012, F2).

Uma agenda simples de propósito: diária ou semanal, num horário. Não há mensal
nem "a cada N" porque a regra agendada de automação responde a uma pergunta
diferente da recorrência (ADR 0010) — ali a pergunta é "quando nasce a próxima
ocorrência?", e ela precisa de calendário; aqui é "com que frequência eu varro
o quadro?", e varrer todo dia de manhã cobre quase tudo.

O horário é local ao **projeto** (ADR 0006), e não ao servidor. "Toda manhã às
8h" tem de ser 8h de quem lê o quadro; guardar em UTC e mostrar convertido daria
uma regra que muda de horário sozinha entre um país e outro.

Duas garantias que o cálculo precisa dar, e que a recorrência já aprendeu na
prática:

1. **Atraso não acumula.** Se o job ficou fora do ar por dois dias, a rodada
   seguinte roda UMA vez e reagenda para a frente — não uma vez por dia perdido.
2. **A próxima é sempre no futuro.** Uma data no passado faria o job rodar em
   laço a cada tique até alcançar o presente.
"""

# Python imports
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

# Django imports
from django.utils import timezone

UTC = ZoneInfo("UTC")

#: 0 = domingo, como o resto do produto (ADR 0005) e como `Date.getDay`.
DIAS_DA_SEMANA = (0, 1, 2, 3, 4, 5, 6)


def _fuso(automacao):
    return ZoneInfo(automacao.project.timezone or "America/Sao_Paulo")


def _horario(config):
    """"08:00" → `time(8, 0)`. Sem horário, a varredura é às 8h."""
    bruto = (config or {}).get("time") or "08:00"
    try:
        hora, minuto = (int(parte) for parte in str(bruto).split(":")[:2])
        return time(hour=hora % 24, minute=minuto % 60)
    except (ValueError, TypeError):
        return time(hour=8, minute=0)


def _dias(config):
    """Os dias escolhidos na semanal. Vazio quer dizer todos — nunca nenhum.

    "Nenhum" seria uma regra que nunca roda, e regra muda é o defeito que este
    recurso mais precisa evitar.
    """
    escolhidos = [int(dia) for dia in (config or {}).get("weekdays") or [] if str(dia).lstrip("-").isdigit()]
    validos = [dia for dia in escolhidos if dia in DIAS_DA_SEMANA]
    return validos or list(DIAS_DA_SEMANA)


def _dia_da_semana(momento):
    """`datetime.weekday()` conta de segunda; o produto conta de domingo."""
    return (momento.weekday() + 1) % 7


def proxima_execucao(automacao, depois_de=None):
    """Quando esta regra deve rodar pela próxima vez, em UTC.

    Devolve `None` para regra que não é agendada — quem a acorda é o evento.
    """
    from plane.db.models import AutomationTrigger

    if automacao.trigger_type != AutomationTrigger.SCHEDULED:
        return None

    config = automacao.trigger_config or {}
    fuso = _fuso(automacao)
    agora = (depois_de or timezone.now()).astimezone(fuso)
    horario = _horario(config)
    semanal = (config.get("frequency") or "daily") == "weekly"
    dias = _dias(config) if semanal else list(DIAS_DA_SEMANA)

    # Começa hoje e anda no máximo uma semana: com sete dias sempre há um dia
    # válido, porque a lista vazia já virou "todos".
    candidato = datetime.combine(agora.date(), horario, tzinfo=fuso)
    for _ in range(8):
        if candidato > agora and _dia_da_semana(candidato) in dias:
            return candidato.astimezone(UTC)
        candidato += timedelta(days=1)
    return None


def reagendar(automacao, depois_de=None):
    """Grava o próximo horário. É o que faz o job enxergar a regra."""
    from plane.db.models import Automation

    proxima = proxima_execucao(automacao, depois_de)
    Automation.objects.filter(pk=automacao.pk).update(next_run_at=proxima)
    automacao.next_run_at = proxima
    return proxima
