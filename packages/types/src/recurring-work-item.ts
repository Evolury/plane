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
/** De onde a data da subtarefa é contada (F7). */
export type TSubtaskDueAnchor = "after_creation" | "before_due";

/** Vencimento relativo de uma subtarefa da tarefa de origem. */
export type TSubtaskSchedule = {
  subtask: string;
  anchor: TSubtaskDueAnchor;
  /** Sempre positivo: a direção vem da âncora, não do sinal. */
  offset_days: number;
};

/** Responsável da origem que não é mais membro do projeto. */
export type TInactiveAssignee = {
  id: string;
  display_name: string;
  avatar_url: string | null;
};

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
  /** Antecedência: nasce N dias e M horas antes do vencimento; o nascimento vira o início. */
  lead_time_days: number;
  /** 0 a 23 — a partir de 24 horas, usa-se dias. */
  lead_time_hours: number;
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
  /** Só leitura: responsáveis da origem que saíram do projeto — a geração já os descarta. */
  inactive_assignees: TInactiveAssignee[];
  /** Só leitura: vencimento relativo das subtarefas da origem. */
  subtask_schedules: TSubtaskSchedule[];
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
  /** Quantas subtarefas cabem numa ocorrência, contando a árvore inteira. */
  subtask_cap?: number;
  /** A árvore da origem passou do teto — parte dela não será copiada. */
  subtask_cap_exceeded?: boolean;
};
