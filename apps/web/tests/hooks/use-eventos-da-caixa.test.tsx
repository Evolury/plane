/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: a caixa de entrada e a página de UMA tarefa (ADR 0013).
//
// As duas usam o mesmo canal do quadro e diferem só na reação. O que se tranca
// aqui é justamente o que as distingue — e, na caixa, o detalhe que mais
// facilmente se perde numa refatoração: **ela conecta SEM projeto**. Exigir um
// projeto a mandaria para uma sala que não é a dela, e o sino pararia de
// receber sem ninguém notar.

import { renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const recontar = vi.fn(async () => undefined);
const addIssue = vi.fn();
const retrieve = vi.fn(async (_ws: string, _p: string, id: string) => ({ id, name: id }));
const revalidarValoresDoProjeto = vi.fn();
const consumirEscritaLocal = vi.fn(() => false);

vi.mock("react", async () => {
  const react = await vi.importActual<typeof import("react")>("react");
  return { ...react, useContext: () => ({ issue: { issues: { consumirEscritaLocal, addIssue } } }) };
});

vi.mock("@/hooks/store/notifications", () => ({
  useWorkspaceNotifications: () => ({ getUnreadNotificationsCount: recontar }),
}));
vi.mock("@/hooks/store/user", () => ({ useUser: () => ({ data: { id: "eu" } }) }));
vi.mock("@/lib/store-context", () => ({ StoreContext: {} }));
vi.mock("@/components/issue-properties/store", () => ({ revalidarValoresDoProjeto }));
vi.mock("@/services/issue", () => ({
  IssueService: class {
    retrieve = retrieve;
  },
}));
vi.mock("@plane/constants", () => ({ LIVE_BASE_URL: "", LIVE_BASE_PATH: "/live" }));

class SocketFalso {
  static ultimo: SocketFalso | undefined;
  readyState = 1;
  onopen: (() => void) | null = null;
  onmessage: ((e: { data: string }) => void) | null = null;
  onclose: ((e: { code: number }) => void) | null = null;
  onerror: (() => void) | null = null;
  fechado = false;
  constructor(public url: string) {
    SocketFalso.ultimo = this;
  }
  close() {
    this.fechado = true;
  }
  receber(dados: unknown) {
    this.onmessage?.({ data: JSON.stringify(dados) });
  }
}
vi.stubGlobal("WebSocket", SocketFalso);

const { useEventosDaCaixa } = await import("@/hooks/use-eventos-da-caixa");
const { useEventosDaTarefa } = await import("@/hooks/use-eventos-da-tarefa");

describe("caixa de entrada", () => {
  beforeEach(() => {
    recontar.mockClear();
    SocketFalso.ultimo = undefined;
  });

  it("conecta SEM projectId", () => {
    // O detalhe que sustenta o resto: notificação é de uma PESSOA. Com projeto,
    // o `live` a poria na sala do projeto e o sino não receberia nada.
    renderHook(() => useEventosDaCaixa("evolury"));

    const url = new URL(SocketFalso.ultimo!.url);
    expect(url.searchParams.get("workspaceSlug")).toBe("evolury");
    expect(url.searchParams.has("projectId")).toBe(false);
  });

  it("reconta ao ser avisada", async () => {
    renderHook(() => useEventosDaCaixa("evolury"));
    SocketFalso.ultimo!.receber({ tipo: "notificacao" });

    await waitFor(() => expect(recontar).toHaveBeenCalledWith("evolury"));
  });

  it("junta uma rajada numa recontagem só", async () => {
    // Uma automação que avisa a equipe inteira dispara vários quase juntos, e a
    // resposta a todos é a mesma pergunta ao servidor.
    renderHook(() => useEventosDaCaixa("evolury"));
    for (let i = 0; i < 5; i++) SocketFalso.ultimo!.receber({ tipo: "notificacao" });

    await waitFor(() => expect(recontar).toHaveBeenCalled());
    expect(recontar).toHaveBeenCalledTimes(1);
  });

  it("ignora aviso de tarefa", async () => {
    renderHook(() => useEventosDaCaixa("evolury"));
    SocketFalso.ultimo!.receber({ tipo: "alterada", tarefa: "t1", ator: "outra" });

    await new Promise((r) => setTimeout(r, 1000));
    expect(recontar).not.toHaveBeenCalled();
  });

  it("não reconta depois de sair da tela", async () => {
    const { unmount } = renderHook(() => useEventosDaCaixa("evolury"));
    SocketFalso.ultimo!.receber({ tipo: "notificacao" });
    unmount();

    await new Promise((r) => setTimeout(r, 1100));
    expect(recontar).not.toHaveBeenCalled();
  });
});

describe("página de UMA tarefa", () => {
  beforeEach(() => {
    addIssue.mockClear();
    retrieve.mockClear();
    revalidarValoresDoProjeto.mockClear();
    SocketFalso.ultimo = undefined;
  });

  const montar = () => renderHook(() => useEventosDaTarefa("evolury", "projeto-1", "tarefa-1"));

  it("aplica a tarefa fresca no store raiz", async () => {
    // Aqui não há `issueUpdate`: não existe store de quadro, e sem lista não há
    // o que reposicionar. `addIssue` mescla no mapa de onde a página lê.
    montar();
    SocketFalso.ultimo!.receber({ tipo: "alterada", tarefa: "tarefa-1", ator: "outra" });

    await waitFor(() => expect(addIssue).toHaveBeenCalled());
    expect(retrieve).toHaveBeenCalledWith("evolury", "projeto-1", "tarefa-1");
  });

  it("ignora aviso de OUTRA tarefa", async () => {
    montar();
    SocketFalso.ultimo!.receber({ tipo: "alterada", tarefa: "outra-tarefa", ator: "outra" });

    await new Promise((r) => setTimeout(r, 400));
    expect(retrieve).not.toHaveBeenCalled();
  });

  it("revalida propriedade mesmo sendo de outra tarefa", async () => {
    // A chave dos valores é do PROJETO: a resposta do endereço muda igual.
    montar();
    SocketFalso.ultimo!.receber({ tipo: "propriedade", tarefa: "outra-tarefa", ator: "outra" });

    await waitFor(() => expect(revalidarValoresDoProjeto).toHaveBeenCalledWith("projeto-1"));
  });

  it("não reage a `removida` — tirar a tarefa da tela é decisão de produto", async () => {
    montar();
    SocketFalso.ultimo!.receber({ tipo: "removida", tarefa: "tarefa-1", ator: "outra" });

    await new Promise((r) => setTimeout(r, 400));
    expect(retrieve).not.toHaveBeenCalled();
    expect(addIssue).not.toHaveBeenCalled();
  });
});
