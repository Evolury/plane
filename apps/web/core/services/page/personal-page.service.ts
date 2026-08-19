/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: páginas pessoais de "Minhas tarefas" (ADR 0015). Mesmo contrato do
// serviço de páginas de projeto, sem o projeto na rota — porque não há projeto.

import { API_BASE_URL } from "@plane/constants";
import type { TDocumentPayload, TPage, TPageShare } from "@plane/types";
import { APIService } from "@/services/api.service";

export class PersonalPageService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  private base(workspaceSlug: string) {
    return `/api/workspaces/${workspaceSlug}/my-tasks/pages`;
  }

  async fetchAll(workspaceSlug: string): Promise<TPage[]> {
    return this.get(`${this.base(workspaceSlug)}/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async fetchById(workspaceSlug: string, pageId: string, trackVisit: boolean): Promise<TPage> {
    return this.get(`${this.base(workspaceSlug)}/${pageId}/`, { params: { track_visit: trackVisit } })
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async create(workspaceSlug: string, data: Partial<TPage>): Promise<TPage> {
    return this.post(`${this.base(workspaceSlug)}/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async update(workspaceSlug: string, pageId: string, data: Partial<TPage>): Promise<TPage> {
    return this.patch(`${this.base(workspaceSlug)}/${pageId}/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async remove(workspaceSlug: string, pageId: string): Promise<void> {
    return this.delete(`${this.base(workspaceSlug)}/${pageId}/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async lock(workspaceSlug: string, pageId: string): Promise<void> {
    return this.post(`${this.base(workspaceSlug)}/${pageId}/lock/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async unlock(workspaceSlug: string, pageId: string): Promise<void> {
    return this.delete(`${this.base(workspaceSlug)}/${pageId}/lock/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async archive(workspaceSlug: string, pageId: string): Promise<{ archived_at: string }> {
    return this.post(`${this.base(workspaceSlug)}/${pageId}/archive/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async restore(workspaceSlug: string, pageId: string): Promise<void> {
    return this.delete(`${this.base(workspaceSlug)}/${pageId}/archive/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async fetchDescriptionBinary(workspaceSlug: string, pageId: string): Promise<any> {
    return this.get(`${this.base(workspaceSlug)}/${pageId}/description/`, {
      headers: { "Content-Type": "application/octet-stream" },
      responseType: "arraybuffer",
    })
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async updateDescription(workspaceSlug: string, pageId: string, data: TDocumentPayload): Promise<any> {
    return this.patch(`${this.base(workspaceSlug)}/${pageId}/description/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error;
      });
  }

  /** A aba "Compartilhado comigo": páginas pessoais de outras pessoas. */
  async fetchSharedWithMe(workspaceSlug: string): Promise<TPage[]> {
    return this.get(`/api/workspaces/${workspaceSlug}/my-tasks/shared-pages/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async fetchShares(workspaceSlug: string, pageId: string): Promise<TPageShare[]> {
    return this.get(`${this.base(workspaceSlug)}/${pageId}/shares/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async createShare(
    workspaceSlug: string,
    pageId: string,
    data: { shared_with: string; role: number }
  ): Promise<TPageShare> {
    return this.post(`${this.base(workspaceSlug)}/${pageId}/shares/`, data)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async removeShare(workspaceSlug: string, pageId: string, shareId: string): Promise<void> {
    return this.delete(`${this.base(workspaceSlug)}/${pageId}/shares/${shareId}/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async duplicate(workspaceSlug: string, pageId: string): Promise<TPage> {
    return this.post(`${this.base(workspaceSlug)}/${pageId}/duplicate/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }
}
