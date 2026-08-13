/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: tarefas recorrentes (ADR 0010).

export type TRecurrenceFrequency = "daily" | "weekly" | "monthly" | "yearly";
export type TMonthlyMode = "day_of_month" | "weekday_of_month";
export type TGenerationMode = "schedule" | "after_completion";
export type TRecurrenceEndMode = "never" | "on_date" | "after_count";

export type TRecurringWorkItem = {
  id: string;
  name: string;
  is_active: boolean;
  // agenda
  frequency: TRecurrenceFrequency;
  interval: number;
  /** 0 = domingo, como a semana do produto (ADR 0005) */
  weekdays: number[];
  monthly_mode: TMonthlyMode | null;
  day_of_month: number | null;
  /** 1 a 4, ou -1 para a última */
  week_of_month: number | null;
  weekday_of_month: number | null;
  month_of_year: number | null;
  time_of_day: string;
  start_date: string;
  // fim
  end_mode: TRecurrenceEndMode;
  end_date: string | null;
  end_after_count: number | null;
  // geração
  generation_mode: TGenerationMode;
  days_after_completion: number | null;
  skip_while_previous_open: boolean;
  next_run_at: string | null;
  occurrences_created: number;
  /** Só leitura: as próximas datas previstas */
  next_occurrences: string[];
  // molde
  template_description_html: string;
  template_priority: string;
  template_state: string | null;
  template_assignees: string[];
  template_labels: string[];
  template_estimate_point: string | null;
  template_type: string | null;
  project: string;
  workspace: string;
  created_at: string;
  updated_at: string;
};
