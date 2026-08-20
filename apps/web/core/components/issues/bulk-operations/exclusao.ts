/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: as contas da exclusão em massa (ADR 0018).
//
// Fora do componente de propósito: o que decide QUEM pode excluir O QUÊ é
// exatamente o que precisa de teste, e teste de componente com store, rota e
// permissão em volta prova menos e quebra mais.
//
// A tela não é a guarda: o servidor recusa o pedido inteiro se alguma tarefa
// não for de quem pediu. O que estas funções fazem é não OFERECER o que seria
// recusado — botão que promete e falha é pior que botão ausente.

import type { TIssue } from "@plane/types";

/** O mesmo teto do servidor (`plane/utils/exclusao_em_massa.py`). */
export const TETO_DE_EXCLUSAO_EM_MASSA = 500;

export type TPermissaoDeExclusao = {
  /** Quem está pedindo. */
  usuarioId: string | undefined;
  /** Administrador NAQUELE projeto — a seleção pode atravessar vários. */
  ehAdminEm: (projectId: string | undefined | null) => boolean;
};

/**
 * A mesma regra do servidor, e a mesma da exclusão de uma tarefa: administrador
 * do projeto OU quem criou.
 */
export const podeExcluir = (tarefa: TIssue, permissao: TPermissaoDeExclusao): boolean => {
  if (permissao.ehAdminEm(tarefa.project_id)) return true;
  return !!permissao.usuarioId && tarefa.created_by === permissao.usuarioId;
};

export type TSeparacao = { elegiveis: TIssue[]; bloqueadas: TIssue[] };

export const separarElegiveis = (tarefas: TIssue[], permissao: TPermissaoDeExclusao): TSeparacao => {
  const elegiveis: TIssue[] = [];
  const bloqueadas: TIssue[] = [];
  tarefas.forEach((tarefa) => (podeExcluir(tarefa, permissao) ? elegiveis : bloqueadas).push(tarefa));
  return { elegiveis, bloqueadas };
};

/**
 * Um pedido por projeto.
 *
 * O endpoint é por projeto, e a seleção não é: em "Minhas tarefas" e nas visões
 * do espaço, as tarefas escolhidas vêm de projetos diferentes. Sem agrupar,
 * metade da seleção iria no pedido errado e voltaria como "não encontrada".
 */
export const agruparPorProjeto = (tarefas: TIssue[]): Record<string, string[]> => {
  const grupos: Record<string, string[]> = {};
  tarefas.forEach((tarefa) => {
    if (!tarefa.project_id) return;
    (grupos[tarefa.project_id] ??= []).push(tarefa.id);
  });
  return grupos;
};

/** Passou do teto? A conta é por projeto, porque o pedido é por projeto. */
export const passouDoTeto = (grupos: Record<string, string[]>): boolean =>
  Object.values(grupos).some((ids) => ids.length > TETO_DE_EXCLUSAO_EM_MASSA);
