/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: acesso ao store de "Minhas tarefas".

import { useContext } from "react";
// context
import { StoreContext } from "@/lib/store-context";
import type { IMyTasksStore } from "@/store/my-tasks/my-tasks.store";

export const useMyTasks = (): IMyTasksStore => {
  const context = useContext(StoreContext);
  if (context === undefined) throw new Error("useMyTasks must be used within StoreProvider");
  return context.myTasksStore;
};
