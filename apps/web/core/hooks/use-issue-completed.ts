/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: tarefa concluída ganha tratamento visual próprio (ADR 0009).
// A informação vem do GRUPO do estado, não de um campo — é assim que todo o
// resto do produto decide o que é conclusão.

import { useProjectState } from "@/hooks/store/use-project-state";

export const useIsIssueCompleted = (stateId: string | null | undefined): boolean => {
  const { getStateById } = useProjectState();
  return getStateById(stateId ?? undefined)?.group === "completed";
};
