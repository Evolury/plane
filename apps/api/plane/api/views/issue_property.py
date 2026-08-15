# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Leitura das definições de propriedade pela API pública (ADR 0011)."""

from plane.api.serializers.issue_property import IssuePropertyAPISerializer
from plane.app.permissions import ProjectEntityPermission
from plane.db.models import IssueProperty
from plane.utils.openapi import (
    CURSOR_PARAMETER,
    EXPAND_PARAMETER,
    FIELDS_PARAMETER,
    ORDER_BY_PARAMETER,
    PER_PAGE_PARAMETER,
    PROJECT_NOT_FOUND_RESPONSE,
    create_paginated_response,
    work_item_docs,
)

from .base import BaseAPIView


class IssuePropertyListAPIEndpoint(BaseAPIView):
    """Definições das propriedades personalizadas do projeto.

    Só leitura. Escrever definição é configuração de projeto, e as regras dela
    — nome único, tipo que não muda, moeda obrigatória em campo de moeda —
    vivem no caminho da tela. Um segundo caminho de escrita seria um segundo
    lugar para essas regras, e é sempre o segundo que esquece uma.
    """

    serializer_class = IssuePropertyAPISerializer
    model = IssueProperty
    permission_classes = [ProjectEntityPermission]
    use_read_replica = True

    def get_queryset(self):
        return (
            IssueProperty.objects.filter(
                workspace__slug=self.kwargs.get("slug"),
                project_id=self.kwargs.get("project_id"),
                project__project_projectmember__member=self.request.user,
                project__project_projectmember__is_active=True,
            )
            .prefetch_related("options")
            .distinct()
            .order_by("sort_order", "created_at")
        )

    @work_item_docs(
        operation_id="list_issue_properties",
        description=(
            "Retrieve the custom property definitions of a project — name, type, options and "
            "formatting. Use it to resolve the identifiers returned in a work item's "
            "`property_values`."
        ),
        parameters=[
            CURSOR_PARAMETER,
            PER_PAGE_PARAMETER,
            ORDER_BY_PARAMETER,
            FIELDS_PARAMETER,
            EXPAND_PARAMETER,
        ],
        responses={
            200: create_paginated_response(
                IssuePropertyAPISerializer,
                "PaginatedIssuePropertyResponse",
                "Paginated list of custom property definitions",
                "Paginated Issue Properties",
            ),
            404: PROJECT_NOT_FOUND_RESPONSE,
        },
    )
    def get(self, request, slug, project_id):
        """List custom property definitions

        Retrieve the custom property definitions of the project, in the order they
        are shown on screen.
        """
        return self.paginate(
            request=request,
            queryset=self.get_queryset(),
            on_results=lambda propriedades: IssuePropertyAPISerializer(
                propriedades, many=True, fields=self.fields, expand=self.expand
            ).data,
        )
