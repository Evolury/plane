# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from rest_framework import serializers


class BaseSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(read_only=True)

    # Evolury: `created_by` e `updated_by` nunca vêm do cliente.
    #
    # São campos de auditoria: o `BaseModel.save()` os preenche a partir do
    # usuário do pedido. Mas ele só mexe em `created_by` na CRIAÇÃO — numa
    # atualização toca apenas em `updated_by`. Com `fields = "__all__"`, que é o
    # que a maioria dos serializers usa, os dois entram como escrevíveis, e um
    # `PATCH` com `created_by` de outra pessoa passava e ficava gravado.
    #
    # Medido antes desta correção: `PATCH /projects/<id>/` com
    # `{"created_by": "<outro usuário>"}` respondeu 200 e o banco passou a
    # atribuir o projeto a quem nunca o criou.
    #
    # Por que aqui e não nos 52 serializers que têm a lacuna: `read_only_fields`
    # do `Meta` não se herda — cada subclasse declara o seu do zero, então a
    # regra escrita lá se perde na próxima classe que alguém criar. Forçando em
    # `get_fields`, vale para toda subclasse, inclusive a de amanhã.
    #
    # `created_at`/`updated_at` não entram na lista porque já estão travados por
    # outro caminho: `auto_now_add`/`auto_now` os tornam não editáveis no modelo,
    # e o DRF os marca somente-leitura sozinho. Acrescentá-los aqui seria código
    # que não faz nada — conferido, não suposto.
    CAMPOS_DE_AUDITORIA = ("created_by", "updated_by")

    def get_fields(self):
        campos = super().get_fields()
        for nome in self.CAMPOS_DE_AUDITORIA:
            campo = campos.get(nome)
            if campo is not None:
                campo.read_only = True
        return campos


class DynamicBaseSerializer(BaseSerializer):
    def __init__(self, *args, **kwargs):
        # If 'fields' is provided in the arguments, remove it and store it separately.
        # This is done so as not to pass this custom argument up to the superclass.
        fields = kwargs.pop("fields", [])
        self.expand = kwargs.pop("expand", []) or []
        fields = self.expand

        # Call the initialization of the superclass.
        super().__init__(*args, **kwargs)
        # If 'fields' was provided, filter the fields of the serializer accordingly.
        if fields is not None:
            self.fields = self._filter_fields(fields)

    def _filter_fields(self, fields):
        """
        Adjust the serializer's fields based on the provided 'fields' list.

        :param fields: List or dictionary specifying which fields to include in the serializer.
        :return: The updated fields for the serializer.
        """
        # Check each field_name in the provided fields.
        for field_name in fields:
            # If the field is a dictionary (indicating nested fields),
            # loop through its keys and values.
            if isinstance(field_name, dict):
                for key, value in field_name.items():
                    # If the value of this nested field is a list,
                    # perform a recursive filter on it.
                    if isinstance(value, list):
                        self._filter_fields(self.fields[key], value)

        # Create a list to store allowed fields.
        allowed = []
        for item in fields:
            # If the item is a string, it directly represents a field's name.
            if isinstance(item, str):
                allowed.append(item)
            # If the item is a dictionary, it represents a nested field.
            # Add the key of this dictionary to the allowed list.
            elif isinstance(item, dict):
                allowed.append(list(item.keys())[0])

        for field in allowed:
            if field not in self.fields:
                from . import (
                    WorkspaceLiteSerializer,
                    ProjectLiteSerializer,
                    UserLiteSerializer,
                    StateLiteSerializer,
                    IssueSerializer,
                    LabelSerializer,
                    CycleIssueSerializer,
                    IssueLiteSerializer,
                    IssueRelationSerializer,
                    IntakeIssueLiteSerializer,
                    IssueReactionLiteSerializer,
                    IssueLinkLiteSerializer,
                    RelatedIssueSerializer,
                )

                # Expansion mapper
                expansion = {
                    "user": UserLiteSerializer,
                    "workspace": WorkspaceLiteSerializer,
                    "project": ProjectLiteSerializer,
                    "default_assignee": UserLiteSerializer,
                    "project_lead": UserLiteSerializer,
                    "state": StateLiteSerializer,
                    "created_by": UserLiteSerializer,
                    "issue": IssueSerializer,
                    "actor": UserLiteSerializer,
                    "owned_by": UserLiteSerializer,
                    "members": UserLiteSerializer,
                    "assignees": UserLiteSerializer,
                    "labels": LabelSerializer,
                    "issue_cycle": CycleIssueSerializer,
                    "parent": IssueLiteSerializer,
                    "issue_relation": IssueRelationSerializer,
                    "issue_intake": IntakeIssueLiteSerializer,
                    "issue_related": RelatedIssueSerializer,
                    "issue_reactions": IssueReactionLiteSerializer,
                    "issue_link": IssueLinkLiteSerializer,
                    "sub_issues": IssueLiteSerializer,
                }

            if field not in self.fields and field in expansion:
                self.fields[field] = expansion[field](
                    many=(
                        True
                        if field
                        in [
                            "members",
                            "assignees",
                            "labels",
                            "issue_cycle",
                            "issue_relation",
                            "issue_intake",
                            "issue_reactions",
                            "issue_attachment",
                            "issue_link",
                            "sub_issues",
                            "issue_related",
                        ]
                        else False
                    )
                )

        return self.fields

    def to_representation(self, instance):
        response = super().to_representation(instance)

        # Ensure 'expand' is iterable before processing
        if self.expand:
            for expand in self.expand:
                if expand in self.fields:
                    # Import all the expandable serializers
                    from . import (
                        WorkspaceLiteSerializer,
                        ProjectLiteSerializer,
                        UserLiteSerializer,
                        StateLiteSerializer,
                        IssueSerializer,
                        LabelSerializer,
                        CycleIssueSerializer,
                        IssueRelationSerializer,
                        IntakeIssueLiteSerializer,
                        IssueLiteSerializer,
                        IssueReactionLiteSerializer,
                        IssueAttachmentLiteSerializer,
                        IssueLinkLiteSerializer,
                        RelatedIssueSerializer,
                    )

                    # Expansion mapper
                    expansion = {
                        "user": UserLiteSerializer,
                        "workspace": WorkspaceLiteSerializer,
                        "project": ProjectLiteSerializer,
                        "default_assignee": UserLiteSerializer,
                        "project_lead": UserLiteSerializer,
                        "state": StateLiteSerializer,
                        "created_by": UserLiteSerializer,
                        "issue": IssueSerializer,
                        "actor": UserLiteSerializer,
                        "owned_by": UserLiteSerializer,
                        "members": UserLiteSerializer,
                        "assignees": UserLiteSerializer,
                        "labels": LabelSerializer,
                        "issue_cycle": CycleIssueSerializer,
                        "parent": IssueLiteSerializer,
                        "issue_relation": IssueRelationSerializer,
                        "issue_intake": IntakeIssueLiteSerializer,
                        "issue_related": RelatedIssueSerializer,
                        "issue_reactions": IssueReactionLiteSerializer,
                        "issue_attachment": IssueAttachmentLiteSerializer,
                        "issue_link": IssueLinkLiteSerializer,
                        "sub_issues": IssueLiteSerializer,
                    }
                    # Check if field in expansion then expand the field
                    if expand in expansion:
                        if isinstance(response.get(expand), list):
                            exp_serializer = expansion[expand](getattr(instance, expand), many=True)
                        else:
                            exp_serializer = expansion[expand](getattr(instance, expand))
                        response[expand] = exp_serializer.data
                    else:
                        # You might need to handle this case differently
                        response[expand] = getattr(instance, f"{expand}_id", None)

            # Check if issue_attachments is in fields or expand
            if "issue_attachments" in self.fields or "issue_attachments" in self.expand:
                # Import the model here to avoid circular imports
                from plane.db.models import FileAsset

                issue_id = getattr(instance, "id", None)

                if issue_id:
                    # Fetch related issue_attachments
                    issue_attachments = FileAsset.objects.filter(
                        issue_id=issue_id,
                        entity_type=FileAsset.EntityTypeContext.ISSUE_ATTACHMENT,
                    )
                    # Serialize issue_attachments and add them to the response
                    response["issue_attachments"] = IssueAttachmentLiteSerializer(issue_attachments, many=True).data
                else:
                    response["issue_attachments"] = []

        return response
