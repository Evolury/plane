/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: filtros de exibição de "Minhas tarefas" — espelho do
// ProfileIssuesFilter, chaveado por workspace e persistido em localStorage
// como o do perfil. O agrupamento é fixo em etapa pessoal ("my_task_stage",
// spec) e a ordenação padrão é manual ("sort_order", que nesta página é o
// sort pessoal da associação — ADR 0002).

import { isEmpty, set } from "lodash-es";
import { action, computed, makeObservable, observable, runInAction } from "mobx";
import { computedFn } from "mobx-utils";
import type { TSupportedFilterTypeForUpdate } from "@plane/constants";
import { EIssueFilterType } from "@plane/constants";
import type {
  IIssueDisplayFilterOptions,
  IIssueDisplayProperties,
  IIssueFilters,
  IssuePaginationOptions,
  TIssueKanbanFilters,
  TIssueParams,
  TSupportedFilterForUpdate,
  TWorkItemFilterExpression,
} from "@plane/types";
import { EIssuesStoreType } from "@plane/types";
import { handleIssueQueryParamsByLayout } from "@plane/utils";
import type { IBaseIssueFilterStore } from "../helpers/issue-filter-helper.store";
import { IssueFilterHelperStore } from "../helpers/issue-filter-helper.store";
import type { IIssueRootStore } from "../root.store";

const MY_TASKS_DEFAULT_DISPLAY_FILTERS: IIssueDisplayFilterOptions = {
  layout: "list",
  group_by: "my_task_stage",
  sub_group_by: null,
  order_by: "sort_order",
  show_empty_groups: true,
};

export interface IMyTasksIssuesFilter extends IBaseIssueFilterStore {
  // helper actions
  getFilterParams: (
    options: IssuePaginationOptions,
    cursor: string | undefined,
    groupId: string | undefined,
    subGroupId: string | undefined
  ) => Partial<Record<TIssueParams, string | boolean>>;
  // actions
  fetchFilters: (workspaceSlug: string) => Promise<void>;
  updateFilterExpression: (workspaceSlug: string, filters: TWorkItemFilterExpression) => Promise<void>;
  updateFilters: (
    workspaceSlug: string,
    projectId: string | undefined,
    filterType: TSupportedFilterTypeForUpdate,
    filters: TSupportedFilterForUpdate
  ) => Promise<void>;
}

export class MyTasksIssuesFilter extends IssueFilterHelperStore implements IMyTasksIssuesFilter {
  // observables
  filters: { [workspaceSlug: string]: IIssueFilters } = {};
  // root store
  rootIssueStore: IIssueRootStore;

  constructor(_rootStore: IIssueRootStore) {
    super();
    makeObservable(this, {
      filters: observable,
      issueFilters: computed,
      appliedFilters: computed,
      fetchFilters: action,
      updateFilters: action,
    });
    this.rootIssueStore = _rootStore;
  }

  get issueFilters() {
    const workspaceSlug = this.rootIssueStore.workspaceSlug;
    if (!workspaceSlug) return undefined;
    return this.getIssueFilters(workspaceSlug);
  }

  get appliedFilters() {
    const workspaceSlug = this.rootIssueStore.workspaceSlug;
    if (!workspaceSlug) return undefined;
    return this.getAppliedFilters(workspaceSlug);
  }

  getIssueFilters(workspaceSlug: string) {
    const displayFilters = this.filters[workspaceSlug] || undefined;
    if (isEmpty(displayFilters)) return undefined;
    return this.computedIssueFilters(displayFilters);
  }

  getAppliedFilters(workspaceSlug: string) {
    const userFilters = this.getIssueFilters(workspaceSlug);
    if (!userFilters) return undefined;

    const filteredParams = handleIssueQueryParamsByLayout(userFilters?.displayFilters?.layout, "my_tasks");
    if (!filteredParams) return undefined;

    return this.computedFilteredParams(
      userFilters?.richFilters,
      userFilters?.displayFilters,
      filteredParams
    ) as Partial<Record<TIssueParams, string | boolean>>;
  }

  getFilterParams = computedFn(
    (
      options: IssuePaginationOptions,
      cursor: string | undefined,
      groupId: string | undefined,
      subGroupId: string | undefined
    ) => {
      const workspaceSlug = this.rootIssueStore.workspaceSlug;
      const filterParams = workspaceSlug ? this.getAppliedFilters(workspaceSlug) : undefined;
      return this.getPaginationParams(filterParams, options, cursor, groupId, subGroupId);
    }
  );

  fetchFilters = async (workspaceSlug: string) => {
    const _filters = this.handleIssuesLocalFilters.get(
      EIssuesStoreType.MY_TASKS,
      workspaceSlug,
      this.rootIssueStore.currentUserId,
      undefined
    );

    const richFilters: TWorkItemFilterExpression = _filters?.rich_filters;
    // O agrupamento é a identidade da página: sempre etapa pessoal,
    // independentemente do que estiver persistido. Etapas vazias sempre
    // visíveis — sem isso não há para onde arrastar um item numa etapa nova
    // (achado da validação visual da F3; vira preferência na F5 se fizer
    // sentido).
    const displayFilters: IIssueDisplayFilterOptions = {
      ...this.computedDisplayFilters(_filters?.display_filters, MY_TASKS_DEFAULT_DISPLAY_FILTERS),
      group_by: "my_task_stage",
      sub_group_by: null,
      show_empty_groups: true,
    };
    const displayProperties: IIssueDisplayProperties = this.computedDisplayProperties(_filters?.display_properties);
    const kanbanFilters = {
      group_by: _filters?.kanban_filters?.group_by || [],
      sub_group_by: _filters?.kanban_filters?.sub_group_by || [],
    };

    runInAction(() => {
      set(this.filters, [workspaceSlug, "richFilters"], richFilters);
      set(this.filters, [workspaceSlug, "displayFilters"], displayFilters);
      set(this.filters, [workspaceSlug, "displayProperties"], displayProperties);
      set(this.filters, [workspaceSlug, "kanbanFilters"], kanbanFilters);
    });
  };

  updateFilterExpression: IMyTasksIssuesFilter["updateFilterExpression"] = async (workspaceSlug, filters) => {
    try {
      runInAction(() => {
        set(this.filters, [workspaceSlug, "richFilters"], filters);
      });

      this.rootIssueStore.myTasksIssues.fetchIssuesWithExistingPagination(workspaceSlug, "mutation");
      this.handleIssuesLocalFilters.set(
        EIssuesStoreType.MY_TASKS,
        EIssueFilterType.FILTERS,
        workspaceSlug,
        this.rootIssueStore.currentUserId,
        undefined,
        { rich_filters: filters }
      );
    } catch (error) {
      console.log("error while updating rich filters", error);
      throw error;
    }
  };

  updateFilters: IMyTasksIssuesFilter["updateFilters"] = async (workspaceSlug, _projectId, type, filters) => {
    try {
      if (isEmpty(this.filters) || isEmpty(this.filters[workspaceSlug])) return;

      const _filters = {
        richFilters: this.filters[workspaceSlug].richFilters,
        displayFilters: this.filters[workspaceSlug].displayFilters as IIssueDisplayFilterOptions,
        displayProperties: this.filters[workspaceSlug].displayProperties as IIssueDisplayProperties,
        kanbanFilters: this.filters[workspaceSlug].kanbanFilters as TIssueKanbanFilters,
      };

      switch (type) {
        case EIssueFilterType.DISPLAY_FILTERS: {
          const updatedDisplayFilters = filters as IIssueDisplayFilterOptions;
          _filters.displayFilters = { ..._filters.displayFilters, ...updatedDisplayFilters };

          // O agrupamento por etapa é fixo nesta página (spec), e etapas
          // vazias permanecem visíveis — são o destino do drag.
          _filters.displayFilters.group_by = "my_task_stage";
          _filters.displayFilters.sub_group_by = null;
          _filters.displayFilters.show_empty_groups = true;
          updatedDisplayFilters.group_by = "my_task_stage";
          updatedDisplayFilters.sub_group_by = null;
          updatedDisplayFilters.show_empty_groups = true;

          runInAction(() => {
            Object.keys(updatedDisplayFilters).forEach((_key) => {
              set(
                this.filters,
                [workspaceSlug, "displayFilters", _key],
                updatedDisplayFilters[_key as keyof IIssueDisplayFilterOptions]
              );
            });
          });

          this.rootIssueStore.myTasksIssues.fetchIssuesWithExistingPagination(workspaceSlug, "mutation");

          this.handleIssuesLocalFilters.set(
            EIssuesStoreType.MY_TASKS,
            type,
            workspaceSlug,
            this.rootIssueStore.currentUserId,
            undefined,
            { display_filters: _filters.displayFilters }
          );
          break;
        }
        case EIssueFilterType.DISPLAY_PROPERTIES: {
          const updatedDisplayProperties = filters as IIssueDisplayProperties;
          _filters.displayProperties = { ..._filters.displayProperties, ...updatedDisplayProperties };

          runInAction(() => {
            Object.keys(updatedDisplayProperties).forEach((_key) => {
              set(
                this.filters,
                [workspaceSlug, "displayProperties", _key],
                updatedDisplayProperties[_key as keyof IIssueDisplayProperties]
              );
            });
          });

          this.handleIssuesLocalFilters.set(
            EIssuesStoreType.MY_TASKS,
            type,
            workspaceSlug,
            this.rootIssueStore.currentUserId,
            undefined,
            { display_properties: _filters.displayProperties }
          );
          break;
        }
        case EIssueFilterType.KANBAN_FILTERS: {
          const updatedKanbanFilters = filters as TIssueKanbanFilters;
          _filters.kanbanFilters = { ..._filters.kanbanFilters, ...updatedKanbanFilters };

          this.handleIssuesLocalFilters.set(
            EIssuesStoreType.MY_TASKS,
            type,
            workspaceSlug,
            this.rootIssueStore.currentUserId,
            undefined,
            { kanban_filters: _filters.kanbanFilters }
          );

          runInAction(() => {
            Object.keys(updatedKanbanFilters).forEach((_key) => {
              set(
                this.filters,
                [workspaceSlug, "kanbanFilters", _key],
                updatedKanbanFilters[_key as keyof TIssueKanbanFilters]
              );
            });
          });
          break;
        }
        default:
          break;
      }
    } catch (error) {
      this.fetchFilters(workspaceSlug);
      throw error;
    }
  };
}
