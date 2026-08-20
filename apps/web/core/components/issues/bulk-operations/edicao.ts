/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: as contas do preenchimento em massa (ADR 0019).
//
// Fora do componente porque é onde o erro dá menos na vista: um campo oferecido
// em seleção que atravessa projetos manda o estado do projeto A para a tarefa
// do projeto B, e o servidor recusa a coisa inteira — o usuário só vê "não deu".
//
// A tela não é a guarda; ela é a promessa. Quem cobra é o servidor.

import type { TIssue, TIssuePriorities } from "@plane/types";

/** O mesmo teto do servidor (`plane/utils/edicao_em_massa.py`). */
export const TETO_DE_EDICAO_EM_MASSA = 500;

/** Os modos de um campo de lista, e o padrão. Ver o ADR 0019 para o porquê. */
export const MODOS_DE_LISTA = ["add", "remove", "replace"] as const;
export type TModoDeLista = (typeof MODOS_DE_LISTA)[number];
export const MODO_PADRAO: TModoDeLista = "add";

/**
 * O projeto da seleção — ou nada, quando ela atravessa projetos.
 *
 * Estado, etiqueta, responsável, estimativa e propriedade personalizada são DO
 * PROJETO: em "Minhas tarefas" e nas visões do espaço, oferecer esses campos
 * seria prometer o que não existe.
 */
export const projetoUnico = (tarefas: TIssue[]): string | undefined => {
  const projetos = new Set(tarefas.map((tarefa) => tarefa.project_id).filter(Boolean));
  return projetos.size === 1 ? (projetos.values().next().value as string) : undefined;
};

export type TValorComum<T> = { misto: boolean; valor: T | undefined };

/**
 * O valor que TODAS compartilham, ou "misto".
 *
 * É o que faz o campo abrir mostrando "Vários" em vez de mostrar o valor da
 * primeira tarefa — que é como se apaga o das outras sem perceber.
 */
export const valorComum = <T>(valores: (T | undefined | null)[]): TValorComum<T> => {
  if (valores.length === 0) return { misto: false, valor: undefined };
  const chave = (valor: unknown) =>
    Array.isArray(valor) ? JSON.stringify([...valor].map(String).sort()) : JSON.stringify(valor ?? null);
  const primeira = chave(valores[0]);
  const misto = valores.some((valor) => chave(valor) !== primeira);
  return { misto, valor: misto ? undefined : ((valores[0] ?? undefined) as T | undefined) };
};

export type TRascunho = Partial<{
  state_id: string;
  priority: TIssuePriorities;
  assignee_ids: string[];
  label_ids: string[];
  start_date: string | null;
  target_date: string | null;
}>;

/** Quantas mudanças o rascunho carrega — é o número que vai no botão. */
export const quantasMudancas = (rascunho: TRascunho, propriedades: Record<string, unknown>): number =>
  Object.keys(rascunho).length + Object.keys(propriedades).length;

/**
 * Datas coerentes ANTES de pedir.
 *
 * O servidor confere de novo, e por tarefa — ele conhece as datas que já
 * existem. Aqui só se evita a viagem quando o próprio rascunho já se contradiz.
 */
export const datasDoRascunhoSaoCoerentes = (rascunho: TRascunho): boolean => {
  const inicio = rascunho.start_date;
  const vencimento = rascunho.target_date;
  if (!inicio || !vencimento) return true;
  return inicio <= vencimento;
};

export type TPermissaoDeEdicao = {
  usuarioId: string | undefined;
  /** Administradora ou membro NAQUELE projeto — convidado só edita o que criou. */
  ehEditorEm: (projectId: string | undefined | null) => boolean;
};

export const podeEditar = (tarefa: TIssue, permissao: TPermissaoDeEdicao): boolean => {
  if (permissao.ehEditorEm(tarefa.project_id)) return true;
  return !!permissao.usuarioId && tarefa.created_by === permissao.usuarioId;
};

export const separarEditaveis = (tarefas: TIssue[], permissao: TPermissaoDeEdicao) => {
  const editaveis: TIssue[] = [];
  const bloqueadas: TIssue[] = [];
  tarefas.forEach((tarefa) => (podeEditar(tarefa, permissao) ? editaveis : bloqueadas).push(tarefa));
  return { editaveis, bloqueadas };
};

/** Um pedido por projeto — o endpoint é por projeto, a seleção não. */
export const agruparPorProjeto = (tarefas: TIssue[]): Record<string, string[]> => {
  const grupos: Record<string, string[]> = {};
  tarefas.forEach((tarefa) => {
    if (!tarefa.project_id) return;
    (grupos[tarefa.project_id] ??= []).push(tarefa.id);
  });
  return grupos;
};
