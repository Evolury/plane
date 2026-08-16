/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: automações personalizadas — quando / se / então (ADR 0012).
//
// Os tipos espelham o que o backend valida, e não um formato próprio da tela:
// a regra é gravada exatamente como está aqui. A condição é a MESMA árvore que
// o quadro manda em `filters` — por isso ela é tipada como `unknown` e não como
// uma estrutura própria: quem a conhece é o pacote de filtros ricos, e duplicar
// a definição aqui criaria duas verdades sobre a mesma coisa.

/** Os quatro gatilhos. A agendada chega na F2. */
export const AUTOMATION_TRIGGER = {
  WORK_ITEM_CREATED: "work_item_created",
  FIELD_CHANGED: "field_changed",
  COMMENT_ADDED: "comment_added",
  SCHEDULED: "scheduled",
} as const;
export type TAutomationTrigger = (typeof AUTOMATION_TRIGGER)[keyof typeof AUTOMATION_TRIGGER];

/**
 * A configuração do gatilho.
 *
 * `field` usa o vocabulário do FILTRO (`state_id`, `priority`, `property_<uuid>`),
 * e não o do histórico — é o mesmo seletor de campo do "se", e é o que não
 * quebra quando alguém renomeia uma propriedade.
 */
export type TAutomationTriggerConfig = {
  field?: string;
  from?: string[];
  to?: string[];
};

export const AUTOMATION_ACTION = {
  SET_STATE: "set_state",
  SET_PRIORITY: "set_priority",
  SET_ASSIGNEES: "set_assignees",
  SET_LABELS: "set_labels",
  SET_DATE: "set_date",
  SET_PROPERTY: "set_property",
} as const;
export type TAutomationActionType = (typeof AUTOMATION_ACTION)[keyof typeof AUTOMATION_ACTION];

/** Como uma ação de lista trata o que já estava lá. */
export type TAutomationListMode = "add" | "remove" | "replace";

/** Papéis resolvidos na execução, e não no dia em que a regra foi escrita. */
export type TAutomationSpecialAssignee = "creator" | "trigger_actor";

export type TAutomationActionConfig = {
  // set_state
  state_id?: string;
  // set_priority
  priority?: string;
  // set_assignees / set_labels
  mode?: TAutomationListMode;
  assignees?: string[];
  especiais?: TAutomationSpecialAssignee[];
  labels?: string[];
  // set_date
  //
  // `date_mode` tem nome próprio, e não reaproveita `mode`: uma chave só para
  // "acrescentar/remover/substituir" e para "relativa/fixa" seria duas
  // perguntas diferentes no mesmo campo, e o compilador já reclamou disso.
  field?: "start_date" | "target_date";
  date_mode?: "relative" | "fixed";
  date?: string;
  offset_days?: number;
  // set_property
  property_id?: string;
  value?: unknown;
};

export type TAutomationAction = {
  type: TAutomationActionType;
  config: TAutomationActionConfig;
};

export type TAutomationRunStatus = "matched" | "skipped" | "failed";

export type TAutomation = {
  id: string;
  name: string;
  description: string;
  is_active: boolean;
  trigger_type: TAutomationTrigger;
  trigger_config: TAutomationTriggerConfig;
  /** A árvore de filtro, no formato que o backend já aceita. `null` = todas. */
  condition: unknown;
  actions: TAutomationAction[];
  last_run_at: string | null;
  run_count: number;
  error_count: number;
  /** Preenchido quando o motor desligou a regra sozinho. */
  disabled_reason: string;
  ultima_execucao: {
    status: TAutomationRunStatus;
    created_at: string;
    issue_id: string | null;
  } | null;
  created_at: string;
};

export type TAutomationPayload = Partial<
  Pick<TAutomation, "name" | "description" | "is_active" | "trigger_type" | "trigger_config" | "condition" | "actions">
>;

/** Uma linha do registro de execuções. */
export type TAutomationRun = {
  id: string;
  status: TAutomationRunStatus;
  trigger_summary: Record<string, unknown>;
  actions_result: { tipo: string; status: string; detalhe: string }[];
  error: string;
  duration_ms: number;
  depth: number;
  created_at: string;
  issue: string | null;
  issue_detail: { id: string; name: string; sequence_id: number } | null;
};

/** A resposta de "essa regra vai pegar o quê?", antes de ligar a regra. */
export type TAutomationSimulation = {
  total: number;
  amostra: { id: string; name: string; sequence_id: number }[];
};
