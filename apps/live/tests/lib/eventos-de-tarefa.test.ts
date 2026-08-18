/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: as salas por projeto (ADR 0013).
//
// O que se tranca aqui é o **isolamento entre projetos**. Ele é a única coisa
// separando "o quadro atualiza sozinho" de "todo mundo fica sabendo que uma
// tarefa mudou em projeto do qual não participa" — e é uma linha de código, um
// `Map.get`, fácil de perder numa refatoração e impossível de ver na tela.
//
// O Redis é substituído por um duplo que guarda o ouvinte: assinar de verdade
// exigiria um servidor no teste, e o que interessa afirmar é o que este módulo
// faz COM a mensagem, não que o `ioredis` sabe entregá-la.

import { beforeEach, describe, expect, it, vi } from "vitest";

const ouvintes: ((canal: string, mensagem: string) => void)[] = [];
const assinados: string[] = [];
let duplicatasCriadas = 0;

const assinanteFalso = {
  subscribe: vi.fn(async (canal: string) => {
    assinados.push(canal);
  }),
  on: vi.fn((evento: string, ouvinte: (canal: string, mensagem: string) => void) => {
    if (evento === "message") ouvintes.push(ouvinte);
  }),
  quit: vi.fn(async () => {}),
  disconnect: vi.fn(),
};

vi.mock("@/redis", () => ({
  redisManager: {
    getClient: () => ({
      duplicate: () => {
        duplicatasCriadas += 1;
        return assinanteFalso;
      },
    }),
  },
}));

const { salasDeEventos, CANAL } = await import("@/lib/eventos-de-tarefa");

/** O mínimo de um `ws` que o módulo toca: estado e envio. */
const socketFalso = (readyState = 1) => ({
  readyState,
  enviadas: [] as string[],
  send(carga: string) {
    this.enviadas.push(carga);
  },
});

const publicar = (evento: Record<string, unknown>) => {
  for (const ouvinte of ouvintes) ouvinte(CANAL, JSON.stringify(evento));
};

const evento = (projeto: string, tarefa = "tarefa-1") => ({
  tipo: "alterada",
  projeto,
  tarefa,
  ator: "pessoa-1",
});

describe("salas de eventos", () => {
  beforeEach(async () => {
    await salasDeEventos.encerrar();
    ouvintes.length = 0;
    assinados.length = 0;
    duplicatasCriadas = 0;
  });

  it("entrega a quem está na sala do projeto", async () => {
    const ws = socketFalso();
    await salasDeEventos.entrar("projeto-1", "pessoa-projeto-1", ws as never);

    publicar(evento("projeto-1"));

    expect(ws.enviadas).toHaveLength(1);
    expect(JSON.parse(ws.enviadas[0])).toEqual({ tipo: "alterada", tarefa: "tarefa-1", ator: "pessoa-1" });
  });

  it("NÃO entrega a quem está na sala de outro projeto", async () => {
    // A afirmação que sustenta o isolamento. Sem ela, um `Map.get` trocado por
    // um laço sobre todas as salas passaria em todo o resto desta suíte.
    const deOutroProjeto = socketFalso();
    await salasDeEventos.entrar("projeto-2", "pessoa-projeto-2", deOutroProjeto as never);

    publicar(evento("projeto-1"));

    expect(deOutroProjeto.enviadas).toEqual([]);
  });

  it("não repassa o campo `projeto` — quem recebe já sabe em qual está", async () => {
    const ws = socketFalso();
    await salasDeEventos.entrar("projeto-1", "pessoa-projeto-1", ws as never);

    publicar(evento("projeto-1"));

    expect(Object.keys(JSON.parse(ws.enviadas[0])).sort()).toEqual(["ator", "tarefa", "tipo"]);
  });

  it("para de entregar depois que a conexão sai", async () => {
    const ws = socketFalso();
    await salasDeEventos.entrar("projeto-1", "pessoa-projeto-1", ws as never);
    salasDeEventos.sair("projeto-1", "pessoa-projeto-1", ws as never);

    publicar(evento("projeto-1"));

    expect(ws.enviadas).toEqual([]);
    expect(salasDeEventos.tamanho("projeto-1")).toBe(0);
  });

  it("pula conexão que já fechou em vez de estourar", async () => {
    const fechada = socketFalso(3); // 3 === CLOSED
    const aberta = socketFalso();
    await salasDeEventos.entrar("projeto-1", "pessoa-projeto-1", fechada as never);
    await salasDeEventos.entrar("projeto-1", "pessoa-projeto-1", aberta as never);

    publicar(evento("projeto-1"));

    expect(fechada.enviadas).toEqual([]);
    expect(aberta.enviadas).toHaveLength(1);
  });

  it("assina o canal uma vez só, com várias conexões chegando juntas", async () => {
    // Dois assinantes entregariam cada mensagem em dobro, e o cliente rebuscaria
    // duas vezes por mudança.
    await Promise.all([
      salasDeEventos.entrar("projeto-1", "pessoa-projeto-1", socketFalso() as never),
      salasDeEventos.entrar("projeto-2", "pessoa-projeto-2", socketFalso() as never),
      salasDeEventos.entrar("projeto-3", "pessoa-projeto-3", socketFalso() as never),
    ]);

    expect(duplicatasCriadas).toBe(1);
    expect(assinados).toEqual([CANAL]);
  });

  it("descarta mensagem que não é JSON sem derrubar o processo", async () => {
    const ws = socketFalso();
    await salasDeEventos.entrar("projeto-1", "pessoa-projeto-1", ws as never);

    expect(() => {
      for (const ouvinte of ouvintes) ouvinte(CANAL, "isto não é json");
    }).not.toThrow();
    expect(ws.enviadas).toEqual([]);
  });

  it("esquece a sala vazia, para o mapa não crescer para sempre", async () => {
    const ws = socketFalso();
    await salasDeEventos.entrar("projeto-1", "pessoa-projeto-1", ws as never);
    salasDeEventos.sair("projeto-1", "pessoa-projeto-1", ws as never);

    // Entregar numa sala que não existe mais não pode estourar.
    expect(() => publicar(evento("projeto-1"))).not.toThrow();
  });
});

describe("sala da pessoa", () => {
  beforeEach(async () => {
    await salasDeEventos.encerrar();
    ouvintes.length = 0;
  });

  const notificacaoPara = (usuarios: string[]) => ({ tipo: "notificacao", usuarios });

  it("entrega a notificação a quem ela nomeia", async () => {
    const meu = socketFalso();
    await salasDeEventos.entrar("projeto-1", "pessoa-1", meu as never);

    publicar(notificacaoPara(["pessoa-1"]));

    expect(meu.enviadas).toHaveLength(1);
    expect(JSON.parse(meu.enviadas[0])).toEqual({ tipo: "notificacao" });
  });

  it("NÃO entrega a quem ela não nomeia", async () => {
    // O isolamento entre pessoas: sem isto, a caixa de entrada de alguém
    // piscaria por notificação que é de outro.
    const outro = socketFalso();
    await salasDeEventos.entrar("projeto-1", "pessoa-2", outro as never);

    publicar(notificacaoPara(["pessoa-1"]));

    expect(outro.enviadas).toEqual([]);
  });

  it("não repassa a lista de destinatários", async () => {
    // Saber quem MAIS foi avisado não é assunto de quem recebe.
    const meu = socketFalso();
    await salasDeEventos.entrar(undefined, "pessoa-1", meu as never);

    publicar(notificacaoPara(["pessoa-1", "pessoa-2", "pessoa-3"]));

    expect(Object.keys(JSON.parse(meu.enviadas[0]))).toEqual(["tipo"]);
  });

  it("conexão SEM projeto recebe notificação e ignora aviso de tarefa", async () => {
    // É exatamente o caso da caixa de entrada: o sino não vive num quadro.
    const sino = socketFalso();
    await salasDeEventos.entrar(undefined, "pessoa-1", sino as never);

    publicar({ tipo: "alterada", projeto: "projeto-1", tarefa: "t1", ator: null });
    expect(sino.enviadas).toEqual([]);

    publicar(notificacaoPara(["pessoa-1"]));
    expect(sino.enviadas).toHaveLength(1);
  });

  it("sair tira das DUAS salas", async () => {
    const ws = socketFalso();
    await salasDeEventos.entrar("projeto-1", "pessoa-1", ws as never);
    salasDeEventos.sair("projeto-1", "pessoa-1", ws as never);

    expect(salasDeEventos.tamanho("projeto-1")).toBe(0);
    expect(salasDeEventos.tamanhoPorPessoa("pessoa-1")).toBe(0);
    publicar(notificacaoPara(["pessoa-1"]));
    expect(ws.enviadas).toEqual([]);
  });
});
