/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: propriedade personalizada como eixo do quadro (ADR 0011).
//
// Três decisões que o compilador não pega, porque todas se resolvem em tempo
// de execução: a chave de agrupamento é um id, o campo da tarefa tem o mesmo
// nome dessa chave, e arrastar precisa ser liberado para ela.
//
// A quarta — a marca "usar em agrupamentos" — é vigiada dos dois lados: aqui
// para o menu não oferecer, e no contrato da API para o servidor recusar.

import { describe, expect, it } from "vitest";
import { ehChaveDePropriedade, podeArrastarNoAgrupamento } from "@plane/constants";
import type { TIssueGroupByOptions } from "@plane/types";

const CHAVE = "property_9f8c1d2e-0000-4000-8000-000000000001" as TIssueGroupByOptions;

describe("chave de propriedade", () => {
  it("reconhece a chave de propriedade", () => {
    expect(ehChaveDePropriedade(CHAVE)).toBe(true);
  });

  it("não confunde com agrupamento nativo nem com vazio", () => {
    expect(ehChaveDePropriedade("state")).toBe(false);
    expect(ehChaveDePropriedade("propriedade")).toBe(false);
    expect(ehChaveDePropriedade(null)).toBe(false);
    expect(ehChaveDePropriedade(undefined)).toBe(false);
  });
});

describe("arrastar no agrupamento", () => {
  it("libera o arrasto quando o quadro agrupa por propriedade", () => {
    expect(podeArrastarNoAgrupamento(CHAVE)).toBe(true);
  });

  it("preserva o que já era permitido", () => {
    expect(podeArrastarNoAgrupamento("state")).toBe(true);
    expect(podeArrastarNoAgrupamento("my_task_stage")).toBe(true);
  });

  it("continua barrando o que nunca foi arrastável", () => {
    // Agrupar por projeto e por quem criou não são coisas que um arrasto
    // deva mudar — mover cartão não troca a tarefa de projeto.
    expect(podeArrastarNoAgrupamento("project")).toBe(false);
    expect(podeArrastarNoAgrupamento("created_by")).toBe(false);
    expect(podeArrastarNoAgrupamento(undefined)).toBe(false);
  });
});
