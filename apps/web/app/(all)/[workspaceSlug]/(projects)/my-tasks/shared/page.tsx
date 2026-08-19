/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: a aba "Compartilhado comigo" (ADR 0015) — páginas pessoais de outras
// pessoas. Página de projeto não entra: quem está no projeto já a vê lá, e
// listá-la aqui duplicaria a mesma página com regras de acesso diferentes.

import { observer } from "mobx-react";
import useSWR from "swr";
// plane imports
import { useTranslation } from "@plane/i18n";
import { EmptyStateDetailed } from "@plane/propel/empty-state";
// components
import { PageHead } from "@/components/core/page-title";
import { MyTasksTabs } from "@/components/my-tasks/tabs";
import { PagesListHeaderRoot } from "@/components/pages/header";
import { PagesListRoot } from "@/components/pages/list/root";
import { PageLoader } from "@/components/pages/loaders/page-loader";
// hooks
import { EPageStoreType, usePageStore } from "@/hooks/store";
import type { Route } from "./+types/page";

const storeType = EPageStoreType.PERSONAL;

function PaginasCompartilhadasComigo({ params }: Route.ComponentProps) {
  const { workspaceSlug } = params;
  const { t } = useTranslation();
  const { fetchSharedPages, getCurrentProjectPageIdsByTab, loader } = usePageStore(storeType);

  useSWR(workspaceSlug ? `PERSONAL_SHARED_PAGES_${workspaceSlug}` : null, () => fetchSharedPages(workspaceSlug));

  const ids = getCurrentProjectPageIdsByTab("shared") ?? [];

  const conteudo = () => {
    if (loader === "init-loader") return <PageLoader />;
    if (ids.length === 0)
      return (
        <EmptyStateDetailed
          assetKey="page"
          title={t("my_tasks.pages.shared_empty_title")}
          description={t("my_tasks.pages.shared_empty_description")}
        />
      );
    return <PagesListRoot pageType="shared" storeType={storeType} />;
  };

  return (
    <>
      <PageHead title={t("my_tasks.tabs.shared")} />
      <div className="relative flex h-full w-full flex-col overflow-hidden">
        <PagesListHeaderRoot storeType={storeType} navigation={<MyTasksTabs workspaceSlug={workspaceSlug} />} />
        <div className="h-full w-full overflow-hidden">{conteudo()}</div>
      </div>
    </>
  );
}

export default observer(PaginasCompartilhadasComigo);
