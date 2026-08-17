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
  // scheduled — o horário é local ao PROJETO (ADR 0006), não ao servidor
  frequency?: "daily" | "weekly";
  /** "HH:MM". */
  time?: string;
  /** 0 = domingo (ADR 0005). Vazio quer dizer todos, nunca nenhum. */
  weekdays?: number[];
};

export const AUTOMATION_ACTION = {
  SET_STATE: "set_state",
  SET_PRIORITY: "set_priority",
  SET_ASSIGNEES: "set_assignees",
  SET_LABELS: "set_labels",
  SET_DATE: "set_date",
  SET_PROPERTY: "set_property",
  // F2 — a voz e o resto
  ADD_COMMENT: "add_comment",
  NOTIFY: "notify",
  ARCHIVE: "archive",
  ADD_TO_CYCLE: "add_to_cycle",
  ADD_TO_MODULE: "add_to_module",
  // F3 — a criação. Só existe em gatilho de EVENTO: agendado + criar é
  // recorrência, e a combinação é recusada ao salvar (ADR 0012).
  CREATE_WORK_ITEM: "create_work_item",
  CREATE_SUBTASKS: "create_subtasks",
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
  especiais?: (TAutomationSpecialAssignee | TAutomationNotifyTarget)[];
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
  // add_comment / notify — texto com a lista FECHADA de variáveis
  // ({{tarefa}}, {{responsável}}, {{quem_disparou}}, {{estado}}, {{vencimento}}).
  // O que não estiver na lista fica literal, e não vira erro.
  text?: string;
  // notify
  users?: string[];
  email?: boolean;
  // create_work_item / create_subtasks
  //
  // Sem campo de recorrência, de propósito: a tarefa nascida de uma reação é
  // tarefa comum. Criação por agenda é trabalho de Tarefas recorrentes.
  /** create_work_item: o nome da tarefa. Aceita as mesmas variáveis do texto. */
  name?: string;
  /** add_to_module: id fixo — módulo é contêiner durável, ciclo não é. */
  module_id?: string;
  /** create_subtasks: a lista do checklist, um nome por item. */
  names?: string[];
  herdar_responsaveis?: boolean;
  /** Vencimento relativo ao dia da criação. Nunca data fixa, que vence e some. */
  due_in_days?: number;
};

/** Papéis que a ação de notificar aceita, além de pessoas escolhidas. */
export type TAutomationNotifyTarget = "assignees" | "creator" | "trigger_actor";

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
  /** Ocorrência de recorrência dispara esta regra de "tarefa criada"? */
  include_recurring: boolean;
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
  Pick<
    TAutomation,
    | "name"
    | "description"
    | "is_active"
    | "trigger_type"
    | "trigger_config"
    | "include_recurring"
    | "condition"
    | "actions"
  >
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
  /** Só para regra agendada: quando ela rodaria, calculado no servidor. */
  proxima_execucao: string | null;
};
