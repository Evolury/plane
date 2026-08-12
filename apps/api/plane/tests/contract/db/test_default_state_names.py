# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Nomes dos estados padrão em pt-BR e a migração 0127.

A migração renomeia apenas o que ainda está com o nome padrão em inglês:
projeto personalizado não é tocado, e projeto que já tem o nome de destino
fica de fora por causa da constraint (name, project).
"""

import importlib

import pytest
from django.apps import apps as django_apps

from plane.db.models import Project, State
from plane.db.models.state import DEFAULT_STATES

migration = importlib.import_module("plane.db.migrations.0127_evolury_default_state_names_pt_br")


@pytest.mark.contract
class TestDefaultStateNames:
    @pytest.mark.django_db
    def test_default_states_are_pt_br(self):
        """Projeto novo nasce com os cinco estados visíveis em pt-BR (+ triagem)."""
        names = [state["name"] for state in DEFAULT_STATES]
        assert names == ["Em espera", "A fazer", "Em andamento", "Concluído", "Cancelado", "Triagem"]

    @pytest.mark.django_db
    def test_migration_renames_english_defaults(self, workspace, create_user):
        """Estados ainda com o nome padrão em inglês passam para pt-BR."""
        project = Project.objects.create(
            name="Padrão", identifier="PAD", workspace=workspace, project_lead=create_user
        )
        State.objects.filter(project=project).delete()
        originais = [
            ("Backlog", "backlog"),
            ("Todo", "unstarted"),
            ("In Progress", "started"),
            ("Done", "completed"),
            ("Cancelled", "cancelled"),
        ]
        for name, group in originais:
            State.objects.create(name=name, group=group, project=project, workspace=workspace, color="#000")

        migration.rename_default_states(django_apps, None)

        renomeados = set(State.objects.filter(project=project).values_list("name", flat=True))
        assert renomeados == {"Em espera", "A fazer", "Em andamento", "Concluído", "Cancelado"}
        # o slug acompanha o nome (bulk_update não passa pelo save do modelo)
        em_espera = State.objects.get(project=project, name="Em espera")
        assert em_espera.slug == "em-espera"

    @pytest.mark.django_db
    def test_migration_preserves_customized_names(self, workspace, create_user):
        """Nome personalizado pelo usuário não é tocado."""
        project = Project.objects.create(
            name="Personalizado", identifier="PER", workspace=workspace, project_lead=create_user
        )
        State.objects.filter(project=project).delete()
        State.objects.create(name="Recentes", group="backlog", project=project, workspace=workspace, color="#000")
        State.objects.create(
            name="Em Planejamento", group="unstarted", project=project, workspace=workspace, color="#000"
        )

        migration.rename_default_states(django_apps, None)

        assert set(State.objects.filter(project=project).values_list("name", flat=True)) == {
            "Recentes",
            "Em Planejamento",
        }

    @pytest.mark.django_db
    def test_migration_skips_project_that_already_has_target_name(self, workspace, create_user):
        """Com o nome de destino já ocupado, o estado antigo fica como está.

        Renomear estouraria a constraint (name, project) — melhor deixar o
        projeto intacto do que quebrar a migração inteira.
        """
        project = Project.objects.create(
            name="Conflito", identifier="CON", workspace=workspace, project_lead=create_user
        )
        State.objects.filter(project=project).delete()
        State.objects.create(name="Backlog", group="backlog", project=project, workspace=workspace, color="#000")
        State.objects.create(name="Em espera", group="unstarted", project=project, workspace=workspace, color="#000")

        migration.rename_default_states(django_apps, None)

        assert set(State.objects.filter(project=project).values_list("name", flat=True)) == {
            "Backlog",
            "Em espera",
        }

    @pytest.mark.django_db
    def test_migration_is_idempotent(self, workspace, create_user):
        """Rodar duas vezes não muda nada na segunda."""
        project = Project.objects.create(
            name="Repetido", identifier="REP", workspace=workspace, project_lead=create_user
        )
        State.objects.filter(project=project).delete()
        State.objects.create(name="Done", group="completed", project=project, workspace=workspace, color="#000")

        migration.rename_default_states(django_apps, None)
        migration.rename_default_states(django_apps, None)

        assert list(State.objects.filter(project=project).values_list("name", flat=True)) == ["Concluído"]
