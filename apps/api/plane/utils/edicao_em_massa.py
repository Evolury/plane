# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Preencher campos de muitas tarefas de uma vez (ADR 0019).

O cliente disto já existia inteiro no repositório — serviço, store, tipo do
payload e até as mensagens de erro traduzidas. O que a edição Community não
tinha era o servidor: `bulk-operation-issues` é da edição paga. Aqui ele é
escrito, com o mesmo contrato que o cliente já espera.

**Campo de lista tem MODO, e o padrão é acrescentar.** Foi a lição mais cara
desta pesquisa: o Jira substituía por padrão, e o efeito foi tanta gente
apagando etiquetas achando que estava somando que virou chamado clássico
(JRA-30729). Hoje o Jira Cloud oferece acrescentar, remover e substituir — é o
que está aqui, com "acrescentar" pré-selecionado. O store do front, aliás, já
somava: a atualização otimista dele faz `uniq([...existente, ...novo])`.

**Responsável não tem modo.** Uma tarefa aqui tem UM responsável (ADR 0016),
garantido por índice único no banco: atribuir em massa é substituir, e somar
seria pedir ao banco uma coisa que ele recusa.

**Ciclo e módulo não passam por aqui.** Os endpoints deles já aceitam lista de
tarefas e já gravam a atividade com o tipo certo (`cycle.activity.created`) —
reescrever isso só criaria um segundo caminho para o mesmo destino.
"""

#: Teto por requisição, igual ao da exclusão em massa (ADR 0018).
TETO_DE_EDICAO_EM_MASSA = 500

#: Campos que são coluna da tarefa: escrita em bloco, sem tabela de ligação.
CAMPOS_SIMPLES = ("state_id", "priority", "start_date", "target_date", "estimate_point")

#: Campos que são tabela de ligação e aceitam modo.
CAMPOS_DE_LISTA = ("label_ids", "assignee_ids")

#: Os modos de um campo de lista.
MODOS = ("add", "remove", "replace")

#: O padrão. Ver o cabeçalho: somar é o que a pessoa espera, e substituir sem
#: aviso é o que faz alguém perder etiqueta sem perceber.
MODO_PADRAO = "add"


def aplicar_modo(atuais, pedidos, modo):
    """O valor final de um campo de lista, para UMA tarefa.

    Devolve lista sem repetição e com ordem estável — ordem instável faria o
    histórico registrar mudança onde não houve nenhuma.
    """
    atuais = [str(item) for item in (atuais or [])]
    pedidos = [str(item) for item in (pedidos or [])]

    if modo == "replace":
        final = pedidos
    elif modo == "remove":
        fora = set(pedidos)
        final = [item for item in atuais if item not in fora]
    else:  # add
        final = atuais + [item for item in pedidos if item not in set(atuais)]

    vistos = set()
    saida = []
    for item in final:
        if item not in vistos:
            vistos.add(item)
            saida.append(item)
    return saida


def modo_de(modos, campo):
    """O modo pedido para um campo, ou o padrão. Modo desconhecido não passa."""
    modo = (modos or {}).get(campo, MODO_PADRAO)
    return modo if modo in MODOS else MODO_PADRAO


def datas_finais(issue, propriedades):
    """(início, vencimento) como ficarão nesta tarefa.

    O que não foi pedido continua o que era: validar a data pedida contra o
    vazio, em vez de contra a data que a tarefa já tem, deixaria passar um
    início posterior a um vencimento que ninguém tocou.
    """
    inicio = propriedades["start_date"] if "start_date" in propriedades else issue.start_date
    vencimento = propriedades["target_date"] if "target_date" in propriedades else issue.target_date
    return inicio, vencimento


def _texto(data):
    return data.isoformat() if hasattr(data, "isoformat") else (str(data) if data else None)


def erro_de_data(issue, propriedades):
    """Qual data quebrou a regra nesta tarefa — ou `None`.

    Devolve o campo pedido, e não "a data", porque a mensagem que o usuário lê
    é diferente para cada um: uma fala do início, a outra do vencimento. As duas
    já estão traduzidas desde antes deste endpoint existir.
    """
    inicio, vencimento = datas_finais(issue, propriedades)
    inicio, vencimento = _texto(inicio), _texto(vencimento)
    if not inicio or not vencimento or inicio <= vencimento:
        return None
    return "start_date" if "start_date" in propriedades else "target_date"
