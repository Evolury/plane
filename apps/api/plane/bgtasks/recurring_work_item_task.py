# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Geração das ocorrências de tarefas recorrentes (ADR 0010).

O job varre as regras vencidas e cria a tarefa de cada uma. Três regras
governam o que ele faz, e todas existem para o mesmo fim: o quadro não pode
encher de trabalho que ninguém pediu.

1. **Atraso não acumula.** Se o job ficou fora do ar por dois dias, a rodada
   seguinte gera UMA ocorrência — a mais recente devida — e segue.
2. **Enquanto a anterior estiver aberta, não gera** (quando a regra pede).
3. **A mesma data nunca gera duas tarefas**, garantido pela unicidade de
   (regra, data prevista) no banco, e não por confiança no relógio.
"""

# Python imports
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Django imports
from django.db import IntegrityError, transaction
from django.utils import timezone

# Third party imports
from celery import shared_task

# Module imports
from plane.db.models import (
    Issue,
    IssueAssignee,
    IssueLabel,
    RecurringWorkItem,
    RecurringWorkItemOccurrence,
    State,
)
from plane.bgtasks.issue_activities_task import issue_activity
from plane.utils.exception_logger import log_exception
from plane.utils.recurrence import proxima_data


def _estado_inicial(regra):
    """O estado do molde, quando ainda válido; senão o padrão do projeto.

    O estado escolhido pode ter sido excluído depois — `State` é excluído
    logicamente, então a referência sobrevive e é aqui que ela é conferida.
    """
    escolhido = regra.template_state
    if escolhido is not None and escolhido.deleted_at is None and escolhido.project_id == regra.project_id:
        return escolhido
    return State.objects.filter(project=regra.project, default=True).first()


def _tem_ocorrencia_aberta(regra):
    """Alguma ocorrência anterior ainda não foi encerrada."""
    return (
        RecurringWorkItemOccurrence.objects.filter(recurring_work_item=regra, issue__isnull=False)
        .exclude(issue__state__group__in=["completed", "cancelled"])
        .exists()
    )


def _criar_ocorrencia(regra, previsto_para):
    """Cria a tarefa do molde e registra a ocorrência.

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

    estado = _estado_inicial(regra)
    with transaction.atomic():
        tarefa = Issue.objects.create(
            project=regra.project,
            workspace_id=regra.workspace_id,
            name=regra.name,
            description_html=regra.template_description_html or "<p></p>",
            priority=regra.template_priority or "none",
            state=estado,
            type=regra.template_type,
            estimate_point=regra.template_estimate_point,
            created_by_id=regra.created_by_id,
        )

        IssueAssignee.objects.bulk_create(
            [
                IssueAssignee(
                    issue=tarefa, assignee=responsavel, project=regra.project, workspace_id=regra.workspace_id
                )
                for responsavel in regra.template_assignees.all()
            ],
            batch_size=100,
            ignore_conflicts=True,
        )
        IssueLabel.objects.bulk_create(
            [
                IssueLabel(issue=tarefa, label=etiqueta, project=regra.project, workspace_id=regra.workspace_id)
                for etiqueta in regra.template_labels.all()
            ],
            batch_size=100,
            ignore_conflicts=True,
        )

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


def processar_regra(regra, agora=None):
    """Gera o que estiver devido para uma regra. Devolve a tarefa criada, se houve."""
    agora = agora or timezone.now()

    if not regra.is_active or regra.next_run_at is None or regra.next_run_at > agora:
        return None
    if regra.skip_while_previous_open and _tem_ocorrencia_aberta(regra):
        # Não gera, mas anda com o relógio: senão a regra ficaria presa na data
        # antiga e dispararia tudo de uma vez quando alguém concluísse.
        RecurringWorkItem.objects.filter(pk=regra.pk).update(next_run_at=proxima_data(regra, agora))
        return None

    tarefa = _criar_ocorrencia(regra, regra.next_run_at)

    # Atraso não acumula: a próxima data é calculada a partir de AGORA, e não
    # da data vencida, então datas perdidas ficam para trás de propósito.
    regra.refresh_from_db(fields=["occurrences_created"])
    RecurringWorkItem.objects.filter(pk=regra.pk).update(next_run_at=proxima_data(regra, agora))
    return tarefa


@shared_task
def generate_recurring_work_items():
    """Job do beat: roda a cada 15 minutos."""
    agora = timezone.now()
    regras = RecurringWorkItem.objects.filter(
        is_active=True, next_run_at__isnull=False, next_run_at__lte=agora
    ).select_related("project")

    for regra in regras:
        try:
            processar_regra(regra, agora=agora)
        except Exception as erro:  # uma regra quebrada não pode parar as outras
            log_exception(erro)


def agendar_proxima_data(regra, a_partir_de=None):
    """Recalcula e grava o `next_run_at` — usado ao criar e ao editar a regra."""
    referencia = a_partir_de or timezone.now()
    inicio = datetime.combine(regra.start_date, regra.time_of_day, tzinfo=ZoneInfo(regra.project.timezone))
    # Regra que começa no futuro conta a partir do próprio começo; regra cujo
    # horário de hoje já passou não gera retroativamente — atraso não acumula.
    base = max(referencia, inicio.astimezone(ZoneInfo("UTC")) - timedelta(seconds=1))
    proxima = proxima_data(regra, base)
    RecurringWorkItem.objects.filter(pk=regra.pk).update(next_run_at=proxima)
    regra.next_run_at = proxima
    return proxima
