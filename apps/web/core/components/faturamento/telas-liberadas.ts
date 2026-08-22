/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/**
 * As telas que atravessam o bloqueio por falta de pagamento (ADR 0021).
 *
 * São duas, e cada uma existe por um motivo diferente:
 *
 * - **Faturamento**, porque pagar não pode depender de estar pago.
 * - **Exportações**, porque exportar sobrevive a todos os estados. É a linha
 *   que separa cobrança de sequestro de dado — e a primeira versão desta trava
 *   escondia Exportações junto com o resto, visto no navegador.
 *
 * Curta de propósito: uma lista que cresce sozinha deixa de ser exceção e vira
 * regra.
 */
export const TELAS_QUE_ATRAVESSAM_O_BLOQUEIO = ["/settings/billing", "/settings/exports"];
