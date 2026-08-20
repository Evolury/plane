/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// plane imports
import type { TIssuePriorities } from "@plane/constants";
import { translate } from "@plane/i18n";
import { ISSUE_PRIORITIES } from "@plane/constants";
import type { TFilterProperty, TSupportedOperators } from "@plane/types";
import { EQUALITY_OPERATOR, COLLECTION_OPERATOR } from "@plane/types";
// local imports
import type { TCreateFilterConfigParams, IFilterIconConfig, TCreateFilterConfig } from "../../../rich-filters";
import { createFilterConfig, getMultiSelectConfig, createOperatorConfigEntry } from "../../../rich-filters";

// ------------ Priority filter ------------

/**
 * Priority filter specific params
 */
export type TCreatePriorityFilterParams = TCreateFilterConfigParams &
  IFilterIconConfig<TIssuePriorities> & {
    // Evolury: rótulo traduzido por opção — mesmo mecanismo do `label` de
    // TCreateFilterConfigParams (o app injeta; utils não depende de i18n)
    getOptionLabel?: (priority: TIssuePriorities) => string;
  };

/**
 * Helper to get the priority multi select config
 * @param params - The filter params
 * @returns The priority multi select config
 */
export const getPriorityMultiSelectConfig = (
  params: TCreatePriorityFilterParams,
  singleValueOperator: TSupportedOperators
) =>
  getMultiSelectConfig<{ key: TIssuePriorities; i18n_title: string }, TIssuePriorities, TIssuePriorities>(
    {
      items: ISSUE_PRIORITIES,
      getId: (priority) => priority.key,
      // Evolury: o padrão sai traduzido. Antes o fallback era o texto em
      // inglês da constante, e quem não passasse `getOptionLabel` mostrava
      // "Urgent" na tela.
      getLabel: (priority) => params.getOptionLabel?.(priority.key) ?? translate(priority.i18n_title),
      getValue: (priority) => priority.key,
      getIconData: (priority) => priority.key,
    },
    {
      singleValueOperator,
      ...params,
    },
    {
      getOptionIcon: params.getOptionIcon,
    }
  );

/**
 * Get the priority filter config
 * @template K - The filter key
 * @param key - The filter key to use
 * @returns A function that takes parameters and returns the priority filter config
 */
export const getPriorityFilterConfig =
  <P extends TFilterProperty>(key: P): TCreateFilterConfig<P, TCreatePriorityFilterParams> =>
  (params: TCreatePriorityFilterParams) =>
    createFilterConfig<P>({
      id: key,
      label: "Priority",
      ...params,
      icon: params.filterIcon,
      supportedOperatorConfigsMap: new Map([
        createOperatorConfigEntry(COLLECTION_OPERATOR.IN, params, (updatedParams) =>
          getPriorityMultiSelectConfig(updatedParams, EQUALITY_OPERATOR.EXACT)
        ),
      ]),
    });
