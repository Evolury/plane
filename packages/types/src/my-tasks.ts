/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: tipos de "Minhas tarefas" — etapas pessoais e associação item↔etapa.
// Regras em docs/evolury/funcionalidades/minhas-tarefas/.

import type { TStateGroups } from "./state";

export type TWorkStage = {
  id: string;
  name: string;
  color: string;
  /** Grupo global (triage não é elegível) */
  group: TStateGroups;
  sort_order: number;
  /** A "primeira etapa": recebe todo item atribuído sem associação */
  is_default: boolean;
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
