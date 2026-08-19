/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TLogoProps } from "../common";
import type { EPageAccess } from "../enums";
import type { TPageExtended } from "./extended";

export type TPage = {
  access: EPageAccess | undefined;
  archived_at: string | null | undefined;
  color: string | undefined;
  created_at: Date | undefined;
  created_by: string | undefined;
  description_json: object | undefined;
  description_html: string | undefined;
  id: string | undefined;
  is_favorite: boolean;
  is_locked: boolean;
  label_ids: string[] | undefined;
  name: string | undefined;
  owned_by: string | undefined;
  project_ids?: string[] | undefined;
  updated_at: Date | undefined;
  updated_by: string | undefined;
  workspace: string | undefined;
  logo_props: TLogoProps | undefined;
  deleted_at: Date | undefined;
  /**
   * Evolury: meu papel numa página pessoal de outra pessoa — 5 pode ler, 15
   * pode editar, ausente quando a página é minha ou é de projeto (ADR 0015).
   */
  share_role?: number | null;
} & TPageExtended;

// page filters
// Evolury: "shared" é a aba "Compartilhado comigo" (ADR 0015).
export type TPageNavigationTabs = "public" | "private" | "archived" | "shared";

export type TPageFiltersSortKey = "name" | "created_at" | "updated_at" | "opened_at";

export type TPageFiltersSortBy = "asc" | "desc";

export type TPageFilterProps = {
  created_at?: string[] | null;
  created_by?: string[] | null;
  favorites?: boolean;
  labels?: string[] | null;
};

export type TPageFilters = {
  searchQuery: string;
  sortKey: TPageFiltersSortKey;
  sortBy: TPageFiltersSortBy;
  filters?: TPageFilterProps;
};

export type TPageEmbedType = "mention" | "issue";

export type TPageVersion = {
  created_at: string;
  created_by: string;
  deleted_at: string | null;
  description_binary?: string | null;
  description_html?: string | null;
  description_json?: object;
  id: string;
  last_saved_at: string;
  owned_by: string;
  page: string;
  updated_at: string;
  updated_by: string;
  workspace: string;
};

export type TDocumentPayload = {
  description_binary: string;
  description_html: string;
  description_json: object;
};

export type TWebhookConnectionQueryParams = {
  // Evolury: `personal_page` é a página de "Minhas tarefas" (ADR 0015).
  documentType: "project_page" | "team_page" | "workspace_page" | "personal_page";
  projectId?: string;
  teamId?: string;
  workspaceSlug: string;
};

/**
 * Evolury: uma linha de "esta página pessoal também é vista por" (ADR 0015).
 * Os papéis são 5 (pode ler) e 15 (pode editar), na mesma escala de
 * `EUserPermissions`.
 */
export type TPageShare = {
  id: string;
  page: string;
  shared_with: string;
  shared_with_detail?: {
    id: string;
    display_name: string;
    avatar_url?: string | null;
  };
  role: number;
  created_at?: string;
};

export const PAPEL_DA_PAGINA = { LER: 5, EDITAR: 15 } as const;
