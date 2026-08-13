/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: tarefa concluída ganha tratamento visual próprio (ADR 0009).
// A informação vem do GRUPO do estado, não de um campo — é assim que todo o
// resto do produto decide o que é conclusão.

import { useCallback } from "react";
import type { IState } from "@plane/types";
import { useProject } from "@/hooks/store/use-project";
import { useProjectState } from "@/hooks/store/use-project-state";

export const useIssueStateGroup = (stateId: string | null | undefined): string | undefined => {
  const { getStateById } = useProjectState();
  return getStateById(stateId ?? undefined)?.group;
};

export const useIsIssueCompleted = (stateId: string | null | undefined): boolean =>
  useIssueStateGroup(stateId) === "completed";

export const useIsIssueCancelled = (stateId: string | null | undefined): boolean =>
  useIssueStateGroup(stateId) === "cancelled";

/**
 * Aparência de tarefa encerrada, em um lugar só.
 *
 * Concluída e cancelada saem as duas do fluxo de trabalho, então as duas ficam
 * esmaecidas; a cancelada ganha um fundo levemente avermelhado, porque "não vai
 * ser feita" não é a mesma notícia que "foi feita". Vale para QUALQUER etapa do
 * grupo, não só para as que nascem com o projeto — é o grupo que manda, como em
 * todo o resto do produto.
 *
 * Devolve o mapa de classes para espalhar no `cn`; espalhe ANTES das classes de
 * seleção e arraste, que são transitórias e devem prevalecer.
 */
export const useClosedIssueStyles = (stateId: string | null | undefined): Record<string, boolean> => {
  const grupo = useIssueStateGroup(stateId);
  return {
    "opacity-60": grupo === "completed" || grupo === "cancelled",
    "bg-danger-subtle/50": grupo === "cancelled",
  };
};

/**
 * Destinos de concluir e reabrir, por projeto.
 *
 * Concluir espelha o resolvedor do backend (`get_completion_state`): o estado
 * configurado no projeto quando válido, senão o primeiro do grupo concluído por
 * `sequence`. Reabrir devolve ao estado padrão do projeto — o mesmo destino de
 * uma tarefa recém-criada.
 *
 * Fica separado do componente porque a conclusão em massa e a conclusão de
 * subtarefas precisam resolver o destino de VÁRIOS projetos, não só o do item
 * que está na tela.
 */
export const useCompletionTargets = () => {
  const { getProjectStates } = useProjectState();
  const { getProjectById } = useProject();

  const getCompletionState = useCallback(
    (projectId: string | null | undefined): IState | undefined => {
      const estados = getProjectStates(projectId ?? undefined) ?? [];
      const concluidos = estados.filter((e) => e.group === "completed").sort((a, b) => a.sequence - b.sequence);
      const configurado = concluidos.find((e) => e.id === getProjectById(projectId ?? undefined)?.completion_state);
      return configurado ?? concluidos[0];
    },
    [getProjectStates, getProjectById]
  );

  const getReopenState = useCallback(
    (projectId: string | null | undefined): IState | undefined => {
      const estados = getProjectStates(projectId ?? undefined) ?? [];
      // Nunca "reabrir" para um estado que segue concluído ou cancelado.
      const abertos = estados
        .filter((e) => e.group !== "completed" && e.group !== "cancelled")
        .sort((a, b) => a.sequence - b.sequence);
      return abertos.find((e) => e.default) ?? abertos[0];
    },
    [getProjectStates]
  );

  return { getCompletionState, getReopenState };
};
