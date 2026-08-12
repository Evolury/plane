/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: cabeçalho de "Minhas tarefas" — gestão de etapas + controles
// padrão de layout/filtros/exibição (F5, espelho do perfil).

import { useState } from "react";
import { observer } from "mobx-react";
import { ListTodo, Settings2 } from "lucide-react";
// plane imports
import { useTranslation } from "@plane/i18n";
import { Breadcrumbs, Header } from "@plane/ui";
// components
import { BreadcrumbLink } from "@/components/common/breadcrumb-link";
import { MyTasksFilters } from "@/components/my-tasks/filters";
import { MyTasksStagesPanel } from "@/components/my-tasks/stages-panel";

export const MyTasksHeader = observer(function MyTasksHeader() {
  const { t } = useTranslation();
  // states
  const [isStagesPanelOpen, setIsStagesPanelOpen] = useState(false);

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
        <MyTasksFilters />
      </Header.RightItem>
    </Header>
  );
});
