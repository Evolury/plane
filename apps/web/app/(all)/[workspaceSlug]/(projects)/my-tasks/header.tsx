/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: cabeçalho de "Minhas tarefas" com o alternador lista/kanban.
// O agrupamento é fixo por etapa (spec); só o layout troca aqui — a linha
// completa de filtros/propriedades chega na F5.

import { useState } from "react";
import { observer } from "mobx-react";
import { useParams } from "next/navigation";
import { LayoutGrid, List, ListTodo, Settings2 } from "lucide-react";
// plane imports
import { EIssueFilterType } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { EIssuesStoreType } from "@plane/types";
import type { TIssueLayouts } from "@plane/types";
import { Breadcrumbs, Header } from "@plane/ui";
import { cn } from "@plane/utils";
// components
import { BreadcrumbLink } from "@/components/common/breadcrumb-link";
import { MyTasksStagesPanel } from "@/components/my-tasks/stages-panel";
// hooks
import { useIssues } from "@/hooks/store/use-issues";

const LAYOUT_OPTIONS: { key: TIssueLayouts; icon: typeof List; labelKey: string }[] = [
  { key: "list", icon: List, labelKey: "issue.layouts.list" },
  { key: "kanban", icon: LayoutGrid, labelKey: "issue.layouts.kanban" },
];

export const MyTasksHeader = observer(function MyTasksHeader() {
  const { workspaceSlug } = useParams();
  const { t } = useTranslation();
  // store hooks
  const {
    issuesFilter: { issueFilters, updateFilters },
  } = useIssues(EIssuesStoreType.MY_TASKS);
  // states
  const [isStagesPanelOpen, setIsStagesPanelOpen] = useState(false);
  // derived values
  const activeLayout = issueFilters?.displayFilters?.layout ?? "list";

  const handleLayoutChange = (layout: TIssueLayouts) => {
    if (!workspaceSlug) return;
    updateFilters(workspaceSlug.toString(), undefined, EIssueFilterType.DISPLAY_FILTERS, { layout });
  };

  return (
    <Header>
      <Header.LeftItem>
        <div className="flex items-center gap-2.5">
          <Breadcrumbs>
            <Breadcrumbs.Item
              component={
                <BreadcrumbLink label={t("sidebar.my_tasks")} icon={<ListTodo className="size-4 text-secondary" />} />
              }
            />
          </Breadcrumbs>
        </div>
      </Header.LeftItem>
      <Header.RightItem>
        <button
          type="button"
          onClick={() => setIsStagesPanelOpen(true)}
          className="flex items-center gap-1.5 rounded-sm bg-layer-1 px-2 py-1 text-12 font-medium text-secondary hover:text-primary"
        >
          <Settings2 className="size-3.5" />
          {t("my_tasks.stages.title")}
        </button>
        <MyTasksStagesPanel isOpen={isStagesPanelOpen} onClose={() => setIsStagesPanelOpen(false)} />
        <div className="flex items-center gap-0.5 rounded-sm bg-layer-1 p-0.5">
          {LAYOUT_OPTIONS.map((option) => (
            <button
              key={option.key}
              type="button"
              aria-label={t(option.labelKey)}
              onClick={() => handleLayoutChange(option.key)}
              className={cn("grid place-items-center rounded-sm p-1 text-secondary hover:text-primary", {
                "shadow-sm bg-surface-1 text-primary": activeLayout === option.key,
              })}
            >
              <option.icon className="size-3.5" />
            </button>
          ))}
        </div>
      </Header.RightItem>
    </Header>
  );
});
