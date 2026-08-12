/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: painel de gestão das etapas pessoais (F4 de minhas tarefas).
//
// Em vez de copiar a família project-states/, o painel a REUSA: o GroupList é
// parametrizado por callbacks e só lê os campos comuns (id/name/color/group/
// default/sequence), então um adaptador TWorkStage↔IState basta — zero
// divergência com o código herdado. Mapeamentos: sequence↔sort_order,
// default↔is_default; `description` não existe em etapa e é descartada.

import { useMemo } from "react";
import { observer } from "mobx-react";
import { useParams } from "next/navigation";
// plane imports
import { useTranslation } from "@plane/i18n";
import { MY_TASKS_STAGE_GROUP_ORDER } from "@plane/constants";
import type { IState, TStateOperationsCallbacks, TWorkStage } from "@plane/types";
import { EIssuesStoreType } from "@plane/types";
import { EModalWidth, ModalCore } from "@plane/ui";
// components
import { GroupList } from "@/components/project-states";
// hooks
import { useIssues } from "@/hooks/store/use-issues";
import { useMyTasks } from "@/hooks/use-my-tasks";

/** Etapa pessoal no formato que a família project-states consome. */
const stageToState = (stage: TWorkStage): IState => ({
  id: stage.id,
  name: stage.name,
  color: stage.color,
  group: stage.group,
  default: stage.is_default,
  description: "",
  project_id: "",
  workspace_id: stage.workspace,
  sequence: stage.sort_order,
  order: stage.sort_order,
});

/** Payload do formulário/drag de volta para o formato de etapa. */
const stateToStagePayload = (data: Partial<IState>): Partial<TWorkStage> => {
  const payload: Partial<TWorkStage> = {};
  if (data.name !== undefined) payload.name = data.name;
  if (data.color !== undefined) payload.color = data.color;
  if (data.group !== undefined) payload.group = data.group;
  if (data.sequence !== undefined) payload.sort_order = data.sequence;
  return payload;
};

type TMyTasksStagesPanelProps = {
  isOpen: boolean;
  onClose: () => void;
};

export const MyTasksStagesPanel = observer(function MyTasksStagesPanel(props: TMyTasksStagesPanelProps) {
  const { isOpen, onClose } = props;
  const { workspaceSlug: routerWorkspaceSlug } = useParams();
  const workspaceSlug = routerWorkspaceSlug?.toString();
  const { t } = useTranslation();
  // store hooks
  const { sortedStages, createStage, updateStage, deleteStage, markStageAsDefault } = useMyTasks();
  const {
    issues: { fetchIssuesWithExistingPagination },
  } = useIssues(EIssuesStoreType.MY_TASKS);

  const groupedStages = useMemo(() => {
    const grouped: Record<string, IState[]> = {};
    for (const group of MY_TASKS_STAGE_GROUP_ORDER) grouped[group] = [];
    for (const stage of sortedStages) {
      if (!grouped[stage.group]) grouped[stage.group] = [];
      grouped[stage.group].push(stageToState(stage));
    }
    return grouped;
  }, [sortedStages]);

  // Excluir migra associações para a padrão e trocar a padrão muda onde os
  // itens sem associação aparecem — nos dois casos a listagem é refeita para
  // o agrupamento refletir o servidor sem reload.
  const refetchIssues = () => {
    if (workspaceSlug) fetchIssuesWithExistingPagination(workspaceSlug, "mutation");
  };

  const stateOperationsCallbacks: TStateOperationsCallbacks = useMemo(
    () => ({
      createState: async (data: Partial<IState>) => {
        if (!workspaceSlug) throw new Error("workspace ausente");
        return stageToState(await createStage(workspaceSlug, stateToStagePayload(data)));
      },
      updateState: async (stageId: string, data: Partial<IState>) => {
        if (!workspaceSlug) return undefined;
        return stageToState(await updateStage(workspaceSlug, stageId, stateToStagePayload(data)));
      },
      deleteState: async (stageId: string) => {
        if (!workspaceSlug) return;
        await deleteStage(workspaceSlug, stageId);
        refetchIssues();
      },
      moveStatePosition: async (stageId: string, data: Partial<IState>) => {
        if (!workspaceSlug) return;
        await updateStage(workspaceSlug, stageId, stateToStagePayload(data));
      },
      markStateAsDefault: async (stageId: string) => {
        if (!workspaceSlug) return;
        await markStageAsDefault(workspaceSlug, stageId);
        refetchIssues();
      },
    }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [workspaceSlug, createStage, updateStage, deleteStage, markStageAsDefault]
  );

  return (
    <ModalCore isOpen={isOpen} handleClose={onClose} width={EModalWidth.XXXL}>
      <div className="flex max-h-[80vh] flex-col gap-4 overflow-hidden p-5">
        <div className="flex-shrink-0">
          <h3 className="text-16 font-medium">{t("my_tasks.stages.title")}</h3>
          <p className="mt-1 text-13 text-tertiary">{t("my_tasks.stages.description")}</p>
        </div>
        <div className="overflow-y-auto pr-1">
          <GroupList
            groupedStates={groupedStages}
            stateOperationsCallbacks={stateOperationsCallbacks}
            isEditable
            shouldTrackEvents={false}
          />
        </div>
      </div>
    </ModalCore>
  );
});
