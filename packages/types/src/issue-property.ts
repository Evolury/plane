/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: propriedades personalizadas da tarefa (ADR 0011).

/** Os seis tipos da v1. Pessoa, fórmula, rollup e checkbox ficaram de fora. */
export type TPropertyType = "text" | "number" | "date" | "select" | "multi_select" | "currency";

/** Moeda é da propriedade, não do valor — senão soma-se real com dólar. */
export type TPropertyCurrency = "BRL" | "USD" | "EUR";

export type TIssuePropertyOption = {
  id: string;
  name: string;
  color: string;
  sort_order: number;
};

export type TIssueProperty = {
  id: string;
  name: string;
  property_type: TPropertyType;
  /** Barra a criação da tarefa, nunca a conclusão. */
  is_required: boolean;
  /** Desativar preserva os valores; some dos formulários e dos filtros. */
  is_active: boolean;
  show_on_card: boolean;
  sort_order: number;
  currency: TPropertyCurrency | null;
  decimal_places: number;
  options: TIssuePropertyOption[];
  /** Só leitura: quantas TAREFAS usam a propriedade — o número do aviso. */
  values_count: number;
  project: string;
  workspace: string;
  created_at: string;
  updated_at: string;
};

/**
 * O que a tela envia ao salvar. As opções chegam sem `id` quando são novas e
 * sem `sort_order` sempre — a ordem é a da lista, e quem a resolve é a API.
 */
export type TIssuePropertyPayload = Partial<Omit<TIssueProperty, "options">> & {
  options?: { id?: string; name: string; color: string }[];
};

export type TIssuePropertyList = {
  properties: TIssueProperty[];
  /** Teto por projeto, servido pela API para a tela não repetir a constante. */
  cap: number;
};

/** O valor de uma propriedade no formato da API. Vazio é sempre `null`. */
export type TPropertyValue = string | string[] | null;

/**
 * O que a tarefa devolve: as definições ativas e o que ela tem preenchido.
 *
 * O nome evita `TIssuePropertyValues`, que já existe herdado em
 * `issues/issue-property-values.ts` e colidiria no barril de exportação.
 */
export type TIssuePropertiesForIssue = {
  properties: TIssueProperty[];
  values: Record<string, TPropertyValue>;
};
