/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useContext } from "react";
// store
import { StoreContext } from "@/lib/store-context";
import type { IFaturamentoStore } from "@/store/faturamento.store";

export const useFaturamento = (): IFaturamentoStore => {
  const context = useContext(StoreContext);
  if (context === undefined) throw new Error("useFaturamento must be used within StoreProvider");
  return context.faturamento;
};
