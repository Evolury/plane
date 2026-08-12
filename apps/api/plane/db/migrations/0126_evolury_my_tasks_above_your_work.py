# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Evolury: "Minhas tarefas" passa a ficar acima de "Minhas atividades"
# (your_work, antigo "Seu trabalho") na sidebar. As preferências já criadas
# nasceram com my_tasks ancorada logo ABAIXO de your_work; aqui os pares
# invertidos trocam de sort_order entre si — a troca preserva a posição do
# par em relação aos demais itens, respeitando reordenações manuais.

from django.db import migrations


def swap_my_tasks_above_your_work(apps, schema_editor):
    WorkspaceUserPreference = apps.get_model("db", "WorkspaceUserPreference")

    my_tasks_by_owner = {
        (pref.user_id, pref.workspace_id): pref
        for pref in WorkspaceUserPreference.objects.filter(key="my_tasks")
    }

    to_update = []
    for your_work in WorkspaceUserPreference.objects.filter(key="your_work"):
        my_tasks = my_tasks_by_owner.get((your_work.user_id, your_work.workspace_id))
        if my_tasks is not None and my_tasks.sort_order > your_work.sort_order:
            my_tasks.sort_order, your_work.sort_order = (your_work.sort_order, my_tasks.sort_order)
            to_update.extend([my_tasks, your_work])

    WorkspaceUserPreference.objects.bulk_update(to_update, ["sort_order"], batch_size=100)


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0125_evolury_work_stages"),
    ]

    operations = [
        migrations.RunPython(swap_my_tasks_above_your_work, migrations.RunPython.noop),
    ]
