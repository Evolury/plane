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

vi.mock("react", async () => {
  const react = await vi.importActual<typeof import("react")>("react");
  // Só o `useContext` é trocado: o gancho lê dali o store RAIZ, e montar o
  // provedor de verdade traria a árvore de stores inteira para um teste que
  // quer afirmar uma decisão de três linhas.
  return { ...react, useContext: () => ({ issue: { issues: { consumirEscritaLocal } } }) };
});

const issueUpdate = vi.fn();
const removeIssueFromList = vi.fn();
const rebuscarQuadro = vi.fn();
const retrieveIssues = vi.fn(async (_ws: string, _p: string, ids: string[]) => ids.map((id) => ({ id, name: id })));

let groupedIssueIds: unknown = { grupo: ["tarefa-no-quadro"] };
let meuId = "eu";

const consumirEscritaLocal = vi.fn(() => false);

vi.mock("@/hooks/store/use-issues", () => ({
  useIssues: () => ({ issues: { groupedIssueIds, issueUpdate, removeIssueFromList } }),
}));

vi.mock("@/lib/store-context", () => ({ StoreContext: {} }));

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
const montar = () => renderHook(() => useEventosDeTarefa("evolury", "projeto-1", "PROJECT" as never, rebuscarQuadro));

const avisoDe = (tarefa: string, ator: string | null = "outra-pessoa") => ({ tipo: "alterada", tarefa, ator });

describe("useEventosDeTarefa", () => {
  beforeEach(() => {
    issueUpdate.mockClear();
    retrieveIssues.mockClear();
    groupedIssueIds = { grupo: ["tarefa-no-quadro"] };
    meuId = "eu";
    consumirEscritaLocal.mockReset();
    consumirEscritaLocal.mockReturnValue(false);
    removeIssueFromList.mockClear();
    rebuscarQuadro.mockClear();
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

  it("ignora o eco da escrita feita NESTA aba", async () => {
    // A aba escreveu: o store raiz reconhece a anotação e a gasta.
    consumirEscritaLocal.mockReturnValue(true);
    montar();
    SocketFalso.ultimo!.receber(avisoDe("tarefa-no-quadro", meuId));

    await new Promise((r) => setTimeout(r, 400));
    expect(consumirEscritaLocal).toHaveBeenCalledWith("tarefa-no-quadro");
    expect(retrieveIssues).not.toHaveBeenCalled();
  });

  it("ATUALIZA quando a mesma pessoa mudou em OUTRA aba", async () => {
    // O defeito que a fase 1 deixou: o ator é o mesmo usuário, mas esta aba não
    // escreveu nada, então não há anotação para gastar — e o aviso vale.
    consumirEscritaLocal.mockReturnValue(false);
    montar();
    SocketFalso.ultimo!.receber(avisoDe("tarefa-no-quadro", meuId));

    await waitFor(() => expect(retrieveIssues).toHaveBeenCalled());
  });

  it("não gasta anotação quando o ator é outra pessoa", async () => {
    // Gastar aqui torraria a anotação de uma escrita minha ainda pendente, e o
    // eco seguinte passaria a ser tratado como mudança alheia.
    montar();
    SocketFalso.ultimo!.receber(avisoDe("tarefa-no-quadro", "outra-pessoa"));

    await waitFor(() => expect(retrieveIssues).toHaveBeenCalled());
    expect(consumirEscritaLocal).not.toHaveBeenCalled();
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

  it("ignora tipo que não conhece", async () => {
    montar();
    SocketFalso.ultimo!.receber({ tipo: "inventada", tarefa: "tarefa-no-quadro", ator: "outra-pessoa" });

    await new Promise((r) => setTimeout(r, 400));
    expect(retrieveIssues).not.toHaveBeenCalled();
    expect(rebuscarQuadro).not.toHaveBeenCalled();
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

describe("tarefa que sai do quadro", () => {
  beforeEach(() => {
    removeIssueFromList.mockClear();
    retrieveIssues.mockClear();
    groupedIssueIds = { grupo: ["tarefa-no-quadro"] };
  });

  it("tira o cartão sem buscar nada", async () => {
    // Tirar é exato: não depende de filtro e não precisa do servidor. Buscar
    // aqui seria pedir uma tarefa que o quadro está justamente descartando.
    montar();
    SocketFalso.ultimo!.receber({ tipo: "removida", tarefa: "tarefa-no-quadro", ator: "outra-pessoa" });

    await waitFor(() => expect(removeIssueFromList).toHaveBeenCalledWith("tarefa-no-quadro"));
    expect(retrieveIssues).not.toHaveBeenCalled();
  });

  it("não tenta tirar tarefa que não está neste quadro", async () => {
    montar();
    SocketFalso.ultimo!.receber({ tipo: "removida", tarefa: "tarefa-de-fora", ator: "outra-pessoa" });

    await new Promise((r) => setTimeout(r, 400));
    expect(removeIssueFromList).not.toHaveBeenCalled();
  });
});

describe("tarefa nova", () => {
  beforeEach(() => {
    rebuscarQuadro.mockClear();
    retrieveIssues.mockClear();
    groupedIssueIds = { grupo: ["tarefa-no-quadro"] };
  });

  it("rebusca a lista, e não a tarefa", async () => {
    // Acrescentar a tarefa direto faria aparecer, para quem filtrou, um cartão
    // que o filtro exclui: `updateIssueList` não avalia os filtros ricos.
    montar();
    SocketFalso.ultimo!.receber({ tipo: "criada", tarefa: "tarefa-nova", ator: "outra-pessoa" });

    await waitFor(() => expect(rebuscarQuadro).toHaveBeenCalled());
    expect(retrieveIssues).not.toHaveBeenCalled();
  });

  it("não desiste por a tarefa ainda não estar no quadro", async () => {
    // A guarda `estaNoQuadro` vale para os outros tipos. Aqui ela mataria o
    // caso inteiro: tarefa nova nunca está no quadro — é o que se quer saber.
    groupedIssueIds = { grupo: [] };
    montar();
    SocketFalso.ultimo!.receber({ tipo: "criada", tarefa: "tarefa-nova", ator: "outra-pessoa" });

    await waitFor(() => expect(rebuscarQuadro).toHaveBeenCalled());
  });

  it("junta uma rajada numa rebusca só", async () => {
    // Uma automação que cria subtarefas dispara várias de uma vez.
    montar();
    for (const t of ["a", "b", "c", "d"]) {
      SocketFalso.ultimo!.receber({ tipo: "criada", tarefa: t, ator: "outra-pessoa" });
    }

    await waitFor(() => expect(rebuscarQuadro).toHaveBeenCalled());
    expect(rebuscarQuadro).toHaveBeenCalledTimes(1);
  });

  it("não rebusca depois de sair do quadro", async () => {
    const { unmount } = montar();
    SocketFalso.ultimo!.receber({ tipo: "criada", tarefa: "tarefa-nova", ator: "outra-pessoa" });
    unmount();

    await new Promise((r) => setTimeout(r, 900));
    expect(rebuscarQuadro).not.toHaveBeenCalled();
  });
});
