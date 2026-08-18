/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: as portas do canal de eventos (ADR 0013).
//
// O caso que motiva o arquivo é o `js/request-forgery` que o CodeQL pegou:
// `workspaceSlug` e `projectId` vinham crus da URL de quem conecta para dentro
// do CAMINHO de uma requisição à API. Com `projectId = "../../users/me"`, o
// caminho normaliza para um endpoint que responde 200 a qualquer sessão — e a
// porta de acesso ao projeto abria sozinha.
//
// Por isso a afirmação central não é "fechou a conexão", e sim **a requisição
// nunca saiu**: fechar depois de perguntar já teria deixado o pedido forjado
// chegar à API.

import { beforeEach, describe, expect, it, vi } from "vitest";

const podeVer = vi.fn(async () => true);
const currentUser = vi.fn(async () => ({ id: "pessoa-1" }));
const entrar = vi.fn(async () => {});

vi.mock("@/services/project.service", () => ({
  ProjectService: class {
    podeVer = podeVer;
  },
}));
vi.mock("@/services/user.service", () => ({
  UserService: class {
    currentUser = currentUser;
  },
}));
vi.mock("@/lib/eventos-de-tarefa", () => ({ salasDeEventos: { entrar, sair: vi.fn() }, CANAL: "evolury:tarefas" }));
vi.mock("@/env", () => ({ env: { CORS_ALLOWED_ORIGINS: "https://plane.evolury.app.br" } }));

const { EventosController } = await import("@/controllers/eventos.controller");

const PROJETO = "181b5270-48dd-4a87-87b6-aa8e4df76a08";
const ORIGEM = "https://plane.evolury.app.br";

const socketFalso = () => ({
  readyState: 1,
  fechamentos: [] as { code: number; reason: string }[],
  ouvintes: {} as Record<string, unknown>,
  close(code: number, reason: string) {
    this.fechamentos.push({ code, reason });
    this.readyState = 3;
  },
  on(evento: string, fn: unknown) {
    this.ouvintes[evento] = fn;
  },
  ping() {},
});

const pedido = (query: Record<string, string>, origin: string | undefined = ORIGEM) => ({
  query,
  headers: { cookie: "session-id=abc", origin },
});

const conectar = async (query: Record<string, string>, origin?: string) => {
  const ws = socketFalso();
  await new EventosController().handleConnection(ws as never, pedido(query, origin) as never);
  return ws;
};

describe("porta de forma dos parâmetros", () => {
  beforeEach(() => {
    podeVer.mockClear();
    currentUser.mockClear();
    entrar.mockClear();
  });

  it.each([
    ["travessia no id do projeto", { workspaceSlug: "evolury", projectId: "../../users/me" }],
    ["id do projeto que não é UUID", { workspaceSlug: "evolury", projectId: "qualquer-coisa" }],
    ["barra no slug", { workspaceSlug: "evolury/../..", projectId: PROJETO }],
    ["url inteira no slug", { workspaceSlug: "http://attacker.example", projectId: PROJETO }],
    ["slug com espaço", { workspaceSlug: "com espaco", projectId: PROJETO }],
  ])("recusa %s sem chegar a perguntar à API", async (_nome, query) => {
    const ws = await conectar(query);

    // A afirmação que importa: nenhuma requisição forjada saiu daqui.
    expect(podeVer).not.toHaveBeenCalled();
    expect(entrar).not.toHaveBeenCalled();
    expect(ws.fechamentos[0]?.code).toBe(1008);
  });

  it("deixa passar o par bem formado", async () => {
    // Sem isto, recusar tudo passaria em todos os testes acima.
    const ws = await conectar({ workspaceSlug: "evolury", projectId: PROJETO });

    expect(podeVer).toHaveBeenCalledWith(expect.any(String), "evolury", PROJETO);
    expect(entrar).toHaveBeenCalled();
    expect(ws.fechamentos).toEqual([]);
  });
});

describe("porta de origem", () => {
  beforeEach(() => {
    podeVer.mockClear();
    entrar.mockClear();
  });

  it("recusa origem de terceiro", async () => {
    // A autenticação é por cookie, e cookie o navegador manda sozinho — inclusive
    // a partir de uma página de terceiro que abra um WebSocket para cá. O
    // `cors()` do Express não cobre: a negociação de WebSocket não faz preflight.
    const ws = await conectar({ workspaceSlug: "evolury", projectId: PROJETO }, "https://attacker.example");

    expect(entrar).not.toHaveBeenCalled();
    expect(ws.fechamentos[0]?.code).toBe(1008);
  });

  it("aceita quem não declara origem", async () => {
    // Cliente que não é navegador não manda o cabeçalho — e também não carrega
    // cookie de terceiro, que é o ataque que esta porta existe para barrar.
    const ws = await conectar({ workspaceSlug: "evolury", projectId: PROJETO }, undefined);

    expect(entrar).toHaveBeenCalled();
    expect(ws.fechamentos).toEqual([]);
  });
});

describe("porta de acesso ao projeto", () => {
  beforeEach(() => {
    podeVer.mockClear();
    entrar.mockClear();
  });

  it("não entra na sala de projeto que a API nega", async () => {
    podeVer.mockResolvedValueOnce(false);

    const ws = await conectar({ workspaceSlug: "evolury", projectId: PROJETO });

    expect(entrar).not.toHaveBeenCalled();
    expect(ws.fechamentos[0]?.code).toBe(1008);
  });
});
