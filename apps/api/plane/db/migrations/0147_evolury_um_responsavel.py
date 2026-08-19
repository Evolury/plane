# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Evolury — uma tarefa tem um responsável, e nunca mais de um (ADR 0016).

O colapso vem antes das travas: sem ele, a migração quebraria em qualquer banco
que já tenha tarefa com dois. Fica o **mais recente**, mesma regra que as portas
de escrita passam a aplicar.
"""

from django.db import migrations, models
from django.utils import timezone

from plane.utils.responsavel import excedentes


def colapsar(apps, schema_editor):
    """Deixa um responsável por tarefa e por rascunho; o resto sai por soft delete."""
    agora = timezone.now()
    for modelo, dono in (("IssueAssignee", "issue_id"), ("DraftIssueAssignee", "draft_issue_id")):
        Atribuicao = apps.get_model("db", modelo)
        # A regra de quem sobrevive mora em `excedentes()` porque a suíte roda
        # com `--nomigrations` e nunca executa este arquivo: sem extrair, a
        # decisão ficaria sem teste.
        a_apagar = excedentes(
            Atribuicao.objects.filter(deleted_at__isnull=True).values_list("id", dono, "created_at")
        )
        if a_apagar:
            Atribuicao.objects.filter(id__in=a_apagar).update(deleted_at=agora)


def nao_desfaz(apps, schema_editor):
    """Sem volta: quem foi apagado não se distingue de quem já estava apagado antes."""


class Migration(migrations.Migration):
    dependencies = [("db", "0146_evolury_compartilhamento_de_pagina")]

    operations = [
        migrations.RunPython(colapsar, nao_desfaz),
        migrations.AddConstraint(
            model_name="draftissueassignee",
            constraint=models.UniqueConstraint(
                condition=models.Q(("deleted_at__isnull", True)),
                fields=("draft_issue",),
                name="draft_issue_assignee_um_responsavel_por_rascunho",
            ),
        ),
        migrations.AddConstraint(
            model_name="issueassignee",
            constraint=models.UniqueConstraint(
                condition=models.Q(("deleted_at__isnull", True)),
                fields=("issue",),
                name="issue_assignee_um_responsavel_por_tarefa",
            ),
        ),
    ]
