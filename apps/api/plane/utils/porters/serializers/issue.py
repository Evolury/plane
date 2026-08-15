# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Third party imports
from rest_framework import serializers

# Evolury: propriedades personalizadas (ADR 0011)
from plane.utils.issue_properties import propriedades_ativas, rotulo_do_valor, valores_por_tarefa

# Module imports
from plane.app.serializers import IssueSerializer


# Evolury: propriedades personalizadas na exportação (ADR 0011, P3).
#
# Dado que só existe dentro da tela é dado preso — a exportação entrou na v1
# por princípio, e não como sobra.
#
# O gancho é o `ListSerializer` porque é ele que enxerga o CONJUNTO: uma
# consulta para todas as tarefas do arquivo, em vez de uma por linha. O
# `to_representation` de cada tarefa só lê o que já veio.
#
# As colunas nascem do dicionário de cada registro — o formatador de CSV deriva
# os cabeçalhos das chaves —, então uma propriedade nova vira coluna nova sem
# ninguém declarar nada.
class IssueExportListSerializer(serializers.ListSerializer):
    def to_representation(self, data):
        tarefas = list(data)
        projetos = {t.project_id for t in tarefas}
        propriedades = []
        for projeto in projetos:
            propriedades.extend(propriedades_ativas(projeto))
        self.child._propriedades_de_exportacao = propriedades
        self.child._valores_de_exportacao = valores_por_tarefa([t.id for t in tarefas]) if propriedades else {}
        return super().to_representation(tarefas)


class IssueExportSerializer(IssueSerializer):
    """
    Export-optimized serializer that extends IssueSerializer with human-readable fields.

    Converts UUIDs to readable values for CSV/JSON export.
    """

    identifier = serializers.SerializerMethodField()
    project_name = serializers.CharField(source="project.name", read_only=True, default="")
    project_identifier = serializers.CharField(source="project.identifier", read_only=True, default="")
    state_name = serializers.CharField(source="state.name", read_only=True, default="")
    created_by_name = serializers.CharField(source="created_by.full_name", read_only=True, default="")

    assignees = serializers.SerializerMethodField()
    parent = serializers.SerializerMethodField()
    labels = serializers.SerializerMethodField()
    cycles = serializers.SerializerMethodField()
    modules = serializers.SerializerMethodField()
    comments = serializers.SerializerMethodField()
    estimate = serializers.SerializerMethodField()
    links = serializers.SerializerMethodField()
    relations = serializers.SerializerMethodField()
    subscribers = serializers.SerializerMethodField()

    class Meta(IssueSerializer.Meta):
        list_serializer_class = IssueExportListSerializer
        fields = [
            "project_name",
            "project_identifier",
            "parent",
            "identifier",
            "sequence_id",
            "name",
            "state_name",
            "priority",
            "assignees",
            "subscribers",
            "created_by_name",
            "start_date",
            "target_date",
            "completed_at",
            "created_at",
            "updated_at",
            "archived_at",
            "estimate",
            "labels",
            "cycles",
            "modules",
            "links",
            "relations",
            "comments",
            "sub_issues_count",
            "link_count",
            "attachment_count",
            "is_draft",
        ]

    def to_representation(self, instance):
        """Acrescenta uma coluna por propriedade personalizada do projeto.

        O valor sai como TEXTO legível — nome da opção, moeda junto do número —
        porque exportação é para gente ler, e id de opção numa planilha não diz
        nada a ninguém.
        """
        dados = super().to_representation(instance)
        propriedades = getattr(self, "_propriedades_de_exportacao", None)
        if not propriedades:
            return dados
        valores = getattr(self, "_valores_de_exportacao", {}) or {}
        meus = valores.get(instance.id, {})
        for propriedade in propriedades:
            if propriedade.project_id != instance.project_id:
                continue
            dados[propriedade.name] = rotulo_do_valor(propriedade, meus.get(str(propriedade.id)))
        return dados

    def get_identifier(self, obj):
        return f"{obj.project.identifier}-{obj.sequence_id}"

    def get_assignees(self, obj):
        return [u.full_name for u in obj.assignees.all() if u.is_active]

    def get_subscribers(self, obj):
        """Return list of subscriber names."""
        return [sub.subscriber.full_name for sub in obj.issue_subscribers.all() if sub.subscriber]

    def get_parent(self, obj):
        if not obj.parent:
            return ""
        return f"{obj.parent.project.identifier}-{obj.parent.sequence_id}"

    def get_labels(self, obj):
        return [il.label.name for il in obj.label_issue.all() if il.deleted_at is None]

    def get_cycles(self, obj):
        return [ic.cycle.name for ic in obj.issue_cycle.all()]

    def get_modules(self, obj):
        return [im.module.name for im in obj.issue_module.all()]

    def get_estimate(self, obj):
        """Return estimate point value."""
        if obj.estimate_point:
            return obj.estimate_point.value if hasattr(obj.estimate_point, "value") else str(obj.estimate_point)
        return ""

    def get_links(self, obj):
        """Return list of issue links with titles."""
        return [
            {
                "url": link.url,
                "title": link.title if link.title else link.url,
            }
            for link in obj.issue_link.all()
        ]

    def get_relations(self, obj):
        """Return list of related issues."""
        relations = []

        # Outgoing relations (this issue relates to others)
        for rel in obj.issue_relation.all():
            if rel.related_issue:
                relations.append(
                    {
                        "type": rel.relation_type if hasattr(rel, "relation_type") else "related",
                        "issue": f"{rel.related_issue.project.identifier}-{rel.related_issue.sequence_id}",
                        "direction": "outgoing",
                    }
                )

        # Incoming relations (other issues relate to this one)
        for rel in obj.issue_related.all():
            if rel.issue:
                relations.append(
                    {
                        "type": rel.relation_type if hasattr(rel, "relation_type") else "related",
                        "issue": f"{rel.issue.project.identifier}-{rel.issue.sequence_id}",
                        "direction": "incoming",
                    }
                )

        return relations

    def get_comments(self, obj):
        """Return list of comments with author and timestamp."""
        return [
            {
                "comment": comment.comment_stripped if hasattr(comment, "comment_stripped") else comment.comment_html,
                "created_by": comment.actor.full_name if comment.actor else "",
                "created_at": comment.created_at.strftime("%Y-%m-%d %H:%M:%S") if comment.created_at else "",
            }
            for comment in obj.issue_comments.all()
        ]
