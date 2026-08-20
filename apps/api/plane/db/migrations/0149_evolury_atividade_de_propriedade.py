# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Evolury: o histórico de propriedade personalizada volta a ser visível.
#
# Desde o ADR 0011 a mudança de valor sempre foi GRAVADA — com o nome da
# propriedade em `field` e o verbo genérico "updated". O que nunca existiu foi
# quem a desenhasse: as três telas de atividade despacham por campo conhecido e
# devolvem nada para o resto, então cada uma dessas linhas era escrita e
# engolida.
#
# A correção dá um verbo próprio às novas. Esta migração faz o mesmo com as
# antigas, para que o histórico já gravado apareça em vez de continuar invisível.
#
# O casamento é por (projeto, nome), e não só por nome: nome de propriedade é
# único DENTRO do projeto, e dois projetos podem ter "Canal" querendo dizer
# coisas diferentes.
#
# **Propriedade renomeada não é alcançada**, e é aceito: a linha antiga guarda o
# nome de quando a mudança aconteceu, e inventar um vínculo por semelhança seria
# adivinhar. Ela continua invisível, como está hoje — nada piora.

from django.db import migrations


def marcar(apps, schema_editor):
    # A regra mora em `plane/utils/issue_properties.py` para poder ser provada:
    # o `pytest.ini` roda com `--nomigrations`, então regra escrita só aqui não
    # é executada por teste nenhum (foi a lição da 0147).
    from plane.utils.issue_properties import marcar_atividades_de_propriedade

    marcar_atividades_de_propriedade(
        apps.get_model("db", "IssueActivity"),
        apps.get_model("db", "IssueProperty"),
    )


def desmarcar(apps, schema_editor):
    """Volta ao verbo genérico. O `new_identifier` fica: ele não atrapalha
    ninguém e é a única pista de qual propriedade a linha descreve."""
    IssueActivity = apps.get_model("db", "IssueActivity")
    IssueActivity.objects.filter(verb="property_updated").update(verb="updated")


class Migration(migrations.Migration):
    dependencies = [
        ("db", "0148_evolury_propriedade_no_agrupamento"),
    ]

    operations = [
        migrations.RunPython(marcar, desmarcar),
    ]
