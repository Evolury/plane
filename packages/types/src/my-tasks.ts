/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: tipos de "Minhas tarefas" — etapas pessoais e associação item↔etapa.
// Regras em docs/evolury/funcionalidades/minhas-tarefas/.

import type { TStateGroups } from "./state";

// Evolury: o tipo mora em `state.ts` — declará-lo aqui fechava um ciclo entre
// os dois arquivos (ADR 0014). Reexportado para quem já o importava daqui.
export type { TBaldeDeVencimento } from "./state";

export type TWorkStage = {
  id: string;
  name: string;
  color: string;
  /** Grupo global (triage não é elegível) */
  group: TStateGroups;
  sort_order: number;
  /** A "primeira etapa": recebe todo item atribuído sem associação */
  is_default: boolean;
  /** Destino da tarefa concluída, entre as etapas do grupo concluído */
  is_completion: boolean;
  /**
   * Evolury: para onde a varredura diária manda cada balde de vencimento
   * (ADR 0014). Opcionais, ao contrário de `is_default` — balde sem etapa
   * marcada simplesmente não move ninguém.
   */
  is_due_today: boolean;
  is_due_tomorrow: boolean;
  is_due_later: boolean;
  is_overdue: boolean;
  /**
   * A varredura não TIRA tarefa desta etapa. De saída, nunca de chegada:
   * a etapa de vencidas é destino e travada ao mesmo tempo.
   */
  automation_disabled: boolean;
  workspace: string;
  owner: string;
  created_at: string;
  updated_at: string;
};

export type TWorkStageIssue = {
  id: string;
  stage: string;
  issue: string;
  sort_order: number;
  workspace: string;
  owner: string;
};
