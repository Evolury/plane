# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""A varredura que põe cada tarefa na etapa que o vencimento dela indica.

Evolury: ADR 0014.

A decisão que organiza tudo: **a etapa é a leitura visual do vencimento**. Se ela
fosse um lugar independente da data, a pessoa arrastaria uma tarefa para "Em
Andamento" e a madrugada a puxaria de volta — todo dia. Significando a data,
pessoa e varredura concordam por construção.

Três coisas aqui se implementam ao contrário com facilidade, e o sintoma seria
silencioso:

* **o opt-out é de SAÍDA, nunca de chegada.** A etapa de vencidas é destino das
  vencidas E a que mais se quer travar; bloquear a chegada a deixaria vazia para
  sempre;
* **a varredura NÃO carimba data.** Tarefa sem vencimento vai para hoje e
  continua sem vencimento — a ausência é o lembrete;
* **balde sem etapa marcada não move ninguém.** As quatro marcações são
  opcionais, ao contrário da etapa padrão.
"""

from datetime import timedelta
from zoneinfo import ZoneInfo

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from plane.db.models import Issue, StateGroup, WorkStage, WorkStageIssue, WorkStageSweep
from plane.utils.exception_logger import log_exception

#: Balde → campo que marca a etapa de destino.
MARCACAO_DO_BALDE = {
    "vencidas": "is_overdue",
    "hoje": "is_due_today",
    "amanha": "is_due_tomorrow",
    "depois": "is_due_later",
}

#: Grupos que a varredura nunca toca.
#:
#: Uma tarefa concluída ontem está tecnicamente vencida, e movê-la para
#: "vencidas" seria ressuscitar trabalho terminado. Fica como trava do motor, e
#: não como caixa que alguém precisa achar e marcar.
GRUPOS_INTOCAVEIS = (StateGroup.COMPLETED.value, StateGroup.CANCELLED.value)


def balde_da_tarefa(vencimento, hoje):
    """Em que balde esta data cai, do ponto de vista de `hoje`.

    Sem vencimento vai para hoje, e isso é conceito, não caso de borda: **tarefa
    sem vencimento é tarefa esquecida**, e mandá-la para hoje é pô-la na frente
    de quem pode decidir. Ela continua sem data — quem a carimbasse apagaria o
    lembrete no mesmo gesto que o criou.
    """
    if vencimento is None:
        return "hoje"
    if vencimento < hoje:
        return "vencidas"
    if vencimento == hoje:
        return "hoje"
    if vencimento == hoje + timedelta(days=1):
        return "amanha"
    return "depois"


def _destinos(etapas):
    """Balde → etapa marcada, para os baldes que têm uma."""
    destinos = {}
    for balde, marcacao in MARCACAO_DO_BALDE.items():
        etapa = next((e for e in etapas if getattr(e, marcacao)), None)
        if etapa is not None:
            destinos[balde] = etapa
    return destinos


def varrer(workspace_id, owner_id, hoje):
    """Move as tarefas desta pessoa, neste workspace, para os baldes de `hoje`.

    Idempotente: recalcula onde cada tarefa deveria estar, então rodar duas vezes
    no mesmo dia não muda nada. Devolve quantas mudaram de etapa.
    """
    etapas = list(WorkStage.objects.filter(workspace_id=workspace_id, owner_id=owner_id))
    if not etapas:
        return 0

    destinos = _destinos(etapas)
    if not destinos:
        return 0

    padrao = next((e for e in etapas if e.is_default), None)
    travadas = {e.id for e in etapas if e.automation_disabled}

    # As tarefas atribuídas a esta pessoa, fora dos grupos intocáveis. O estado
    # pode ser nulo, e nesse caso a tarefa entra: quem não tem estado não está
    # concluída nem cancelada.
    tarefas = (
        Issue.objects.filter(workspace_id=workspace_id, assignees__id=owner_id)
        .filter(Q(state__isnull=True) | ~Q(state__group__in=GRUPOS_INTOCAVEIS))
        .exclude(archived_at__isnull=False)
        .values("id", "target_date")
        .distinct()
    )

    # Onde cada tarefa está hoje. Sem linha aqui, ela pertence implicitamente à
    # etapa padrão — é assim que o overlay funciona desde o ADR 0001.
    associacoes = {
        linha["issue_id"]: linha["stage_id"]
        for linha in WorkStageIssue.objects.filter(workspace_id=workspace_id, owner_id=owner_id).values(
            "issue_id", "stage_id"
        )
    }

    movidas = 0
    with transaction.atomic():
        for tarefa in tarefas:
            atual_id = associacoes.get(tarefa["id"], padrao.id if padrao else None)
            # Etapa travada não SOLTA. Chegar continua podendo — a etapa de
            # vencidas depende disso para existir.
            if atual_id in travadas:
                continue

            destino = destinos.get(balde_da_tarefa(tarefa["target_date"], hoje))
            # Balde sem etapa marcada: a tarefa fica onde está.
            if destino is None or destino.id == atual_id:
                continue
            WorkStageIssue.objects.update_or_create(
                workspace_id=workspace_id,
                owner_id=owner_id,
                issue_id=tarefa["id"],
                defaults={"stage_id": destino.id},
            )
            movidas += 1

    return movidas


def dia_local(user_timezone):
    """O dia de hoje no relógio da pessoa.

    Meia-noite não é um instante: é um instante por fuso. Etapa pessoal é pessoal
    também no relógio (ADR 0006 e 0014).
    """
    try:
        fuso = ZoneInfo(user_timezone or "America/Sao_Paulo")
    except Exception:
        fuso = ZoneInfo("America/Sao_Paulo")
    return timezone.now().astimezone(fuso).date()


def varrer_quem_virou_o_dia():
    """Passa por quem já virou o dia e ainda não foi varrido hoje.

    O marcador não existe para evitar repetição — a varredura é idempotente — e
    sim para **se recuperar sozinha**: worker fora do ar às 00h05 não pode custar
    o dia inteiro de organização de ninguém.
    """
    from plane.db.models import User

    pendentes = (
        WorkStage.objects.filter(
            Q(is_due_today=True) | Q(is_due_tomorrow=True) | Q(is_due_later=True) | Q(is_overdue=True)
        )
        .values_list("workspace_id", "owner_id")
        .distinct()
    )

    fusos = dict(User.objects.filter(pk__in={o for _, o in pendentes}).values_list("pk", "user_timezone"))
    marcadores = {
        (m["workspace_id"], m["owner_id"]): m["ran_on"]
        for m in WorkStageSweep.objects.all().values("workspace_id", "owner_id", "ran_on")
    }

    total = 0
    for workspace_id, owner_id in pendentes:
        try:
            hoje = dia_local(fusos.get(owner_id))
            if marcadores.get((workspace_id, owner_id)) == hoje:
                continue
            varrer(workspace_id, owner_id, hoje)
            WorkStageSweep.objects.update_or_create(
                workspace_id=workspace_id, owner_id=owner_id, defaults={"ran_on": hoje}
            )
            total += 1
        except Exception as erro:
            # Uma pessoa com dado estranho não pode travar a varredura das
            # outras: o laço segue e o erro fica registrado.
            log_exception(erro)
    return total
