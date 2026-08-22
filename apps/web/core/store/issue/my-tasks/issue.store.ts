/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: store de work items de "Minhas tarefas" — espelho do ProfileIssues
// sobre o BaseIssuesStore, com o roteamento do ADR 0002: payloads que só
// mexem na organização pessoal (etapa e/ou ordenação) vão para o
// POST .../move/ em vez do PATCH do issue, preservando o silêncio do ADR 0001
// (sem atividade, webhook ou notificação; o item real não muda).

import { clone } from "lodash-es";
import { action, makeObservable, runInAction } from "mobx";
import type {
  IssuePaginationOptions,
  TBulkOperationsPayload,
  TIssue,
  TIssuesResponse,
  TLoader,
  ViewFlags,
} from "@plane/types";
import { MyTasksService } from "@/services/my-tasks.service";
import type { IBaseIssuesStore } from "../helpers/base-issues.store";
import { BaseIssuesStore } from "../helpers/base-issues.store";
import type { IIssueRootStore } from "../root.store";
import type { IMyTasksIssuesFilter } from "./filter.store";

export interface IMyTasksIssues extends IBaseIssuesStore {
  viewFlags: ViewFlags;
  fetchIssues: (
    workspaceSlug: string,
    loadType: TLoader,
    options: IssuePaginationOptions,
    isExistingPaginationOptions?: boolean
  ) => Promise<TIssuesResponse | undefined>;
  fetchIssuesWithExistingPagination: (workspaceSlug: string, loadType: TLoader) => Promise<TIssuesResponse | undefined>;
  fetchNextIssues: (
    workspaceSlug: string,
    groupId?: string,
    subGroupId?: string
  ) => Promise<TIssuesResponse | undefined>;
  updateIssue: (workspaceSlug: string, projectId: string, issueId: string, data: Partial<TIssue>) => Promise<void>;
  archiveIssue: (workspaceSlug: string, projectId: string, issueId: string) => Promise<void>;
  archiveBulkIssues: (workspaceSlug: string, projectId: string, issueIds: string[]) => Promise<void>;
  bulkUpdateProperties: (workspaceSlug: string, projectId: string, data: TBulkOperationsPayload) => Promise<void>;
  reposicionarPeloCiclo: (
    workspaceSlug: string,
    projectId: string,
    issueId: string,
    data: Partial<TIssue>,
    previousStateId: string | null | undefined
  ) => void;
  quickAddIssue: undefined;
}

export class MyTasksIssues extends BaseIssuesStore implements IMyTasksIssues {
  // filter store
  issueFilterStore: IMyTasksIssuesFilter;
  // services
  myTasksService: MyTasksService;

  constructor(_rootStore: IIssueRootStore, issueFilterStore: IMyTasksIssuesFilter) {
    super(_rootStore, issueFilterStore);
    makeObservable(this, {
      fetchIssues: action,
      fetchNextIssues: action,
      fetchIssuesWithExistingPagination: action,
    });
    this.issueFilterStore = issueFilterStore;
    this.myTasksService = new MyTasksService();
  }

  get viewFlags() {
    return {
      enableQuickAdd: false,
      enableIssueCreation: false,
      enableInlineEditing: true,
    };
  }

  fetchParentStats = () => {};
  updateParentStats = () => {};

  fetchIssues: IMyTasksIssues["fetchIssues"] = async (
    workspaceSlug,
    loadType,
    options,
    isExistingPaginationOptions = false
  ) => {
    try {
      runInAction(() => {
        this.setLoader(loadType);
      });
      this.clear(!isExistingPaginationOptions, !isExistingPaginationOptions);

      const params = this.issueFilterStore?.getFilterParams(options, undefined, undefined, undefined);
      const response = await this.myTasksService.getIssues(workspaceSlug, params, {
        signal: this.controller.signal,
      });

      this.onfetchIssues(response, options, workspaceSlug, undefined, undefined, !isExistingPaginationOptions);
      return response;
    } catch (error) {
      this.setLoader(undefined);
      throw error;
    }
  };

  fetchNextIssues = async (workspaceSlug: string, groupId?: string, subGroupId?: string) => {
    const cursorObject = this.getPaginationData(groupId, subGroupId);
    if (!this.paginationOptions || (cursorObject && !cursorObject?.nextPageResults)) return;
    try {
      this.setLoader("pagination", groupId, subGroupId);

      const params = this.issueFilterStore?.getFilterParams(
        this.paginationOptions,
        this.getNextCursor(groupId, subGroupId),
        groupId,
        subGroupId
      );
      const response = await this.myTasksService.getIssues(workspaceSlug, params);

      this.onfetchNexIssues(response, groupId, subGroupId);
      return response;
    } catch (error) {
      this.setLoader(undefined, groupId, subGroupId);
      throw error;
    }
  };

  fetchIssuesWithExistingPagination = async (workspaceSlug: string, loadType: TLoader) => {
    if (!this.paginationOptions) return;
    return await this.fetchIssues(workspaceSlug, loadType, this.paginationOptions, true);
  };

  /**
   * Roteamento do ADR 0002: mudança de etapa (my_task_stage_id) e/ou
   * reordenação pessoal (sort_order sozinho — nesta página o sort_order do
   * payload É o pessoal, sobrescrito pelo servidor) vão para o move/ da API
   * de minhas tarefas, com atualização local otimista e reversão em falha.
   * Qualquer outra edição segue o fluxo normal (PATCH do issue, com
   * atividade) — a exceção de silêncio vale só para organização pessoal.
   */
  updateIssue = async (workspaceSlug: string, projectId: string, issueId: string, data: Partial<TIssue>) => {
    const mutatedKeys = Object.keys(data).filter((key) => !["id", "project_id"].includes(key));
    const isStageMove = "my_task_stage_id" in data;
    const isPersonalReorder = !isStageMove && mutatedKeys.length === 1 && mutatedKeys[0] === "sort_order";

    if (!isStageMove && !isPersonalReorder) {
      // O estado anterior precisa ser lido ANTES da atualização: o issueUpdate
      // já grava o novo no mapa compartilhado, e comparar depois diria sempre
      // que nada mudou.
      const estadoAnterior = this.rootIssueStore.issues.getIssueById(issueId)?.state_id;
      const resultado = await this.issueUpdate(workspaceSlug, projectId, issueId, data);
      this.reposicionarPeloCiclo(workspaceSlug, projectId, issueId, data, estadoAnterior);
      return resultado;
    }

    const issueBeforeUpdate = clone(this.rootIssueStore.issues.getIssueById(issueId));
    const targetStageId = (data.my_task_stage_id ?? issueBeforeUpdate?.my_task_stage_id) as string | undefined;
    if (!targetStageId) return;

    // Local otimista + reagrupamento, sem PATCH (shouldSync=false)
    await this.issueUpdate(workspaceSlug, projectId, issueId, data, false);
    try {
      await this.myTasksService.moveIssue(workspaceSlug, issueId, {
        stage_id: targetStageId,
        ...(data.sort_order !== undefined ? { sort_order: data.sort_order } : {}),
      });
    } catch (error) {
      // Reversão manual do estado local
      if (issueBeforeUpdate) {
        const revertPayload: Partial<TIssue> = {};
        for (const key of mutatedKeys) {
          (revertPayload as Record<string, unknown>)[key] = (issueBeforeUpdate as Record<string, unknown>)[key];
        }
        if (isStageMove) revertPayload.my_task_stage_id = issueBeforeUpdate.my_task_stage_id;
        await this.issueUpdate(workspaceSlug, projectId, issueId, revertPayload, false);
      }
      throw error;
    }
  };

  /**
   * Evolury: o cartão acompanha o ciclo da tarefa na hora (ADR 0009).
   *
   * O reposicionamento de verdade é do servidor, no mesmo funil que trata todos
   * os caminhos de mudança de estado — mas ele roda em segundo plano, e sem
   * isto o cartão ficaria na etapa antiga até a próxima busca. Espelha a regra
   * do backend: concluir vai para a etapa de conclusão, cancelar para a de
   * canceladas, e sair de um grupo encerrado devolve à padrão.
   *
   * Só estado local (shouldSync=false): nenhuma requisição sai daqui.
   */
  reposicionarPeloCiclo = (
    workspaceSlug: string,
    projectId: string,
    issueId: string,
    data: Partial<TIssue>,
    previousStateId: string | null | undefined
  ) => {
    if (!("state_id" in data) || !data.state_id) return;
    const rootStore = this.rootIssueStore.rootStore;
    const issue = this.rootIssueStore.issues.getIssueById(issueId);
    const grupoNovo = rootStore.state.getStateById(data.state_id)?.group;
    const grupoAnterior = rootStore.state.getStateById(previousStateId ?? undefined)?.group;
    if (!grupoNovo || grupoNovo === grupoAnterior) return;

    const encerrados = new Set(["completed", "cancelled"]);
    if (!encerrados.has(grupoNovo) && !encerrados.has(grupoAnterior ?? "")) return;

    const etapas = rootStore.myTasksStore.sortedStages;
    // O botão de reabrir devolve a tarefa ao estado PADRÃO do projeto, e ali
    // "de volta ao começo" é a resposta certa. Quem escolhe "Em andamento" no
    // campo de estado está dizendo onde a tarefa está — a etapa segue a
    // escolha, não o começo da fila.
    const estadoEhOPadrao = !!rootStore.state.getStateById(data.state_id)?.default;
    const destino =
      grupoNovo === "completed"
        ? (etapas.find((etapa) => etapa.group === "completed" && etapa.is_completion) ??
          etapas.find((etapa) => etapa.group === "completed"))
        : grupoNovo === "cancelled"
          ? etapas.find((etapa) => etapa.group === "cancelled")
          : estadoEhOPadrao
            ? etapas.find((etapa) => etapa.is_default)
            : (etapas.find((etapa) => etapa.group === grupoNovo) ?? etapas.find((etapa) => etapa.is_default));
    if (!destino) return;

    // Quem já está numa etapa do grupo de destino escolheu ficar lá.
    const etapaAtual = etapas.find((etapa) => etapa.id === issue?.my_task_stage_id);
    if (etapaAtual?.group === grupoNovo) return;

    this.issueUpdate(workspaceSlug, projectId, issueId, { my_task_stage_id: destino.id }, false);
  };

  // Aliases como no ProfileIssues — não podem ser sobrescritos com outro nome
  archiveBulkIssues = this.bulkArchiveIssues;
  archiveIssue = this.issueArchive;

  // Criação não acontece nesta página no v1 (spec)
  quickAddIssue = undefined;
}
