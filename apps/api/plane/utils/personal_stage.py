# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Reflexo da conclusão nas etapas pessoais de "Minhas tarefas".

Exceção deliberada e de MÃO ÚNICA ao ADR 0001: o estado real do work item não
conhece a organização pessoal de ninguém, mas concluir é um fato compartilhado
— sem isto, a tarefa concluída ficaria parada em "Hoje" na lista de quem a tem
atribuída. O caminho contrário continua valendo: mover a etapa pessoal não
altera nada no projeto (ADR 0009).
"""

# Module imports
from plane.db.models import IssueAssignee, State, StateGroup, WorkStage, WorkStageIssue


def _etapa_de_conclusao(workspace_id, owner_id):
    """A primeira etapa do usuário no grupo concluído, na ordem da tela."""
    return (
        WorkStage.objects.filter(
            workspace_id=workspace_id,
            owner_id=owner_id,
            group=StateGroup.COMPLETED.value,
        )
        .order_by("sort_order")
        .first()
    )


def sync_personal_stages_on_completion(issue_id, previous_state_id, new_state_id):
    """Move a associação pessoal de cada responsável para a etapa de concluídas.

    Só age na ENTRADA no grupo concluído: quem já estava concluído não é
    reposicionado, e quem sai do grupo (reabertura) fica onde está — devolver a
    tarefa para a etapa anterior exigiria guardar de onde ela veio, e o ADR 0009
    fixou a mão única.

    Preserva quem já está numa etapa do grupo concluído: se a pessoa escolheu
    uma etapa própria de concluídas, é dela a última palavra.

    Usuários sem etapas semeadas não recebem associação nenhuma — a listagem
    resolve o implícito (item concluído sem associação aparece na etapa de
    concluídas), então não há nada a gravar.
    """
    # Os ids chegam como texto quando vêm da tarefa em segundo plano (JSON) e
    # como UUID quando vêm do código — comparar sem normalizar faz tudo virar
    # "não mudou nada".
    novo = str(new_state_id) if new_state_id else None
    anterior = str(previous_state_id) if previous_state_id else None
    if not novo or anterior == novo:
        return 0

    procurados = [novo] + ([anterior] if anterior else [])
    grupos = {
        str(pk): grupo for pk, grupo in State.all_objects.filter(pk__in=procurados).values_list("pk", "group")
    }
    if grupos.get(novo) != StateGroup.COMPLETED.value:
        return 0
    if anterior and grupos.get(anterior) == StateGroup.COMPLETED.value:
        return 0

    responsaveis = IssueAssignee.objects.filter(issue_id=issue_id).values_list("assignee_id", "workspace_id")
    movidas = 0
    for owner_id, workspace_id in responsaveis:
        etapa = _etapa_de_conclusao(workspace_id, owner_id)
        if etapa is None:
            continue

        associacao = WorkStageIssue.objects.filter(owner_id=owner_id, issue_id=issue_id).first()
        if associacao is None:
            WorkStageIssue.objects.create(
                workspace_id=workspace_id,
                owner_id=owner_id,
                stage=etapa,
                issue_id=issue_id,
            )
            movidas += 1
            continue

        if associacao.stage.group == StateGroup.COMPLETED.value:
            continue

        associacao.stage = etapa
        associacao.save(update_fields=["stage"])
        movidas += 1

    return movidas
