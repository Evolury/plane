# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Evolury: endpoints das tarefas recorrentes (ADR 0010).
#
# Só admin do projeto — a regra cria trabalho para os outros sem pedir licença,
# e é a mesma porta das Automações, ao lado das quais ela mora.

# Django imports
from django.utils import timezone

# Third party imports
from rest_framework import status
from rest_framework.response import Response

# Module imports
from plane.app.permissions import ROLE, allow_permission
from plane.app.serializers.recurring_work_item import RecurringWorkItemSerializer
from plane.app.views.base import BaseViewSet
from plane.bgtasks.recurring_work_item_task import agendar_proxima_data
from plane.db.models import RecurringWorkItem
from plane.utils.recurrence import proximas_datas


class RecurringWorkItemViewSet(BaseViewSet):
    serializer_class = RecurringWorkItemSerializer
    model = RecurringWorkItem

    def get_queryset(self):
        return (
            RecurringWorkItem.objects.filter(
                workspace__slug=self.kwargs.get("slug"), project_id=self.kwargs.get("project_id")
            )
            .select_related("project", "template_state")
            .prefetch_related("template_assignees", "template_labels")
        )

    @allow_permission(allowed_roles=[ROLE.ADMIN], level="PROJECT")
    def list(self, request, slug, project_id):
        serializer = RecurringWorkItemSerializer(self.get_queryset(), many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @allow_permission(allowed_roles=[ROLE.ADMIN], level="PROJECT")
    def create(self, request, slug, project_id):
        serializer = RecurringWorkItemSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        regra = serializer.save(project_id=project_id, workspace_id=self.workspace_id_from_slug(slug))
        # Sem isto a regra nasce sem relógio e o job nunca a enxerga.
        agendar_proxima_data(regra)
        return Response(RecurringWorkItemSerializer(regra).data, status=status.HTTP_201_CREATED)

    @allow_permission(allowed_roles=[ROLE.ADMIN], level="PROJECT")
    def partial_update(self, request, slug, project_id, pk):
        regra = self.get_queryset().filter(pk=pk).first()
        if regra is None:
            return Response({"error": "Tarefa recorrente não encontrada."}, status=status.HTTP_404_NOT_FOUND)

        serializer = RecurringWorkItemSerializer(regra, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        regra = serializer.save()
        # A agenda pode ter mudado; o relógio antigo não vale mais.
        agendar_proxima_data(regra)
        return Response(RecurringWorkItemSerializer(regra).data, status=status.HTTP_200_OK)

    @allow_permission(allowed_roles=[ROLE.ADMIN], level="PROJECT")
    def destroy(self, request, slug, project_id, pk):
        regra = self.get_queryset().filter(pk=pk).first()
        if regra is None:
            return Response({"error": "Tarefa recorrente não encontrada."}, status=status.HTTP_404_NOT_FOUND)
        # As tarefas já geradas ficam: elas são trabalho, não histórico da regra.
        regra.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @allow_permission(allowed_roles=[ROLE.ADMIN], level="PROJECT")
    def preview(self, request, slug, project_id):
        """As próximas datas de uma agenda que ainda não foi salva.

        É o que torna uma regra complexa confiável: em vez de decifrar
        "mensal, última sexta", a pessoa lê 28/08, 25/09, 30/10.
        """
        serializer = RecurringWorkItemSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        rascunho = RecurringWorkItem(
            **{campo: valor for campo, valor in serializer.validated_data.items() if campo not in ("template_assignees", "template_labels")}
        )
        rascunho.project_id = project_id
        datas = proximas_datas(rascunho, timezone.now(), quantidade=5)
        return Response({"next_occurrences": [data.isoformat() for data in datas]}, status=status.HTTP_200_OK)

    def workspace_id_from_slug(self, slug):
        from plane.db.models import Workspace

        return Workspace.objects.values_list("id", flat=True).get(slug=slug)
