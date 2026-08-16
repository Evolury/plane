/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: filtros de DIGITAR — texto, número e moeda (ADR 0011).
//
// Os quatro formatos do núcleo são de ESCOLHER: calendário ou lista. Estes três
// tipos não têm lista para oferecer, e é o campo de digitar que faltava.
//
// Os operadores são os que já existem — `exact` e `range` —, e não um novo.
// O que muda por tipo é o RÓTULO: em texto, "exact" se chama "contém", porque
// igualdade exata em texto livre promete uma precisão que o dado não tem (quem
// escreveu "Contrato assinado" não vai lembrar do maiúsculo). O backend trata
// texto assim de qualquer forma, com `icontains`.

import { EXTENDED_FILTER_FIELD_TYPE, EQUALITY_OPERATOR, COMPARISON_OPERATOR } from "@plane/types";
import type { TFilterProperty } from "@plane/types";
// local imports
import type { TCreateFilterConfig } from "../shared";
import { createFilterConfig, createFilterFieldConfig, createOperatorConfigEntry } from "../shared";
import type { TCustomPropertyFilterParams } from "./shared";

export type TCreateTextPropertyFilterParams = TCustomPropertyFilterParams<string> & {
  placeholder?: string;
  /** O rótulo do operador. Em texto é "contém", e não "é". */
  rotuloDoOperador?: string;
};

export type TCreateNumberPropertyFilterParams = TCustomPropertyFilterParams<string> & {
  placeholder?: string;
  /** O símbolo da moeda, quando a propriedade é de dinheiro. */
  prefixo?: string;
  casasDecimais?: number;
};

/** O campo de texto de um operador. */
export const getTextInputConfig = (params: TCreateTextPropertyFilterParams) =>
  createFilterFieldConfig<typeof EXTENDED_FILTER_FIELD_TYPE.TEXT, string>({
    ...params,
    type: EXTENDED_FILTER_FIELD_TYPE.TEXT,
    placeholder: params.placeholder,
    // O operador é `exact` por baixo, mas quem lê a condição precisa ver o que
    // ela FAZ: em texto livre, a busca é por trecho.
    operatorLabel: params.rotuloDoOperador ?? "contém",
  });

/** O campo numérico de um operador — `faixa` desenha dois campos. */
export const getNumberInputConfig = (params: TCreateNumberPropertyFilterParams, faixa = false) =>
  createFilterFieldConfig<typeof EXTENDED_FILTER_FIELD_TYPE.NUMBER, string>({
    ...params,
    type: EXTENDED_FILTER_FIELD_TYPE.NUMBER,
    placeholder: params.placeholder,
    prefixo: params.prefixo,
    casasDecimais: params.casasDecimais,
    faixa,
  });

/** Texto: um operador só, rotulado "contém". */
export const getTextPropertyFilterConfig =
  <P extends TFilterProperty>(key: P): TCreateFilterConfig<P, TCreateTextPropertyFilterParams> =>
  (params: TCreateTextPropertyFilterParams) =>
    createFilterConfig<P>({
      id: key,
      ...params,
      label: params.propertyDisplayName,
      icon: params.filterIcon,
      supportedOperatorConfigsMap: new Map([
        createOperatorConfigEntry(EQUALITY_OPERATOR.EXACT, params, (atualizados) =>
          getTextInputConfig(atualizados as TCreateTextPropertyFilterParams)
        ),
      ]),
    });

/**
 * Número e moeda: "é" e "entre".
 *
 * O mesmo par da data, de propósito — o backend traduz `exact` e `range` da
 * mesma forma nos três, e vocabulário repetido é vocabulário que se aprende
 * uma vez.
 */
export const getNumberPropertyFilterConfig =
  <P extends TFilterProperty>(key: P): TCreateFilterConfig<P, TCreateNumberPropertyFilterParams> =>
  (params: TCreateNumberPropertyFilterParams) =>
    createFilterConfig<P>({
      id: key,
      ...params,
      label: params.propertyDisplayName,
      icon: params.filterIcon,
      supportedOperatorConfigsMap: new Map([
        createOperatorConfigEntry(EQUALITY_OPERATOR.EXACT, params, (atualizados) =>
          getNumberInputConfig(atualizados as TCreateNumberPropertyFilterParams)
        ),
        createOperatorConfigEntry(COMPARISON_OPERATOR.RANGE, params, (atualizados) =>
          getNumberInputConfig(atualizados as TCreateNumberPropertyFilterParams, true)
        ),
      ]),
    });
