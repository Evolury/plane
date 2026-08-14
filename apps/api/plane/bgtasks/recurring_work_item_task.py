# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Geração das ocorrências de tarefas recorrentes (ADR 0010, revisão 13/08/2026).

O job varre as regras vencidas e copia a tarefa de origem de cada uma. Três
regras governam o que ele faz, e todas existem para o mesmo fim: o quadro não
pode encher de trabalho que ninguém pediu.

1. **Atraso não acumula.** Se o job ficou fora do ar por dois dias, a rodada
   seguinte gera UMA ocorrência — a mais recente devida — e segue.
2. **Enquanto houver trabalho aberto da série, não gera** (quando a regra
   pede). A origem conta: ela é o item zero da série, e uma ocorrência ao lado
   dela aberta é exatamente a pilha que a guarda evita.
3. **A mesma data nunca gera duas tarefas**, garantido pela unicidade de
   (regra, data prevista) no banco, e não por confiança no relógio.

O que a cópia carrega e o que deixa para trás está na especificação: o que
descreve o trabalho vai; o que descreve aquela execução — comentários,
atividade, anexos, ciclo, módulo, relações, datas — fica.
"""

# Python imports
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Django imports
from django.db import IntegrityError, transaction
from django.db.models import DateTimeField, DurationField, ExpressionWrapper, F, Value
from django.utils import timezone

# Third party imports
from celery import shared_task

# Module imports
from plane.db.models import (
    GenerationMode,
    Issue,
    IssueAssignee,
    IssueLabel,
    ProjectMember,
    RecurringSubtaskSchedule,
    RecurringWorkItem,
    RecurringWorkItemOccurrence,
    State,
    SubtaskDueAnchor,
)
from plane.bgtasks.issue_activities_task import issue_activity
from plane.utils.exception_logger import log_exception
from plane.utils.recurrence import data_apos_conclusao, proxima_data
from plane.utils.subtask_tree import ids_da_arvore


def _estado_inicial(regra):
    """A etapa escolhida na regra, quando ainda válida; senão a padrão do projeto.

    A etapa pode ter sido excluída depois — `State` é excluído logicamente,
    então a referência sobrevive e é aqui que ela é conferida.
    """
    escolhido = regra.initial_state
    if escolhido is not None and escolhido.deleted_at is None and escolhido.project_id == regra.project_id:
        return escolhido
    return State.objects.filter(project=regra.project, default=True).first()


def _origem_aberta(origem):
    return origem.state is None or origem.state.group not in ("completed", "cancelled")


def _tem_trabalho_aberto(regra):
    """Alguma tarefa da série — a origem ou uma ocorrência — segue aberta.

    Aberta = etapa fora dos grupos concluído e cancelado. A junção com a
    tarefa não passa pelo manager de exclusão lógica, então o filtro de
    `deleted_at` é explícito: uma ocorrência excluída não pode segurar a
    guarda — ela nem aparece no quadro para alguém entender o porquê.
    """
    if _origem_aberta(regra.source_issue):
        return True
    return (
        RecurringWorkItemOccurrence.objects.filter(
            recurring_work_item=regra, issue__isnull=False, issue__deleted_at__isnull=True
        )
        .exclude(issue__state__group__in=["completed", "cancelled"])
        .exists()
    )


def _responsaveis_ativos(regra):
    """Quem ainda é membro do projeto — remover alguém não desfaz atribuições.

    Sem este filtro, a origem de quem saiu da empresa continuaria carimbando
    todas as ocorrências futuras com um dono que não existe mais, e trabalho
    com aparência de dono é pior que trabalho sem dono: ninguém assume o que já
    parece atribuído (ADR 0010).
    """
    return set(
        ProjectMember.objects.filter(project_id=regra.project_id, is_active=True).values_list(
            "member_id", flat=True
        )
    )


def _responsavel_padrao(regra):
    """O responsável padrão do projeto, quando ainda vale.

    Mesma validação do caminho normal de criação: membro ativo, com papel de
    membro ou admin — convidado não recebe trabalho por padrão. Sem isto, a
    regra do projeto valeria em toda tarefa criada à mão e seria ignorada
    justamente nas que nascem sozinhas, que é onde ninguém está olhando.
    """
    padrao_id = regra.project.default_assignee_id
    if padrao_id is None:
        return None
    valido = ProjectMember.objects.filter(
        member_id=padrao_id, project_id=regra.project_id, role__gte=15, is_active=True
    ).exists()
    return padrao_id if valido else None


def _linhas_de_vinculo(copia, regra, responsaveis, etiquetas):
    """As linhas de responsável e etiqueta de uma cópia, prontas para inserir."""
    return (
        [
            IssueAssignee(
                issue=copia,
                assignee_id=pessoa,
                project_id=regra.project_id,
                workspace_id=regra.workspace_id,
            )
            for pessoa in responsaveis
        ],
        [
            IssueLabel(
                issue=copia,
                label_id=etiqueta,
                project_id=regra.project_id,
                workspace_id=regra.workspace_id,
            )
            for etiqueta in etiquetas
        ],
    )


def _gravar_vinculos(responsaveis, etiquetas):
    IssueAssignee.objects.bulk_create(responsaveis, batch_size=100, ignore_conflicts=True)
    IssueLabel.objects.bulk_create(etiquetas, batch_size=100, ignore_conflicts=True)


def _vinculos_das_tarefas(ids):
    """Responsáveis e etiquetas de várias tarefas, em duas consultas.

    Uma consulta por subtarefa seria uma centena de idas ao banco numa árvore
    no teto — e o custo da geração foi exatamente o motivo de a subtarefa
    aninhada ter ficado para o ciclo seguinte (ADR 0010).
    """
    responsaveis, etiquetas = {}, {}
    for tarefa_id, pessoa_id in IssueAssignee.objects.filter(issue_id__in=ids).values_list(
        "issue_id", "assignee_id"
    ):
        responsaveis.setdefault(tarefa_id, []).append(pessoa_id)
    for tarefa_id, etiqueta_id in IssueLabel.objects.filter(issue_id__in=ids).values_list(
        "issue_id", "label_id"
    ):
        etiquetas.setdefault(tarefa_id, []).append(etiqueta_id)
    return responsaveis, etiquetas


def _copiar_relacionados(origem, copia, regra, ativos=None, usar_padrao=False):
    """Responsáveis e etiquetas — descrevem o trabalho, então acompanham."""
    if ativos is None:
        ativos = _responsaveis_ativos(regra)
    responsaveis = [
        vinculo.assignee_id
        for vinculo in IssueAssignee.objects.filter(issue=origem)
        if vinculo.assignee_id in ativos
    ]
    # Só a tarefa principal cai no padrão do projeto: subtarefa sem responsável
    # é normal, e carimbar todas elas com a mesma pessoa seria ruído.
    if not responsaveis and usar_padrao:
        padrao = _responsavel_padrao(regra)
        if padrao is not None:
            responsaveis = [padrao]
    etiquetas = list(IssueLabel.objects.filter(issue=origem).values_list("label_id", flat=True))
    _gravar_vinculos(*_linhas_de_vinculo(copia, regra, responsaveis, etiquetas))


def _vencimento_da_subtarefa(agenda, nascimento, vencimento):
    """A data da subtarefa, calculada do zero — nunca deslocada.

    É o que nos livra da classe de defeito do ClickUp, cujo remapeamento não
    funciona quando a data do pai recua: aqui não há data anterior para
    deslocar, há data para calcular a cada ciclo.

    O recorte no nascimento é a regra de segurança: subtarefa não pode vencer
    antes de existir. Data ausente não mente, e data impossível também.
    """
    if agenda is None:
        return None
    if agenda.anchor == SubtaskDueAnchor.AFTER_CREATION:
        calculada = nascimento + timedelta(days=agenda.offset_days)
    else:
        calculada = vencimento - timedelta(days=agenda.offset_days)
    return max(calculada, nascimento)


def _copiar_subtarefas(origem, copia, regra, ativos, nascimento=None, vencimento=None):
    """A árvore inteira de subtarefas, aberta na etapa padrão do projeto.

    O aninhamento entra porque a hierarquia **descreve o trabalho** — é o mesmo
    critério que traz nome, prioridade e etiqueta. Recortá-la no primeiro nível
    entregava uma ocorrência com o passo grande e sem os passos dele, e a
    diferença ficava invisível: o cartão da origem mostra a árvore toda.

    O teto conta a árvore, não os filhos diretos. É o que mantém o custo da
    geração onde estava — o mesmo número de nós, distribuídos de outro jeito.

    Sem agenda própria, a subtarefa nasce **sem data**: o defeito conhecido do
    Asana é a subtarefa que nasce vencida, com a data do ciclo anterior. Data
    ausente não mente. Com agenda, a data é calculada a partir do nascimento ou
    do vencimento desta ocorrência (F7), em qualquer nível.
    """
    ids = ids_da_arvore(origem.id)
    if not ids:
        return

    por_id = Issue.objects.in_bulk(ids)
    responsaveis_da, etiquetas_da = _vinculos_das_tarefas(ids)
    agendas = {
        agenda.subtask_id: agenda
        for agenda in RecurringSubtaskSchedule.objects.filter(
            recurring_work_item=regra, subtask_id__in=ids
        )
    }

    copia_de = {origem.id: copia}
    responsaveis, etiquetas = [], []
    for subtarefa_id in ids:
        filha = por_id.get(subtarefa_id)
        pai = copia_de.get(filha.parent_id) if filha is not None else None
        # Filha de quem não foi copiado não é copiada. A travessia em largura
        # já garante isso; a checagem cobre a tarefa que alguém excluiu entre
        # a travessia e agora, e faz o ramo dela sumir junto, não pela metade.
        if pai is None:
            continue
        subcopia = Issue.objects.create(
            project=regra.project,
            workspace_id=regra.workspace_id,
            parent=pai,
            name=filha.name,
            description_html=filha.description_html or "<p></p>",
            priority=filha.priority or "none",
            type=filha.type,
            estimate_point=filha.estimate_point,
            target_date=(
                _vencimento_da_subtarefa(agendas.get(filha.id), nascimento, vencimento)
                if nascimento and vencimento
                else None
            ),
            created_by_id=regra.created_by_id,
        )
        copia_de[filha.id] = subcopia
        linhas_de_pessoa, linhas_de_etiqueta = _linhas_de_vinculo(
            subcopia,
            regra,
            [pessoa for pessoa in responsaveis_da.get(filha.id, []) if pessoa in ativos],
            etiquetas_da.get(filha.id, []),
        )
        responsaveis += linhas_de_pessoa
        etiquetas += linhas_de_etiqueta

    _gravar_vinculos(responsaveis, etiquetas)


def _criar_ocorrencia(regra, previsto_para, agora):
    """Copia a tarefa de origem e registra a ocorrência.

    O registro entra ANTES da tarefa: se dois workers pegarem a mesma regra, o
    segundo esbarra na unicidade e desiste, em vez de criar a tarefa duas vezes.
    """
    try:
        with transaction.atomic():
            ocorrencia = RecurringWorkItemOccurrence.objects.create(
                recurring_work_item=regra,
                workspace_id=regra.workspace_id,
                scheduled_for=previsto_para,
            )
    except IntegrityError:
        return None

    origem = regra.source_issue
    fuso = ZoneInfo(regra.project.timezone)
    # As datas são calculadas, nunca copiadas: nasce hoje, vence na data da
    # agenda. Com antecedência, "hoje" chega antes do vencimento — e é essa
    # janela que as subtarefas usam de referência (F7).
    nascimento = agora.astimezone(fuso).date()
    vencimento = previsto_para.astimezone(fuso).date()
    with transaction.atomic():
        tarefa = Issue.objects.create(
            project=regra.project,
            workspace_id=regra.workspace_id,
            name=origem.name,
            description_html=origem.description_html or "<p></p>",
            priority=origem.priority or "none",
            state=_estado_inicial(regra),
            type=origem.type,
            estimate_point=origem.estimate_point,
            # As datas são calculadas, nunca copiadas: nasce hoje, vence na
            # data da agenda. Com antecedência, "hoje" chega antes do vencimento.
            start_date=nascimento,
            target_date=vencimento,
            created_by_id=regra.created_by_id,
        )
        ativos = _responsaveis_ativos(regra)
        _copiar_relacionados(origem, tarefa, regra, ativos, usar_padrao=True)
        _copiar_subtarefas(origem, tarefa, regra, ativos, nascimento, vencimento)

        ocorrencia.issue = tarefa
        ocorrencia.save(update_fields=["issue"])
        RecurringWorkItem.objects.filter(pk=regra.pk).update(
            occurrences_created=regra.occurrences_created + 1
        )

    # Ocorrência é tarefa como qualquer outra: história, webhook e notificação.
    # O ator é quem criou a regra — atividade sem ator é buraco no histórico.
    issue_activity.delay(
        type="issue.activity.created",
        requested_data=json.dumps({"name": tarefa.name}),
        actor_id=str(regra.created_by_id) if regra.created_by_id else None,
        issue_id=str(tarefa.id),
        project_id=str(regra.project_id),
        current_instance=None,
        epoch=int(timezone.now().timestamp()),
        notification=True,
        origin=None,
    )
    return tarefa


def _antecedencia(regra):
    """Dias para a véspera, horas para o preparo — somados."""
    return timedelta(days=regra.lead_time_days or 0, hours=regra.lead_time_hours or 0)


def _momento_do_disparo(regra):
    """Quando a regra dispara: a data prevista, adiantada pela antecedência."""
    return regra.next_run_at - _antecedencia(regra)


def processar_regra(regra, agora=None):
    """Gera o que estiver devido para uma regra. Devolve a tarefa criada, se houve."""
    agora = agora or timezone.now()

    if not regra.is_active or regra.next_run_at is None or _momento_do_disparo(regra) > agora:
        return None

    origem = regra.source_issue
    if origem is None or origem.deleted_at is not None:
        # Excluir a origem exclui a regra junto (especificação). Como Issue usa
        # exclusão lógica, o on_delete nunca dispara — a rede de segurança é aqui.
        regra.delete()
        return None
    if origem.archived_at is not None:
        # Arquivar pausa, e pausar se desfaz: nada é gerado, e no modo por
        # agenda o relógio desliza para a próxima data futura — desarquivar
        # retoma dali, sem despejar o período perdido no quadro.
        if regra.generation_mode == GenerationMode.SCHEDULE:
            RecurringWorkItem.objects.filter(pk=regra.pk).update(next_run_at=proxima_data(regra, agora))
        return None

    if regra.skip_while_previous_open and _tem_trabalho_aberto(regra):
        # Não gera, mas no modo por agenda anda com o relógio: senão a regra
        # ficaria presa na data antiga e dispararia tudo de uma vez quando
        # alguém concluísse.
        if regra.generation_mode == GenerationMode.SCHEDULE:
            RecurringWorkItem.objects.filter(pk=regra.pk).update(next_run_at=proxima_data(regra, agora))
        return None

    previsto_para = regra.next_run_at
    tarefa = _criar_ocorrencia(regra, previsto_para, agora)

    regra.refresh_from_db(fields=["occurrences_created"])
    if regra.generation_mode == GenerationMode.AFTER_COMPLETION:
        # A próxima não tem data até alguém concluir esta.
        proxima = None
    else:
        # Atraso não acumula: a base é AGORA, então datas perdidas ficam para
        # trás de propósito. O max protege a antecedência — quando a regra
        # dispara antes do vencimento, a data prevista ainda está no futuro e
        # não pode ser devolvida como se fosse a próxima.
        proxima = proxima_data(regra, max(agora, previsto_para))
    RecurringWorkItem.objects.filter(pk=regra.pk).update(next_run_at=proxima)
    return tarefa


@shared_task
def generate_recurring_work_items():
    """Job do beat: roda a cada 15 minutos."""
    agora = timezone.now()
    antecedencia = ExpressionWrapper(
        F("lead_time_days") * Value(timedelta(days=1)) + F("lead_time_hours") * Value(timedelta(hours=1)),
        output_field=DurationField(),
    )
    regras = (
        RecurringWorkItem.objects.filter(is_active=True, next_run_at__isnull=False)
        .annotate(disparo=ExpressionWrapper(F("next_run_at") - antecedencia, output_field=DateTimeField()))
        .filter(disparo__lte=agora)
        .select_related("project", "source_issue", "source_issue__state", "initial_state")
    )

    for regra in regras:
        try:
            processar_regra(regra, agora=agora)
        except Exception as erro:  # uma regra quebrada não pode parar as outras
            log_exception(erro)


def _origem_concluida(regra):
    origem = regra.source_issue
    return origem is not None and origem.state is not None and origem.state.group == "completed"


def agendar_proxima_data(regra, a_partir_de=None):
    """Recalcula e grava o `next_run_at` — usado ao criar e ao editar a regra."""
    referencia = a_partir_de or timezone.now()
    inicio = datetime.combine(regra.start_date, regra.time_of_day, tzinfo=ZoneInfo(regra.project.timezone))
    inicio_utc = inicio.astimezone(ZoneInfo("UTC"))

    if regra.generation_mode == GenerationMode.AFTER_COMPLETION:
        # Nesse modo o calendário não manda: quem manda é a conclusão — da
        # origem primeiro, e de cada ocorrência depois. Editar a regra não
        # apaga uma data que uma conclusão já marcou; se a origem já estava
        # concluída quando a regra nasceu, a conclusão já aconteceu e conta a
        # partir de agora. Senão, espera.
        if regra.next_run_at is not None:
            proxima = regra.next_run_at
        elif not regra.occurrences_created and _origem_concluida(regra):
            proxima = data_apos_conclusao(regra, referencia)
        else:
            proxima = None
    else:
        # Regra que começa no futuro conta a partir do próprio começo; regra
        # cujo horário de hoje já passou não gera retroativamente — atraso não
        # acumula.
        base = max(referencia, inicio_utc - timedelta(seconds=1))
        proxima = proxima_data(regra, base)

    RecurringWorkItem.objects.filter(pk=regra.pk).update(next_run_at=proxima)
    regra.next_run_at = proxima
    return proxima


def agendar_apos_conclusao(issue_id, novo_estado_id):
    """No modo "após a conclusão", concluir agenda a próxima ocorrência.

    Vale para a origem — que é o item zero da série — e para cada ocorrência
    gerada. Sem isto o modo existiria no formulário e nunca dispararia: a
    agenda dele não está no calendário, está no momento em que alguém termina.

    Também é o que impede o defeito conhecido do Asana, onde concluir com
    atraso pula um mês inteiro: aqui a data nova conta a partir da conclusão,
    então atrasar empurra a próxima, nunca some com ela.
    """
    if not novo_estado_id:
        return None
    estado = State.all_objects.filter(pk=novo_estado_id).values("group").first()
    if not estado or estado["group"] != "completed":
        return None

    ocorrencia = (
        RecurringWorkItemOccurrence.objects.filter(issue_id=issue_id)
        .select_related("recurring_work_item", "recurring_work_item__project")
        .order_by("-scheduled_for")
        .first()
    )
    if ocorrencia is not None:
        regra = ocorrencia.recurring_work_item
    else:
        regra = (
            RecurringWorkItem.objects.filter(source_issue_id=issue_id)
            .select_related("project")
            .first()
        )
    if regra is None:
        return None
    if regra.generation_mode != GenerationMode.AFTER_COMPLETION or not regra.is_active:
        return None

    proxima = data_apos_conclusao(regra, timezone.now())
    RecurringWorkItem.objects.filter(pk=regra.pk).update(next_run_at=proxima)
    return proxima
