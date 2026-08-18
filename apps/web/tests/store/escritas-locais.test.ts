/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: o registro de escritas desta aba (ADR 0013, fase 2).
//
// É o que distingue "fui eu nesta aba" de "fui eu na outra aba". A fase 1
// comparava só o ator do aviso com o usuário da sessão, e por isso duas abas da
// mesma pessoa não se enxergavam.
//
// As três regras que importam, e nenhuma delas se vê na tela: a anotação **vale
// uma vez**, **vence**, e **não existe** para tarefa que esta aba não escreveu.

import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/services/issue", () => ({ IssueService: class {} }));
vi.mock("@/lib/store-context", () => ({ rootStore: {} }));

const { IssueStore } = await import("@/store/issue/issue.store");

describe("escritas locais", () => {
  let store: InstanceType<typeof IssueStore>;

  beforeEach(() => {
    vi.useRealTimers();
    store = new IssueStore();
  });

  it("não conhece tarefa que esta aba não escreveu", () => {
    expect(store.consumirEscritaLocal("nunca-escrita")).toBe(false);
  });

  it("reconhece a tarefa que esta aba escreveu", () => {
    store.registrarEscritaLocal("t1");

    expect(store.consumirEscritaLocal("t1")).toBe(true);
  });

  it("vale UMA vez", () => {
    // É isto que faz a mesma pessoa editando a mesma tarefa em duas abas
    // continuar funcionando: o primeiro aviso é o eco desta aba e some; um
    // segundo só pode ter vindo de outro lugar, e passa.
    store.registrarEscritaLocal("t1");

    expect(store.consumirEscritaLocal("t1")).toBe(true);
    expect(store.consumirEscritaLocal("t1")).toBe(false);
  });

  it("uma tarefa não responde pela outra", () => {
    store.registrarEscritaLocal("t1");

    expect(store.consumirEscritaLocal("t2")).toBe(false);
    expect(store.consumirEscritaLocal("t1")).toBe(true);
  });

  it("anotação vencida não explica o aviso", () => {
    // Sem validade, uma escrita que nunca recebeu eco — porque a conexão caiu,
    // por exemplo — engoliria para sempre o próximo aviso daquela tarefa.
    vi.useFakeTimers();
    store.registrarEscritaLocal("t1");
    vi.advanceTimersByTime(15_001);

    expect(store.consumirEscritaLocal("t1")).toBe(false);
  });

  it("dentro da validade continua explicando", () => {
    // Sem isto, encurtar a validade a zero passaria no teste acima.
    vi.useFakeTimers();
    store.registrarEscritaLocal("t1");
    vi.advanceTimersByTime(14_000);

    expect(store.consumirEscritaLocal("t1")).toBe(true);
  });
});
