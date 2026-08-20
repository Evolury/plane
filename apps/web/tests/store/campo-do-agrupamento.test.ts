/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: qual campo da tarefa corresponde ao agrupamento (ADR 0011).
//
// Para propriedade personalizada a chave É o nome do campo — o servidor anota
// `property_<uuid>` em cada tarefa da resposta agrupada. Sem isso, o mapa
// devolveria `undefined`, o destino do arrasto seria gravado numa chave vazia
// e o cartão não mudaria de coluna.

import { describe, expect, it, vi } from "vitest";
import type { TIssueGroupByOptions } from "@plane/types";

vi.mock("@/services/issue", () => ({ IssueService: vi.fn() }));
vi.mock("@/lib/store-context", () => ({ rootStore: {} }));

const { ISSUE_FILTER_DEFAULT_DATA, ISSUE_GROUP_BY_KEY, campoDoAgrupamento } =
  await import("@/store/issue/helpers/base-issues.store");

const CHAVE = "property_9f8c1d2e-0000-4000-8000-000000000001" as TIssueGroupByOptions;

describe("campo do agrupamento", () => {
  it("devolve a própria chave quando é propriedade", () => {
    expect(campoDoAgrupamento(CHAVE, ISSUE_GROUP_BY_KEY)).toBe(CHAVE);
    expect(campoDoAgrupamento(CHAVE, ISSUE_FILTER_DEFAULT_DATA)).toBe(CHAVE);
  });

  it("continua consultando o mapa para os agrupamentos nativos", () => {
    expect(campoDoAgrupamento("assignees", ISSUE_GROUP_BY_KEY)).toBe("assignee_ids");
    expect(campoDoAgrupamento("my_task_stage", ISSUE_FILTER_DEFAULT_DATA)).toBe("my_task_stage_id");
  });

  it("respeita a discordância proposital entre os dois mapas", () => {
    // Agrupar por grupo de estado LÊ `state_id` e ESCREVE `state__group`.
    // Um mapa só faria o arrasto gravar no campo errado.
    expect(campoDoAgrupamento("state_detail.group", ISSUE_GROUP_BY_KEY)).toBe("state_id");
    expect(campoDoAgrupamento("state_detail.group", ISSUE_FILTER_DEFAULT_DATA)).toBe("state__group");
  });

  it("não devolve campo nenhum sem agrupamento", () => {
    expect(campoDoAgrupamento(undefined, ISSUE_GROUP_BY_KEY)).toBeUndefined();
    expect(campoDoAgrupamento(null, ISSUE_GROUP_BY_KEY)).toBeUndefined();
  });
});
