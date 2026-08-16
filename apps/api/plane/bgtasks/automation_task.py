# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Execução das automações personalizadas (ADR 0012, F1).

Roda fora do tempo de resposta: `despacho.py` só decide que há algo a avaliar e
joga para cá. Aqui acontecem as três etapas do padrão ECA, nesta ordem e sem
misturar — casar o gatilho, provar a condição, executar as ações.

Toda execução vira uma linha de `AutomationRun`, inclusive a que parou na
condição. Isso não é excesso de zelo: uma condição que não casa para em
SILÊNCIO por definição, e "por que a minha regra não rodou?" é a pergunta
número um de quem usa esse tipo de recurso em qualquer produto. Sem o registro,
a resposta honesta seria "não sei".
"""

# Python imports
import time
from datetime import timedelta

# Django imports
from django.db.models import F
from django.utils import timezone

# Third party imports
from celery import shared_task

# Module imports
from plane.db.models import (
    Automation,
    AutomationRun,
    AutomationRunStatus,
    AutomationTrigger,
    Issue,
)
from plane.utils.automacoes import acoes as registro_de_acoes
from plane.utils.automacoes.ator import ator_da_automacao
from plane.utils.automacoes.condicao import CondicaoInvalida, casa
from plane.utils.automacoes.gatilhos import automacao_casa
from plane.utils.exception_logger import log_exception

#: Teto de execuções por regra, por hora.
#:
#: É o freio de emergência, não o mecanismo principal — as travas de laço são o
#: teto de profundidade e a regra que não responde a si mesma. Este existe para
#: o caso que nenhuma das duas prevê: um ciclo entre três regras diferentes, ou
#: uma edição em massa de dez mil tarefas. Ao estourar, a regra se DESLIGA e
#: grava o motivo: uma regra que emudece sem explicação é pior do que uma regra
#: que erra.
TETO_POR_HORA = 200

#: Tipo de evento → gatilho correspondente.
GATILHO_DO_EVENTO = {
    "criada": AutomationTrigger.WORK_ITEM_CREATED,
    "alterada": AutomationTrigger.FIELD_CHANGED,
    "comentada": AutomationTrigger.COMMENT_ADDED,
}


def _estourou_o_teto(automacao) -> bool:
    uma_hora_atras = timezone.now() - timedelta(hours=1)
    return AutomationRun.objects.filter(automation=automacao, created_at__gte=uma_hora_atras).count() >= TETO_POR_HORA


def _desligar(automacao, motivo):
    automacao.is_active = False
    automacao.disabled_reason = motivo
    automacao.save(update_fields=["is_active", "disabled_reason", "updated_at"])


def _registrar(automacao, tarefa, status, evento, resultados, erro, comeco, profundidade):
    AutomationRun.objects.create(
        automation=automacao,
        workspace_id=automacao.workspace_id,
        issue=tarefa,
        status=status,
        trigger_summary=evento,
        actions_result=resultados,
        error=erro or "",
        duration_ms=int((time.monotonic() - comeco) * 1000),
        depth=profundidade,
    )


def executar_automacao(automacao, tarefa, evento, profundidade=0):
    """Prova a condição e, se ela valer, executa as ações em ordem.

    Devolve o status gravado, para que o chamador em lote possa contar.
    """
    comeco = time.monotonic()

    try:
        if not casa(tarefa.id, automacao.condition):
            _registrar(automacao, tarefa, AutomationRunStatus.SKIPPED, evento, [], "", comeco, profundidade)
            return AutomationRunStatus.SKIPPED
    except CondicaoInvalida as erro:
        # A árvore não vale mais — quase sempre porque alguém apagou o campo que
        # a regra usava. É falha DA REGRA, e precisa aparecer como tal; tratá-la
        # como "não casou" esconderia uma regra quebrada atrás de um resultado
        # que parece normal.
        _registrar(
            automacao, tarefa, AutomationRunStatus.FAILED, evento, [], f"condição inválida: {erro}", comeco, profundidade
        )
        return AutomationRunStatus.FAILED

    contexto = {
        "ator_id": ator_da_automacao(automacao.workspace_id).id,
        "automacao": automacao,
        "evento": evento,
        "profundidade": profundidade,
    }

    resultados = []
    for acao in automacao.actions or []:
        if not isinstance(acao, dict):
            continue
        # A tarefa é relida entre ações porque a anterior pode tê-la mudado:
        # "mude para Concluído e depois grave a data de conclusão" precisa ver
        # o estado novo, não o que estava em memória quando o lote começou.
        tarefa.refresh_from_db()
        resultados.append(
            registro_de_acoes.executar(acao.get("type"), tarefa, acao.get("config"), contexto)
        )

    houve_erro = any(resultado["status"] == registro_de_acoes.ERRO for resultado in resultados)
    status = AutomationRunStatus.FAILED if houve_erro else AutomationRunStatus.MATCHED
    _registrar(automacao, tarefa, status, evento, resultados, "", comeco, profundidade)

    Automation.objects.filter(pk=automacao.pk).update(
        last_run_at=timezone.now(),
        run_count=F("run_count") + 1,
        error_count=F("error_count") + (1 if houve_erro else 0),
    )
    return status


@shared_task
def avaliar_automacoes(evento, profundidade=0):
    """As regras do projeto que respondem a este evento."""
    try:
        gatilho = GATILHO_DO_EVENTO.get(evento.get("tipo"))
        if gatilho is None:
            return

        tarefa = Issue.objects.filter(pk=evento["issue_id"]).first()
        if tarefa is None:
            return

        automacoes = Automation.objects.filter(
            project_id=evento["project_id"], is_active=True, trigger_type=gatilho
        )

        for automacao in automacoes:
            if not automacao_casa(automacao, evento):
                continue
            if _estourou_o_teto(automacao):
                _desligar(
                    automacao,
                    f"desligada automaticamente: passou de {TETO_POR_HORA} execuções em uma hora",
                )
                continue
            executar_automacao(automacao, tarefa, evento, profundidade)
    except Exception as erro:
        log_exception(erro)
