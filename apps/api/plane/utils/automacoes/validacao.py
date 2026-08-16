# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Validação de uma regra na hora de salvar (ADR 0012).

O critério para tudo o que está aqui: **regra malformada tem de ser recusada
com uma frase**, e não descoberta depois como silêncio no registro de
execuções. Uma automação que nunca dispara é indistinguível, para quem a
escreveu, de uma automação que dispara e não faz nada — e as duas são
indistinguíveis de "o produto está quebrado". Cada validação abaixo existe para
transformar um desses silêncios em uma mensagem.

A condição é validada montando o `Q` de verdade contra o `IssueFilterSet`: é a
mesma prova que o quadro faz a cada carregamento, então uma árvore que passa
aqui é uma árvore que o motor consegue executar.
"""

# Python imports
import re

# Third party imports
from rest_framework import serializers

# Module imports
from plane.db.models import Issue, IssueProperty, Label, State, User
from plane.utils.automacoes.acoes import ACOES
from plane.utils.automacoes.condicao import CondicaoInvalida, aplicar
from plane.utils.automacoes.gatilhos import CAMPO_DO_HISTORICO
from plane.utils.issue_properties import PREFIXO_DE_FILTRO

#: Campos que podem ser gatilho de "campo alterado".
#:
#: São os do histórico mais as propriedades personalizadas, que entram por
#: prefixo porque o nome do campo é um id em tempo de execução.
CAMPOS_DE_GATILHO = set(CAMPO_DO_HISTORICO.values())

PRIORIDADES = {"urgent", "high", "medium", "low", "none"}
MODOS_DE_LISTA = {"add", "remove", "replace"}

#: "08:00", "8:5" — hora e minuto, com ou sem zero à esquerda.
HORARIO = re.compile(r"^\d{1,2}:\d{1,2}$")

#: As ações que dão à luz. Só existem em gatilho de EVENTO — ver `validar_acoes`.
ACOES_DE_CRIACAO = {"create_work_item", "create_subtasks"}

#: Um checklist é um checklist, não um projeto. Vinte é folgado para o uso real
#: e barra a lista colada de mil linhas que viraria mil tarefas num disparo.
TETO_DE_SUBTAREFAS_POR_REGRA = 20


def _erro(mensagem):
    raise serializers.ValidationError(mensagem)


def validar_gatilho(trigger_type, trigger_config, gatilhos_aceitos, project_id):
    """O "quando" descreve um evento que pode acontecer?"""
    if trigger_type not in gatilhos_aceitos:
        _erro({"trigger_type": f"Gatilho '{trigger_type}' não está disponível."})

    config = trigger_config or {}

    if trigger_type == "scheduled":
        frequencia = config.get("frequency", "daily")
        if frequencia not in ("daily", "weekly"):
            _erro({"trigger_config": "A frequência precisa ser diária ou semanal."})
        horario = config.get("time") or "08:00"
        if not HORARIO.match(str(horario)):
            _erro({"trigger_config": "O horário precisa estar no formato HH:MM."})
        dias = config.get("weekdays") or []
        if not isinstance(dias, list) or any(dia not in range(7) for dia in dias):
            _erro({"trigger_config": "Os dias da semana precisam ser números de 0 (domingo) a 6."})
        # Semanal sem dia escolhido é lida como "todos os dias" no cálculo, e
        # não como "nenhum" — o contrário seria uma regra que nunca roda.
        return {"frequency": frequencia, "time": str(horario), "weekdays": dias}

    if trigger_type != "field_changed":
        return {}

    campo = config.get("field")
    if not campo:
        _erro({"trigger_config": "Escolha o campo que dispara a regra."})

    if campo.startswith(PREFIXO_DE_FILTRO):
        propriedade_id = campo[len(PREFIXO_DE_FILTRO) :]
        if not IssueProperty.objects.filter(pk=propriedade_id, project_id=project_id, is_active=True).exists():
            _erro({"trigger_config": "A propriedade escolhida não existe neste projeto."})
    elif campo not in CAMPOS_DE_GATILHO:
        _erro({"trigger_config": f"O campo '{campo}' não pode disparar uma regra."})

    # "de" e "para" são listas. Um valor solto aqui viraria uma comparação que
    # nunca casa, e a regra ficaria muda — exatamente o que este arquivo evita.
    for ponta in ("from", "to"):
        valor = config.get(ponta)
        if valor is not None and not isinstance(valor, list):
            _erro({"trigger_config": f"'{ponta}' precisa ser uma lista de valores."})

    return {
        "field": campo,
        "from": config.get("from") or [],
        "to": config.get("to") or [],
    }


def validar_condicao(condicao):
    """O "se" é uma árvore que o filtro do produto consegue executar?"""
    if not condicao:
        return None
    if not isinstance(condicao, dict):
        _erro({"condition": "A condição precisa ser um objeto."})
    try:
        # Monta o `Q` de verdade contra um queryset vazio: valida a estrutura,
        # a profundidade e a allowlist de campos sem tocar em dado nenhum.
        aplicar(Issue.objects.none(), condicao)
    except CondicaoInvalida as erro:
        _erro({"condition": f"Condição inválida: {erro}"})
    return condicao


def _validar_acao(acao, project_id):
    if not isinstance(acao, dict):
        _erro({"actions": "Cada ação precisa ser um objeto."})

    tipo = acao.get("type")
    if tipo not in ACOES:
        _erro({"actions": f"Ação '{tipo}' não existe."})

    config = acao.get("config") or {}
    if not isinstance(config, dict):
        _erro({"actions": f"A configuração da ação '{tipo}' precisa ser um objeto."})

    if tipo == "set_state":
        if not State.objects.filter(pk=config.get("state_id") or None, project_id=project_id).exists():
            _erro({"actions": "Escolha um estado deste projeto."})

    elif tipo == "set_priority":
        if config.get("priority") not in PRIORIDADES:
            _erro({"actions": "Escolha uma prioridade válida."})

    elif tipo == "set_assignees":
        modo = config.get("mode", "add")
        if modo not in MODOS_DE_LISTA:
            _erro({"actions": "Modo de responsável inválido."})
        pessoas = config.get("assignees") or []
        especiais = config.get("especiais") or []
        if not pessoas and not especiais and modo != "replace":
            _erro({"actions": "Escolha quem será responsável."})
        if pessoas and User.objects.filter(pk__in=pessoas).count() != len(set(pessoas)):
            _erro({"actions": "Um dos responsáveis escolhidos não existe."})

    elif tipo == "set_labels":
        modo = config.get("mode", "add")
        if modo not in MODOS_DE_LISTA:
            _erro({"actions": "Modo de etiqueta inválido."})
        etiquetas = config.get("labels") or []
        if not etiquetas and modo != "replace":
            _erro({"actions": "Escolha ao menos uma etiqueta."})
        if etiquetas and Label.objects.filter(pk__in=etiquetas, project_id=project_id).count() != len(set(etiquetas)):
            _erro({"actions": "Uma das etiquetas escolhidas não é deste projeto."})

    elif tipo == "set_date":
        if config.get("field") not in ("start_date", "target_date"):
            _erro({"actions": "Escolha a data de início ou a de vencimento."})
        if config.get("date_mode", "relative") == "relative":
            dias = config.get("offset_days")
            if not isinstance(dias, int):
                _erro({"actions": "Informe em quantos dias a data cai."})
        elif not config.get("date"):
            _erro({"actions": "Informe a data."})

    elif tipo == "set_property":
        if not IssueProperty.objects.filter(
            pk=config.get("property_id") or None, project_id=project_id, is_active=True
        ).exists():
            _erro({"actions": "A propriedade escolhida não existe neste projeto."})

    elif tipo == "add_comment":
        if not (config.get("text") or "").strip():
            _erro({"actions": "Escreva o texto do comentário."})

    elif tipo == "notify":
        pessoas = config.get("users") or []
        especiais = config.get("especiais") or []
        if not pessoas and not especiais:
            _erro({"actions": "Escolha quem será avisado."})
        if pessoas and User.objects.filter(pk__in=pessoas).count() != len(set(pessoas)):
            _erro({"actions": "Uma das pessoas escolhidas não existe."})

    elif tipo == "create_work_item":
        if not (config.get("name") or "").strip():
            _erro({"actions": "Dê um nome à tarefa que será criada."})

    elif tipo == "create_subtasks":
        nomes = [str(item).strip() for item in (config.get("names") or []) if str(item).strip()]
        if not nomes:
            _erro({"actions": "Liste ao menos uma subtarefa."})
        if len(nomes) > TETO_DE_SUBTAREFAS_POR_REGRA:
            _erro({"actions": f"No máximo {TETO_DE_SUBTAREFAS_POR_REGRA} subtarefas por regra."})

    # `archive` e `add_to_cycle` não têm configuração: a primeira arquiva a
    # tarefa que disparou, a segunda usa o ciclo ATIVO — um id de ciclo fixo
    # envelheceria na virada do próximo.

    return {"type": tipo, "config": config}


def validar_acoes(acoes, project_id, trigger_type=None):
    """O "então" tem pelo menos uma ação, e todas são executáveis?

    Regra sem ação é o silêncio mais caro de todos: ela dispara, casa a
    condição, escreve no registro que executou — e não faz nada.
    """
    if not isinstance(acoes, list) or not acoes:
        _erro({"actions": "A regra precisa de ao menos uma ação."})

    validadas = [_validar_acao(acao, project_id) for acao in acoes]

    # Agendado + criar É recorrência. Oferecer as duas coisas seria oferecer dois
    # caminhos para o mesmo destino, e o pior deles: Tarefas recorrentes tem
    # calendário, antecedência, controle de ocorrência aberta e pulo, nada disso
    # cabendo numa ação de automação. A combinação não existe — e a recusa é aqui,
    # ao salvar, e não num aviso que a pessoa fecha sem ler.
    if trigger_type == "scheduled":
        criacao = [acao["type"] for acao in validadas if acao["type"] in ACOES_DE_CRIACAO]
        if criacao:
            _erro(
                {
                    "actions": (
                        "Criar tarefa por horário é o que as Tarefas recorrentes fazem, com calendário e "
                        "controle de ocorrência aberta. Use uma regra de evento, ou crie uma tarefa recorrente."
                    )
                }
            )

    return validadas
