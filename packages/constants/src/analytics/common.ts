/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TAnalyticsTabsBase } from "@plane/types";
import { ChartXAxisProperty, ChartYAxisMetric } from "@plane/types";

export interface IInsightField {
  key: string;
  i18nKey: string;
  i18nProps?: {
    entity?: string;
    entityPlural?: string;
    prefix?: string;
    suffix?: string;
    [key: string]: unknown;
  };
}

export const ANALYTICS_INSIGHTS_FIELDS: Record<TAnalyticsTabsBase, IInsightField[]> = {
  overview: [
    {
      key: "total_users",
      i18nKey: "workspace_analytics.total",
      i18nProps: {
        entity: "common.users",
      },
    },
    {
      key: "total_admins",
      i18nKey: "workspace_analytics.total",
      i18nProps: {
        entity: "common.admins",
      },
    },
    {
      key: "total_members",
      i18nKey: "workspace_analytics.total",
      i18nProps: {
        entity: "common.members",
      },
    },
    {
      key: "total_guests",
      i18nKey: "workspace_analytics.total",
      i18nProps: {
        entity: "common.guests",
      },
    },
    {
      key: "total_projects",
      i18nKey: "workspace_analytics.total",
      i18nProps: {
        entity: "common.projects",
      },
    },
    {
      key: "total_work_items",
      i18nKey: "workspace_analytics.total",
      i18nProps: {
        entity: "common.work_items",
      },
    },
    {
      key: "total_cycles",
      i18nKey: "workspace_analytics.total",
      i18nProps: {
        entity: "common.cycles",
      },
    },
    {
      key: "total_intake",
      i18nKey: "workspace_analytics.total",
      i18nProps: {
        entity: "sidebar.intake",
      },
    },
  ],
  "work-items": [
    {
      key: "total_work_items",
      i18nKey: "workspace_analytics.total",
    },
    {
      key: "started_work_items",
      i18nKey: "workspace_analytics.started_work_items",
    },
    {
      key: "backlog_work_items",
      i18nKey: "workspace_analytics.backlog_work_items",
    },
    {
      key: "un_started_work_items",
      i18nKey: "workspace_analytics.un_started_work_items",
    },
    {
      key: "completed_work_items",
      i18nKey: "workspace_analytics.completed_work_items",
    },
  ],
};

// Evolury (20/08/2026): só a chave, como no resto das constantes. O texto em
// inglês ao lado era o que a tela lia.
export const ANALYTICS_DURATION_FILTER_OPTIONS: { i18n_name: string; value: string }[] = [
  { i18n_name: "date_filters.yesterday", value: "yesterday" },
  { i18n_name: "date_filters.last_7_days", value: "last_7_days" },
  { i18n_name: "date_filters.last_30_days", value: "last_30_days" },
  { i18n_name: "ui.duration_last_3_months", value: "last_3_months" },
];

export const ANALYTICS_X_AXIS_VALUES: { value: ChartXAxisProperty; i18n_label: string }[] = [
  {
    value: ChartXAxisProperty.STATES,
    i18n_label: "ui.axis_state_name",
  },
  {
    value: ChartXAxisProperty.STATE_GROUPS,
    i18n_label: "ui.axis_state_group",
  },
  {
    value: ChartXAxisProperty.PRIORITY,
    i18n_label: "ui.axis_priority",
  },
  {
    value: ChartXAxisProperty.LABELS,
    i18n_label: "ui.axis_label",
  },
  {
    value: ChartXAxisProperty.ASSIGNEES,
    i18n_label: "ui.axis_assignee",
  },
  {
    value: ChartXAxisProperty.ESTIMATE_POINTS,
    i18n_label: "ui.axis_estimate_point",
  },
  {
    value: ChartXAxisProperty.CYCLES,
    i18n_label: "ui.axis_cycle",
  },
  {
    value: ChartXAxisProperty.MODULES,
    i18n_label: "ui.axis_module",
  },
  {
    value: ChartXAxisProperty.COMPLETED_AT,
    i18n_label: "ui.axis_completed_date",
  },
  {
    value: ChartXAxisProperty.TARGET_DATE,
    i18n_label: "ui.axis_due_date",
  },
  {
    value: ChartXAxisProperty.START_DATE,
    i18n_label: "ui.axis_start_date",
  },
  {
    value: ChartXAxisProperty.CREATED_AT,
    i18n_label: "ui.axis_created_date",
  },
];

export const ANALYTICS_Y_AXIS_VALUES: { value: ChartYAxisMetric; i18n_label: string }[] = [
  {
    value: ChartYAxisMetric.WORK_ITEM_COUNT,
    i18n_label: "ui.axis_work_item",
  },
  {
    value: ChartYAxisMetric.ESTIMATE_POINT_COUNT,
    i18n_label: "ui.axis_estimate",
  },
  {
    value: ChartYAxisMetric.EPIC_WORK_ITEM_COUNT,
    i18n_label: "ui.axis_epic",
  },
];

export const ANALYTICS_V2_DATE_KEYS = ["completed_at", "target_date", "start_date", "created_at"];
