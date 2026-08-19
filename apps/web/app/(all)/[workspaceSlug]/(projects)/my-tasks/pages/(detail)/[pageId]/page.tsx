/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: o editor de uma página pessoal (ADR 0015). O editor é o mesmo das
// páginas de projeto — o que muda é o serviço por trás e o documento que o
// serviço `live` abre (`personal_page`).

import { useCallback, useEffect, useMemo } from "react";
import { observer } from "mobx-react";
import Link from "next/link";
import useSWR from "swr";
// plane imports
import { useTranslation } from "@plane/i18n";
import { getButtonStyling } from "@plane/propel/button";
import type { TSearchEntityRequestPayload, TWebhookConnectionQueryParams } from "@plane/types";
import { EFileAssetType } from "@plane/types";
import { cn } from "@plane/utils";
// components
import { LogoSpinner } from "@/components/common/logo-spinner";
import { PageHead } from "@/components/core/page-title";
import type { TPageRootConfig, TPageRootHandlers } from "@/components/pages/editor/page-root";
import { PageRoot } from "@/components/pages/editor/page-root";
// hooks
import { useEditorConfig } from "@/hooks/editor";
import { EPageStoreType, usePage, usePageStore } from "@/hooks/store";
import { useEditorAsset } from "@/hooks/store/use-editor-asset";
import { useWorkspace } from "@/hooks/store/use-workspace";
import { useAppRouter } from "@/hooks/use-app-router";
// services
import { PersonalPageService, PersonalPageVersionService } from "@/services/page";
import { WorkspaceService } from "@/services/workspace.service";
import type { Route } from "./+types/page";

const workspaceService = new WorkspaceService();
const personalPageService = new PersonalPageService();
const personalPageVersionService = new PersonalPageVersionService();

const storeType = EPageStoreType.PERSONAL;

function PaginaPessoalDetalhe({ params }: Route.ComponentProps) {
  const router = useAppRouter();
  const { t } = useTranslation();
  const { workspaceSlug, pageId } = params;
  // store
  const { createPage, fetchPageDetails } = usePageStore(storeType);
  const page = usePage({ pageId, storeType });
  const { getWorkspaceBySlug } = useWorkspace();
  const { uploadEditorAsset, duplicateEditorAsset } = useEditorAsset();
  // derived
  const workspaceId = workspaceSlug ? (getWorkspaceBySlug(workspaceSlug)?.id ?? "") : "";
  const { canCurrentUserAccessPage, id, name, updateDescription } = page ?? {};

  // Menção e busca de entidade não recebem projeto: o alcance é o workspace.
  const buscarEntidade = useCallback(
    async (payload: TSearchEntityRequestPayload) => await workspaceService.searchEntity(workspaceSlug, payload),
    [workspaceSlug]
  );

  const { getEditorFileHandlers } = useEditorConfig();

  const { error: erroDetalhe } = useSWR(
    `PERSONAL_PAGE_DETAILS_${pageId}`,
    () => fetchPageDetails(workspaceSlug, pageId),
    { revalidateIfStale: true, revalidateOnFocus: true, revalidateOnReconnect: true }
  );

  const handlers: TPageRootHandlers = useMemo(
    () => ({
      create: createPage,
      fetchAllVersions: async (alvo) => await personalPageVersionService.fetchAllVersions(workspaceSlug, alvo),
      fetchDescriptionBinary: async () => {
        if (!id) return;
        return await personalPageService.fetchDescriptionBinary(workspaceSlug, id);
      },
      fetchEntity: buscarEntidade,
      fetchVersionDetails: async (alvo, versionId) =>
        await personalPageVersionService.fetchVersionById(workspaceSlug, alvo, versionId),
      restoreVersion: async () => {},
      getRedirectionLink: (alvo) =>
        alvo ? `/${workspaceSlug}/my-tasks/pages/${alvo}` : `/${workspaceSlug}/my-tasks/pages`,
      updateDescription: updateDescription ?? (async () => {}),
    }),
    [createPage, buscarEntidade, id, updateDescription, workspaceSlug]
  );

  const config: TPageRootConfig = useMemo(
    () => ({
      fileHandler: getEditorFileHandlers({
        // Sem projeto: o anexo sobe pela rota de workspace, que já aceita
        // PAGE_DESCRIPTION.
        uploadFile: async (blockId, file) => {
          const { asset_id } = await uploadEditorAsset({
            blockId,
            data: { entity_identifier: id ?? "", entity_type: EFileAssetType.PAGE_DESCRIPTION },
            file,
            workspaceSlug,
          });
          return asset_id;
        },
        duplicateFile: async (assetId: string) => {
          const { asset_id } = await duplicateEditorAsset({
            assetId,
            entityId: id,
            entityType: EFileAssetType.PAGE_DESCRIPTION,
            workspaceSlug,
          });
          return asset_id;
        },
        workspaceId,
        workspaceSlug,
      }),
    }),
    [getEditorFileHandlers, workspaceId, workspaceSlug, uploadEditorAsset, id, duplicateEditorAsset]
  );

  const parametrosDoLive: TWebhookConnectionQueryParams = useMemo(
    () => ({ documentType: "personal_page", workspaceSlug }),
    [workspaceSlug]
  );

  useEffect(() => {
    if (page?.deleted_at && page?.id) router.push(handlers.getRedirectionLink());
  }, [page?.deleted_at, page?.id, router, handlers]);

  if ((!page || !id) && !erroDetalhe)
    return (
      <div className="grid size-full place-items-center">
        <LogoSpinner />
      </div>
    );

  if (erroDetalhe || !canCurrentUserAccessPage)
    return (
      <div className="flex h-full w-full flex-col items-center justify-center">
        <h3 className="text-center text-16 font-semibold">{t("ui.page_not_found")}</h3>
        <Link href={`/${workspaceSlug}/my-tasks/pages`} className={cn(getButtonStyling("secondary", "base"), "mt-5")}>
          {t("ui.view_other_pages")}
        </Link>
      </div>
    );

  if (!page) return null;

  return (
    <>
      <PageHead title={name} />
      <div className="flex h-full flex-col justify-between">
        <div className="relative flex h-full w-full flex-shrink-0 flex-col overflow-hidden">
          <PageRoot
            config={config}
            handlers={handlers}
            storeType={storeType}
            page={page}
            webhookConnectionParams={parametrosDoLive}
            workspaceSlug={workspaceSlug}
          />
        </div>
      </div>
    </>
  );
}

export default observer(PaginaPessoalDetalhe);
