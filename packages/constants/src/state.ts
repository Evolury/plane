/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TStateGroups } from "@plane/types";

export type TDraggableData = {
  groupKey: TStateGroups;
  id: string;
};

export const STATE_GROUPS: {
  [key in TStateGroups]: {
    key: TStateGroups;
    label: string;
    i18n_label: string;
    defaultStateName: string;
    color: string;
  };
} = {
  backlog: {
    key: "backlog",
    label: "Backlog",
    i18n_label: "workspace_projects.state.backlog",
    defaultStateName: "Backlog",
    color: "#d9d9d9",
  },
  unstarted: {
    key: "unstarted",
    label: "Unstarted",
    i18n_label: "workspace_projects.state.unstarted",
    defaultStateName: "Todo",
    color: "#3f76ff",
  },
  started: {
    key: "started",
    label: "Started",
    i18n_label: "workspace_projects.state.started",
    defaultStateName: "In Progress",
    color: "#f59e0b",
  },
  completed: {
    key: "completed",
    label: "Completed",
    i18n_label: "workspace_projects.state.completed",
    defaultStateName: "Done",
    color: "#16a34a",
  },
  cancelled: {
    key: "cancelled",
    label: "Canceled",
    i18n_label: "workspace_projects.state.cancelled",
    defaultStateName: "Cancelled",
    color: "#dc2626",
  },
};

// Evolury: ordem dos grupos na página de minhas tarefas — o fluxo semântico
// "agora → em seguida → depois → feito". Quadro, lista e painel de etapas
// compartilham esta ordem; o sort_order das etapas vale DENTRO de cada grupo.
// Backlog antes de concluído por definição de produto (12/08/2026).
export const MY_TASKS_STAGE_GROUP_ORDER: TStateGroups[] = ["unstarted", "started", "backlog", "completed", "cancelled"];

export const ARCHIVABLE_STATE_GROUPS = [STATE_GROUPS.completed.key, STATE_GROUPS.cancelled.key];
export const COMPLETED_STATE_GROUPS = [STATE_GROUPS.completed.key];
export const PENDING_STATE_GROUPS = [
  STATE_GROUPS.backlog.key,
  STATE_GROUPS.unstarted.key,
  STATE_GROUPS.started.key,
  STATE_GROUPS.cancelled.key,
];

export const STATE_DISTRIBUTION = {
  [STATE_GROUPS.backlog.key]: {
    key: STATE_GROUPS.backlog.key,
    issues: "backlog_issues",
    points: "backlog_estimate_points",
  },
  [STATE_GROUPS.unstarted.key]: {
    key: STATE_GROUPS.unstarted.key,
    issues: "unstarted_issues",
    points: "unstarted_estimate_points",
  },
  [STATE_GROUPS.started.key]: {
    key: STATE_GROUPS.started.key,
    issues: "started_issues",
    points: "started_estimate_points",
  },
  [STATE_GROUPS.completed.key]: {
    key: STATE_GROUPS.completed.key,
    issues: "completed_issues",
    points: "completed_estimate_points",
  },
  [STATE_GROUPS.cancelled.key]: {
    key: STATE_GROUPS.cancelled.key,
    issues: "cancelled_issues",
    points: "cancelled_estimate_points",
  },
};

export const PROGRESS_STATE_GROUPS_DETAILS = [
  {
    key: "completed_issues",
    title: "Completed",
    color: "#16A34A",
  },
  {
    key: "started_issues",
    title: "Started",
    color: "#F59E0B",
  },
  {
    key: "unstarted_issues",
    title: "Unstarted",
    color: "#3A3A3A",
  },
  {
    key: "backlog_issues",
    title: "Backlog",
    color: "#A3A3A3",
  },
];

export const DISPLAY_WORKFLOW_PRO_CTA = false;
