/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: o receptor de avisos do `live` (ADR 0013).
//
// Três das afirmações aqui existem porque a falha correspondente NÃO aparece na
// tela — ela aparece como carga, como laço, ou como um cartão que não devia
// estar ali:
//
// * `shouldSync: false` — sem ele, receber um aviso viraria um PATCH, que geraria
//   outro aviso: dois navegadores abertos ficariam se respondendo em laço.
// * o próprio eco — quem mudou já viu o efeito na hora; rebuscar por causa dele
//   desfaz a resposta imediata que ele acabou de ter.
// * `estaNoQuadro` — `updateIssueList` reposiciona pela DIFERENÇA entre antes e
//   depois, então, se o campo do agrupamento mudou, ela ACRESCENTA a tarefa ao
//   grupo novo. Uma tarefa que o filtro deste quadro exclui apareceria nele.

import { renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const issueUpdate = vi.fn();
const retrieveIssues = vi.fn(async (_ws: string, _p: string, ids: string[]) => ids.map((id) => ({ id, name: id })));

let groupedIssueIds: unknown = { grupo: ["tarefa-no-quadro"] };
let meuId = "eu";

vi.mock("@/hooks/store/use-issues", () => ({
  useIssues: () => ({ issues: { groupedIssueIds, issueUpdate } }),
}));

vi.mock("@/hooks/store/user", () => ({
  useUser: () => ({ data: { id: meuId } }),
}));

vi.mock("@/services/issue", () => ({
  IssueService: class {
    retrieveIssues = retrieveIssues;
  },
}));

vi.mock("@plane/constants", () => ({ LIVE_BASE_URL: "", LIVE_BASE_PATH: "/live" }));

/** Um `WebSocket` de mentira que guarda a instância aberta para o teste alimentar. */
class SocketFalso {
  static ultimo: SocketFalso | undefined;
  readyState = 1;
  onopen: (() => void) | null = null;
  onmessage: ((evento: { data: string }) => void) | null = null;
  onclose: ((evento: { code: number }) => void) | null = null;
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

const { useEventosDeTarefa } = await import("@/hooks/use-eventos-de-tarefa");

// `EIssuesStoreType.PROJECT` sem importar `@plane/types`: o valor não é lido
// pelo gancho (o store vem do mock), e importar traria a árvore de tipos inteira.
const montar = () => renderHook(() => useEventosDeTarefa("evolury", "projeto-1", "PROJECT" as never));

const avisoDe = (tarefa: string, ator: string | null = "outra-pessoa") => ({ tipo: "alterada", tarefa, ator });

describe("useEventosDeTarefa", () => {
  beforeEach(() => {
    issueUpdate.mockClear();
    retrieveIssues.mockClear();
    groupedIssueIds = { grupo: ["tarefa-no-quadro"] };
    meuId = "eu";
    SocketFalso.ultimo = undefined;
  });

  it("abre o canal do projeto com os parâmetros que o `live` exige", () => {
    montar();

    const url = new URL(SocketFalso.ultimo!.url);
    expect(url.pathname).toBe("/live/eventos/");
    expect(url.searchParams.get("workspaceSlug")).toBe("evolury");
    expect(url.searchParams.get("projectId")).toBe("projeto-1");
  });

  it("aplica a tarefa fresca no store SEM escrever de volta na API", async () => {
    montar();
    SocketFalso.ultimo!.receber(avisoDe("tarefa-no-quadro"));

    await waitFor(() => expect(issueUpdate).toHaveBeenCalled());
    const [, , issueId, dados, shouldSync] = issueUpdate.mock.calls[0];
    expect(issueId).toBe("tarefa-no-quadro");
    expect(dados).toMatchObject({ id: "tarefa-no-quadro" });
    // O argumento que impede o laço entre dois navegadores abertos.
    expect(shouldSync).toBe(false);
  });

  it("ignora o próprio eco", async () => {
    montar();
    SocketFalso.ultimo!.receber(avisoDe("tarefa-no-quadro", meuId));

    await new Promise((r) => setTimeout(r, 400));
    expect(retrieveIssues).not.toHaveBeenCalled();
  });

  it("ignora tarefa que não está neste quadro", async () => {
    montar();
    SocketFalso.ultimo!.receber(avisoDe("tarefa-de-fora"));

    await new Promise((r) => setTimeout(r, 400));
    expect(retrieveIssues).not.toHaveBeenCalled();
  });

  it("enxerga a tarefa também no quadro subagrupado", async () => {
    // A outra forma de `groupedIssueIds`: `{grupo: {subgrupo: id[]}}`. Varrer só
    // a primeira faria o quadro subagrupado parar de atualizar, em silêncio.
    groupedIssueIds = { grupo: { subgrupo: ["tarefa-aninhada"] } };
    montar();
    SocketFalso.ultimo!.receber(avisoDe("tarefa-aninhada"));

    await waitFor(() => expect(retrieveIssues).toHaveBeenCalled());
  });

  it("ignora tipo que a Fase 1 não trata", async () => {
    montar();
    SocketFalso.ultimo!.receber({ tipo: "criada", tarefa: "tarefa-no-quadro", ator: "outra-pessoa" });

    await new Promise((r) => setTimeout(r, 400));
    expect(retrieveIssues).not.toHaveBeenCalled();
  });

  it("junta uma rajada numa busca só", async () => {
    // Edição em lote de 200 tarefas não pode virar 200 requisições.
    groupedIssueIds = { grupo: ["a", "b", "c"] };
    montar();
    SocketFalso.ultimo!.receber(avisoDe("a"));
    SocketFalso.ultimo!.receber(avisoDe("b"));
    SocketFalso.ultimo!.receber(avisoDe("c"));

    await waitFor(() => expect(retrieveIssues).toHaveBeenCalled());
    expect(retrieveIssues).toHaveBeenCalledTimes(1);
    expect(retrieveIssues.mock.calls[0][2].sort()).toEqual(["a", "b", "c"]);
  });

  it("descarta mensagem que não é JSON", async () => {
    montar();

    expect(() => SocketFalso.ultimo!.onmessage?.({ data: "nada disso" })).not.toThrow();
    expect(retrieveIssues).not.toHaveBeenCalled();
  });

  it("fecha o canal ao sair do quadro", () => {
    const { unmount } = montar();
    const socket = SocketFalso.ultimo!;

    unmount();

    expect(socket.fechado).toBe(true);
  });

  it("não reconecta depois de recusa de acesso", async () => {
    montar();
    const socket = SocketFalso.ultimo!;
    // 1008 é o que o `live` devolve para origem, sessão ou projeto negados.
    // Reconectar depois disso só repetiria a recusa, num laço contra a API.
    socket.onclose?.({ code: 1008 });

    await new Promise((r) => setTimeout(r, 1500));
    expect(SocketFalso.ultimo).toBe(socket);
  });
});
