/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: cliente da API de "Minhas tarefas".
// Contratos em docs/evolury/funcionalidades/minhas-tarefas/arquitetura.md.

// helpers
import { API_BASE_URL } from "@plane/constants";
import type { TIssuesResponse, TWorkStage, TWorkStageIssue } from "@plane/types";
// services
import { APIService } from "@/services/api.service";

export class MyTasksService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  async getStages(workspaceSlug: string): Promise<TWorkStage[]> {
    return this.get(`/api/workspaces/${workspaceSlug}/my-tasks/stages/`)
      .then((res) => res?.data)
      .catch((err) => {
        throw err?.response?.data;
      });
  }

  async createStage(workspaceSlug: string, payload: Partial<TWorkStage>): Promise<TWorkStage> {
    return this.post(`/api/workspaces/${workspaceSlug}/my-tasks/stages/`, payload)
      .then((res) => res?.data)
      .catch((err) => {
        throw err?.response?.data;
      });
  }

  async updateStage(workspaceSlug: string, stageId: string, payload: Partial<TWorkStage>): Promise<TWorkStage> {
    return this.patch(`/api/workspaces/${workspaceSlug}/my-tasks/stages/${stageId}/`, payload)
      .then((res) => res?.data)
      .catch((err) => {
        throw err?.response?.data;
      });
  }

  async deleteStage(workspaceSlug: string, stageId: string): Promise<void> {
    return this.delete(`/api/workspaces/${workspaceSlug}/my-tasks/stages/${stageId}/`)
      .then((res) => res?.data)
      .catch((err) => {
        throw err?.response?.data;
      });
  }

  async markStageAsDefault(workspaceSlug: string, stageId: string): Promise<void> {
    return this.post(`/api/workspaces/${workspaceSlug}/my-tasks/stages/${stageId}/mark-default/`)
      .then((res) => res?.data)
      .catch((err) => {
        throw err?.response?.data;
      });
  }

  async getIssues(workspaceSlug: string, params: object = {}, config = {}): Promise<TIssuesResponse> {
    return this.get(`/api/workspaces/${workspaceSlug}/my-tasks/issues/`, { params }, config)
      .then((res) => res?.data)
      .catch((err) => {
        throw err?.response?.data;
      });
  }

  async moveIssue(
    workspaceSlug: string,
    issueId: string,
    payload: { stage_id: string; sort_order?: number }
  ): Promise<TWorkStageIssue> {
    return this.post(`/api/workspaces/${workspaceSlug}/my-tasks/issues/${issueId}/move/`, payload)
      .then((res) => res?.data)
      .catch((err) => {
        throw err?.response?.data;
      });
  }
}
