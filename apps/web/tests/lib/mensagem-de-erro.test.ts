/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: regressão do defeito de 17/08/2026 — a criação rápida engolia a
// frase que o servidor mandou e mostrava "Ocorreu algum erro".

import { describe, expect, it } from "vitest";
import { mensagemDoErro } from "@/lib/mensagem-de-erro";

describe("mensagemDoErro", () => {
  it("lê a frase dos nossos endpoints de propriedade", () => {
    // O formato exato que fez a criação rápida falhar em silêncio.
    expect(mensagemDoErro({ property_values: "Preencha: Local." })).toBe("Preencha: Local.");
  });

  it("lê os formatos das duas APIs e do DRF", () => {
    expect(mensagemDoErro({ error: "Sem permissão." })).toBe("Sem permissão.");
    expect(mensagemDoErro({ detail: "Não encontrado." })).toBe("Não encontrado.");
    expect(mensagemDoErro({ name: ["Este campo é obrigatório."] })).toBe("Este campo é obrigatório.");
  });

  it("prefere a chave conhecida quando há mais de uma", () => {
    expect(mensagemDoErro({ outro_campo: "ruído", error: "a que vale" })).toBe("a que vale");
  });

  it("junta as frases de uma lista de erros de campo", () => {
    expect(mensagemDoErro({ name: ["Primeira.", "Segunda."] })).toBe("Primeira. Segunda.");
  });

  it("desembrulha a resposta do axios", () => {
    expect(mensagemDoErro({ response: { data: { detail: "de dentro" } } })).toBe("de dentro");
  });

  it("devolve undefined quando não há frase, para quem chama escolher o texto", () => {
    // Nunca "[object Object]", que é o que `String(erro)` daria.
    expect(mensagemDoErro(undefined)).toBeUndefined();
    expect(mensagemDoErro(null)).toBeUndefined();
    expect(mensagemDoErro({})).toBeUndefined();
    expect(mensagemDoErro({ campo: 42 })).toBeUndefined();
    expect(mensagemDoErro({ campo: "   " })).toBeUndefined();
  });

  it("aceita a própria string", () => {
    expect(mensagemDoErro("já é uma frase")).toBe("já é uma frase");
  });
});
