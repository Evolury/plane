# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""A porta de entrada do motor de automações (ADR 0012).

É chamada de dentro de `issue_activity`, logo depois de as linhas de histórico
serem gravadas. Ali é o único lugar do produto por onde passam TODAS as
mudanças de tarefa: são 124 chamadas de `issue_activity.delay` em 24 arquivos,
e todas caem na mesma tarefa Celery. Um ponto de enxerto, não 124 — e nenhum
caminho novo escapa por esquecimento.

Este módulo é caminho quente: roda em toda edição de toda tarefa, inclusive nas
instalações que não usam automação nenhuma. Por isso ele desiste cedo e barato,
e por isso ele NÃO levanta exceção: falha de automação não pode derrubar o
registro de histórico de quem estava só arrastando um cartão.
"""

# Django imports
from django.utils import timezone

# Module imports
from plane.db.models import Automation, AutomationTrigger, IssueActivity
from plane.utils.automacoes.gatilhos import (
    TETO_DE_PROFUNDIDADE,
    mudanca_de_propriedade,
    mudancas_das_atividades,
)
from plane.utils.exception_logger import log_exception
from plane.utils.tempo_real import publicar_propriedade

#: Tipo de atividade → tipo de evento, no vocabulário da regra.
#:
#: O que não está aqui não aciona automação: rascunho ("issue_draft.*"),
#: reação, voto, anexo, link, relação. Rascunho fica de fora por decisão de
#: produto — automatizar o que ainda não foi publicado surpreende quem estava
#: só escrevendo.
TIPO_DE_EVENTO = {
    "issue.activity.created": "criada",
    "issue.activity.updated": "alterada",
    "comment.activity.created": "comentada",
}

#: Gatilhos que um evento pode acordar. A agendada nunca entra por aqui.
GATILHOS_POR_EVENTO = {
    "criada": [AutomationTrigger.WORK_ITEM_CREATED],
    "alterada": [AutomationTrigger.FIELD_CHANGED],
    "comentada": [AutomationTrigger.COMMENT_ADDED],
}


def _linha_para_dicionario(linha):
    return {
        "verb": linha.verb,
        "field": linha.field,
        "old_value": linha.old_value,
        "new_value": linha.new_value,
        "old_identifier": str(linha.old_identifier) if linha.old_identifier else None,
        "new_identifier": str(linha.new_identifier) if linha.new_identifier else None,
    }


def despachar_atividades(
    tipo,
    issue_id,
    project_id,
    actor_id,
    linhas,
    automacao_origem=None,
    profundidade=0,
    de_recorrencia=False,
):
    """Decide se há o que avaliar e, havendo, joga para a fila.

    A avaliação em si NÃO acontece aqui: condição é consulta ao banco e ação é
    escrita, e nenhuma das duas pode entrar no tempo de resposta de quem mudou
    o cartão. O que acontece aqui é só o descarte barato.
    """
    try:
        # O encadeamento tem fim. Passou do teto, para — sem registrar, porque
        # quem precisa saber é a regra que chegou perto, e ela já registrou.
        if profundidade > TETO_DE_PROFUNDIDADE:
            return

        evento = TIPO_DE_EVENTO.get(tipo)
        if evento is None or not issue_id or not project_id:
            return

        gatilhos = GATILHOS_POR_EVENTO[evento]
        # A pergunta mais barata primeiro: este projeto tem alguma regra viva
        # para este gatilho? Numa instalação sem automação, o caminho quente
        # termina aqui, num índice.
        if not Automation.objects.filter(
            project_id=project_id, is_active=True, trigger_type__in=gatilhos
        ).exists():
            return

        mudancas = []
        if evento == "alterada":
            mudancas = mudancas_das_atividades([_linha_para_dicionario(linha) for linha in linhas])
            # Edição que não mexeu em nenhum campo que vira gatilho (nome,
            # descrição, estimativa) não tem por que acordar o motor.
            if not mudancas:
                return

        despachar_evento(
            evento=evento,
            issue_id=issue_id,
            project_id=project_id,
            actor_id=actor_id,
            mudancas=mudancas,
            automacao_origem=automacao_origem,
            profundidade=profundidade,
            de_recorrencia=de_recorrencia,
        )
    except Exception as erro:
        log_exception(erro)


def despachar_evento(
    evento, issue_id, project_id, actor_id, mudancas, automacao_origem, profundidade, de_recorrencia=False
):
    """Enfileira a avaliação. Import tardio para não fechar ciclo de importação."""
    from plane.bgtasks.automation_task import avaliar_automacoes

    avaliar_automacoes.delay(
        evento={
            "tipo": evento,
            "issue_id": str(issue_id),
            "project_id": str(project_id),
            "actor_id": str(actor_id) if actor_id else None,
            "mudancas": mudancas,
            "automacao_origem": str(automacao_origem) if automacao_origem else None,
            # Quem nasceu de uma agenda de rotina não é, por padrão, um evento
            # ao qual reagir. Ver `include_recurring` no modelo.
            "de_recorrencia": bool(de_recorrencia),
        },
        profundidade=profundidade,
    )


def registrar_atividade_de_propriedade(
    tarefa,
    propriedade,
    de,
    para,
    actor_id,
    automacao_origem=None,
    profundidade=0,
):
    """Grava a mudança de propriedade no histórico e acorda as regras.

    Mora aqui, e não na view, porque agora tem dois chamadores — a tela e a
    própria automação — e o histórico precisa sair idêntico dos dois.

    Duas chaves para a mesma mudança, de propósito: o histórico recebe o NOME
    da propriedade, que é o que faz sentido para quem lê seis meses depois; a
    regra recebe o ID (`property_<uuid>`), que é o que não quebra quando alguém
    renomeia a propriedade. Casar regra por nome seria deixar um rename
    silencioso desligar automações.
    """
    if de == para:
        return

    IssueActivity.objects.create(
        issue=tarefa,
        actor_id=actor_id,
        verb="updated",
        old_value=de,
        new_value=para,
        field=propriedade.name,
        project_id=tarefa.project_id,
        workspace_id=tarefa.workspace_id,
        comment=f"alterou {propriedade.name} para",
        epoch=int(timezone.now().timestamp()),
    )

    # Evolury: o cartão lê o valor de uma chave própria, do projeto inteiro
    # (ADR 0013, fase 3). Fica ANTES da guarda de automação abaixo: a tela
    # precisa do aviso mesmo num projeto que não tem regra nenhuma.
    publicar_propriedade(issue_id=tarefa.id, project_id=tarefa.project_id, actor_id=actor_id)

    try:
        if profundidade > TETO_DE_PROFUNDIDADE:
            return
        if not Automation.objects.filter(
            project_id=tarefa.project_id,
            is_active=True,
            trigger_type=AutomationTrigger.FIELD_CHANGED,
        ).exists():
            return
        despachar_evento(
            evento="alterada",
            issue_id=tarefa.id,
            project_id=tarefa.project_id,
            actor_id=actor_id,
            mudancas=[mudanca_de_propriedade(propriedade.id, de, para)],
            automacao_origem=automacao_origem,
            profundidade=profundidade,
        )
    except Exception as erro:
        log_exception(erro)
