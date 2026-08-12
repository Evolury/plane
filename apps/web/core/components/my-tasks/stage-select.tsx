/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: seletor de etapa pessoal na linha "Você" do popover de
// responsáveis (F7 de minhas tarefas — espelho do recurso do Asana).
// Autocontido: busca as etapas (store) e a etapa efetiva do item (endpoint
// dedicado, sob demanda) e move via POST .../move/ — pessoal e silencioso
// (ADR 0001). Cliques aqui não podem alternar a atribuição: o chip vive
// dentro de um Combobox.Option, então tudo é interceptado com
// preventDefault/stopPropagation.

import { useState } from "react";
import { observer } from "mobx-react";
import { useParams } from "next/navigation";
import { createPortal } from "react-dom";
import { usePopper } from "react-popper";
import { ChevronDown } from "lucide-react";
import useSWR, { useSWRConfig } from "swr";
// plane imports
import { useTranslation } from "@plane/i18n";
import { EIssuesStoreType } from "@plane/types";
import { cn } from "@plane/utils";
// hooks
import { useIssues } from "@/hooks/store/use-issues";
import { useMyTasks } from "@/hooks/use-my-tasks";
// services
import { MyTasksService } from "@/services/my-tasks.service";

const myTasksService = new MyTasksService();

type TMyTasksStageSelectProps = {
  workItemId: string;
};

export const MyTasksStageSelect = observer(function MyTasksStageSelect(props: TMyTasksStageSelectProps) {
  const { workItemId } = props;
  const { workspaceSlug: routerWorkspaceSlug } = useParams();
  const workspaceSlug = routerWorkspaceSlug?.toString();
  const { t } = useTranslation();
  const { mutate } = useSWRConfig();
  // states
  const [isOpen, setIsOpen] = useState(false);
  const [referenceElement, setReferenceElement] = useState<HTMLButtonElement | null>(null);
  const [popperElement, setPopperElement] = useState<HTMLDivElement | null>(null);
  const { styles, attributes } = usePopper(referenceElement, popperElement, {
    placement: "bottom-end",
    modifiers: [{ name: "preventOverflow", options: { padding: 12 } }],
  });
  // store hooks
  const { sortedStages, fetchStages } = useMyTasks();
  const {
    issues: { fetchIssuesWithExistingPagination },
  } = useIssues(EIssuesStoreType.MY_TASKS);

  const swrKey = workspaceSlug ? `MY_TASKS_ISSUE_STAGE_${workspaceSlug}_${workItemId}` : null;
  const { data } = useSWR(
    swrKey,
    async () => {
      if (!workspaceSlug) return undefined;
      if (sortedStages.length === 0) await fetchStages(workspaceSlug);
      return myTasksService.getIssueStage(workspaceSlug, workItemId);
    },
    { revalidateIfStale: false, revalidateOnFocus: false }
  );

  const currentStage = sortedStages.find((stage) => stage.id === data?.stage_id);
  if (!currentStage) return null;

  const handleSelect = async (stageId: string) => {
    if (!workspaceSlug || stageId === currentStage.id) {
      setIsOpen(false);
      return;
    }
    setIsOpen(false);
    await myTasksService.moveIssue(workspaceSlug, workItemId, { stage_id: stageId });
    await mutate(swrKey);
    // Se a página de minhas tarefas estiver carregada, reflete sem reload
    // (retorna cedo quando a página nunca foi aberta).
    fetchIssuesWithExistingPagination(workspaceSlug, "mutation");
  };

  const stopAll = (e: React.SyntheticEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  return (
    <>
      <button
        type="button"
        ref={setReferenceElement}
        aria-label={t("my_tasks.stage_in_my_tasks")}
        title={t("my_tasks.stage_in_my_tasks")}
        className="flex max-w-24 flex-shrink-0 items-center gap-0.5 rounded-sm border border-subtle px-1 py-0.5 text-10 text-tertiary hover:bg-layer-1-hover hover:text-secondary"
        onClick={(e) => {
          stopAll(e);
          setIsOpen((prev) => !prev);
        }}
        onMouseDown={stopAll}
        onKeyDown={(e) => e.stopPropagation()}
      >
        <span
          className="size-2 flex-shrink-0 rounded-full"
          style={{ backgroundColor: currentStage.color }}
          aria-hidden="true"
        />
        <span className="truncate">{currentStage.name}</span>
        <ChevronDown className="size-3 flex-shrink-0" />
      </button>
      {isOpen &&
        createPortal(
          <div
            ref={setPopperElement}
            className="z-40 my-1 w-44 rounded-sm border-[0.5px] border-strong bg-surface-1 p-1 text-11 shadow-raised-200"
            style={{ ...styles.popper }}
            {...attributes.popper}
            onClick={(e) => e.stopPropagation()}
            onMouseDown={(e) => e.stopPropagation()}
          >
            {sortedStages.map((stage) => (
              <button
                key={stage.id}
                type="button"
                className={cn(
                  "flex w-full items-center gap-2 rounded-sm px-2 py-1 text-left hover:bg-layer-1-hover",
                  stage.id === currentStage.id ? "text-primary" : "text-secondary"
                )}
                onClick={(e) => {
                  stopAll(e);
                  handleSelect(stage.id);
                }}
              >
                <span
                  className="size-2 flex-shrink-0 rounded-full"
                  style={{ backgroundColor: stage.color }}
                  aria-hidden="true"
                />
                <span className="flex-grow truncate">{stage.name}</span>
              </button>
            ))}
          </div>,
          document.body
        )}
    </>
  );
});
