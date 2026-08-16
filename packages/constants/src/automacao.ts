/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: catálogos das automações personalizadas (ADR 0012).
//
// O que está aqui é o vocabulário que a tela oferece. Ele é deliberadamente
// menor do que o do Jira: quatro gatilhos em vez de quinze, seis ações em vez
// de quarenta, e nenhuma linguagem de expressão. O corte está justificado no
// ADR — o resumo é que gatilho que ninguém pediu é superfície de laço de graça,
// e que "smart values" são uma linguagem com depurador próprio.

import type { TWorkItemFilterProperty } from "@plane/types";

/**
 * Os campos que podem disparar "campo alterado".
 *
 * É o vocabulário do FILTRO, e não o do histórico, porque é o mesmo seletor de
 * campo do "se" — e porque casar pelo nome que a tela mostra quebraria a regra
 * quando alguém renomeasse um estado.
 *
 * Ficaram de fora nome, descrição, pai e estimativa: mudam o tempo todo, quase
 * nunca são o que se quer automatizar, e transformam edição em massa em
 * tempestade de execuções.
 */
export const CAMPOS_DE_GATILHO = [
  { valor: "state_id", i18n: "automations.field.state" },
  { valor: "priority", i18n: "automations.field.priority" },
  { valor: "assignee_id", i18n: "automations.field.assignee" },
  { valor: "label_id", i18n: "automations.field.label" },
  { valor: "start_date", i18n: "automations.field.start_date" },
  { valor: "target_date", i18n: "automations.field.target_date" },
  { valor: "module_id", i18n: "automations.field.module" },
  { valor: "cycle_id", i18n: "automations.field.cycle" },
] as const;

/**
 * Os campos que a condição oferece.
 *
 * A lista é a do produto inteiro: a condição é o filtro do quadro, e restringir
 * aqui criaria a pergunta "por que consigo filtrar por isso na tela e não na
 * regra?". As propriedades personalizadas entram por fora, pelo projeto.
 */
export const CAMPOS_DA_CONDICAO: TWorkItemFilterProperty[] = [
  "state_id",
  "state_group",
  "priority",
  "assignee_id",
  "label_id",
  "cycle_id",
  "module_id",
  "created_by_id",
  "subscriber_id",
  "mention_id",
  "start_date",
  "target_date",
  "created_at",
  "updated_at",
];

/** As prioridades, na ordem em que o produto as mostra. */
export const PRIORIDADES_DA_AUTOMACAO = ["urgent", "high", "medium", "low", "none"] as const;

/**
 * As variáveis do texto de comentário e notificação.
 *
 * **Lista fechada, e não linguagem.** O Jira resolve isto com *smart values*,
 * que têm funções, aninhamento e modo de depuração próprio. O que não estiver
 * aqui fica literal na tela — quem escreveu `{{orçamento}}` sem querer vê o que
 * escreveu, em vez de ver o comentário sumir.
 */
export const VARIAVEIS_DA_AUTOMACAO = ["tarefa", "responsável", "quem_disparou", "estado", "vencimento"] as const;

/** Dias da semana, 0 = domingo (ADR 0005). */
export const DIAS_DA_SEMANA_DA_AUTOMACAO = [
  { valor: 0, i18n: "automations.weekday.sunday" },
  { valor: 1, i18n: "automations.weekday.monday" },
  { valor: 2, i18n: "automations.weekday.tuesday" },
  { valor: 3, i18n: "automations.weekday.wednesday" },
  { valor: 4, i18n: "automations.weekday.thursday" },
  { valor: 5, i18n: "automations.weekday.friday" },
  { valor: 6, i18n: "automations.weekday.saturday" },
] as const;

/**
 * As receitas prontas do estado vazio.
 *
 * Existem por adoção, não por poder: a lição do monday é que quem chega numa
 * tela de automação em branco não sabe o que é possível, e uma receita
 * preenchida ensina o modelo inteiro num clique. Elas não são um tipo especial
 * de regra — abrem o mesmo editor, já respondido.
 *
 * Cada uma deixa em aberto exatamente o que depende do projeto (qual estado,
 * qual etiqueta), porque adivinhar isso produziria uma regra errada com cara
 * de pronta.
 */
export const RECEITAS_DE_AUTOMACAO = [
  {
    chave: "urgente_avisa",
    i18n: "automations.recipes.urgent_notify",
    trigger_type: "field_changed",
    trigger_config: { field: "priority", to: ["urgent"] },
    actions: [{ type: "set_assignees", config: { mode: "add", especiais: ["trigger_actor"] } }],
  },
  {
    chave: "nova_recebe_etiqueta",
    i18n: "automations.recipes.new_gets_label",
    trigger_type: "work_item_created",
    trigger_config: {},
    actions: [{ type: "set_labels", config: { mode: "add", labels: [] } }],
  },
  {
    chave: "concluida_limpa_prazo",
    i18n: "automations.recipes.done_clears_due",
    trigger_type: "field_changed",
    trigger_config: { field: "state_id", to: [] },
    actions: [{ type: "set_priority", config: { priority: "none" } }],
  },
  {
    chave: "comentario_reabre",
    i18n: "automations.recipes.comment_reopens",
    trigger_type: "comment_added",
    trigger_config: {},
    actions: [{ type: "set_state", config: { state_id: "" } }],
  },
  {
    // A receita que existe para mostrar a diferença entre reagir e repetir:
    // o checklist nasce PORQUE a tarefa entrou numa etapa, não porque é terça.
    chave: "checklist_de_homologacao",
    i18n: "automations.recipes.review_checklist",
    trigger_type: "field_changed",
    trigger_config: { field: "state_id", to: [] },
    actions: [
      {
        type: "create_subtasks",
        config: { names: ["Conferir requisitos", "Testar", "Aprovar"], herdar_responsaveis: true },
      },
    ],
  },
  {
    chave: "vence_amanha_avisa",
    i18n: "automations.recipes.due_tomorrow",
    trigger_type: "scheduled",
    trigger_config: { frequency: "daily", time: "08:00", weekdays: [] },
    actions: [{ type: "notify", config: { especiais: ["assignees"], text: "", email: true } }],
  },
] as const;
