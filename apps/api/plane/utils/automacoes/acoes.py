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
from django.utils.html import escape

# Module imports
from plane.db.models import Issue, IssueProperty, State
from plane.utils.automacoes.despacho import registrar_atividade_de_propriedade
from plane.utils.automacoes.variaveis import aplicar as aplicar_variaveis
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


# --------------------------------------------------------------------------
# A voz — comentar e notificar (F2)
# --------------------------------------------------------------------------


@acao("add_comment")
def _comentar(tarefa, config, contexto):
    """Escreve um comentário em nome do robô.

    Passa pelo mesmo caminho da tela: cria o `IssueComment` e dispara
    `comment.activity.created`. É o que faz a menção, a notificação de quem
    acompanha e o webhook saírem exatamente como saem quando uma pessoa comenta.
    """
    from plane.bgtasks.issue_activities_task import issue_activity
    from plane.db.models import IssueComment

    texto = aplicar_variaveis(config.get("text"), tarefa, contexto)
    if not texto.strip():
        raise AcaoInvalida("ação de comentário sem texto")

    # O corpo do comentário é HTML no produto. O texto da regra é digitado como
    # texto simples, e escapá-lo aqui evita que uma regra vire injeção de marcação
    # na tela de quem lê.
    html = f"<p>{escape(texto)}</p>"
    comentario = IssueComment.objects.create(
        issue=tarefa,
        project_id=tarefa.project_id,
        workspace_id=tarefa.workspace_id,
        actor_id=contexto["ator_id"],
        comment_html=html,
        comment_stripped=texto,
    )

    issue_activity.delay(
        type="comment.activity.created",
        requested_data=json.dumps({"id": str(comentario.id), "comment_html": html}, cls=DjangoJSONEncoder),
        current_instance=None,
        issue_id=str(tarefa.id),
        actor_id=str(contexto["ator_id"]),
        project_id=str(tarefa.project_id),
        epoch=int(timezone.now().timestamp()),
        notification=True,
        automacao_origem=str(contexto["automacao"].id),
        automacao_profundidade=contexto["profundidade"] + 1,
    )
    return _resultado("add_comment", APLICADA, texto[:120])


@acao("notify")
def _notificar(tarefa, config, contexto):
    """Avisa pessoas escolhidas, no sino e por e-mail.

    Diferente do aviso que já sai de qualquer mudança: aquele vai para quem
    ACOMPANHA a tarefa; este vai para quem a regra escolheu, com a mensagem que
    a regra escreveu. É a diferença entre "algo mudou" e "isto é com você".

    O e-mail entra pela mesma fila de sempre (`EmailNotificationLog`, recolhida
    de cinco em cinco minutos) — reusar o agrupamento dela evita que uma regra
    ativa vire uma mensagem por evento na caixa de entrada de alguém.
    """
    from plane.db.models import EmailNotificationLog, Notification, User

    destinatarios = set(str(item) for item in (config.get("users") or []))
    especiais = set(config.get("especiais") or [])
    if "assignees" in especiais:
        destinatarios.update(
            str(item)
            for item in tarefa.issue_assignee.filter(deleted_at__isnull=True).values_list("assignee_id", flat=True)
        )
    if "creator" in especiais and tarefa.created_by_id:
        destinatarios.add(str(tarefa.created_by_id))
    if "trigger_actor" in especiais:
        quem = (contexto.get("evento") or {}).get("actor_id")
        if quem:
            destinatarios.add(str(quem))

    # O robô nunca é destinatário: notificação para quem não abre o produto é
    # linha morta no banco.
    destinatarios.discard(str(contexto["ator_id"]))
    if not destinatarios:
        return _resultado("notify", SEM_EFEITO, "ninguém para avisar")

    texto = aplicar_variaveis(config.get("text"), tarefa, contexto) or tarefa.name
    dados = {
        "issue": {
            "id": str(tarefa.id),
            "name": tarefa.name,
            "identifier": tarefa.project.identifier,
            "sequence_id": tarefa.sequence_id,
            "state_name": tarefa.state.name if tarefa.state_id else "",
            "state_group": tarefa.state.group if tarefa.state_id else "",
            "project_id": str(tarefa.project_id),
            "workspace_slug": tarefa.project.workspace.slug,
        },
        "automation": {"id": str(contexto["automacao"].id), "name": contexto["automacao"].name},
    }

    existentes = set(str(item) for item in User.objects.filter(pk__in=destinatarios).values_list("pk", flat=True))
    Notification.objects.bulk_create(
        [
            Notification(
                workspace_id=tarefa.workspace_id,
                project_id=tarefa.project_id,
                sender="in_app:automation",
                triggered_by_id=contexto["ator_id"],
                receiver_id=pessoa,
                entity_identifier=tarefa.id,
                entity_name="issue",
                title=texto,
                message={"text": texto},
                message_stripped=texto,
                data=dados,
            )
            for pessoa in existentes
        ],
        batch_size=50,
    )

    if config.get("email", True):
        EmailNotificationLog.objects.bulk_create(
            [
                EmailNotificationLog(
                    triggered_by_id=contexto["ator_id"],
                    receiver_id=pessoa,
                    entity_identifier=tarefa.id,
                    entity_name="issue",
                    entity="issue",
                    new_value=texto[:300],
                    data=dados,
                )
                for pessoa in existentes
            ],
            batch_size=50,
            ignore_conflicts=True,
        )

    return _resultado("notify", APLICADA, f"{len(existentes)} pessoa(s) avisada(s)")


# --------------------------------------------------------------------------
# Arquivar, ciclo e módulo (F2)
# --------------------------------------------------------------------------


@acao("archive")
def _arquivar(tarefa, config, contexto):
    """Arquiva a tarefa.

    O produto só arquiva o que está concluído ou cancelado — a mesma trava do
    arquivamento automático herdado. Uma regra que arquivasse trabalho em
    andamento faria sumir da tela algo que ninguém terminou.
    """
    if tarefa.archived_at is not None:
        return _resultado("archive", SEM_EFEITO, "a tarefa já estava arquivada")
    grupo = tarefa.state.group if tarefa.state_id else None
    if grupo not in ("completed", "cancelled"):
        return _resultado("archive", SEM_EFEITO, "só arquiva tarefa concluída ou cancelada")

    quando = timezone.now().date()
    Issue.objects.filter(pk=tarefa.pk).update(archived_at=quando)

    from plane.bgtasks.issue_activities_task import issue_activity

    issue_activity.delay(
        type="issue.activity.updated",
        requested_data=json.dumps({"archived_at": str(quando)}, cls=DjangoJSONEncoder),
        current_instance=json.dumps({"archived_at": None}, cls=DjangoJSONEncoder),
        issue_id=str(tarefa.id),
        actor_id=str(contexto["ator_id"]),
        project_id=str(tarefa.project_id),
        epoch=int(timezone.now().timestamp()),
        notification=True,
        automacao_origem=str(contexto["automacao"].id),
        automacao_profundidade=contexto["profundidade"] + 1,
    )
    return _resultado("archive", APLICADA, f"arquivada em {quando}")


@acao("add_to_cycle")
def _incluir_no_ciclo(tarefa, config, contexto):
    """Põe a tarefa no ciclo ativo do projeto.

    "Ativo", e não um ciclo escolhido na regra: um id fixo aqui envelheceria na
    virada do próximo ciclo, e a regra passaria a alimentar um ciclo encerrado
    sem ninguém perceber.
    """
    from plane.bgtasks.issue_activities_task import issue_activity
    from plane.db.models import Cycle, CycleIssue

    agora = timezone.now()
    ciclo = (
        Cycle.objects.filter(project_id=tarefa.project_id, start_date__lte=agora, end_date__gte=agora)
        .order_by("start_date")
        .first()
    )
    if ciclo is None:
        return _resultado("add_to_cycle", SEM_EFEITO, "o projeto não tem ciclo ativo agora")

    if CycleIssue.objects.filter(issue=tarefa, cycle=ciclo, deleted_at__isnull=True).exists():
        return _resultado("add_to_cycle", SEM_EFEITO, f"a tarefa já estava no ciclo {ciclo.name}")

    # Uma tarefa mora em um ciclo só: o vínculo antigo sai antes.
    CycleIssue.objects.filter(issue=tarefa).delete()
    CycleIssue.objects.create(
        issue=tarefa, cycle=ciclo, project_id=tarefa.project_id, workspace_id=tarefa.workspace_id
    )

    issue_activity.delay(
        type="cycle.activity.created",
        requested_data=json.dumps({"cycles_list": [str(tarefa.id)]}, cls=DjangoJSONEncoder),
        current_instance=json.dumps({"created_cycle_issues": [], "updated_cycle_issues": []}, cls=DjangoJSONEncoder),
        issue_id=str(tarefa.id),
        actor_id=str(contexto["ator_id"]),
        project_id=str(tarefa.project_id),
        epoch=int(timezone.now().timestamp()),
        notification=True,
        automacao_origem=str(contexto["automacao"].id),
        automacao_profundidade=contexto["profundidade"] + 1,
    )
    return _resultado("add_to_cycle", APLICADA, f"incluída no ciclo {ciclo.name}")


# --------------------------------------------------------------------------
# Criação — tarefa e subtarefas (F3)
# --------------------------------------------------------------------------
#
# Aqui a preocupação central NÃO é laço, é DUPLICATA. Nos produtos que têm este
# recurso, a reclamação recorrente é a mesma: "a regra criou o checklist duas
# vezes" (Asana) e "a automação duplicou o clone" (Jira, onde a criação chega a
# levantar o evento mais de uma vez).
#
# A resposta é idempotência garantida pelo BANCO, e não pela confiança de que o
# motor roda uma vez só — a mesma forma que a recorrência já usa aqui. A chave é
# (regra, tarefa de origem, nome do item): mover para Homologação, voltar e mover
# de novo não recria nada; acrescentar um item à regra e disparar de novo cria só
# o item novo.
#
# E o que NUNCA acontece: a tarefa criada não recebe recorrência, nem herda a da
# origem. Criação por agenda é trabalho de Tarefas recorrentes (ADR 0010), que
# tem calendário, antecedência e controle de ocorrência aberta; a automação não
# vai reimplementar nada disso pior. Por isso a combinação "gatilho agendado +
# criar" nem chega a existir — a validação a recusa.


def _ja_criou(automacao, origem, chave):
    from plane.db.models import AutomationCreation

    return AutomationCreation.objects.filter(
        automation=automacao, source_issue=origem, chave=chave, deleted_at__isnull=True
    ).exists()


def _e_molde_de_recorrencia(tarefa) -> bool:
    """A tarefa é a origem de uma recorrência ativa?

    Mexer nela mexe em TODAS as ocorrências futuras. Acrescentar subtarefa a um
    molde por regra é o defeito que a Asana tem, onde as subtarefas se acumulam
    na tarefa recorrente ciclo após ciclo.
    """
    from plane.db.models import RecurringWorkItem

    return RecurringWorkItem.objects.filter(
        source_issue=tarefa, is_active=True, deleted_at__isnull=True
    ).exists()


def _nascer(nome, projeto_id, workspace_id, contexto, pai=None, extras=None):
    """Cria a tarefa e conta a história dela, como qualquer criação do produto."""
    from plane.bgtasks.issue_activities_task import issue_activity

    campos = {
        "name": nome[:255],
        "project_id": projeto_id,
        "workspace_id": workspace_id,
        **(extras or {}),
    }
    if pai is not None:
        campos["parent"] = pai

    # A autoria vai pelo `save`, e não no `create`.
    #
    # `BaseModel.save` reescreve `created_by` a partir do usuário da requisição
    # quando não recebe `created_by_id` — e no worker não há requisição, então o
    # valor passado no `create` era descartado e a tarefa nascia sem autor.
    # Descoberto na verificação visual: o robô assinava as ALTERAÇÕES e não
    # assinava as CRIAÇÕES, o que é justamente a metade que interessa aqui.
    nova = Issue(**campos)
    nova.save(created_by_id=contexto["ator_id"])

    issue_activity.delay(
        type="issue.activity.created",
        requested_data=json.dumps({"name": nova.name}, cls=DjangoJSONEncoder),
        current_instance=None,
        issue_id=str(nova.id),
        actor_id=str(contexto["ator_id"]),
        project_id=str(projeto_id),
        epoch=int(timezone.now().timestamp()),
        notification=True,
        automacao_origem=str(contexto["automacao"].id),
        automacao_profundidade=contexto["profundidade"] + 1,
    )
    return nova


def _datas(config):
    """Vencimento relativo ao dia da criação, quando a regra pedir.

    Relativo, e nunca fixo: "entregar em 3 dias" continua certo no mês que vem;
    uma data absoluta escrita na regra vence e nunca mais volta a fazer sentido.
    """
    dias = config.get("due_in_days")
    if dias is None:
        return {}
    return {"target_date": timezone.localtime().date() + timedelta(days=int(dias))}


def _registrar_criacao(automacao, origem, nova, chave):
    from plane.db.models import AutomationCreation

    AutomationCreation.objects.create(
        automation=automacao,
        workspace_id=origem.workspace_id,
        source_issue=origem,
        issue=nova,
        chave=chave,
    )


@acao("create_work_item")
def _criar_tarefa(tarefa, config, contexto):
    """Cria UMA tarefa em resposta ao que aconteceu nesta."""
    nome = aplicar_variaveis(config.get("name"), tarefa, contexto).strip()
    if not nome:
        raise AcaoInvalida("ação de criar tarefa sem nome")

    automacao = contexto["automacao"]
    if _ja_criou(automacao, tarefa, ""):
        return _resultado("create_work_item", SEM_EFEITO, "esta regra já criou uma tarefa para esta origem")

    # A tarefa nova nasce na etapa PADRÃO do projeto, nunca na etapa da origem.
    # É a mesma lição já escrita no modelo da recorrência (ADR 0010): a instância
    # que reaparece dentro da coluna "Concluído" é o defeito mais reclamado do
    # Asana. `Issue.save` já resolve o padrão sozinho — o que se faz aqui é não
    # atrapalhar.
    nova = _nascer(nome, tarefa.project_id, tarefa.workspace_id, contexto, extras=_datas(config))
    _copiar_responsaveis(tarefa, nova, config, contexto)
    _registrar_criacao(automacao, tarefa, nova, "")
    return _resultado("create_work_item", APLICADA, f"criada: {nova.name}")


@acao("create_subtasks")
def _criar_subtarefas(tarefa, config, contexto):
    """Cria o checklist de subtarefas desta tarefa.

    Uma ação com a LISTA de nomes, e não uma ação por subtarefa. O monday resolve
    isso encadeando três receitas idênticas; uma lista faz o mesmo com um terço
    da tela, e mantém o conjunto legível como conjunto.
    """
    nomes = [str(item).strip() for item in (config.get("names") or []) if str(item).strip()]
    if not nomes:
        raise AcaoInvalida("ação de subtarefas sem nenhum nome")

    if _e_molde_de_recorrencia(tarefa):
        # Recusa com motivo, e não em silêncio: quem escreveu a regra precisa
        # saber que ela não vale para o molde — e por quê.
        return _resultado(
            "create_subtasks",
            SEM_EFEITO,
            "a tarefa é a origem de uma recorrência ativa; subtarefa aqui mudaria todas as ocorrências futuras",
        )

    automacao = contexto["automacao"]
    criadas, puladas = [], 0
    for nome in nomes:
        rotulo = aplicar_variaveis(nome, tarefa, contexto).strip()[:255]
        if not rotulo or _ja_criou(automacao, tarefa, rotulo):
            puladas += 1
            continue
        nova = _nascer(rotulo, tarefa.project_id, tarefa.workspace_id, contexto, pai=tarefa, extras=_datas(config))
        _copiar_responsaveis(tarefa, nova, config, contexto)
        _registrar_criacao(automacao, tarefa, nova, rotulo)
        criadas.append(rotulo)

    if not criadas:
        return _resultado("create_subtasks", SEM_EFEITO, "todas já tinham sido criadas por esta regra")
    detalhe = ", ".join(criadas)
    if puladas:
        detalhe += f" ({puladas} já existia(m))"
    return _resultado("create_subtasks", APLICADA, detalhe)


def _copiar_responsaveis(origem, nova, config, contexto):
    """Herança do pai, quando a regra pedir.

    É o comportamento que o monday oferece ao criar subitem, e existe por um
    motivo prático: subtarefa que nasce sem responsável nasce órfã, e ninguém
    olha para ela.
    """
    if not config.get("herdar_responsaveis"):
        return
    from plane.db.models import IssueAssignee

    pessoas = list(origem.issue_assignee.filter(deleted_at__isnull=True).values_list("assignee_id", flat=True))
    if not pessoas:
        return
    IssueAssignee.objects.bulk_create(
        [
            IssueAssignee(
                issue=nova,
                assignee_id=pessoa,
                project_id=nova.project_id,
                workspace_id=nova.workspace_id,
                created_by_id=contexto["ator_id"],
            )
            for pessoa in pessoas
        ],
        batch_size=20,
        ignore_conflicts=True,
    )


def executar(tipo, tarefa, config, contexto):
    """Executa uma ação pelo tipo. Tipo desconhecido é erro registrado, não queda."""
    funcao = ACOES.get(tipo)
    if funcao is None:
        return _resultado(tipo, ERRO, "tipo de ação desconhecido")
    try:
        return funcao(tarefa, config or {}, contexto)
    except AcaoInvalida as erro:
        return _resultado(tipo, ERRO, str(erro))
