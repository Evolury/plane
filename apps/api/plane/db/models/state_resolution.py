# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Evolury: resolve para onde o botão de concluir move a tarefa (ADR 0009).
# Mora junto do modelo porque tanto a API quanto as tarefas em segundo plano
# precisam da mesma resposta.

from .state import State, StateGroup


def get_completion_state(project):
    """Estado de conclusão do projeto, ou None se ele não tiver nenhum.

    Usa `project.completion_state` quando configurado; senão, o primeiro
    estado do grupo concluído DO PRÓPRIO PROJETO — a ordem que o usuário vê
    na tela de estados é `sequence`, então o primeiro dela é o destino menos
    surpreendente.
    """
    escolhido = project.completion_state
    # `State` é excluído logicamente, então o SET_NULL do banco nunca dispara:
    # depois de excluir o estado escolhido, o projeto continua apontando para
    # ele. Por isso o `deleted_at` entra na checagem, junto do grupo — que pode
    # ter sido alterado depois da escolha.
    if escolhido is not None and escolhido.deleted_at is None and escolhido.group == StateGroup.COMPLETED.value:
        return escolhido

    return (
        State.objects.filter(project=project, group=StateGroup.COMPLETED.value)
        .order_by("sequence")
        .first()
    )
