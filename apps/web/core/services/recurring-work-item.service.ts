/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: serviço das tarefas recorrentes (ADR 0010).

import { API_BASE_URL } from "@plane/constants";
import type { TRecurringWorkItem } from "@plane/types";
import { APIService } from "@/services/api.service";

export class RecurringWorkItemService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  private base(workspaceSlug: string, projectId: string) {
    return `/api/workspaces/${workspaceSlug}/projects/${projectId}/recurring-work-items`;
  }

  async list(workspaceSlug: string, projectId: string): Promise<TRecurringWorkItem[]> {
    return this.get(`${this.base(workspaceSlug, projectId)}/`)
      .then((res) => res?.data)
      .catch((err) => {
        throw err?.response?.data;
      });
  }

  async create(
    workspaceSlug: string,
    projectId: string,
    data: Partial<TRecurringWorkItem>
  ): Promise<TRecurringWorkItem> {
    return this.post(`${this.base(workspaceSlug, projectId)}/`, data)
      .then((res) => res?.data)
      .catch((err) => {
        throw err?.response?.data;
      });
  }

  async update(
    workspaceSlug: string,
    projectId: string,
    id: string,
    data: Partial<TRecurringWorkItem>
  ): Promise<TRecurringWorkItem> {
    return this.patch(`${this.base(workspaceSlug, projectId)}/${id}/`, data)
      .then((res) => res?.data)
      .catch((err) => {
        throw err?.response?.data;
      });
  }

  async destroy(workspaceSlug: string, projectId: string, id: string): Promise<void> {
    return this.delete(`${this.base(workspaceSlug, projectId)}/${id}/`)
      .then((res) => res?.data)
      .catch((err) => {
        throw err?.response?.data;
      });
  }

  /** Próximas datas de uma agenda que ainda não foi salva. */
  async preview(
    workspaceSlug: string,
    projectId: string,
    data: Partial<TRecurringWorkItem>
  ): Promise<{ next_occurrences: string[] }> {
    return this.post(`${this.base(workspaceSlug, projectId)}/preview/`, data)
      .then((res) => res?.data)
      .catch((err) => {
        throw err?.response?.data;
      });
  }
}
