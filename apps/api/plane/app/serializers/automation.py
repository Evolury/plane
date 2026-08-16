# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Evolury: serializer das automações personalizadas (ADR 0012, F1).
#
# A validação inteira mora em `plane.utils.automacoes.validacao` e é chamada
# daqui, que é a fronteira. O motivo de ela ser rigorosa está lá: regra
# malformada tem de ser recusada com uma frase, porque uma automação que nunca
# dispara é indistinguível, para quem a escreveu, de uma que dispara e não faz
# nada.

# Third party imports
from rest_framework import serializers

# Module imports
from plane.db.models import Automation, AutomationRun
from plane.utils.automacoes.gatilhos import GATILHOS_ACEITOS
from plane.utils.automacoes.validacao import validar_acoes, validar_condicao, validar_gatilho

from .base import BaseSerializer


class AutomationSerializer(BaseSerializer):
    ultima_execucao = serializers.SerializerMethodField()

    class Meta:
        model = Automation
        fields = "__all__"
        read_only_fields = [
            "workspace",
            "project",
            # Contadores e relógio são do motor. Deixá-los graváveis permitiria
            # a um cliente zerar o teto por hora simplesmente pedindo.
            "next_run_at",
            "last_run_at",
            "run_count",
            "error_count",
            "disabled_reason",
            "created_by",
            "updated_by",
            "deleted_at",
        ]

    def get_ultima_execucao(self, obj):
        """O resumo da última execução — o que a lista mostra sem abrir o log."""
        ultima = obj.runs.order_by("-created_at").first()
        if ultima is None:
            return None
        return {
            "status": ultima.status,
            "created_at": ultima.created_at,
            "issue_id": str(ultima.issue_id) if ultima.issue_id else None,
        }

    def validate(self, attrs):
        # Em edição parcial, o que não veio no pedido continua valendo — validar
        # só o que chegou deixaria passar a combinação inválida entre um campo
        # novo e um antigo (trocar o gatilho sem trocar a configuração dele).
        instancia = self.instance
        project_id = self.context.get("project_id") or (instancia.project_id if instancia else None)

        trigger_type = attrs.get("trigger_type", instancia.trigger_type if instancia else None)
        trigger_config = attrs.get("trigger_config", instancia.trigger_config if instancia else {})
        condicao = attrs.get("condition", instancia.condition if instancia else None)
        acoes = attrs.get("actions", instancia.actions if instancia else None)

        attrs["trigger_config"] = validar_gatilho(trigger_type, trigger_config, GATILHOS_ACEITOS, project_id)
        attrs["condition"] = validar_condicao(condicao)
        attrs["actions"] = validar_acoes(acoes, project_id, trigger_type)

        # Reativar à mão limpa o motivo do desligamento automático: deixá-lo ali
        # faria a tela seguir avisando de um problema que a pessoa já resolveu.
        if attrs.get("is_active") and instancia is not None and not instancia.is_active:
            attrs["disabled_reason"] = ""

        return attrs


class AutomationRunSerializer(BaseSerializer):
    """Uma linha do registro de execuções — só leitura, sempre."""

    issue_detail = serializers.SerializerMethodField()

    class Meta:
        model = AutomationRun
        fields = [
            "id",
            "status",
            "trigger_summary",
            "actions_result",
            "error",
            "duration_ms",
            "depth",
            "created_at",
            "issue",
            "issue_detail",
        ]
        read_only_fields = fields

    def get_issue_detail(self, obj):
        if obj.issue_id is None or obj.issue is None:
            return None
        return {"id": str(obj.issue_id), "name": obj.issue.name, "sequence_id": obj.issue.sequence_id}
