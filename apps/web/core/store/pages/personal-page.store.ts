/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: store das páginas pessoais de "Minhas tarefas" (ADR 0015).
//
// Espelha o store das páginas de projeto — os componentes de lista consomem os
// dois pela mesma interface, via `usePageStore(storeType)`. A diferença é que
// aqui não há projeto para filtrar: tudo o que o servidor devolve é meu.

import { set, unset } from "lodash-es";
import { action, computed, makeObservable, observable, runInAction } from "mobx";
import { computedFn } from "mobx-utils";
import { translate } from "@plane/i18n";
import type { TPage, TPageFilters, TPageNavigationTabs } from "@plane/types";
import { getPageName, orderPages, shouldFilterPage } from "@plane/utils";
import { PersonalPageService } from "@/services/page";
import type { CoreRootStore } from "../root.store";
import type { TPersonalPage } from "./personal-page";
import { PersonalPage } from "./personal-page";

type TLoader = "init-loader" | "mutation-loader" | undefined;

type TError = { title: string; description: string };

export interface IPersonalPageStore {
  loader: TLoader;
  data: Record<string, TPersonalPage>;
  error: TError | undefined;
  filters: TPageFilters;
  isAnyPageAvailable: boolean;
  canCurrentUserCreatePage: boolean;
  getCurrentProjectPageIdsByTab: (pageType: TPageNavigationTabs) => string[] | undefined;
  getCurrentProjectFilteredPageIdsByTab: (pageType: TPageNavigationTabs) => string[] | undefined;
  getPageById: (pageId: string) => TPersonalPage | undefined;
  updateFilters: <T extends keyof TPageFilters>(filterKey: T, filterValue: TPageFilters[T]) => void;
  clearAllFilters: () => void;
  fetchPagesList: (workspaceSlug: string) => Promise<TPage[] | undefined>;
  fetchSharedPages: (workspaceSlug: string) => Promise<TPage[] | undefined>;
  fetchPageDetails: (
    workspaceSlug: string,
    pageId: string,
    options?: { trackVisit?: boolean }
  ) => Promise<TPage | undefined>;
  createPage: (pageData: Partial<TPage>) => Promise<TPage | undefined>;
  removePage: (params: { pageId: string; shouldSync?: boolean }) => Promise<void>;
}

export class PersonalPageStore implements IPersonalPageStore {
  loader: TLoader = "init-loader";
  data: Record<string, TPersonalPage> = {};
  error: TError | undefined = undefined;
  filters: TPageFilters = {
    searchQuery: "",
    sortKey: "updated_at",
    sortBy: "desc",
  };
  service: PersonalPageService;
  rootStore: CoreRootStore;

  constructor(private store: CoreRootStore) {
    makeObservable(this, {
      loader: observable.ref,
      data: observable,
      error: observable,
      filters: observable,
      isAnyPageAvailable: computed,
      canCurrentUserCreatePage: computed,
      updateFilters: action,
      clearAllFilters: action,
      fetchPagesList: action,
      fetchSharedPages: action,
      fetchPageDetails: action,
      createPage: action,
      removePage: action,
    });
    this.rootStore = store;
    this.service = new PersonalPageService();
  }

  get isAnyPageAvailable() {
    if (this.loader) return true;
    return Object.keys(this.data).length > 0;
  }

  /** Quem tem "Minhas tarefas" tem caderno próprio — não há papel a consultar. */
  get canCurrentUserCreatePage() {
    return true;
  }

  /**
   * Página pessoal não tem público/privado: ela é de quem a criou. As divisões
   * são outras — minhas x compartilhadas comigo, ativas x arquivadas. Por isso
   * não dá para usar o `filterPagesByPageType` compartilhado, que decide pelo
   * campo `access`.
   */
  private porAba = (pageType: TPageNavigationTabs) => {
    const euId = this.store.user.data?.id;
    const todas = Object.values(this.data || {});
    if (pageType === "shared") return todas.filter((p) => p.owned_by !== euId && !p.archived_at);
    const minhas = todas.filter((p) => p.owned_by === euId);
    return minhas.filter((p) => (pageType === "archived" ? !!p.archived_at : !p.archived_at));
  };

  getCurrentProjectPageIdsByTab = computedFn((pageType: TPageNavigationTabs) =>
    this.porAba(pageType).map((page) => page.id as string)
  );

  getCurrentProjectFilteredPageIdsByTab = computedFn((pageType: TPageNavigationTabs) => {
    const doTipo = this.porAba(pageType);
    const filtradas = doTipo.filter(
      (p) =>
        getPageName(p.name).toLowerCase().includes(this.filters.searchQuery.toLowerCase()) &&
        shouldFilterPage(p, this.filters.filters)
    );
    return orderPages(filtradas, this.filters.sortKey, this.filters.sortBy).map((page) => page.id as string);
  });

  getPageById = computedFn((pageId: string) => this.data?.[pageId] || undefined);

  updateFilters = <T extends keyof TPageFilters>(filterKey: T, filterValue: TPageFilters[T]) => {
    runInAction(() => {
      set(this.filters, [filterKey], filterValue);
    });
  };

  clearAllFilters = () =>
    runInAction(() => {
      set(this.filters, ["filters"], {});
    });

  private guardar = (page: TPage) => {
    if (!page?.id) return;
    const existente = this.getPageById(page.id);
    if (existente) {
      const { name: _name, ...resto } = page;
      existente.mutateProperties(resto, false);
    } else {
      set(this.data, [page.id], new PersonalPage(this.store, page));
    }
  };

  fetchPagesList = async (workspaceSlug: string) => {
    try {
      if (!workspaceSlug) return undefined;

      runInAction(() => {
        this.loader = Object.keys(this.data).length > 0 ? "mutation-loader" : "init-loader";
        this.error = undefined;
      });

      const pages = await this.service.fetchAll(workspaceSlug);
      runInAction(() => {
        for (const page of pages) this.guardar(page);
        this.loader = undefined;
      });

      return pages;
    } catch (error) {
      runInAction(() => {
        this.loader = undefined;
        this.error = {
          title: translate("toast.failed"),
          description: translate("toast.pages_fetch_failed"),
        };
      });
      throw error;
    }
  };

  /** A aba "Compartilhado comigo" — páginas pessoais de outras pessoas. */
  fetchSharedPages = async (workspaceSlug: string) => {
    try {
      if (!workspaceSlug) return undefined;

      runInAction(() => {
        this.loader = Object.keys(this.data).length > 0 ? "mutation-loader" : "init-loader";
        this.error = undefined;
      });

      const pages = await this.service.fetchSharedWithMe(workspaceSlug);
      runInAction(() => {
        for (const page of pages) this.guardar(page);
        this.loader = undefined;
      });

      return pages;
    } catch (error) {
      runInAction(() => {
        this.loader = undefined;
        this.error = {
          title: translate("toast.failed"),
          description: translate("toast.pages_fetch_failed"),
        };
      });
      throw error;
    }
  };

  fetchPageDetails = async (workspaceSlug: string, pageId: string, options?: { trackVisit?: boolean }) => {
    try {
      if (!workspaceSlug || !pageId) return undefined;

      runInAction(() => {
        this.loader = this.getPageById(pageId) ? "mutation-loader" : "init-loader";
        this.error = undefined;
      });

      const page = await this.service.fetchById(workspaceSlug, pageId, options?.trackVisit ?? true);
      runInAction(() => {
        if (page?.id) {
          const instancia = this.getPageById(page.id);
          if (instancia) instancia.mutateProperties(page, false);
          else set(this.data, [page.id], new PersonalPage(this.store, page));
        }
        this.loader = undefined;
      });

      return page;
    } catch (error) {
      runInAction(() => {
        this.loader = undefined;
        this.error = {
          title: translate("toast.failed"),
          description: translate("toast.page_fetch_failed"),
        };
      });
      throw error;
    }
  };

  createPage = async (pageData: Partial<TPage>) => {
    try {
      const { workspaceSlug } = this.store.router;
      if (!workspaceSlug) return undefined;

      runInAction(() => {
        this.loader = "mutation-loader";
        this.error = undefined;
      });

      const page = await this.service.create(workspaceSlug, pageData);
      runInAction(() => {
        if (page?.id) set(this.data, [page.id], new PersonalPage(this.store, page));
        this.loader = undefined;
      });

      return page;
    } catch (error) {
      runInAction(() => {
        this.loader = undefined;
        this.error = {
          title: translate("toast.failed"),
          description: translate("toast.page_create_failed"),
        };
      });
      throw error;
    }
  };

  removePage = async ({ pageId }: { pageId: string; shouldSync?: boolean }) => {
    try {
      const { workspaceSlug } = this.store.router;
      if (!workspaceSlug || !pageId) return undefined;

      await this.service.remove(workspaceSlug, pageId);
      runInAction(() => {
        unset(this.data, [pageId]);
        if (this.rootStore.favorite.entityMap[pageId]) this.rootStore.favorite.removeFavoriteFromStore(pageId);
      });
    } catch (error) {
      runInAction(() => {
        this.loader = undefined;
        this.error = {
          title: translate("toast.failed"),
          description: translate("toast.page_delete_failed_alt"),
        };
      });
      throw error;
    }
  };
}
