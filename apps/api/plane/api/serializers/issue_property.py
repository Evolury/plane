# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""As definições de propriedade na API pública (ADR 0011).

Só leitura, e por decisão: criar campo é ato de configuração do projeto, com
regras que a tela já aplica — nome único, tipo que não muda depois, moeda
obrigatória em campo de moeda. Abrir isso na API pública seria abrir um segundo
caminho para as mesmas regras, e o segundo caminho é sempre o que esquece uma.

O que faltava aqui não era escrever: era LER. Sem as definições, quem recebe
`property_values` tem um par de ids opacos e nenhuma forma de saber que
`"a3f…"` é "Canal" e que `"7b2…"` é "Indicação".
"""

from rest_framework import serializers

from plane.db.models import IssueProperty, IssuePropertyOption, TIPOS_DE_SELECAO

from .base import BaseSerializer


class IssuePropertyOptionAPISerializer(BaseSerializer):
    class Meta:
        model = IssuePropertyOption
        fields = ["id", "name", "color", "sort_order"]
        read_only_fields = fields


class IssuePropertyAPISerializer(BaseSerializer):
    options = serializers.SerializerMethodField()

    class Meta:
        model = IssueProperty
        fields = [
            "id",
            "name",
            "property_type",
            "is_required",
            "is_active",
            "show_on_card",
            "sort_order",
            "currency",
            "decimal_places",
            "options",
            "project",
            "workspace",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_options(self, obj):
        """Opções só nas de seleção — nas demais seria lista vazia em todo item."""
        if obj.property_type not in TIPOS_DE_SELECAO:
            return []
        return IssuePropertyOptionAPISerializer(
            sorted(obj.options.all(), key=lambda o: (o.sort_order, o.created_at)), many=True
        ).data
