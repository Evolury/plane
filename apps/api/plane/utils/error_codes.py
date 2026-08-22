# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

ERROR_CODES = {
    # issues
    "INVALID_ARCHIVE_STATE_GROUP": 4091,
    "INVALID_ISSUE_DATES": 4100,
    "INVALID_ISSUE_START_DATE": 4101,
    "INVALID_ISSUE_TARGET_DATE": 4102,
    # pages
    "PAGE_LOCKED": 4701,
    "PAGE_ARCHIVED": 4702,
    # Evolury: faturamento (ADR 0021). Faixa própria, e recusa própria: estes
    # códigos viajam com 402, não com 403. Plano é dinheiro; papel é permissão.
    # Separá-los é o que deixa o cliente saber qual tela mostrar sem adivinhar.
    "PLANO_NAO_INCLUI": 4801,
    "LIMITE_DO_PLANO": 4802,
    "ESPACO_SOMENTE_LEITURA": 4803,
    "ESPACO_BLOQUEADO": 4804,
    "CUPOM_INVALIDO": 4805,
    "SEM_ASSINATURA": 4806,
}
