# Copyright (c) 2026-present Evolury
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Evolury: os segredos do Asaas (ADR 0021).
#
# Ficam em `InstanceConfiguration` criptografada, como os do e-mail e os do
# OAuth — o mesmo lugar, para não haver dois padrões de segredo na instância.
# Do `bws` para o ambiente, do ambiente para a configuração.

import os

faturamento_config_variables = [
    {
        "key": "ASAAS_API_KEY",
        "value": os.environ.get("ASAAS_API_KEY", ""),
        "category": "FATURAMENTO",
        "is_encrypted": True,
    },
    {
        # De 32 a 255 caracteres, exigência do Asaas. É o que o webhook compara
        # em tempo constante — sem ele, qualquer um forja um pagamento.
        "key": "ASAAS_WEBHOOK_TOKEN",
        "value": os.environ.get("ASAAS_WEBHOOK_TOKEN", ""),
        "category": "FATURAMENTO",
        "is_encrypted": True,
    },
    {
        # `producao` ou `sandbox`. O padrão é produção porque é o que existe:
        # a conta de sandbox da Evolury está indisponível, e a decisão foi
        # validar em produção com valores baixos.
        "key": "ASAAS_AMBIENTE",
        "value": os.environ.get("ASAAS_AMBIENTE", "producao"),
        "category": "FATURAMENTO",
        "is_encrypted": False,
    },
]
