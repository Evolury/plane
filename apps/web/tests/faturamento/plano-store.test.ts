/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// O store do plano esconde; quem recusa é o servidor (ADR 0021).
//
// A parte que merece teste não é a que esconde: é a que **não** esconde. Sem
// retrato — porque ainda não chegou, ou porque a rede falhou — a resposta tem
// de ser "mostra". O contrário faria toda navegação começar com o menu piscando
// e, no caso da falha de rede, esconderia recurso de quem pagou por ele.

import { beforeEach, describe, expect, it, vi } from "vitest";

const retratoMock = vi.fn();

vi.mock("@/services/faturamento.service", () => ({
  FaturamentoService: class {
    retrato = retratoMock;
  },
}));

const { FaturamentoStore } = await import("@/store/faturamento.store");

const RETRATO_ESSENCIAL = {
  plano: "essencial",
  nome: "Essencial",
  ciclo: "mensal",
  status: "ativa",
  pode_escrever: true,
  pago_ate: "2026-09-20",
  proxima_cobranca_em: "2026-09-20",
  promocao_termina_em: null,
  proximo_marco: null,
  recursos: { analytics: false, api_publica: false, webhooks: false },
  limites: { propriedades_por_projeto: 5, automacoes_ativas: 2 },
  assentos: { incluidos: 3, extras: 0, usados: 2 },
  convidados: { cota: 0, usados: 0 },
  automacoes_ativas: 1,
};

describe("store do plano", () => {
  beforeEach(() => {
    retratoMock.mockReset();
  });

  it("sem retrato, mostra tudo — não pisca menu em quem já pagou", () => {
    const store = new FaturamentoStore();
    expect(store.recursoLiberado("espaco", "analytics")).toBe(true);
    expect(store.podeEscrever("espaco")).toBe(true);
  });

  it("com retrato, respeita o que o plano inclui", async () => {
    retratoMock.mockResolvedValue(RETRATO_ESSENCIAL);
    const store = new FaturamentoStore();

    await store.buscarRetrato("espaco");

    expect(store.recursoLiberado("espaco", "analytics")).toBe(false);
    expect(store.recursoLiberado("espaco", "webhooks")).toBe(false);
    expect(store.limite("espaco", "propriedades_por_projeto")).toBe(5);
  });

  it("guarda um retrato por espaço", async () => {
    retratoMock.mockResolvedValue(RETRATO_ESSENCIAL);
    const store = new FaturamentoStore();

    await store.buscarRetrato("um");

    expect(store.retrato("um")?.plano).toBe("essencial");
    // O outro espaço não herda o plano do primeiro.
    expect(store.retrato("outro")).toBeUndefined();
    expect(store.recursoLiberado("outro", "analytics")).toBe(true);
  });

  it("falha de rede não esconde recurso", async () => {
    retratoMock.mockRejectedValue(new Error("sem rede"));
    const store = new FaturamentoStore();

    const resultado = await store.buscarRetrato("espaco");

    expect(resultado).toBeUndefined();
    expect(store.carregando).toBe(false);
    expect(store.recursoLiberado("espaco", "analytics")).toBe(true);
  });

  it("estado que não escreve chega como tal", async () => {
    retratoMock.mockResolvedValue({ ...RETRATO_ESSENCIAL, status: "restrita", pode_escrever: false });
    const store = new FaturamentoStore();

    await store.buscarRetrato("espaco");

    expect(store.podeEscrever("espaco")).toBe(false);
  });

  it("espaço sem slug não vira chamada", async () => {
    const store = new FaturamentoStore();

    await store.buscarRetrato("");

    expect(retratoMock).not.toHaveBeenCalled();
  });
});
