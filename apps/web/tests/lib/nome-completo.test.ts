/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/**
 * O nome não se repete na tela.
 *
 * Oito lugares do produto juntavam `first_name` e `last_name` com um espaço no
 * meio. Muita gente lê "Nome" e digita o nome inteiro — e a saudação virava
 * "Boas-vindas ao QooWork, Tássio Câmara Câmara", medido em 22/08/2026 com
 * `first_name="Tássio Câmara"` e `last_name="Câmara"` gravados.
 *
 * O que este arquivo prende é o par: **a repetição some** e **nome de gente
 * continua inteiro**. A segunda metade importa tanto quanto a primeira — uma
 * regra mais esperta comeria sobrenome legítimo, e errar o nome de alguém na
 * tela de boas-vindas é pior do que repetir.
 */

import { describe, expect, it } from "vitest";
import { nomeCompleto } from "@plane/utils";

describe("nome completo", () => {
  it("não repete o sobrenome que já está no nome", () => {
    expect(nomeCompleto({ first_name: "Tássio Câmara", last_name: "Câmara" })).toBe("Tássio Câmara");
    expect(nomeCompleto({ first_name: "Ana Maria Silva", last_name: "Silva" })).toBe("Ana Maria Silva");
  });

  it("ignora caixa e espaço sobrando na comparação", () => {
    expect(nomeCompleto({ first_name: "Tássio  CÂMARA", last_name: " câmara " })).toBe("Tássio CÂMARA");
  });

  it("junta quando são nomes diferentes", () => {
    expect(nomeCompleto({ first_name: "Tássio", last_name: "Câmara" })).toBe("Tássio Câmara");
    expect(nomeCompleto({ first_name: "Ana Maria", last_name: "Silva" })).toBe("Ana Maria Silva");
  });

  it("respeita limite de palavra — parte de palavra não é repetição", () => {
    expect(nomeCompleto({ first_name: "Anamaria", last_name: "Maria" })).toBe("Anamaria Maria");
    expect(nomeCompleto({ first_name: "Cardoso", last_name: "Oso" })).toBe("Cardoso Oso");
  });

  it("aguenta campo vazio, nulo e pessoa ausente", () => {
    expect(nomeCompleto({ first_name: "Ana", last_name: "" })).toBe("Ana");
    expect(nomeCompleto({ first_name: "", last_name: "Silva" })).toBe("Silva");
    expect(nomeCompleto({ first_name: null, last_name: null })).toBe("");
    expect(nomeCompleto(undefined)).toBe("");
    expect(nomeCompleto(null)).toBe("");
  });

  it("o nome inteiro no primeiro campo, sozinho, sai inteiro", () => {
    expect(nomeCompleto({ first_name: "José da Silva", last_name: "" })).toBe("José da Silva");
  });
});
