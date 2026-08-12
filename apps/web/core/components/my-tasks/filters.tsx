/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: controles de filtro/exibição de "Minhas tarefas" (F5) — espelho do
// ProfileIssuesFilter: seleção de layout, toggle de filtros ricos e dropdown
// de propriedades de exibição. O agrupamento não aparece como escolha real:
// é fixo por etapa (spec), e o dropdown mostra a única opção travada.

import { useCallback } from "react";
import { observer } from "mobx-react";
import { useParams } from "next/navigation";
// plane imports
import { EIssueFilterType, ISSUE_DISPLAY_FILTERS_BY_PAGE } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import type { IIssueDisplayFilterOptions, IIssueDisplayProperties } from "@plane/types";
import { EIssueLayoutTypes, EIssuesStoreType } from "@plane/types";
// components
import { DisplayFiltersSelection, FiltersDropdown, LayoutSelection } from "@/components/issues/issue-layouts/filters";
import { WorkItemFiltersToggle } from "@/components/work-item-filters/filters-toggle";
// hooks
import { useIssues } from "@/hooks/store/use-issues";

export const MyTasksFilters = observer(function MyTasksFilters() {
  const { t } = useTranslation();
  const { workspaceSlug: routerWorkspaceSlug } = useParams();
  const workspaceSlug = routerWorkspaceSlug?.toString();
  const {
    issuesFilter: { issueFilters, updateFilters },
  } = useIssues(EIssuesStoreType.MY_TASKS);
  const activeLayout = issueFilters?.displayFilters?.layout;

  const handleLayoutChange = useCallback(
    (layout: EIssueLayoutTypes) => {
      if (!workspaceSlug) return;
      updateFilters(workspaceSlug, undefined, EIssueFilterType.DISPLAY_FILTERS, { layout: layout });
    },
    [workspaceSlug, updateFilters]
  );

  const handleDisplayFilters = useCallback(
    (updatedDisplayFilter: Partial<IIssueDisplayFilterOptions>) => {
      if (!workspaceSlug) return;
      updateFilters(workspaceSlug, undefined, EIssueFilterType.DISPLAY_FILTERS, updatedDisplayFilter);
    },
    [workspaceSlug, updateFilters]
  );

  const handleDisplayProperties = useCallback(
    (property: Partial<IIssueDisplayProperties>) => {
      if (!workspaceSlug) return;
      updateFilters(workspaceSlug, undefined, EIssueFilterType.DISPLAY_PROPERTIES, property);
    },
    [workspaceSlug, updateFilters]
  );

  return (
    <div className="relative flex items-center justify-end gap-2">
      <LayoutSelection
        layouts={[EIssueLayoutTypes.LIST, EIssueLayoutTypes.KANBAN]}
        onChange={(layout) => handleLayoutChange(layout)}
        selectedLayout={activeLayout}
      />
      {workspaceSlug && <WorkItemFiltersToggle entityType={EIssuesStoreType.MY_TASKS} entityId={workspaceSlug} />}
      <FiltersDropdown title={t("common.display")} placement="bottom-end">
        <DisplayFiltersSelection
          layoutDisplayFiltersOptions={
            activeLayout ? ISSUE_DISPLAY_FILTERS_BY_PAGE.my_tasks.layoutOptions[activeLayout] : undefined
          }
          displayFilters={issueFilters?.displayFilters ?? {}}
          handleDisplayFiltersUpdate={handleDisplayFilters}
          displayProperties={issueFilters?.displayProperties ?? {}}
          handleDisplayPropertiesUpdate={handleDisplayProperties}
        />
      </FiltersDropdown>
    </div>
  );
});
