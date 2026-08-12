/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: store de "Minhas tarefas" — etapas pessoais e a listagem básica
// dos itens atribuídos (F2). A integração completa com os layouts base
// (BaseKanBanRoot/BaseListRoot, drag-drop) chega na F3, conforme o ADR 0002.

import { action, computed, makeObservable, observable, runInAction } from "mobx";
// plane imports
import { MY_TASKS_STAGE_GROUP_ORDER } from "@plane/constants";
import type { TWorkStage } from "@plane/types";
// services
import { MyTasksService } from "@/services/my-tasks.service";

/** Payload de item da listagem — os campos serializados pelo endpoint,
 * incluindo a anotação my_task_stage_id (null nunca ocorre com seed feito). */
export type TMyTasksIssue = {
  id: string;
  name: string;
  sequence_id: number;
  project_id: string;
  priority: string | null;
  state_id: string | null;
  state__group: string | null;
  target_date: string | null;
  created_at: string;
  my_task_stage_id: string | null;
  assignee_ids: string[];
  label_ids: string[];
};

export interface IMyTasksStore {
  // observables
  stagesLoader: boolean;
  issuesLoader: boolean;
  stageMap: Record<string, TWorkStage>;
  issueMap: Record<string, TMyTasksIssue>;
  // computed
  sortedStages: TWorkStage[];
  defaultStage: TWorkStage | undefined;
  groupedIssueIds: Record<string, string[]>;
  // actions
  fetchStages: (workspaceSlug: string) => Promise<void>;
  fetchIssues: (workspaceSlug: string) => Promise<void>;
  moveIssue: (workspaceSlug: string, issueId: string, stageId: string, sortOrder?: number) => Promise<void>;
  createStage: (workspaceSlug: string, data: Partial<TWorkStage>) => Promise<TWorkStage>;
  updateStage: (workspaceSlug: string, stageId: string, data: Partial<TWorkStage>) => Promise<TWorkStage>;
  deleteStage: (workspaceSlug: string, stageId: string) => Promise<void>;
  markStageAsDefault: (workspaceSlug: string, stageId: string) => Promise<void>;
}

export class MyTasksStore implements IMyTasksStore {
  stagesLoader = false;
  issuesLoader = false;
  stageMap: Record<string, TWorkStage> = {};
  issueMap: Record<string, TMyTasksIssue> = {};
  // services
  myTasksService: MyTasksService;

  constructor() {
    makeObservable(this, {
      stagesLoader: observable.ref,
      issuesLoader: observable.ref,
      stageMap: observable,
      issueMap: observable,
      sortedStages: computed,
      defaultStage: computed,
      groupedIssueIds: computed,
      fetchStages: action,
      fetchIssues: action,
      moveIssue: action,
      createStage: action,
      updateStage: action,
      deleteStage: action,
      markStageAsDefault: action,
    });
    this.myTasksService = new MyTasksService();
  }

  get sortedStages() {
    // Ordem por grupo (MY_TASKS_STAGE_GROUP_ORDER) e, dentro do grupo, pelo
    // sort_order — a mesma ordenação do painel de etapas. O painel reordena
    // por arrasto calculando a posição entre as irmãs do MESMO grupo, então
    // uma ordenação achatada divergiria dele (causa do bug de 12/08: etapa
    // arrastada ao topo do backlog ganhou sort negativo e aparecia antes de
    // tudo no quadro).
    return Object.values(this.stageMap).sort((a, b) => {
      const groupDiff = MY_TASKS_STAGE_GROUP_ORDER.indexOf(a.group) - MY_TASKS_STAGE_GROUP_ORDER.indexOf(b.group);
      if (groupDiff !== 0) return groupDiff;
      return a.sort_order - b.sort_order;
    });
  }

  get defaultStage() {
    return Object.values(this.stageMap).find((stage) => stage.is_default);
  }

  /** Ids de itens por etapa, na ordem pessoal; itens sem associação caem na
   * etapa padrão — o servidor já resolve isso na anotação. */
  get groupedIssueIds() {
    const grouped: Record<string, string[]> = {};
    for (const stage of this.sortedStages) grouped[stage.id] = [];
    for (const issue of Object.values(this.issueMap)) {
      const stageId = issue.my_task_stage_id ?? this.defaultStage?.id;
      if (!stageId) continue;
      if (!grouped[stageId]) grouped[stageId] = [];
      grouped[stageId].push(issue.id);
    }
    return grouped;
  }

  fetchStages = async (workspaceSlug: string) => {
    this.stagesLoader = true;
    try {
      const stages = await this.myTasksService.getStages(workspaceSlug);
      runInAction(() => {
        this.stageMap = Object.fromEntries(stages.map((stage) => [stage.id, stage]));
        this.stagesLoader = false;
      });
    } catch (error) {
      runInAction(() => {
        this.stagesLoader = false;
      });
      throw error;
    }
  };

  fetchIssues = async (workspaceSlug: string) => {
    this.issuesLoader = true;
    try {
      const response = await this.myTasksService.getIssues(workspaceSlug, {
        order_by: "-created_at",
      });
      const results = (response?.results ?? []) as unknown as TMyTasksIssue[];
      runInAction(() => {
        this.issueMap = Object.fromEntries(results.map((issue) => [issue.id, issue]));
        this.issuesLoader = false;
      });
    } catch (error) {
      runInAction(() => {
        this.issuesLoader = false;
      });
      throw error;
    }
  };

  // CRUD de etapas (painel de gestão, F4). Cada operação ressincroniza o
  // stageMap pelo fetch — contexto de gestão, 1 request extra é irrelevante e
  // evita divergência com constraints do servidor (nome único, padrão única).
  createStage = async (workspaceSlug: string, data: Partial<TWorkStage>) => {
    const stage = await this.myTasksService.createStage(workspaceSlug, data);
    await this.fetchStages(workspaceSlug);
    return stage;
  };

  updateStage = async (workspaceSlug: string, stageId: string, data: Partial<TWorkStage>) => {
    const stage = await this.myTasksService.updateStage(workspaceSlug, stageId, data);
    await this.fetchStages(workspaceSlug);
    return stage;
  };

  deleteStage = async (workspaceSlug: string, stageId: string) => {
    await this.myTasksService.deleteStage(workspaceSlug, stageId);
    await this.fetchStages(workspaceSlug);
  };

  markStageAsDefault = async (workspaceSlug: string, stageId: string) => {
    await this.myTasksService.markStageAsDefault(workspaceSlug, stageId);
    await this.fetchStages(workspaceSlug);
  };

  moveIssue = async (workspaceSlug: string, issueId: string, stageId: string, sortOrder?: number) => {
    const issueBeforeMove = this.issueMap[issueId];
    if (!issueBeforeMove) return;
    const previousStageId = issueBeforeMove.my_task_stage_id;
    // Atualização otimista com reversão em falha
    runInAction(() => {
      this.issueMap[issueId] = { ...issueBeforeMove, my_task_stage_id: stageId };
    });
    try {
      await this.myTasksService.moveIssue(workspaceSlug, issueId, {
        stage_id: stageId,
        ...(sortOrder !== undefined ? { sort_order: sortOrder } : {}),
      });
    } catch (error) {
      runInAction(() => {
        this.issueMap[issueId] = { ...issueBeforeMove, my_task_stage_id: previousStageId };
      });
      throw error;
    }
  };
}
