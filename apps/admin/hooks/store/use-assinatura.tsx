/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useContext } from "react";
// store
import { StoreContext } from "@/providers/store-context";
import type { IAssinaturaStore } from "@/store/assinatura.store";

export const useAssinatura = (): IAssinaturaStore => {
  const context = useContext(StoreContext);
  if (context === undefined) throw new Error("useAssinatura must be used within StoreProvider");
  return context.assinatura;
};
