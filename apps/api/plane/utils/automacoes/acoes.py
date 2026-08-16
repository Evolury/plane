# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""O "então" da automação (ADR 0012).

Toda ação escreve pelo MESMO caminho que a tela usa: monta um pedido parcial e
o entrega ao `IssueCreateSerializer`. Não é economia de linhas — é o que
garante que a automação obedeça às mesmas regras que uma pessoa obedece:
responsável precisa ser membro do projeto com permissão de escrita, etiqueta e
estado precisam ser do próprio projeto, data de início não pode passar do
vencimento. Uma automação que pudesse violar isso seria uma porta lateral para
gravar estado inválido, e o defeito só apareceria meses depois, numa tela que
não sabe explicar o que está vendo.

Depois de gravar, cada ação chama `issue_activity` com o robô como ator. É o
que faz o histórico, o webhook e a notificação contarem a mesma história — e é
por onde o encadeamento entre regras acontece, com teto.

O registro `ACOES` é a fonte da verdade sobre o que é uma ação válida: tipo que
não está aqui é recusado na validação da regra. Fase que ainda não chegou
simplesmente não tem entrada no dicionário, e não há um segundo lugar para
esquecer de atualizar.
"""

# Python imports
import json
import uuid
from datetime import timedelta

# Django imports
from django.core.serializers.json import DjangoJSONEncoder
from django.utils import timezone

# Module imports
from plane.db.models import IssueProperty, State
from plane.utils.automacoes.despacho import registrar_atividade_de_propriedade
from plane.utils.issue_properties import (
    ValorInvalido,
    gravar_valor,
    rotulo_do_valor,
    valores_por_tarefa,
)

# O serializer de tarefa e a tarefa Celery de histórico são importados DENTRO
# de `_gravar`, e não aqui em cima, de propósito: este módulo é a camada de
# domínio da automação e é lido pela validação do serializer de automação. Um
# import de topo faria o pacote `plane.app.serializers` depender de si mesmo
# por um caminho longo — o ciclo que o `manage.py check` acusa e que só aparece
# em uma das ordens de importação possíveis.

#: tipo → função. Ver o cabeçalho: é a allowlist de ações.
ACOES = {}

#: Resultados possíveis de uma ação, na linguagem do log.
APLICADA = "aplicada"
#: "Já estava assim." É resultado legítimo e precisa aparecer no registro —
#: é o que explica a regra que roda todo dia e não muda nada, e é o que evita
#: gravar atividade falsa (e disparar webhook falso) por uma escrita que não
#: escreveu.
SEM_EFEITO = "sem_efeito"
ERRO = "erro"


class AcaoInvalida(Exception):
    """A configuração da ação não descreve nada executável."""


def acao(tipo):
    def registrar(fn):
        ACOES[tipo] = fn
        return fn

    return registrar


def _resultado(tipo, status, detalhe=""):
    return {"tipo": tipo, "status": status, "detalhe": detalhe}


def _como_uuid(valor):
    """O id gravado na regra vem como texto; a chave do banco é UUID."""
    try:
        return uuid.UUID(str(valor))
    except (ValueError, AttributeError, TypeError):
        return valor


def _gravar(tarefa, pedido, anterior, contexto, tipo, detalhe):
    """Aplica um pedido parcial e registra a atividade em nome do robô.

    `anterior` traz só as chaves que mudaram, e não um retrato inteiro da
    tarefa: é exatamente o que `update_issue_activity` lê para decidir o que
    escrever no histórico, e um retrato completo abriria espaço para registrar
    mudança em campo que ninguém tocou.
    """
    from plane.app.serializers.issue import IssueCreateSerializer
    from plane.bgtasks.issue_activities_task import issue_activity

    serializer = IssueCreateSerializer(
        tarefa,
        data=pedido,
        partial=True,
        context={"project_id": str(tarefa.project_id)},
    )
    if not serializer.is_valid():
        return _resultado(tipo, ERRO, json.dumps(serializer.errors, cls=DjangoJSONEncoder))

    serializer.save()

    issue_activity.delay(
        type="issue.activity.updated",
        requested_data=json.dumps(pedido, cls=DjangoJSONEncoder),
        current_instance=json.dumps(anterior, cls=DjangoJSONEncoder),
        issue_id=str(tarefa.id),
        actor_id=str(contexto["ator_id"]),
        project_id=str(tarefa.project_id),
        epoch=int(timezone.now().timestamp()),
        notification=True,
        automacao_origem=str(contexto["automacao"].id),
        automacao_profundidade=contexto["profundidade"] + 1,
    )
    return _resultado(tipo, APLICADA, detalhe)


# --------------------------------------------------------------------------
# Estado e prioridade — os dois campos simples
# --------------------------------------------------------------------------


@acao("set_state")
def _mudar_estado(tarefa, config, contexto):
    destino = config.get("state_id")
    if not destino:
        raise AcaoInvalida("ação de estado sem estado de destino")
    if str(tarefa.state_id) == str(destino):
        return _resultado("set_state", SEM_EFEITO, "a tarefa já estava neste estado")

    # O detalhe vai para o registro de execuções, que é uma tela para PESSOA
    # ler. Um par de UUIDs ali é tão útil quanto não ter registro nenhum.
    nomes = dict(
        State.objects.filter(pk__in=[i for i in (tarefa.state_id, destino) if i]).values_list("pk", "name")
    )
    de = nomes.get(tarefa.state_id, "—")
    para = nomes.get(_como_uuid(destino), destino)

    return _gravar(
        tarefa,
        {"state_id": str(destino)},
        {"state_id": str(tarefa.state_id) if tarefa.state_id else None},
        contexto,
        "set_state",
        f"{de} → {para}",
    )


@acao("set_priority")
def _mudar_prioridade(tarefa, config, contexto):
    destino = config.get("priority")
    if not destino:
        raise AcaoInvalida("ação de prioridade sem prioridade de destino")
    if tarefa.priority == destino:
        return _resultado("set_priority", SEM_EFEITO, "a prioridade já era esta")
    return _gravar(
        tarefa,
        {"priority": destino},
        {"priority": tarefa.priority},
        contexto,
        "set_priority",
        f"prioridade {tarefa.priority} → {destino}",
    )


# --------------------------------------------------------------------------
# Responsáveis e etiquetas — listas, com três modos
# --------------------------------------------------------------------------


def _pessoas_especiais(config, tarefa, contexto):
    """"Quem criou" e "quem disparou", resolvidos na hora da execução.

    Guardar o id da pessoa na regra seria congelar quem era o responsável no
    dia em que a regra foi escrita; o que se quer dizer é o PAPEL.
    """
    especiais = set(config.get("especiais") or [])
    pessoas = []
    if "creator" in especiais and tarefa.created_by_id:
        pessoas.append(str(tarefa.created_by_id))
    if "trigger_actor" in especiais:
        quem = (contexto.get("evento") or {}).get("actor_id")
        # O robô não entra: atribuir a automação a si mesma não quer dizer nada,
        # e apareceria na tela como uma pessoa que não existe.
        if quem and str(quem) != str(contexto["ator_id"]):
            pessoas.append(str(quem))
    return pessoas


def _nova_lista(atuais, pedidos, modo):
    """Aplica o modo sobre a lista atual. Devolve `None` quando nada muda."""
    atuais_txt = [str(item) for item in atuais]
    pedidos_txt = [str(item) for item in pedidos]
    if modo == "replace":
        nova = list(dict.fromkeys(pedidos_txt))
    elif modo == "remove":
        remover = set(pedidos_txt)
        nova = [item for item in atuais_txt if item not in remover]
    else:  # add
        nova = atuais_txt + [item for item in pedidos_txt if item not in set(atuais_txt)]
    if set(nova) == set(atuais_txt):
        return None
    return nova


@acao("set_assignees")
def _mudar_responsaveis(tarefa, config, contexto):
    modo = config.get("mode", "add")
    pedidos = [str(item) for item in (config.get("assignees") or [])]
    pedidos += _pessoas_especiais(config, tarefa, contexto)
    if not pedidos and modo != "replace":
        raise AcaoInvalida("ação de responsável sem ninguém escolhido")

    atuais = list(
        tarefa.issue_assignee.filter(deleted_at__isnull=True).values_list("assignee_id", flat=True)
    )
    nova = _nova_lista(atuais, pedidos, modo)
    if nova is None:
        return _resultado("set_assignees", SEM_EFEITO, "os responsáveis já eram estes")
    return _gravar(
        tarefa,
        {"assignee_ids": nova},
        {"assignee_ids": [str(item) for item in atuais]},
        contexto,
        "set_assignees",
        f"{len(atuais)} → {len(nova)} responsável(is)",
    )


@acao("set_labels")
def _mudar_etiquetas(tarefa, config, contexto):
    modo = config.get("mode", "add")
    pedidos = [str(item) for item in (config.get("labels") or [])]
    if not pedidos and modo != "replace":
        raise AcaoInvalida("ação de etiqueta sem etiqueta escolhida")

    atuais = list(tarefa.label_issue.filter(deleted_at__isnull=True).values_list("label_id", flat=True))
    nova = _nova_lista(atuais, pedidos, modo)
    if nova is None:
        return _resultado("set_labels", SEM_EFEITO, "as etiquetas já eram estas")
    return _gravar(
        tarefa,
        {"label_ids": nova},
        {"label_ids": [str(item) for item in atuais]},
        contexto,
        "set_labels",
        f"{len(atuais)} → {len(nova)} etiqueta(s)",
    )


# --------------------------------------------------------------------------
# Datas — fixa ou relativa
# --------------------------------------------------------------------------


@acao("set_date")
def _mudar_data(tarefa, config, contexto):
    campo = config.get("field")
    if campo not in ("start_date", "target_date"):
        raise AcaoInvalida("ação de data sem campo válido")

    # `date_mode` tem nome próprio, e não reaproveita `mode`: numa ação de lista
    # `mode` responde "acrescentar/remover/substituir", e numa de data
    # responderia "relativa/fixa" — duas perguntas no mesmo campo.
    if config.get("date_mode", "relative") == "relative":
        # Relativa ao DIA DA EXECUÇÃO, no fuso do produto (ADR 0006). Contar a
        # partir do horário do servidor daria um dia a menos toda madrugada.
        dias = config.get("offset_days")
        if dias is None:
            raise AcaoInvalida("ação de data relativa sem número de dias")
        destino = (timezone.localtime().date() + timedelta(days=int(dias))).isoformat()
    else:
        destino = config.get("date")
        if not destino:
            raise AcaoInvalida("ação de data sem data")

    atual = getattr(tarefa, campo)
    atual_txt = atual.isoformat() if atual else None
    if atual_txt == destino:
        return _resultado("set_date", SEM_EFEITO, "a data já era esta")
    return _gravar(
        tarefa,
        {campo: destino},
        {campo: atual_txt},
        contexto,
        "set_date",
        f"{campo} {atual_txt} → {destino}",
    )


# --------------------------------------------------------------------------
# Propriedade personalizada — o campo que o cliente inventou (ADR 0011)
# --------------------------------------------------------------------------


@acao("set_property")
def _mudar_propriedade(tarefa, config, contexto):
    propriedade_id = config.get("property_id")
    if not propriedade_id:
        raise AcaoInvalida("ação de propriedade sem propriedade")

    propriedade = IssueProperty.objects.filter(
        pk=propriedade_id, project_id=tarefa.project_id, is_active=True
    ).first()
    if propriedade is None:
        # Propriedade apagada ou desligada não é erro da execução de hoje: é
        # uma regra que perdeu o campo. Registrar como "sem efeito" com o motivo
        # é mais útil do que marcar a regra inteira como falha.
        return _resultado("set_property", SEM_EFEITO, "a propriedade não existe mais neste projeto")

    anterior = valores_por_tarefa([tarefa.id]).get(tarefa.id, {}).get(str(propriedade.id))
    novo = config.get("value")
    de, para = rotulo_do_valor(propriedade, anterior), rotulo_do_valor(propriedade, novo)
    if de == para:
        return _resultado("set_property", SEM_EFEITO, f"{propriedade.name} já era este valor")

    try:
        gravar_valor(tarefa, propriedade, novo)
    except ValorInvalido as erro:
        return _resultado("set_property", ERRO, str(erro))

    # A gravação de propriedade não passa pelo serializer da tarefa, então a
    # atividade é registrada aqui — pelo mesmo caminho que a tela usa, para que
    # o histórico fique idêntico venha de onde vier.
    registrar_atividade_de_propriedade(
        tarefa=tarefa,
        propriedade=propriedade,
        de=de,
        para=para,
        actor_id=contexto["ator_id"],
        automacao_origem=str(contexto["automacao"].id),
        profundidade=contexto["profundidade"] + 1,
    )
    return _resultado("set_property", APLICADA, f"{propriedade.name}: {de or '—'} → {para or '—'}")


def executar(tipo, tarefa, config, contexto):
    """Executa uma ação pelo tipo. Tipo desconhecido é erro registrado, não queda."""
    funcao = ACOES.get(tipo)
    if funcao is None:
        return _resultado(tipo, ERRO, "tipo de ação desconhecido")
    try:
        return funcao(tarefa, config or {}, contexto)
    except AcaoInvalida as erro:
        return _resultado(tipo, ERRO, str(erro))
