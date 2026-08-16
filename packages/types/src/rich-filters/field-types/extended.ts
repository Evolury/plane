/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TFilterValue } from "../expression";
// Evolury: campos de digitar (ADR 0011)
import type { TBaseFilterFieldConfig } from "./shared";

/**
 * Extended filter types
 */
export const EXTENDED_FILTER_FIELD_TYPE = {
  // Evolury: os formatos que faltavam para texto, número e moeda (ADR 0011).
  //
  // Os quatro formatos do núcleo são de ESCOLHER — calendário ou lista. Estes
  // dois são de DIGITAR, e entram aqui, no ponto de extensão que o upstream
  // deixou vazio, para uma atualização do produto não conflitar com eles.
  TEXT: "text",
  NUMBER: "number",
} as const;

// -------- CAMPOS DE DIGITAR --------

/** Campo de texto — o operador é rotulado "contém". */
export type TTextFilterFieldConfig<V extends TFilterValue = TFilterValue> = TBaseFilterFieldConfig & {
  type: typeof EXTENDED_FILTER_FIELD_TYPE.TEXT;
  placeholder?: string;
  defaultValue?: V;
};

/** Campo numérico — para igualdade e faixa. */
export type TNumberFilterFieldConfig<V extends TFilterValue = TFilterValue> = TBaseFilterFieldConfig & {
  type: typeof EXTENDED_FILTER_FIELD_TYPE.NUMBER;
  placeholder?: string;
  defaultValue?: V;
  /** O símbolo da moeda, quando a propriedade é de dinheiro. */
  prefixo?: string;
  casasDecimais?: number;
  /** Faixa: dois campos em vez de um. */
  faixa?: boolean;
};

// -------- UNION TYPES --------

/**
 * All extended filter configurations
 */
export type TExtendedFilterFieldConfigs<V extends TFilterValue = TFilterValue> =
  | TTextFilterFieldConfig<V>
  | TNumberFilterFieldConfig<V>;
