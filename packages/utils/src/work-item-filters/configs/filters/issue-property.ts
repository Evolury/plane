/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: filtro por propriedade personalizada de seleção (ADR 0011).
//
// Espelha o filtro de etiqueta, que é o mesmo formato: uma lista de opções com
// id, nome e cor. A diferença é que a lista não vem do produto — vem da
// configuração do projeto —, e por isso o `key` é montado em tempo de execução.

import type { TFilterProperty, TSupportedOperators } from "@plane/types";
import { EQUALITY_OPERATOR, COLLECTION_OPERATOR } from "@plane/types";
import type { TCreateFilterConfigParams, IFilterIconConfig, TCreateFilterConfig } from "../../../rich-filters";
import { createFilterConfig, getMultiSelectConfig, createOperatorConfigEntry } from "../../../rich-filters";

/** Uma opção de seleção: o mínimo que a lista precisa para desenhar. */
export type TIssuePropertyFilterOption = {
  id: string;
  name: string;
  color: string;
};

export type TCreateIssuePropertyFilterParams = TCreateFilterConfigParams &
  IFilterIconConfig<string> & {
    options: TIssuePropertyFilterOption[];
  };

export const getIssuePropertyMultiSelectConfig = (
  params: TCreateIssuePropertyFilterParams,
  singleValueOperator: TSupportedOperators
) =>
  getMultiSelectConfig<TIssuePropertyFilterOption, string, string>(
    {
      items: params.options,
      getId: (opcao) => opcao.id,
      getLabel: (opcao) => opcao.name,
      getValue: (opcao) => opcao.id,
      getIconData: (opcao) => opcao.color,
    },
    { singleValueOperator, ...params },
    { getOptionIcon: params.getOptionIcon }
  );

export const getIssuePropertyFilterConfig =
  <P extends TFilterProperty>(key: P): TCreateFilterConfig<P, TCreateIssuePropertyFilterParams> =>
  (params: TCreateIssuePropertyFilterParams) =>
    createFilterConfig<P>({
      id: key,
      label: params.label ?? "",
      ...params,
      icon: params.filterIcon,
      supportedOperatorConfigsMap: new Map([
        createOperatorConfigEntry(COLLECTION_OPERATOR.IN, params, (updatedParams) =>
          getIssuePropertyMultiSelectConfig(updatedParams, EQUALITY_OPERATOR.EXACT)
        ),
      ]),
    });
