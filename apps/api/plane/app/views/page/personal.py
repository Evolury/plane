# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Evolury — páginas pessoais de "Minhas tarefas".

Uma página pessoal é uma `Page` do workspace **sem** vínculo ativo em
`ProjectPage`. O modelo já permitia isso: `Page.workspace` é FK direta e
`Page.projects` é M2M através de `ProjectPage`. Ver ADR 0015.

Quem manda é o dono. Não há papel de projeto para consultar, e papel de
workspace não vale: administrador de workspace não lê o caderno pessoal de
ninguém.
"""

# Python imports
import json
from datetime import datetime

# Django imports
from django.contrib.postgres.aggregates import ArrayAgg
from django.contrib.postgres.fields import ArrayField
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Exists, OuterRef, Q, UUIDField, Value
from django.db.models.functions import Coalesce
from django.http import StreamingHttpResponse

# Third party imports
from rest_framework import status
from rest_framework.response import Response

# Module imports
from plane.app.permissions import PersonalPagePermission
from plane.app.serializers import (
    PageBinaryUpdateSerializer,
    PageDetailSerializer,
    PageSerializer,
    PageVersionDetailSerializer,
    PageVersionSerializer,
)
from plane.bgtasks.copy_s3_object import copy_s3_objects_of_description_and_assets
from plane.bgtasks.page_transaction_task import page_transaction
from plane.bgtasks.page_version_task import track_page_version
from plane.bgtasks.recent_visited_task import recent_visited_task
from plane.db.models import (
    Page,
    PageLog,
    PageVersion,
    ProjectPage,
    UserFavorite,
    UserRecentVisit,
    Workspace,
)
from plane.utils.error_codes import ERROR_CODES

from ..base import BaseAPIView, BaseViewSet
from .base import unarchive_archive_page_and_descendants


def paginas_pessoais(slug, user):
    """Páginas do workspace que são de `user` e não estão em projeto nenhum.

    O vínculo com projeto é apagado por soft delete, então "sem projeto" tem de
    ser `~Exists(ProjectPage.objects...)` — o gerenciador padrão já descarta as
    linhas apagadas. Um `project_pages__isnull=True` traria de volta a página
    que já esteve num projeto, porque junção em SQL não passa por gerenciador.
    """
    return (
        Page.objects.filter(workspace__slug=slug, owned_by=user)
        .annotate(em_projeto=Exists(ProjectPage.objects.filter(page_id=OuterRef("pk"))))
        .filter(em_projeto=False)
    )


class PersonalPageViewSet(BaseViewSet):
    serializer_class = PageSerializer
    model = Page
    permission_classes = [PersonalPagePermission]
    search_fields = ["name"]

    def get_queryset(self):
        favorita = UserFavorite.objects.filter(
            user=self.request.user,
            entity_type="page",
            entity_identifier=OuterRef("pk"),
            workspace__slug=self.kwargs.get("slug"),
        )
        return self.filter_queryset(
            paginas_pessoais(self.kwargs.get("slug"), self.request.user)
            .filter(parent__isnull=True)
            .select_related("workspace", "owned_by")
            .prefetch_related("labels")
            .annotate(is_favorite=Exists(favorita))
            .annotate(
                label_ids=Coalesce(
                    ArrayAgg(
                        "page_labels__label_id",
                        distinct=True,
                        filter=~Q(page_labels__label_id__isnull=True),
                    ),
                    Value([], output_field=ArrayField(UUIDField())),
                ),
                project_ids=Value([], output_field=ArrayField(UUIDField())),
            )
            .order_by("-is_favorite", "-created_at")
            .distinct()
        )

    def list(self, request, slug):
        return Response(PageSerializer(self.get_queryset(), many=True).data, status=status.HTTP_200_OK)

    def create(self, request, slug):
        workspace = Workspace.objects.filter(slug=slug).first()
        if workspace is None:
            return Response({"error": "Workspace não encontrado"}, status=status.HTTP_404_NOT_FOUND)

        serializer = PageSerializer(
            data=request.data,
            context={
                "workspace_id": workspace.id,
                "owned_by_id": request.user.id,
                "description_json": request.data.get("description_json", {}),
                "description_binary": request.data.get("description_binary", None),
                "description_html": request.data.get("description_html", "<p></p>"),
            },
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()
        page_transaction.delay(
            new_description_html=request.data.get("description_html", "<p></p>"),
            old_description_html=None,
            page_id=serializer.data["id"],
        )
        page = self.get_queryset().get(pk=serializer.data["id"])
        return Response(PageDetailSerializer(page).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, slug, page_id=None):
        page = self.get_queryset().filter(pk=page_id).first()
        if page is None:
            return Response({"error": "Página não encontrada"}, status=status.HTTP_404_NOT_FOUND)

        data = PageDetailSerializer(page).data
        data["issue_ids"] = PageLog.objects.filter(page_id=page_id, entity_name="issue").values_list(
            "entity_identifier", flat=True
        )
        if request.query_params.get("track_visit", "true").lower() == "true":
            recent_visited_task.delay(
                slug=slug,
                entity_name="page",
                entity_identifier=page_id,
                user_id=request.user.id,
                project_id=None,
            )
        return Response(data, status=status.HTTP_200_OK)

    def partial_update(self, request, slug, page_id):
        page = request.pagina_pessoal

        if page.is_locked:
            return Response({"error": "Página bloqueada"}, status=status.HTTP_400_BAD_REQUEST)

        parent = request.data.get("parent", None)
        if parent and not paginas_pessoais(slug, request.user).filter(pk=parent).exists():
            return Response({"error": "Página mãe não encontrada"}, status=status.HTTP_400_BAD_REQUEST)

        descricao_anterior = page.description_html
        serializer = PageDetailSerializer(page, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()
        if request.data.get("description_html"):
            page_transaction.delay(
                new_description_html=request.data.get("description_html", "<p></p>"),
                old_description_html=descricao_anterior,
                page_id=page_id,
            )
        return Response(serializer.data, status=status.HTTP_200_OK)

    def lock(self, request, slug, page_id):
        page = request.pagina_pessoal
        page.is_locked = True
        page.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def unlock(self, request, slug, page_id):
        page = request.pagina_pessoal
        page.is_locked = False
        page.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def archive(self, request, slug, page_id):
        UserFavorite.objects.filter(
            entity_type="page", entity_identifier=page_id, workspace__slug=slug
        ).delete()
        unarchive_archive_page_and_descendants(page_id, datetime.now())
        return Response({"archived_at": str(datetime.now())}, status=status.HTTP_200_OK)

    def unarchive(self, request, slug, page_id):
        page = request.pagina_pessoal
        # Desarquivar filha de mãe arquivada quebraria a hierarquia.
        if page.parent_id and page.parent.archived_at:
            page.parent = None
            page.save(update_fields=["parent"])
        unarchive_archive_page_and_descendants(page_id, None)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def destroy(self, request, slug, page_id):
        page = request.pagina_pessoal

        if page.archived_at is None:
            return Response(
                {"error": "A página precisa ser arquivada antes de excluída"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        Page.objects.filter(parent_id=page_id, workspace__slug=slug).update(parent=None)
        page.delete()
        UserFavorite.objects.filter(
            workspace__slug=slug, entity_identifier=page_id, entity_type="page"
        ).delete()
        UserRecentVisit.objects.filter(
            workspace__slug=slug, entity_identifier=page_id, entity_name="page"
        ).delete(soft=False)
        return Response(status=status.HTTP_204_NO_CONTENT)


class PersonalPageDescriptionViewSet(BaseViewSet):
    permission_classes = [PersonalPagePermission]

    def retrieve(self, request, slug, page_id):
        binario = request.pagina_pessoal.description_binary

        def fluxo():
            yield binario if binario else b""

        resposta = StreamingHttpResponse(fluxo(), content_type="application/octet-stream")
        resposta["Content-Disposition"] = 'attachment; filename="page_description.bin"'
        return resposta

    def partial_update(self, request, slug, page_id):
        page = request.pagina_pessoal

        if page.is_locked:
            return Response(
                {"error_code": ERROR_CODES["PAGE_LOCKED"], "error_message": "PAGE_LOCKED"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if page.archived_at:
            return Response(
                {"error_code": ERROR_CODES["PAGE_ARCHIVED"], "error_message": "PAGE_ARCHIVED"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        descricao_anterior = page.description_html
        instancia = json.dumps({"description_html": descricao_anterior}, cls=DjangoJSONEncoder)

        serializer = PageBinaryUpdateSerializer(page, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()
        if request.data.get("description_html"):
            page_transaction.delay(
                new_description_html=request.data.get("description_html", "<p></p>"),
                old_description_html=descricao_anterior,
                page_id=page_id,
            )
        track_page_version.delay(page_id=page_id, existing_instance=instancia, user_id=request.user.id)
        return Response({"message": "Updated successfully"})


class PersonalPageVersionEndpoint(BaseAPIView):
    permission_classes = [PersonalPagePermission]

    def get(self, request, slug, page_id, pk=None):
        if pk:
            versao = PageVersion.objects.filter(workspace__slug=slug, page_id=page_id, pk=pk).first()
            if versao is None:
                return Response({"error": "Versão não encontrada"}, status=status.HTTP_404_NOT_FOUND)
            return Response(PageVersionDetailSerializer(versao).data, status=status.HTTP_200_OK)

        versoes = PageVersion.objects.filter(workspace__slug=slug, page_id=page_id)
        return Response(PageVersionSerializer(versoes, many=True).data, status=status.HTTP_200_OK)


class PersonalPageDuplicateEndpoint(BaseAPIView):
    permission_classes = [PersonalPagePermission]

    def post(self, request, slug, page_id):
        page = request.pagina_pessoal

        page.pk = None
        page.name = f"{page.name} (Cópia)"
        page.description_binary = None
        page.owned_by = request.user
        page.created_by = request.user
        page.updated_by = request.user
        page.save()

        page_transaction.delay(
            new_description_html=page.description_html, old_description_html=None, page_id=page.id
        )

        # Anexo de página pessoal sobe pela rota de workspace e nasce com
        # project_id nulo — que é exatamente o filtro que copy_assets aplica.
        copy_s3_objects_of_description_and_assets.delay(
            entity_name="PAGE",
            entity_identifier=page.id,
            project_id=None,
            slug=slug,
            user_id=request.user.id,
        )

        copia = (
            Page.objects.filter(pk=page.id)
            .annotate(project_ids=Value([], output_field=ArrayField(UUIDField())))
            .first()
        )
        return Response(PageDetailSerializer(copia).data, status=status.HTTP_201_CREATED)
