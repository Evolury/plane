/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { RECURSO_ANALYTICS } from "@plane/constants";

/**
 * Quais itens da navegação do espaço são recurso de plano (ADR 0021).
 *
 * Um mapa só, lido pelas duas barras — a fixa e a estendida. Duas listas
 * seriam duas chances de o selo aparecer em um lugar e não no outro, que foi
 * exatamente o que aconteceu na primeira tentativa: o selo entrou na barra que
 * a tela nem usa.
 */
export const RECURSOS_DA_NAVEGACAO: Record<string, string | undefined> = {
  analytics: RECURSO_ANALYTICS,
};
