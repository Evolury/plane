/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: página pessoal de "Minhas tarefas" (ADR 0015).
//
// Mesmo `BasePage` das páginas de projeto — muda só quem responde às chamadas e
// de onde vem a permissão. Não há projeto, então não há papel de projeto a
// consultar: a resposta é sempre "sou o dono?".

import { computed, makeObservable, observable } from "mobx";
import { computedFn } from "mobx-utils";
import type { TPage } from "@plane/types";
import { PAPEL_DA_PAGINA } from "@plane/types";
import { PersonalPageService } from "@/services/page";
import type { RootStore } from "@/store/root.store";
import { BasePage } from "./base-page";
import type { TPageInstance } from "./base-page";

const personalPageService = new PersonalPageService();

export type TPersonalPage = TPageInstance;

export class PersonalPage extends BasePage implements TPersonalPage {
  /**
   * Meu papel quando a página é de outra pessoa: 5 pode ler, 15 pode editar.
   * Nulo quando a página é minha. Vem do servidor — a tela não deduz.
   */
  share_role: number | null | undefined;

  constructor(store: RootStore, page: TPage) {
    const { workspaceSlug } = store.router;
    const exigir = () => {
      if (!workspaceSlug || !page.id) throw new Error("Missing required fields.");
      return { workspaceSlug, pageId: page.id };
    };

    super(store, page, {
      update: async (payload) => {
        const { workspaceSlug: slug, pageId } = exigir();
        return await personalPageService.update(slug, pageId, payload);
      },
      updateDescription: async (document) => {
        const { workspaceSlug: slug, pageId } = exigir();
        await personalPageService.updateDescription(slug, pageId, document);
      },
      updateAccess: async (payload) => {
        // Página pessoal não tem público/privado: ela é de quem a criou. O
        // campo continua existindo no modelo, então guardar é honesto — só não
        // há tela que mexa nele.
        const { workspaceSlug: slug, pageId } = exigir();
        await personalPageService.update(slug, pageId, payload);
      },
      lock: async () => {
        const { workspaceSlug: slug, pageId } = exigir();
        await personalPageService.lock(slug, pageId);
      },
      unlock: async () => {
        const { workspaceSlug: slug, pageId } = exigir();
        await personalPageService.unlock(slug, pageId);
      },
      archive: async () => {
        const { workspaceSlug: slug, pageId } = exigir();
        return await personalPageService.archive(slug, pageId);
      },
      restore: async () => {
        const { workspaceSlug: slug, pageId } = exigir();
        await personalPageService.restore(slug, pageId);
      },
      duplicate: async () => {
        const { workspaceSlug: slug, pageId } = exigir();
        return await personalPageService.duplicate(slug, pageId);
      },
    });

    this.share_role = page?.share_role ?? null;

    makeObservable(this, {
      share_role: observable.ref,
      canCurrentUserAccessPage: computed,
      canCurrentUserEditPage: computed,
      canCurrentUserDuplicatePage: computed,
      canCurrentUserLockPage: computed,
      canCurrentUserChangeAccess: computed,
      canCurrentUserArchivePage: computed,
      canCurrentUserDeletePage: computed,
      canCurrentUserFavoritePage: computed,
      canCurrentUserMovePage: computed,
      isContentEditable: computed,
    });
  }

  /** Meu papel quando a página é de outra pessoa; nulo quando é minha. */
  private get papel() {
    return this.share_role ?? null;
  }

  get canCurrentUserAccessPage() {
    return this.isCurrentUserOwner || this.papel !== null;
  }

  get canCurrentUserEditPage() {
    return this.isCurrentUserOwner || this.papel === PAPEL_DA_PAGINA.EDITAR;
  }

  get canCurrentUserDuplicatePage() {
    return this.isCurrentUserOwner;
  }

  get canCurrentUserLockPage() {
    return this.isCurrentUserOwner;
  }

  /** Não existe acesso a mudar: a página é pessoal e ponto. */
  get canCurrentUserChangeAccess() {
    return false;
  }

  get canCurrentUserArchivePage() {
    return this.isCurrentUserOwner;
  }

  get canCurrentUserDeletePage() {
    return this.isCurrentUserOwner;
  }

  get canCurrentUserFavoritePage() {
    return this.isCurrentUserOwner;
  }

  /** Mover entre pessoal e projeto é a F3. */
  get canCurrentUserMovePage() {
    return false;
  }

  get isContentEditable() {
    return this.canCurrentUserEditPage && !this.archived_at && !this.is_locked;
  }

  getRedirectionLink = computedFn(() => {
    const { workspaceSlug } = this.rootStore.router;
    return `/${workspaceSlug}/my-tasks/pages/${this.id}`;
  });
}
