/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: automações personalizadas (ADR 0012, F1).

import { API_BASE_URL } from "@plane/constants";
import type { TAutomation, TAutomationPayload, TAutomationRun, TAutomationSimulation } from "@plane/types";
import { APIService } from "@/services/api.service";

export class AutomationService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  private base(workspaceSlug: string, projectId: string) {
    return `/api/workspaces/${workspaceSlug}/projects/${projectId}/automations`;
  }

  async list(workspaceSlug: string, projectId: string): Promise<TAutomation[]> {
    return this.get(`${this.base(workspaceSlug, projectId)}/`)
      .then((res) => res?.data)
      .catch((err) => {
        throw err?.response?.data;
      });
  }

  async create(workspaceSlug: string, projectId: string, data: TAutomationPayload): Promise<TAutomation> {
    return this.post(`${this.base(workspaceSlug, projectId)}/`, data)
      .then((res) => res?.data)
      .catch((err) => {
        throw err?.response?.data;
      });
  }

  async update(
    workspaceSlug: string,
    projectId: string,
    automationId: string,
    data: TAutomationPayload
  ): Promise<TAutomation> {
    return this.patch(`${this.base(workspaceSlug, projectId)}/${automationId}/`, data)
      .then((res) => res?.data)
      .catch((err) => {
        throw err?.response?.data;
      });
  }

  async destroy(workspaceSlug: string, projectId: string, automationId: string): Promise<void> {
    return this.delete(`${this.base(workspaceSlug, projectId)}/${automationId}/`)
      .then((res) => res?.data)
      .catch((err) => {
        throw err?.response?.data;
      });
  }

  /** O registro de execuções — a resposta a "por que não rodou?". */
  async runs(workspaceSlug: string, projectId: string, automationId: string): Promise<TAutomationRun[]> {
    return this.get(`${this.base(workspaceSlug, projectId)}/${automationId}/runs/`)
      .then((res) => res?.data)
      .catch((err) => {
        throw err?.response?.data;
      });
  }

  /** Quantas tarefas casam com a condição AGORA. Não escreve nada. */
  async simulate(workspaceSlug: string, projectId: string, condition: unknown): Promise<TAutomationSimulation> {
    return this.post(`${this.base(workspaceSlug, projectId)}/simulate/`, { condition })
      .then((res) => res?.data)
      .catch((err) => {
        throw err?.response?.data;
      });
  }
}
