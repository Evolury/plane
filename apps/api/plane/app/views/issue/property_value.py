# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Evolury: valores de propriedade personalizada numa tarefa (ADR 0011, P2).
#
# Escrever valor é de quem pode editar a tarefa — não é porta de admin. Quem é
# porta de admin é CONFIGURAR a propriedade, porque isso cria trabalho para os
# outros; preencher o campo é o trabalho.

# Django imports
from django.utils import timezone

# Third party imports
from rest_framework import status
from rest_framework.response import Response

# Module imports
from plane.app.permissions import ROLE, allow_permission
from plane.app.views.base import BaseViewSet
from plane.db.models import Issue, IssueActivity, IssueProperty
from plane.utils.issue_properties import (
    ValorInvalido,
    gravar_valor,
    propriedades_ativas,
    rotulo_do_valor,
    valores_por_tarefa,
)


class IssuePropertyValueViewSet(BaseViewSet):
    model = IssueProperty

    @allow_permission(allowed_roles=[ROLE.ADMIN, ROLE.MEMBER, ROLE.GUEST], level="PROJECT")
    def list(self, request, slug, project_id, issue_id):
        """As propriedades ativas do projeto e o que esta tarefa tem preenchido.

        As duas coisas juntas, e numa ida só: a tela precisa das definições
        para desenhar os campos e dos valores para preenchê-los, e separá-las
        seria uma segunda chamada para montar uma seção.
        """
        propriedades = propriedades_ativas(project_id)
        valores = valores_por_tarefa([issue_id]).get(issue_id, {})
        return Response(
            {
                "properties": [
                    {
                        "id": str(p.id),
                        "name": p.name,
                        "property_type": p.property_type,
                        "is_required": p.is_required,
                        "show_on_card": p.show_on_card,
                        "currency": p.currency,
                        "decimal_places": p.decimal_places,
                        "options": [{"id": str(o.id), "name": o.name, "color": o.color} for o in p.options.all()],
                    }
                    for p in propriedades
                ],
                "values": valores,
            },
            status=status.HTTP_200_OK,
        )

    @allow_permission(allowed_roles=[ROLE.ADMIN, ROLE.MEMBER], level="PROJECT")
    def create(self, request, slug, project_id, issue_id):
        """Grava (ou apaga, com vazio) o valor de uma propriedade."""
        tarefa = Issue.objects.filter(pk=issue_id, project_id=project_id).first()
        if tarefa is None:
            return Response({"error": "Tarefa não encontrada."}, status=status.HTTP_404_NOT_FOUND)

        propriedade = IssueProperty.objects.filter(
            pk=request.data.get("property"), project_id=project_id, is_active=True
        ).first()
        if propriedade is None:
            return Response(
                {"property": "Propriedade não encontrada neste projeto."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        anterior = valores_por_tarefa([tarefa.id]).get(tarefa.id, {}).get(str(propriedade.id))
        novo = request.data.get("value")
        try:
            gravar_valor(tarefa, propriedade, novo)
        except ValorInvalido as erro:
            return Response({"value": str(erro)}, status=status.HTTP_400_BAD_REQUEST)

        self._registrar_atividade(tarefa, propriedade, anterior, novo, request.user.id)
        return Response(
            {"property": str(propriedade.id), "value": novo},
            status=status.HTTP_200_OK,
        )

    def _registrar_atividade(self, tarefa, propriedade, anterior, novo, actor_id):
        """A mudança de valor entra no histórico da tarefa.

        A tarefa passou a carregar informação de negócio, e mudança sem
        histórico é buraco no rastro (ADR 0011). O que se grava é o RÓTULO, e
        não o id da opção — id não diz nada a quem lê seis meses depois.
        """
        de = rotulo_do_valor(propriedade, anterior)
        para = rotulo_do_valor(propriedade, novo)
        if de == para:
            return
        IssueActivity.objects.create(
            issue=tarefa,
            actor_id=actor_id,
            verb="updated",
            old_value=de,
            new_value=para,
            # O nome da propriedade é o campo: é o que o histórico precisa
            # dizer, e ele é do projeto de quem lê.
            field=propriedade.name,
            project_id=tarefa.project_id,
            workspace_id=tarefa.workspace_id,
            comment=f"alterou {propriedade.name} para",
            epoch=int(timezone.now().timestamp()),
        )
