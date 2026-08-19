/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TBaldeDeVencimento } from "./my-tasks";

export type TStateGroups = "backlog" | "unstarted" | "started" | "completed" | "cancelled";

export interface IState {
  readonly id: string;
  color: string;
  default: boolean;
  description: string;
  group: TStateGroups;
  name: string;
  project_id: string;
  sequence: number;
  workspace_id: string;
  order: number;
}

export interface IStateLite {
  color: string;
  group: TStateGroups;
  id: string;
  name: string;
}

export interface IStateResponse {
  [key: string]: IState[];
}

export type TStateOperationsCallbacks = {
  createState: (data: Partial<IState>) => Promise<IState>;
  updateState: (stateId: string, data: Partial<IState>) => Promise<IState | undefined>;
  deleteState: (stateId: string) => Promise<void>;
  moveStatePosition: (stateId: string, data: Partial<IState>) => Promise<void>;
  markStateAsDefault: (stateId: string) => Promise<void>;
  // Evolury: destino da conclusão (ADR 0009). Opcionais porque cada tela
  // responde de um jeito — o projeto grava em `completion_state`, "Minhas
  // tarefas" marca a etapa pessoal — e o componente compartilhado não deve
  // saber de nenhum dos dois.
  markStateAsCompletion?: (stateId: string) => Promise<void>;
  getCompletionStateInfo?: (stateId: string) => { isCompletion: boolean; isExplicit: boolean };
  // Evolury: baldes de vencimento e opt-out da varredura (ADR 0014). Opcionais
  // pelo mesmo motivo dos dois acima — só "Minhas tarefas" sabe responder, e o
  // componente compartilhado não deve saber que eles existem. Estado de projeto
  // não passa nenhum, e nada aparece na tela dele.
  markStageBucket?: (stageId: string, balde: TBaldeDeVencimento, ativo: boolean) => Promise<void>;
  getStageBucketInfo?: (stageId: string) => TMarcacoesDaEtapa;
  toggleStageAutomation?: (stageId: string, desativada: boolean) => Promise<void>;
  /**
   * Evolury: esta etapa pode ser excluída?
   *
   * Opcional pelo mesmo motivo dos outros: só "Minhas tarefas" sabe responder.
   * Sem ele, vale a regra herdada — desabilitar a padrão e a última que sobrar.
   *
   * Quando responde `false`, o controle de excluir **não é desenhado**, e não
   * apenas desabilitado: botão cinza que não faz nada é convite a tentar.
   */
  canDeleteStage?: (stageId: string) => boolean;
  /**
   * Evolury: como esta tela chama a etapa que recebe o que chega.
   *
   * Em Configurações → Estados isso é o "padrão"; em "Minhas tarefas" é a
   * **entrada** — o lugar por onde a tarefa entra. Mesma mecânica, nomes
   * diferentes, e o componente compartilhado não deve escolher por ninguém.
   *
   * Viaja neste objeto, e não como propriedade própria, porque a alternativa
   * seria atravessar quatro componentes com uma prop só para trocar um
   * substantivo. O objeto já carrega getters além de ações — `getStageBucketInfo`
   * e `getCompletionStateInfo` estão aqui pelo mesmo motivo.
   */
  rotulosDaEntrada?: { atual: string; acao: string; salvando: string };
};

/** Evolury: o que a linha da etapa mostra sobre a varredura (ADR 0014). */
export type TMarcacoesDaEtapa = {
  hoje: boolean;
  amanha: boolean;
  depois: boolean;
  vencidas: boolean;
  /** A varredura não TIRA tarefa daqui. De saída, nunca de chegada. */
  semAutomacao: boolean;
};
