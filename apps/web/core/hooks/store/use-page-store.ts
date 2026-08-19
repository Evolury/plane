/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useContext } from "react";
// context
import { StoreContext } from "@/lib/store-context";
// mobx store
import type { IPersonalPageStore } from "@/store/pages/personal-page.store";
import type { IProjectPageStore } from "@/store/pages/project-page.store";

export enum EPageStoreType {
  PROJECT = "PROJECT_PAGE",
  // Evolury: páginas pessoais de "Minhas tarefas" (ADR 0015).
  PERSONAL = "PERSONAL_PAGE",
}

export type TReturnType = {
  [EPageStoreType.PROJECT]: IProjectPageStore;
  [EPageStoreType.PERSONAL]: IPersonalPageStore;
};

export const usePageStore = <T extends EPageStoreType>(storeType: T): TReturnType[T] => {
  const context = useContext(StoreContext);
  if (context === undefined) throw new Error("usePageStore must be used within StoreProvider");

  // A conversão é o preço do mapa: `TReturnType[T]` com `T` genérico exige a
  // interseção dos dois stores, e cada ramo devolve só um deles. O `switch`
  // acima é a prova que o compilador não consegue fazer sozinho.
  if (storeType === EPageStoreType.PROJECT) {
    return context.projectPages as TReturnType[T];
  }

  if (storeType === EPageStoreType.PERSONAL) {
    return context.personalPages as TReturnType[T];
  }

  throw new Error(`Invalid store type: ${storeType}`);
};
