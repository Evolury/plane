/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/**
 * O nome de exibição aceita nome de gente.
 *
 * A regra vinha do upstream tratando o campo como apelido — e o efeito era um
 * formulário que recusava "Tássio Câmara" com uma mensagem que nem mencionava
 * espaço, fazendo qualquer pessoa concluir que o acento é que era proibido. O
 * acento nunca foi: `\p{L}` sempre cobriu.
 *
 * O que este arquivo prende é o par: **espaço passa** e **caractere de injeção
 * continua recusado**. A segunda metade importa tanto quanto a primeira —
 * afrouxar a expressão sem ela é como a proteção some sem ninguém notar.
 */

import { describe, expect, it } from "vitest";
import { validateDisplayName } from "@plane/utils";

describe("nome de exibição", () => {
  it("aceita nome com espaço", () => {
    expect(validateDisplayName("Tássio Câmara")).toBe(true);
    expect(validateDisplayName("José da Silva")).toBe(true);
    expect(validateDisplayName("李 明")).toBe(true);
  });

  it("aceita o que já aceitava", () => {
    for (const nome of ["Tássio", "josé_123", "müller-2024", "john.doe-123"]) {
      expect(validateDisplayName(nome)).toBe(true);
    }
  });

  it("continua recusando caractere de injeção, com a mensagem específica", () => {
    // A primeira versão deste teste só exigia "não passa" — e passava verde com
    // a checagem de injeção removida, porque a própria expressão já recusa `<`
    // e `%`. Exigir a mensagem é o que prende a checagem dedicada: sem ela, cai
    // na mensagem genérica e o teste fica vermelho.
    for (const nome of ["Tássio<script>", 'nome "aspas"', "chave{}", "porcento%"]) {
      expect(validateDisplayName(nome)).toContain("special characters");
    }
  });

  it("não aceita tabulação nem quebra de linha", () => {
    // Espaço literal, e não `\s`: nome com tabulação ou quebra suja layout e log.
    expect(validateDisplayName("Tássio\tCâmara")).not.toBe(true);
    expect(validateDisplayName("Tássio\nCâmara")).not.toBe(true);
  });

  it("segue opcional, e o limite de tamanho segue valendo", () => {
    expect(validateDisplayName("")).toBe(true);
    expect(validateDisplayName("a".repeat(51))).not.toBe(true);
  });
});
