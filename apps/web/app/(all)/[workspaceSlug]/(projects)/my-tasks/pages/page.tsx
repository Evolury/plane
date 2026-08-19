/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: a aba Páginas de "Minhas tarefas" (ADR 0015).

import { useState } from "react";
import { observer } from "mobx-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import useSWR from "swr";
// plane imports
import { useTranslation } from "@plane/i18n";
import { cn } from "@plane/utils";
// components
import { PageHead } from "@/components/core/page-title";
import { EmptyStateDetailed } from "@plane/propel/empty-state";
import { MyTasksTabs } from "@/components/my-tasks/tabs";
import { PagesListHeaderRoot } from "@/components/pages/header";
import { PagesListRoot } from "@/components/pages/list/root";
import { PageLoader } from "@/components/pages/loaders/page-loader";
// hooks
import { EPageStoreType, usePageStore } from "@/hooks/store";
import type { Route } from "./+types/page";

const storeType = EPageStoreType.PERSONAL;

function PaginasPessoaisPage({ params }: Route.ComponentProps) {
  const { workspaceSlug } = params;
  const { t } = useTranslation();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [criando, setCriando] = useState(false);
  // store
  const { fetchPagesList, getCurrentProjectPageIdsByTab, createPage, loader } = usePageStore(storeType);
  // derived
  const pageType = searchParams.get("type") === "archived" ? "archived" : "private";

  useSWR(workspaceSlug ? `PERSONAL_PAGES_${workspaceSlug}` : null, () => fetchPagesList(workspaceSlug));

  const criarPagina = async () => {
    setCriando(true);
    try {
      const pagina = await createPage({});
      if (pagina?.id) router.push(`/${workspaceSlug}/my-tasks/pages/${pagina.id}`);
    } finally {
      setCriando(false);
    }
  };

  const idsDaAba = getCurrentProjectPageIdsByTab(pageType) ?? [];

  const conteudo = () => {
    if (loader === "init-loader") return <PageLoader />;
    if (idsDaAba.length === 0)
      return pageType === "archived" ? (
        <EmptyStateDetailed
          assetKey="page"
          title={t("my_tasks.pages.empty_archived_title")}
          description={t("my_tasks.pages.empty_archived_description")}
        />
      ) : (
        <EmptyStateDetailed
          assetKey="page"
          title={t("my_tasks.pages.empty_title")}
          description={t("my_tasks.pages.empty_description")}
          actions={[
            {
              label: t("my_tasks.pages.new"),
              onClick: criarPagina,
              variant: "primary",
              disabled: criando,
            },
          ]}
        />
      );
    return <PagesListRoot pageType={pageType} storeType={storeType} />;
  };

  return (
    <>
      <PageHead title={t("my_tasks.tabs.pages")} />
      <div className="relative flex h-full w-full flex-col overflow-hidden">
        <PagesListHeaderRoot
          storeType={storeType}
          navigation={<MyTasksTabs workspaceSlug={workspaceSlug} />}
          actions={
            <Link
              href={
                pageType === "archived"
                  ? `/${workspaceSlug}/my-tasks/pages`
                  : `/${workspaceSlug}/my-tasks/pages?type=archived`
              }
              className={cn("rounded-sm px-2 py-1 text-12 font-medium text-secondary hover:text-primary", {
                "bg-layer-1 text-primary": pageType === "archived",
              })}
            >
              {t("my_tasks.pages.archived")}
            </Link>
          }
        />
        <div className="h-full w-full overflow-hidden">{conteudo()}</div>
      </div>
    </>
  );
}

export default observer(PaginasPessoaisPage);
