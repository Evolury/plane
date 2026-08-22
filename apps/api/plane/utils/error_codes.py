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
    # Contratação (E4). Erros de preenchimento e de escolha, separados do que é
    # trava de plano: aqui a resposta é 400, e o que falta é dado, não dinheiro.
    "DOCUMENTO_INVALIDO": 4807,
    "DADOS_INCOMPLETOS": 4808,
    "DADOS_DE_COBRANCA_FALTANDO": 4809,
    "PLANO_INVALIDO": 4810,
    "CICLO_INVALIDO": 4811,
    "FORMA_INVALIDA": 4812,
    "MESMO_PLANO": 4813,
    "CUPOM_VENCIDO": 4814,
    "CUPOM_ESGOTADO": 4815,
    "ACIMA_DO_TETO": 4816,
    # Ciclo de vida (E5).
    "JA_CANCELADA": 4817,
    "NAO_ESTA_CANCELADA": 4818,
    "DADOS_REMOVIDOS": 4819,
    "MOTIVO_OBRIGATORIO": 4820,
}
