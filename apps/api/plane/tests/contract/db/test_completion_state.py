# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Destino do botão de concluir tarefa (ADR 0009).

O botão não cria caminho novo — ele só precisa saber para qual estado mover.
Estes testes fixam essa resolução e o recorte por projeto.
"""

import pytest

from plane.db.models import Project, State, get_completion_state


def _estado(projeto, workspace, nome, grupo, sequence):
    """Cria o estado e força o `sequence`.

    `State.save` reescreve o sequence ao criar (maior do projeto + 15000),
    então passar o valor no create não basta.
    """
    estado = State.objects.create(
        name=nome, group=grupo, project=projeto, workspace=workspace, color="#000"
    )
    State.objects.filter(pk=estado.pk).update(sequence=sequence)
    estado.refresh_from_db()
    return estado


def _projeto(workspace, user, nome, identificador):
    projeto = Project.objects.create(
        name=nome, identifier=identificador, workspace=workspace, project_lead=user
    )
    State.objects.filter(project=projeto).delete()
    return projeto


@pytest.mark.contract
class TestCompletionState:
    @pytest.mark.django_db
    def test_resolves_to_first_completed_state_by_sequence(self, workspace, create_user):
        """Sem configuração, usa o primeiro estado concluído na ordem da tela."""
        projeto = _projeto(workspace, create_user, "Automático", "AUT")
        _estado(projeto, workspace, "Entregue", "completed", 45000)
        primeiro = _estado(projeto, workspace, "Concluído", "completed", 15000)

        assert get_completion_state(projeto) == primeiro

    @pytest.mark.django_db
    def test_configured_state_wins(self, workspace, create_user):
        """Configurado explicitamente, é ele que manda."""
        projeto = _projeto(workspace, create_user, "Configurado", "CFG")
        _estado(projeto, workspace, "Concluído", "completed", 15000)
        escolhido = _estado(projeto, workspace, "Entregue", "completed", 45000)
        projeto.completion_state = escolhido
        projeto.save(update_fields=["completion_state"])

        assert get_completion_state(projeto) == escolhido

    @pytest.mark.django_db
    def test_ignores_configured_state_outside_completed_group(self, workspace, create_user):
        """Estado configurado fora do grupo concluído não vale — cai no automático.

        Protege contra um estado que teve o grupo alterado depois de escolhido.
        """
        projeto = _projeto(workspace, create_user, "Grupo trocado", "GRP")
        automatico = _estado(projeto, workspace, "Concluído", "completed", 15000)
        fora = _estado(projeto, workspace, "Em andamento", "started", 35000)
        projeto.completion_state = fora
        projeto.save(update_fields=["completion_state"])

        assert get_completion_state(projeto) == automatico

    @pytest.mark.django_db
    def test_never_borrows_state_from_another_project(self, workspace, create_user):
        """Projeto sem estado concluído devolve None, não o estado de outro."""
        vizinho = _projeto(workspace, create_user, "Vizinho", "VIZ")
        _estado(vizinho, workspace, "Concluído", "completed", 15000)
        vazio = _projeto(workspace, create_user, "Sem concluído", "SEM")
        _estado(vazio, workspace, "A fazer", "unstarted", 25000)

        assert get_completion_state(vazio) is None

    @pytest.mark.django_db
    def test_deleting_the_configured_state_falls_back(self, workspace, create_user):
        """Excluído o estado escolhido, a resolução volta ao automático.

        `State` é excluído logicamente, então o SET_NULL do banco não dispara e
        o projeto CONTINUA apontando para o estado excluído — quem precisa
        ignorá-lo é o resolvedor.
        """
        projeto = _projeto(workspace, create_user, "Excluído", "EXC")
        automatico = _estado(projeto, workspace, "Concluído", "completed", 15000)
        escolhido = _estado(projeto, workspace, "Entregue", "completed", 45000)
        projeto.completion_state = escolhido
        projeto.save(update_fields=["completion_state"])

        escolhido.delete()
        projeto.refresh_from_db()

        # a referência sobrevive à exclusão lógica...
        assert projeto.completion_state_id == escolhido.pk
        # ...mas não é usada como destino
        assert get_completion_state(projeto) == automatico
