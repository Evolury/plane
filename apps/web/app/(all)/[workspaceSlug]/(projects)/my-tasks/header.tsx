/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: cabeçalho de "Minhas tarefas" — abas Tarefas/Páginas (ADR 0015) e,
// à direita, os controles da aba aberta: gestão de etapas e filtros na de
// tarefas (F5), criação de página na de páginas.

import { useState } from "react";
import { observer } from "mobx-react";
import { ListTodo, Settings2 } from "lucide-react";
import { usePathname, useParams, useRouter } from "next/navigation";
// plane imports
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { Breadcrumbs, Header } from "@plane/ui";
// components
import { BreadcrumbLink } from "@/components/common/breadcrumb-link";
import { MyTasksFilters } from "@/components/my-tasks/filters";
import { MyTasksStagesPanel } from "@/components/my-tasks/stages-panel";
// hooks
import { EPageStoreType, usePageStore } from "@/hooks/store";

export const MyTasksHeader = observer(function MyTasksHeader() {
  const { t } = useTranslation();
  const router = useRouter();
  const pathname = usePathname();
  const { workspaceSlug } = useParams();
  // states
  const [isStagesPanelOpen, setIsStagesPanelOpen] = useState(false);
  const [criandoPagina, setCriandoPagina] = useState(false);
  // store
  const { createPage } = usePageStore(EPageStoreType.PERSONAL);
  // derived
  const naAbaDePaginas = !!pathname?.includes("/my-tasks/pages");
  // "Compartilhado comigo" é só leitura do que é dos outros: nem controles de
  // tarefa, nem criar página.
  const naAbaCompartilhada = !!pathname?.includes("/my-tasks/shared");

  const criarPagina = async () => {
    setCriandoPagina(true);
    try {
      const pagina = await createPage({});
      if (pagina?.id) router.push(`/${workspaceSlug}/my-tasks/pages/${pagina.id}`);
    } catch {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("toast.error"),
        message: t("my_tasks.pages.create_failed"),
      });
    } finally {
      setCriandoPagina(false);
    }
  };

  return (
    <Header>
      <Header.LeftItem>
        <Breadcrumbs>
          <Breadcrumbs.Item
            component={
              <BreadcrumbLink label={t("sidebar.my_tasks")} icon={<ListTodo className="size-4 text-secondary" />} />
            }
          />
        </Breadcrumbs>
      </Header.LeftItem>
      <Header.RightItem>
        {naAbaCompartilhada ? null : naAbaDePaginas ? (
          <Button variant="primary" size="lg" onClick={criarPagina} loading={criandoPagina}>
            {criandoPagina ? t("my_tasks.pages.creating") : t("my_tasks.pages.new")}
          </Button>
        ) : (
          <>
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
          </>
        )}
      </Header.RightItem>
    </Header>
  );
});
