/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury (20/08/2026): estas listas carregam SÓ a chave de tradução.
//
// Antes carregavam também o texto em inglês ao lado da chave, e bastava um
// consumidor ler o campo errado para a tradução — que existe e está correta —
// nunca chegar à tela. Com um campo só, escolher o errado não compila.

// plane imports
import type { TEstimateSystems } from "@plane/types";

export const MAX_ESTIMATE_POINT_INPUT_LENGTH = 20;

export enum EEstimateSystem {
  POINTS = "points",
  CATEGORIES = "categories",
  TIME = "time",
}

export enum EEstimateUpdateStages {
  CREATE = "create",
  EDIT = "edit",
  SWITCH = "switch",
}

export const estimateCount = {
  min: 2,
  max: 6,
};

export const ESTIMATE_SYSTEMS: TEstimateSystems = {
  points: {
    i18n_name: "project_settings.estimates.systems.points.label",
    templates: {
      fibonacci: {
        i18n_title: "project_settings.estimates.systems.points.fibonacci",
        values: [
          { id: undefined, key: 1, value: "1" },
          { id: undefined, key: 2, value: "2" },
          { id: undefined, key: 3, value: "3" },
          { id: undefined, key: 4, value: "5" },
          { id: undefined, key: 5, value: "8" },
          { id: undefined, key: 6, value: "13" },
        ],
      },
      linear: {
        i18n_title: "project_settings.estimates.systems.points.linear",
        values: [
          { id: undefined, key: 1, value: "1" },
          { id: undefined, key: 2, value: "2" },
          { id: undefined, key: 3, value: "3" },
          { id: undefined, key: 4, value: "4" },
          { id: undefined, key: 5, value: "5" },
          { id: undefined, key: 6, value: "6" },
        ],
      },
      squares: {
        i18n_title: "project_settings.estimates.systems.points.squares",
        values: [
          { id: undefined, key: 1, value: "1" },
          { id: undefined, key: 2, value: "4" },
          { id: undefined, key: 3, value: "9" },
          { id: undefined, key: 4, value: "16" },
          { id: undefined, key: 5, value: "25" },
          { id: undefined, key: 6, value: "36" },
        ],
      },
      custom: {
        i18n_title: "project_settings.estimates.systems.points.custom",
        values: [
          { id: undefined, key: 1, value: "1" },
          { id: undefined, key: 2, value: "2" },
        ],
        hide: true,
      },
    },
    is_available: true,
    is_ee: false,
  },
  categories: {
    i18n_name: "project_settings.estimates.systems.categories.label",
    templates: {
      t_shirt_sizes: {
        i18n_title: "project_settings.estimates.systems.categories.t_shirt_sizes",
        values: [
          { id: undefined, key: 1, value: "XS" },
          { id: undefined, key: 2, value: "S" },
          { id: undefined, key: 3, value: "M" },
          { id: undefined, key: 4, value: "L" },
          { id: undefined, key: 5, value: "XL" },
          { id: undefined, key: 6, value: "XXL" },
        ],
      },
      easy_to_hard: {
        i18n_title: "project_settings.estimates.systems.categories.easy_to_hard",
        values: [
          { id: undefined, key: 1, value: "Easy" },
          { id: undefined, key: 2, value: "Medium" },
          { id: undefined, key: 3, value: "Hard" },
          { id: undefined, key: 4, value: "Very Hard" },
        ],
      },
      custom: {
        i18n_title: "project_settings.estimates.systems.categories.custom",
        values: [
          { id: undefined, key: 1, value: "Easy" },
          { id: undefined, key: 2, value: "Hard" },
        ],
        hide: true,
      },
    },
    is_available: true,
    is_ee: false,
  },
  time: {
    i18n_name: "project_settings.estimates.systems.time.label",
    templates: {
      hours: {
        i18n_title: "project_settings.estimates.systems.time.hours",
        values: [
          { id: undefined, key: 1, value: "1" },
          { id: undefined, key: 2, value: "2" },
          { id: undefined, key: 3, value: "3" },
          { id: undefined, key: 4, value: "4" },
          { id: undefined, key: 5, value: "5" },
          { id: undefined, key: 6, value: "6" },
        ],
      },
    },
    is_available: true,
    is_ee: true,
  },
};
