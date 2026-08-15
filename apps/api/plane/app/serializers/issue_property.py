# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Evolury: propriedades personalizadas da tarefa (ADR 0011, P1).

# Third party imports
from rest_framework import serializers

# Module imports
from plane.db.models import (
    ICONES_DE_PROPRIEDADE,
    IssueProperty,
    IssuePropertyOption,
    PropertyType,
    TIPOS_DE_SELECAO,
)

from .base import BaseSerializer

#: As moedas que a interface oferece. Lista curta de propósito: moeda é
#: escolha de configuração, não catálogo — e cada uma a mais é uma coluna que
#: alguém vai somar com outra sem perceber.
MOEDAS = {"BRL", "USD", "EUR"}


class IssuePropertyOptionSerializer(BaseSerializer):
    class Meta:
        model = IssuePropertyOption
        fields = ["id", "name", "color", "sort_order"]
        read_only_fields = ["id"]


class IssuePropertySerializer(BaseSerializer):
    options = IssuePropertyOptionSerializer(many=True, read_only=True)
    values_count = serializers.SerializerMethodField()

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
            "icon",
            "options",
            "values_count",
            "project",
            "workspace",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "project", "workspace", "created_at", "updated_at"]

    def get_values_count(self, obj):
        """Quantas tarefas usam esta propriedade.

        É o número que a confirmação de exclusão mostra. Vem do contexto
        quando a view o prepara: perguntar por propriedade seria uma consulta
        por linha da lista, que é o custo que este projeto já fixa em teste.
        """
        contagens = self.context.get("valores_por_propriedade")
        if contagens is not None:
            return contagens.get(obj.id, 0)
        return obj.values.count()

    def validate_icon(self, icone):
        """Só o que está na lista fechada — ou nada.

        O ícone chega à tela como chave de um mapa de componentes. Texto livre
        vindo do banco virando nome de componente é o tipo de coisa que esta
        base não deixa passar, e a lista curta também é decisão de produto:
        ícone é configuração, não catálogo.
        """
        icone = (icone or "").strip()
        if icone and icone not in ICONES_DE_PROPRIEDADE:
            raise serializers.ValidationError("Ícone inválido.")
        return icone

    def validate_name(self, nome):
        nome = (nome or "").strip()
        if not nome:
            raise serializers.ValidationError("O nome é obrigatório.")
        return nome

    def validate(self, attrs):
        tipo = attrs.get("property_type") or getattr(self.instance, "property_type", None)

        # A unicidade existe no banco, mas erro de integridade vira 500 e a
        # tela precisa de uma mensagem no campo. Duas propriedades com o mesmo
        # nome seriam duas colunas indistinguíveis na tabela e na exportação.
        nome = attrs.get("name")
        projeto = self.context.get("project_id") or getattr(self.instance, "project_id", None)
        if nome and projeto:
            iguais = IssueProperty.objects.filter(project_id=projeto, name__iexact=nome)
            if self.instance is not None:
                iguais = iguais.exclude(pk=self.instance.pk)
            if iguais.exists():
                raise serializers.ValidationError({"name": "Já existe uma propriedade com este nome."})

        # Trocar o tipo é proibido, com UMA exceção: seleção única → múltipla,
        # que é a única conversão que não perde dado — cada valor vira uma
        # lista de um. O caminho de volta perde, e por isso não existe.
        if self.instance is not None and "property_type" in attrs:
            de, para = self.instance.property_type, attrs["property_type"]
            if de != para and not (de == PropertyType.SELECT and para == PropertyType.MULTI_SELECT):
                raise serializers.ValidationError({"property_type": "O tipo não pode ser trocado depois de criada."})

        if tipo == PropertyType.CURRENCY:
            moeda = attrs.get("currency") or getattr(self.instance, "currency", None)
            if moeda not in MOEDAS:
                raise serializers.ValidationError({"currency": f"Escolha uma moeda entre {', '.join(sorted(MOEDAS))}."})
            casas = attrs.get("decimal_places", getattr(self.instance, "decimal_places", 2))
            if casas > 4:
                raise serializers.ValidationError({"decimal_places": "No máximo 4 casas decimais."})
        elif tipo is not None and tipo not in TIPOS_DE_SELECAO:
            # Moeda declarada em campo que não é moeda seria configuração
            # morta, e configuração morta vira pergunta seis meses depois.
            attrs["currency"] = None

        return attrs
