/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: tarefas recorrentes (ADR 0010, revisão 13/08/2026).
//
// A regra é uma agenda apontando para uma tarefa de origem — a tarefa é o
// molde, vivo. Por isso não há mais campos de molde aqui.

export type TRecurrenceFrequency = "daily" | "weekly" | "monthly" | "yearly";
export type TMonthlyMode = "day_of_month" | "last_day" | "weekday_of_month";
export type TGenerationMode = "schedule" | "after_completion";
export type TRecurrenceEndMode = "never" | "on_date" | "after_count";

/** Resumo da origem que a API devolve junto com a regra. */
export type TRecurringSourceIssue = {
  id: string;
  name: string;
  sequence_id: number;
  archived_at: string | null;
  state_group: string | null;
};

export type TRecurringWorkItem = {
  id: string;
  source_issue: string;
  source_issue_detail: TRecurringSourceIssue | null;
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
  /** Antecedência: nasce N dias antes do vencimento; a data de nascimento vira o início. */
  lead_time_days: number;
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
  /** Etapa onde a ocorrência nasce (padrão: a etapa padrão do projeto). */
  initial_state: string | null;
  project: string;
  workspace: string;
  created_at: string;
  updated_at: string;
};

/** O papel de uma tarefa na recorrência: origem, gerada, ou nenhum. */
export type TRecurringWorkItemRole = {
  role: "source" | "occurrence" | null;
  rule: TRecurringWorkItem | null;
  scheduled_for?: string;
};
