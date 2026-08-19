/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: o editor de página pessoal tem cabeçalho próprio — sem as abas de
// "Minhas tarefas" e sem os controles de tarefa (ADR 0015).

import { Outlet } from "react-router";
import useSWR from "swr";
import { AppHeader } from "@/components/core/app-header";
import { ContentWrapper } from "@/components/core/content-wrapper";
import { EPageStoreType, usePageStore } from "@/hooks/store";
import type { Route } from "./+types/layout";
import { PaginaPessoalHeader } from "./header";

export default function LayoutDaPaginaPessoal({ params }: Route.ComponentProps) {
  const { workspaceSlug } = params;
  const { fetchPagesList } = usePageStore(EPageStoreType.PERSONAL);
  // A lista alimenta o seletor de páginas do cabeçalho.
  useSWR(`PERSONAL_PAGES_${workspaceSlug}`, () => fetchPagesList(workspaceSlug));
  return (
    <>
      <AppHeader header={<PaginaPessoalHeader />} />
      <ContentWrapper>
        <Outlet />
      </ContentWrapper>
    </>
  );
}
