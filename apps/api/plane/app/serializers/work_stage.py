# Evolury: serializers das etapas pessoais de "Minhas tarefas".
# Ver docs/evolury/funcionalidades/minhas-tarefas/arquitetura.md.

# Module imports
from plane.db.models import WorkStage, WorkStageIssue

from .base import BaseSerializer


class WorkStageSerializer(BaseSerializer):
    class Meta:
        model = WorkStage
        fields = "__all__"
        # workspace/owner vêm sempre da rota e do request.user; is_default só
        # muda pelo endpoint mark-default, que garante exatamente uma padrão.
        read_only_fields = ["workspace", "owner", "is_default", "created_by", "updated_by", "deleted_at"]


class WorkStageIssueSerializer(BaseSerializer):
    class Meta:
        model = WorkStageIssue
        fields = "__all__"
        read_only_fields = ["workspace", "owner", "issue", "created_by", "updated_by", "deleted_at"]
