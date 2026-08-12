/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: raiz de "Minhas tarefas" — lista/kanban agrupados por etapa
// pessoal sobre os layouts base (ADR 0002), com drag entre etapas e
// reordenação pessoal. Espelho da página de perfil.

import { observer } from "mobx-react";
import { useParams } from "next/navigation";
import useSWR from "swr";
// plane imports
import { useTranslation } from "@plane/i18n";
import { Spinner } from "@plane/ui";
import { EIssuesStoreType } from "@plane/types";
// components
import { MyTasksKanBanLayout } from "@/components/issues/issue-layouts/kanban/roots/my-tasks-root";
import { MyTasksListLayout } from "@/components/issues/issue-layouts/list/roots/my-tasks-root";
import { IssuePeekOverview } from "@/components/issues/peek-overview";
// hooks
import { useIssues } from "@/hooks/store/use-issues";
import { useMyTasks } from "@/hooks/use-my-tasks";
import { IssuesStoreContext } from "@/hooks/use-issue-layout-store";

export const MyTasksRoot = observer(function MyTasksRoot() {
  const { workspaceSlug } = useParams();
  const { t } = useTranslation();
  // store hooks
  const {
    issuesFilter: { issueFilters, fetchFilters },
  } = useIssues(EIssuesStoreType.MY_TASKS);
  const { fetchStages, sortedStages, stagesLoader } = useMyTasks();
  // derived values
  const activeLayout = issueFilters?.displayFilters?.layout || undefined;

  // As etapas precisam existir antes dos layouts: as colunas/grupos vêm delas.
  const { isLoading } = useSWR(
    workspaceSlug ? `MY_TASKS_ROOT_${workspaceSlug}` : null,
    async () => {
      if (!workspaceSlug) return;
      await Promise.all([fetchStages(workspaceSlug.toString()), fetchFilters(workspaceSlug.toString())]);
    },
    { revalidateIfStale: false, revalidateOnFocus: false }
  );

  if ((isLoading || stagesLoader) && sortedStages.length === 0) {
    return (
      <div className="grid h-full w-full place-items-center">
        <Spinner />
      </div>
    );
  }

  if (sortedStages.length === 0) {
    return (
      <div className="grid h-full w-full place-items-center">
        <p className="text-13 text-tertiary">{t("my_tasks.empty_state")}</p>
      </div>
    );
  }

  return (
    <IssuesStoreContext.Provider value={EIssuesStoreType.MY_TASKS}>
      <div className="flex h-full w-full flex-col">
        <div className="relative h-full w-full overflow-auto">
          {activeLayout === "kanban" ? <MyTasksKanBanLayout /> : <MyTasksListLayout />}
        </div>
      </div>
      {/* peek overview */}
      <IssuePeekOverview />
    </IssuesStoreContext.Provider>
  );
});
