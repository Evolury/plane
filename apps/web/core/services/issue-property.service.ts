/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: propriedades personalizadas da tarefa (ADR 0011, P1).

import type {
  TIssueProperty,
  TIssuePropertyList,
  TIssuePropertyPayload,
  TIssuePropertiesForIssue,
  TPropertyValue,
} from "@plane/types";
import { API_BASE_URL } from "@plane/constants";
import { APIService } from "@/services/api.service";

export class IssuePropertyService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  private base(workspaceSlug: string, projectId: string) {
    return `/api/workspaces/${workspaceSlug}/projects/${projectId}/issue-properties`;
  }

  async list(workspaceSlug: string, projectId: string): Promise<TIssuePropertyList> {
    return this.get(`${this.base(workspaceSlug, projectId)}/`)
      .then((res) => res?.data)
      .catch((err) => {
        throw err?.response?.data;
      });
  }

  async create(workspaceSlug: string, projectId: string, data: TIssuePropertyPayload): Promise<TIssueProperty> {
    return this.post(`${this.base(workspaceSlug, projectId)}/`, data)
      .then((res) => res?.data)
      .catch((err) => {
        throw err?.response?.data;
      });
  }

  async update(
    workspaceSlug: string,
    projectId: string,
    propertyId: string,
    data: TIssuePropertyPayload
  ): Promise<TIssueProperty> {
    return this.patch(`${this.base(workspaceSlug, projectId)}/${propertyId}/`, data)
      .then((res) => res?.data)
      .catch((err) => {
        throw err?.response?.data;
      });
  }

  async destroy(workspaceSlug: string, projectId: string, propertyId: string): Promise<void> {
    return this.delete(`${this.base(workspaceSlug, projectId)}/${propertyId}/`)
      .then((res) => res?.data)
      .catch((err) => {
        throw err?.response?.data;
      });
  }

  async reorder(workspaceSlug: string, projectId: string, order: string[]): Promise<void> {
    return this.post(`${this.base(workspaceSlug, projectId)}/reorder/`, { order })
      .then((res) => res?.data)
      .catch((err) => {
        throw err?.response?.data;
      });
  }

  /** Quantas tarefas perdem o valor — o número que a confirmação mostra. */
  async optionUsage(
    workspaceSlug: string,
    projectId: string,
    propertyId: string,
    optionId: string
  ): Promise<{ work_items: number }> {
    return this.get(`${this.base(workspaceSlug, projectId)}/${propertyId}/options/${optionId}/usage/`)
      .then((res) => res?.data)
      .catch((err) => {
        throw err?.response?.data;
      });
  }

  /** As definições ativas e os valores da tarefa — numa ida só. */
  async valuesForIssue(workspaceSlug: string, projectId: string, issueId: string): Promise<TIssuePropertiesForIssue> {
    return this.get(`/api/workspaces/${workspaceSlug}/projects/${projectId}/issues/${issueId}/properties/`)
      .then((res) => res?.data)
      .catch((err) => {
        throw err?.response?.data;
      });
  }

  /** Grava (ou apaga, com vazio) o valor de uma propriedade na tarefa. */
  async setValue(
    workspaceSlug: string,
    projectId: string,
    issueId: string,
    propertyId: string,
    value: TPropertyValue
  ): Promise<void> {
    return this.post(`/api/workspaces/${workspaceSlug}/projects/${projectId}/issues/${issueId}/properties/`, {
      property: propertyId,
      value,
    })
      .then((res) => res?.data)
      .catch((err) => {
        throw err?.response?.data;
      });
  }

  /** Os valores de uma PÁGINA de tarefas — uma chamada, não uma por cartão. */
  async valuesForIssues(
    workspaceSlug: string,
    projectId: string,
    issueIds: string[]
  ): Promise<{ values: Record<string, Record<string, TPropertyValue>> }> {
    return this.get(
      `/api/workspaces/${workspaceSlug}/projects/${projectId}/issue-property-values/?issues=${issueIds.join(",")}`
    )
      .then((res) => res?.data)
      .catch((err) => {
        throw err?.response?.data;
      });
  }

  /** Só os valores das propriedades marcadas para o cartão — uma chamada por projeto. */
  async cardValues(
    workspaceSlug: string,
    projectId: string
  ): Promise<{ values: Record<string, Record<string, TPropertyValue>> }> {
    return this.get(`/api/workspaces/${workspaceSlug}/projects/${projectId}/issue-property-values/?card_only=1`)
      .then((res) => res?.data)
      .catch((err) => {
        throw err?.response?.data;
      });
  }
}
