# Evolury: endpoints de "Minhas tarefas" — etapas pessoais e listagem dos
# work items atribuídos ao usuário, agrupável por etapa.
#
# Regras estruturais (ADRs 0001/0002, docs/evolury/funcionalidades/minhas-tarefas/):
#   - toda consulta filtra owner=request.user — não existe parâmetro de usuário;
#   - mover de etapa é organização pessoal: este módulo não importa
#     issue_activity nem dispara webhook/notificação, deliberadamente;
#   - a listagem anota my_task_stage_id com Coalesce para a etapa padrão, o que
#     implementa a "primeira etapa" sem gravação na atribuição.

# Python imports
import copy

# Django imports
from django.db import IntegrityError, transaction
from django.db.models import F, Func, OuterRef, Q, Subquery, UUIDField, Value
from django.db.models.functions import Coalesce

# Third party imports
from rest_framework import status
from rest_framework.response import Response

# Module imports
from plane.app.permissions import ROLE, allow_permission
from plane.app.serializers import WorkStageIssueSerializer, WorkStageSerializer
from plane.app.views.base import BaseAPIView, BaseViewSet
from plane.db.models import (
    DEFAULT_WORK_STAGES,
    CycleIssue,
    FileAsset,
    Issue,
    IssueLink,
    Workspace,
    WorkStage,
    WorkStageIssue,
)
from plane.utils.filters import ComplexFilterBackend, IssueFilterSet
from plane.utils.grouper import issue_on_results, issue_queryset_grouper
from plane.utils.issue_filters import issue_filters
from plane.utils.order_queryset import order_issue_queryset
from plane.utils.paginator import GroupedOffsetPaginator


def ensure_default_work_stages(workspace, user):
    """Semeia as etapas padrão do usuário no workspace, uma única vez.

    Idempotente sob concorrência: se duas requisições passarem pelo exists()
    ao mesmo tempo, a segunda inserção viola a constraint de nome único e é
    absorvida — o seed de quem chegou primeiro vale.
    """
    if WorkStage.objects.filter(workspace=workspace, owner=user).exists():
        return
    try:
        with transaction.atomic():
            WorkStage.objects.bulk_create(
                [
                    WorkStage(
                        workspace=workspace,
                        owner=user,
                        created_by_id=user.id,
                        **stage,
                    )
                    for stage in DEFAULT_WORK_STAGES
                ]
            )
    except IntegrityError:
        pass


class WorkStageViewSet(BaseViewSet):
    serializer_class = WorkStageSerializer
    model = WorkStage

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(workspace__slug=self.kwargs.get("slug"))
            .filter(owner_id=self.request.user.id)
            .select_related("workspace", "owner")
        )

    @allow_permission(allowed_roles=[ROLE.ADMIN, ROLE.MEMBER], level="WORKSPACE")
    def list(self, request, slug):
        workspace = Workspace.objects.get(slug=slug)
        ensure_default_work_stages(workspace, request.user)
        serializer = WorkStageSerializer(self.get_queryset().order_by("sort_order"), many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @allow_permission(allowed_roles=[ROLE.ADMIN, ROLE.MEMBER], level="WORKSPACE")
    def create(self, request, slug):
        workspace = Workspace.objects.get(slug=slug)
        name = (request.data.get("name") or "").strip()
        if name and WorkStage.objects.filter(workspace=workspace, owner=request.user, name=name).exists():
            return Response(
                {"error": "Já existe uma etapa com esse nome."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = WorkStageSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(workspace_id=workspace.id, owner_id=request.user.id)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @allow_permission(allowed_roles=[ROLE.ADMIN, ROLE.MEMBER], level="WORKSPACE")
    def partial_update(self, request, slug, pk):
        stage = self.get_queryset().filter(pk=pk).first()
        if stage is None:
            return Response({"error": "Etapa não encontrada."}, status=status.HTTP_404_NOT_FOUND)
        name = (request.data.get("name") or "").strip()
        if name and WorkStage.objects.filter(
            workspace=stage.workspace, owner=request.user, name=name
        ).exclude(pk=stage.pk).exists():
            return Response(
                {"error": "Já existe uma etapa com esse nome."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = WorkStageSerializer(stage, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @allow_permission(allowed_roles=[ROLE.ADMIN, ROLE.MEMBER], level="WORKSPACE")
    def destroy(self, request, slug, pk):
        stage = self.get_queryset().filter(pk=pk).first()
        if stage is None:
            return Response({"error": "Etapa não encontrada."}, status=status.HTTP_404_NOT_FOUND)
        if stage.is_default:
            return Response(
                {"error": "A etapa padrão não pode ser excluída."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        default_stage = (
            WorkStage.objects.filter(workspace=stage.workspace, owner=request.user, is_default=True)
            .exclude(pk=stage.pk)
            .first()
        )
        if default_stage is None:
            # Só alcançável se o usuário criou etapas manualmente antes de
            # qualquer listagem (o seed nunca rodou): não há para onde migrar.
            return Response(
                {"error": "Defina uma etapa padrão antes de excluir."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        with transaction.atomic():
            # unique(owner, issue) garante que não há colisão: um item tem no
            # máximo uma associação, então migrar todas para a padrão é seguro.
            WorkStageIssue.objects.filter(stage=stage).update(stage=default_stage)
            stage.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @allow_permission(allowed_roles=[ROLE.ADMIN, ROLE.MEMBER], level="WORKSPACE")
    def mark_default(self, request, slug, pk):
        stage = self.get_queryset().filter(pk=pk).first()
        if stage is None:
            return Response({"error": "Etapa não encontrada."}, status=status.HTTP_404_NOT_FOUND)
        with transaction.atomic():
            # A constraint parcial exige desmarcar a antiga antes de marcar a
            # nova — a ordem das duas instruções não é opcional.
            WorkStage.objects.filter(workspace=stage.workspace, owner=request.user, is_default=True).update(
                is_default=False
            )
            WorkStage.objects.filter(pk=stage.pk).update(is_default=True)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MyTasksIssuesEndpoint(BaseAPIView):
    filter_backends = (ComplexFilterBackend,)
    filterset_class = IssueFilterSet

    def apply_annotations(self, issues):
        # Espelho das anotações do endpoint de perfil — os mesmos campos que o
        # issue_on_results serializa.
        return (
            issues.annotate(
                cycle_id=Subquery(
                    CycleIssue.objects.filter(issue=OuterRef("id"), deleted_at__isnull=True).values("cycle_id")[:1]
                )
            )
            .annotate(
                link_count=IssueLink.objects.filter(issue=OuterRef("id"))
                .order_by()
                .annotate(count=Func(F("id"), function="Count"))
                .values("count")
            )
            .annotate(
                attachment_count=FileAsset.objects.filter(
                    issue_id=OuterRef("id"),
                    entity_type=FileAsset.EntityTypeContext.ISSUE_ATTACHMENT,
                )
                .order_by()
                .annotate(count=Func(F("id"), function="Count"))
                .values("count")
            )
            .annotate(
                sub_issues_count=Issue.issue_objects.filter(parent=OuterRef("id"))
                .order_by()
                .annotate(count=Func(F("id"), function="Count"))
                .values("count")
            )
        )

    @allow_permission(allowed_roles=[ROLE.ADMIN, ROLE.MEMBER], level="WORKSPACE")
    def get(self, request, slug):
        workspace = Workspace.objects.get(slug=slug)
        ensure_default_work_stages(workspace, request.user)
        default_stage = WorkStage.objects.filter(workspace=workspace, owner=request.user, is_default=True).first()
        # None só se o usuário criou etapas manualmente antes de qualquer
        # listagem (seed nunca rodou): itens sem associação ficam com etapa
        # nula até uma etapa padrão ser definida.
        default_stage_id = default_stage.id if default_stage else None

        filters = issue_filters(request.query_params, "GET")
        order_by_param = request.GET.get("order_by", "-created_at")

        issue_queryset = Issue.issue_objects.filter(
            id__in=Issue.issue_objects.filter(
                Q(assignees__in=[request.user]) & Q(issue_assignee__deleted_at__isnull=True),
                workspace__slug=slug,
            ).values_list("id", flat=True),
            workspace__slug=slug,
            project__project_projectmember__member=request.user,
            project__project_projectmember__is_active=True,
        )

        issue_queryset = self.filter_queryset(issue_queryset)
        issue_queryset = issue_queryset.filter(**filters)

        total_issue_queryset = copy.deepcopy(issue_queryset)

        issue_queryset = self.apply_annotations(issue_queryset)
        # group_by=None de propósito: o agrupamento aqui é pela anotação
        # my_task_stage_id (abaixo), mas o grouper é quem anota os arrays
        # assignee_ids/label_ids/module_ids que o issue_on_results serializa.
        issue_queryset = issue_queryset_grouper(queryset=issue_queryset, group_by=None, sub_group_by=None)

        # A etapa é a anotação que torna o overlay um campo agrupável (ADR
        # 0002): associação quando existe, etapa padrão quando não.
        stage_subquery = WorkStageIssue.objects.filter(issue_id=OuterRef("id"), owner=request.user).values(
            "stage_id"
        )[:1]
        order_subquery = WorkStageIssue.objects.filter(issue_id=OuterRef("id"), owner=request.user).values(
            "sort_order"
        )[:1]
        issue_queryset = issue_queryset.annotate(
            my_task_stage_id=Coalesce(
                Subquery(stage_subquery, output_field=UUIDField()),
                Value(default_stage_id, output_field=UUIDField()),
            ),
            my_task_sort_order=Coalesce(Subquery(order_subquery), Value(65535.0)),
        )

        # Ordenação manual: o sort_order pessoal vive na associação, não no
        # item — o pedido de "sort_order" é traduzido para a anotação.
        if order_by_param in ["sort_order", "-sort_order"]:
            order_by_param = order_by_param.replace("sort_order", "my_task_sort_order")
            issue_queryset = issue_queryset.order_by(order_by_param, "created_at")
        else:
            issue_queryset, order_by_param = order_issue_queryset(
                issue_queryset=issue_queryset, order_by_param=order_by_param
            )

        def on_results(issues):
            # issue_on_results serializa a lista de campos fixa do upstream;
            # o campo anotado entra por enriquecimento para não duplicar (e
            # deixar de acompanhar) essa lista aqui.
            results = issue_on_results(issues=issues, group_by=None, sub_group_by=None)
            stage_map = dict(issues.values_list("id", "my_task_stage_id"))
            for result in results:
                result["my_task_stage_id"] = stage_map.get(result["id"])
            return results

        count_filter = Q(
            Q(issue_intake__status=1)
            | Q(issue_intake__status=-1)
            | Q(issue_intake__status=2)
            | Q(issue_intake__isnull=True),
            archived_at__isnull=True,
            is_draft=False,
        )

        group_by = request.GET.get("group_by", False)
        if group_by == "my_task_stage_id":
            stage_ids = list(
                WorkStage.objects.filter(workspace=workspace, owner=request.user).values_list("id", flat=True)
            )
            # O paginator vai pronto em vez de ser montado pelo paginate():
            # a ISSUE_GROUP_BY_ALLOWLIST guarda campos vindos do query param
            # contra injeção de nome de campo no ORM, e my_task_stage_id não
            # entra nela de propósito — só este endpoint anota o campo; nos
            # demais, o valor viraria FieldError. Aqui o nome é literal fixo,
            # exatamente o caso que a allowlist não precisa cobrir.
            paginator = GroupedOffsetPaginator(
                queryset=issue_queryset,
                order_by=order_by_param,
                group_by_field_name="my_task_stage_id",
                group_by_fields=stage_ids,
                count_filter=count_filter,
                total_count_queryset=total_issue_queryset,
            )
            return self.paginate(
                request=request,
                on_results=on_results,
                paginator=paginator,
                group_by_field_name="my_task_stage_id",
            )

        return self.paginate(
            request=request,
            order_by=order_by_param,
            queryset=issue_queryset,
            total_count_queryset=total_issue_queryset,
            on_results=on_results,
        )


class MyTasksIssueMoveEndpoint(BaseAPIView):
    @allow_permission(allowed_roles=[ROLE.ADMIN, ROLE.MEMBER], level="WORKSPACE")
    def post(self, request, slug, issue_id):
        stage_id = request.data.get("stage_id")
        if not stage_id:
            return Response({"error": "stage_id é obrigatório."}, status=status.HTTP_400_BAD_REQUEST)

        stage = WorkStage.objects.filter(workspace__slug=slug, owner=request.user, pk=stage_id).first()
        if stage is None:
            return Response({"error": "Etapa não encontrada."}, status=status.HTTP_404_NOT_FOUND)

        # O item precisa estar atribuído ao usuário e em projeto acessível —
        # os mesmos recortes da listagem.
        issue = Issue.issue_objects.filter(
            pk=issue_id,
            workspace__slug=slug,
            assignees__in=[request.user],
            issue_assignee__deleted_at__isnull=True,
            project__project_projectmember__member=request.user,
            project__project_projectmember__is_active=True,
        ).first()
        if issue is None:
            return Response({"error": "Work item não encontrado."}, status=status.HTTP_404_NOT_FOUND)

        defaults = {"stage": stage, "workspace_id": stage.workspace_id}
        sort_order = request.data.get("sort_order")
        if sort_order is not None:
            defaults["sort_order"] = sort_order

        try:
            association, _ = WorkStageIssue.objects.update_or_create(
                owner=request.user, issue=issue, defaults=defaults
            )
        except IntegrityError:
            # Corrida entre dois upserts do mesmo par (owner, issue): o
            # segundo vira update.
            association = WorkStageIssue.objects.get(owner=request.user, issue=issue)
            association.stage = stage
            if sort_order is not None:
                association.sort_order = sort_order
            association.save()

        serializer = WorkStageIssueSerializer(association)
        return Response(serializer.data, status=status.HTTP_200_OK)
