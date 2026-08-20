/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

export enum E_SORT_ORDER {
  ASC = "asc",
  DESC = "desc",
}
// Evolury (20/08/2026): estas listas carregam SÓ a chave de tradução.
//
// Antes carregavam também o texto em inglês, "como rótulo cru de referência" —
// e metade dos consumidores exibia esse campo. A tradução existia, estava
// correta e nunca era lida: era o defeito visível em ciclos, módulos e
// projetos. Com um campo só, escolher o errado não compila.
export const DATE_AFTER_FILTER_OPTIONS = [
  {
    i18n_name: "date_filters.1_week_from_now",
    value: "1_weeks;after;fromnow",
  },
  {
    i18n_name: "date_filters.2_weeks_from_now",
    value: "2_weeks;after;fromnow",
  },
  {
    i18n_name: "date_filters.1_month_from_now",
    value: "1_months;after;fromnow",
  },
  {
    i18n_name: "date_filters.2_months_from_now",
    value: "2_months;after;fromnow",
  },
];

export const DATE_BEFORE_FILTER_OPTIONS = [
  {
    i18n_name: "date_filters.1_week_ago",
    value: "1_weeks;before;fromnow",
  },
  {
    i18n_name: "date_filters.2_weeks_ago",
    value: "2_weeks;before;fromnow",
  },
  {
    i18n_name: "date_filters.1_month_ago",
    value: "1_months;before;fromnow",
  },
];

export const PROJECT_CREATED_AT_FILTER_OPTIONS = [
  {
    i18n_name: "date_filters.today",
    value: "today;custom;custom",
  },
  {
    i18n_name: "date_filters.yesterday",
    value: "yesterday;custom;custom",
  },
  {
    i18n_name: "date_filters.last_7_days",
    value: "last_7_days;custom;custom",
  },
  {
    i18n_name: "date_filters.last_30_days",
    value: "last_30_days;custom;custom",
  },
];
