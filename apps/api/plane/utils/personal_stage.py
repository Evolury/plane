# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Reflexo do ciclo da tarefa nas etapas pessoais de "Minhas tarefas".

Exceção deliberada ao ADR 0001, e de mão única: o estado real do work item não
conhece a organização pessoal de ninguém, mas concluir, reabrir e cancelar são
fatos compartilhados — sem isto a tarefa concluída ficaria parada em "Hoje" na
lista de quem a tem atribuída, e a cancelada continuaria pedindo atenção. O
caminho contrário segue valendo: mover a etapa pessoal não altera nada no
projeto (ADR 0009).

A regra é a mesma que o projeto usa nos seus estados, traduzida para etapas:

- entrou no grupo concluído  → etapa de conclusão (a marcada, senão a primeira)
- entrou no grupo cancelado  → primeira etapa do grupo cancelado
- voltou para um grupo aberto → etapa padrão, como uma tarefa recém-atribuída
"""

# Module imports
from plane.db.models import IssueAssignee, State, StateGroup, WorkStage, WorkStageIssue

GRUPOS_ENCERRADOS = (StateGroup.COMPLETED.value, StateGroup.CANCELLED.value)


def _etapa_de_conclusao(workspace_id, owner_id):
    """A etapa marcada como destino da conclusão, ou a primeira do grupo."""
    concluidas = WorkStage.objects.filter(
        workspace_id=workspace_id, owner_id=owner_id, group=StateGroup.COMPLETED.value
    )
    return concluidas.filter(is_completion=True).first() or concluidas.order_by("sort_order").first()


def _etapa_de_cancelamento(workspace_id, owner_id):
    """A primeira etapa do grupo cancelado, na ordem da tela."""
    return (
        WorkStage.objects.filter(
            workspace_id=workspace_id, owner_id=owner_id, group=StateGroup.CANCELLED.value
        )
        .order_by("sort_order")
        .first()
    )


def _etapa_padrao(workspace_id, owner_id):
    return WorkStage.objects.filter(workspace_id=workspace_id, owner_id=owner_id, is_default=True).first()


def _destino(grupo_novo, workspace_id, owner_id):
    if grupo_novo == StateGroup.COMPLETED.value:
        return _etapa_de_conclusao(workspace_id, owner_id)
    if grupo_novo == StateGroup.CANCELLED.value:
        return _etapa_de_cancelamento(workspace_id, owner_id)
    return _etapa_padrao(workspace_id, owner_id)


def sync_personal_stages_on_completion(issue_id, previous_state_id, new_state_id):
    """Reposiciona a associação pessoal de cada responsável.

    Age quando a tarefa ENTRA ou SAI de um grupo encerrado. Trocar de estado
    dentro do mesmo grupo não mexe em nada — quem arrastou a tarefa depois de
    concluída fica onde escolheu.

    Preserva quem já está numa etapa do grupo de destino: se a pessoa escolheu
    uma etapa própria de concluídas, é dela a última palavra.

    Usuários sem a etapa de destino não recebem associação nenhuma — a listagem
    resolve o implícito, então não há o que gravar.
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
    grupo_novo = grupos.get(novo)
    grupo_anterior = grupos.get(anterior) if anterior else None
    if grupo_novo is None or grupo_novo == grupo_anterior:
        return 0

    # Só as travessias que mudam o "capítulo" da tarefa: entrar num grupo
    # encerrado, ou sair de um. Andar entre grupos abertos é fluxo de trabalho
    # do projeto, e não diz nada sobre a organização pessoal de ninguém.
    entrou_em_encerrado = grupo_novo in GRUPOS_ENCERRADOS
    saiu_de_encerrado = grupo_anterior in GRUPOS_ENCERRADOS
    if not entrou_em_encerrado and not saiu_de_encerrado:
        return 0

    responsaveis = IssueAssignee.objects.filter(issue_id=issue_id).values_list("assignee_id", "workspace_id")
    movidas = 0
    for owner_id, workspace_id in responsaveis:
        etapa = _destino(grupo_novo, workspace_id, owner_id)
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

        if associacao.stage.group == grupo_novo:
            continue

        associacao.stage = etapa
        associacao.save(update_fields=["stage"])
        movidas += 1

    return movidas
