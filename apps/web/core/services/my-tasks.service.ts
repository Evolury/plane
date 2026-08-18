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
import type { TIssuesResponse, TWorkStage, TWorkStageIssue, TBaldeDeVencimento } from "@plane/types";
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

  async markStageAsCompletion(workspaceSlug: string, stageId: string): Promise<void> {
    return this.post(`/api/workspaces/${workspaceSlug}/my-tasks/stages/${stageId}/mark-completion/`)
      .then((res) => res?.data)
      .catch((err) => {
        throw err?.response?.data;
      });
  }

  /**
   * Evolury: qual balde de vencimento esta etapa recebe (ADR 0014).
   *
   * Endpoint próprio, e não um PATCH, porque a constraint parcial exige soltar
   * a etapa anterior antes de marcar a nova — o PATCH estouraria com 500.
   *
   * `ativo: false` desliga e deixa o balde SEM destino, que é caso legítimo:
   * estas marcações são opcionais, ao contrário da etapa padrão.
   */
  async markStageBucket(
    workspaceSlug: string,
    stageId: string,
    balde: TBaldeDeVencimento,
    ativo: boolean
  ): Promise<void> {
    return this.post(`/api/workspaces/${workspaceSlug}/my-tasks/stages/${stageId}/mark-bucket/`, { balde, ativo })
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

  async getIssueStage(workspaceSlug: string, issueId: string): Promise<{ stage_id: string | null }> {
    return this.get(`/api/workspaces/${workspaceSlug}/my-tasks/issues/${issueId}/stage/`)
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
