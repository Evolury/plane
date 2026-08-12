/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: raiz de "Minhas tarefas" — layouts base agrupados por etapa
// (ADR 0002), com filtros ricos (F5) e empty states. Espelho da página de
// perfil.

import { observer } from "mobx-react";
import { useParams } from "next/navigation";
import useSWR from "swr";
// plane imports
import { ISSUE_DISPLAY_FILTERS_BY_PAGE } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { EmptyStateDetailed } from "@plane/propel/empty-state";
import { Spinner } from "@plane/ui";
import { EIssuesStoreType } from "@plane/types";
// components
import { MyTasksKanBanLayout } from "@/components/issues/issue-layouts/kanban/roots/my-tasks-root";
import { MyTasksListLayout } from "@/components/issues/issue-layouts/list/roots/my-tasks-root";
import { IssuePeekOverview } from "@/components/issues/peek-overview";
import { WorkspaceLevelWorkItemFiltersHOC } from "@/components/work-item-filters/filters-hoc/workspace-level";
import { WorkItemFiltersRow } from "@/components/work-item-filters/filters-row";
// hooks
import { useIssues } from "@/hooks/store/use-issues";
import { useMyTasks } from "@/hooks/use-my-tasks";
import { IssuesStoreContext } from "@/hooks/use-issue-layout-store";

export const MyTasksRoot = observer(function MyTasksRoot() {
  const { workspaceSlug: routerWorkspaceSlug } = useParams();
  const workspaceSlug = routerWorkspaceSlug?.toString();
  const { t } = useTranslation();
  // store hooks
  const {
    issues,
    issuesFilter: { issueFilters, fetchFilters, updateFilterExpression },
  } = useIssues(EIssuesStoreType.MY_TASKS);
  const { fetchStages, sortedStages, stagesLoader } = useMyTasks();
  // derived values
  const activeLayout = issueFilters?.displayFilters?.layout || undefined;

  // As etapas precisam existir antes dos layouts: as colunas/grupos vêm delas.
  const { isLoading } = useSWR(
    workspaceSlug ? `MY_TASKS_ROOT_${workspaceSlug}` : null,
    async () => {
      if (!workspaceSlug) return;
      await Promise.all([fetchStages(workspaceSlug), fetchFilters(workspaceSlug)]);
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

  // Só depois do primeiro fetch dos itens: todos os grupos vazios ⇒ nada
  // atribuído (com filtros limpos) ou nada correspondente (com filtros).
  const groupedIssueIds = issues.groupedIssueIds;
  const isIssuesLoaded = issues.getIssueLoader() !== "init-loader" && groupedIssueIds !== undefined;
  const totalIssues = isIssuesLoaded
    ? Object.values(groupedIssueIds ?? {}).reduce((count, ids) => count + (Array.isArray(ids) ? ids.length : 0), 0)
    : undefined;

  if (!workspaceSlug) return null;

  return (
    <IssuesStoreContext.Provider value={EIssuesStoreType.MY_TASKS}>
      <WorkspaceLevelWorkItemFiltersHOC
        entityId={workspaceSlug}
        entityType={EIssuesStoreType.MY_TASKS}
        filtersToShowByLayout={ISSUE_DISPLAY_FILTERS_BY_PAGE.my_tasks.filters}
        initialWorkItemFilters={issueFilters}
        updateFilters={updateFilterExpression.bind(updateFilterExpression, workspaceSlug)}
        workspaceSlug={workspaceSlug}
      >
        {({ filter: myTasksWorkItemsFilter }) => (
          <>
            <div className="flex h-full w-full flex-col">
              {myTasksWorkItemsFilter && <WorkItemFiltersRow filter={myTasksWorkItemsFilter} />}
              <div className="relative h-full w-full overflow-auto">
                {totalIssues === 0 && myTasksWorkItemsFilter?.hasActiveFilters ? (
                  <EmptyStateDetailed
                    assetKey="search"
                    title={t("common_empty_state.search.title")}
                    description={t("common_empty_state.search.description")}
                    actions={[
                      {
                        label: t("common.clear"),
                        onClick: () => myTasksWorkItemsFilter?.clearFilters(),
                      },
                    ]}
                  />
                ) : totalIssues === 0 ? (
                  <EmptyStateDetailed
                    assetKey="work-item"
                    title={t("my_tasks.empty_title")}
                    description={t("my_tasks.empty_state")}
                  />
                ) : activeLayout === "kanban" ? (
                  <MyTasksKanBanLayout />
                ) : (
                  <MyTasksListLayout />
                )}
              </div>
            </div>
            {/* peek overview */}
            <IssuePeekOverview />
          </>
        )}
      </WorkspaceLevelWorkItemFiltersHOC>
    </IssuesStoreContext.Provider>
  );
});
