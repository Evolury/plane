# Copyright (c) 2023-present Plane Software, Inc. and contributors
# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Evolury: serializers das etapas pessoais de "Minhas tarefas".
# Ver docs/evolury/funcionalidades/minhas-tarefas/arquitetura.md.

# Module imports
from plane.db.models import WorkStage, WorkStageIssue

from .base import BaseSerializer


class WorkStageSerializer(BaseSerializer):
    class Meta:
        model = WorkStage
        fields = "__all__"
        # workspace/owner vêm sempre da rota e do request.user; is_default e
        # is_completion só mudam pelos endpoints mark-default e
        # mark-completion, que garantem exatamente uma de cada.
        read_only_fields = [
            "workspace",
            "owner",
            "is_default",
            "is_completion",
            "created_by",
            "updated_by",
            "deleted_at",
        ]


class WorkStageIssueSerializer(BaseSerializer):
    class Meta:
        model = WorkStageIssue
        fields = "__all__"
        read_only_fields = ["workspace", "owner", "issue", "created_by", "updated_by", "deleted_at"]
