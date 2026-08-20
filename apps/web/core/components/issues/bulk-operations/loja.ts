/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: a loja desta tela sabe operar em massa? (ADR 0018, ADR 0019)
//
// Nem toda loja de tarefas é uma `BaseIssuesStore`: a de rascunhos do espaço é
// uma implementação à parte, com `removeBulkIssues` vazio e sem paginação.
// Perguntar em tempo de execução é honesto; declarar na interface dela o que
// ela não faz seria escrever a mentira no tipo para o compilador se calar.

import type { IBaseIssuesStore } from "@/store/issue/helpers/base-issues.store";

export const sabeOperarEmMassa = (loja: unknown): loja is IBaseIssuesStore =>
  typeof (loja as IBaseIssuesStore)?.restoreBulkIssues === "function";
