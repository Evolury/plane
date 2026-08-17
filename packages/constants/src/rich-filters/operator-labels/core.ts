/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TCoreSupportedOperators, TCoreSupportedDateFilterOperators } from "@plane/types";
import { CORE_EQUALITY_OPERATOR, CORE_COLLECTION_OPERATOR, CORE_COMPARISON_OPERATOR } from "@plane/types";

// Evolury: o mapa guarda CHAVE de tradução, não texto.
//
// Antes eram as palavras "is", "is any of" e "between" escritas aqui — e como
// este é um pacote de constantes, sem acesso ao `t`, não havia caminho nenhum
// para traduzi-las. O resultado é que o operador aparecia em inglês em TODA
// tela do produto, inclusive nos filtros do quadro, num produto em português.
//
// Quem traduz é quem desenha: `filter-item/root.tsx` chama o `t` sobre o que
// vier daqui. Rótulo personalizado definido numa config continua passando
// direto — chave inexistente volta como ela mesma.
/**
 * Core operator labels — chaves de `common.json`
 */
export const CORE_OPERATOR_LABELS_MAP: Record<TCoreSupportedOperators, string> = {
  [CORE_EQUALITY_OPERATOR.EXACT]: "common.rich_filters.operators.is",
  [CORE_COLLECTION_OPERATOR.IN]: "common.rich_filters.operators.is_any_of",
  [CORE_COMPARISON_OPERATOR.RANGE]: "common.rich_filters.operators.between",
} as const;

/**
 * Core date-specific operator labels
 */
export const CORE_DATE_OPERATOR_LABELS_MAP: Record<TCoreSupportedDateFilterOperators, string> = {
  [CORE_EQUALITY_OPERATOR.EXACT]: "common.rich_filters.operators.is",
  [CORE_COMPARISON_OPERATOR.RANGE]: "common.rich_filters.operators.between",
} as const;
