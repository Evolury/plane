# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Evolury: os nomes dos estados criados por padrão passaram a ser pt-BR
# (DEFAULT_STATES). Aqui os projetos já existentes acompanham — mas só os
# que continuam com o nome padrão em inglês: renomear é mexer em conteúdo
# do usuário, então quem personalizou não é tocado.
#
# Casamos nome + grupo para não renomear um estado que só por coincidência
# se chama "Done" em outro grupo. Projetos que já tenham um estado com o
# nome de destino ficam de fora: (name, project) é único enquanto
# deleted_at é nulo, e a renomeação estouraria a constraint.

from django.db import migrations
from django.template.defaultfilters import slugify

RENAMES = [
    ("Backlog", "backlog", "Em espera"),
    ("Todo", "unstarted", "A fazer"),
    ("In Progress", "started", "Em andamento"),
    ("Done", "completed", "Concluído"),
    ("Cancelled", "cancelled", "Cancelado"),
    ("Triage", "triage", "Triagem"),
]


def rename_default_states(apps, schema_editor):
    State = apps.get_model("db", "State")

    for old_name, group, new_name in RENAMES:
        occupied_projects = set(
            State.objects.filter(name=new_name, deleted_at__isnull=True).values_list("project_id", flat=True)
        )

        to_rename = list(
            State.objects.filter(name=old_name, group=group, deleted_at__isnull=True).exclude(
                project_id__in=occupied_projects
            )
        )
        for state in to_rename:
            state.name = new_name
            # slug acompanha o nome (State.save faz isso; bulk_update não passa por lá)
            state.slug = slugify(new_name)

        State.objects.bulk_update(to_rename, ["name", "slug"], batch_size=200)


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0126_evolury_my_tasks_above_your_work"),
    ]

    operations = [
        # Sem reversão automática: o nome pode ter sido editado depois, e
        # devolver "Backlog" a quem nunca o teve seria pior que não reverter.
        migrations.RunPython(rename_default_states, migrations.RunPython.noop),
    ]
