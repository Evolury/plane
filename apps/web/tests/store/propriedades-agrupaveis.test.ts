/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: quais propriedades o menu de "agrupar por" oferece (ADR 0011).
//
// O servidor recusa as demais por conta própria — este filtro existe para o
// menu não oferecer o que a consulta vai negar. Vigiado aqui porque o menu é
// montado por uma função pura, fora de qualquer componente.

import { beforeEach, describe, expect, it } from "vitest";
import type { TIssueProperty } from "@plane/types";
import { guardarPropriedades, propriedadesAgrupaveis } from "@/components/issue-properties/cache";

const PROJETO = "9f8c1d2e-0000-4000-8000-0000000000aa";

const propriedade = (campos: Partial<TIssueProperty>): TIssueProperty =>
  ({
    id: campos.name ?? "p",
    name: "Canal",
    property_type: "select",
    show_in_grouping: true,
    is_active: true,
    options: [],
    ...campos,
  }) as TIssueProperty;

describe("propriedades agrupáveis", () => {
  beforeEach(() => guardarPropriedades(PROJETO, []));

  it("oferece a seleção única marcada", () => {
    guardarPropriedades(PROJETO, [propriedade({ name: "Canal" })]);

    expect(propriedadesAgrupaveis(PROJETO).map((p) => p.name)).toEqual(["Canal"]);
  });

  it("esconde a que foi desmarcada na definição", () => {
    guardarPropriedades(PROJETO, [propriedade({ name: "Canal", show_in_grouping: false })]);

    expect(propriedadesAgrupaveis(PROJETO)).toEqual([]);
  });

  it("continua escondendo os tipos que não viram coluna", () => {
    // Texto ou moeda dariam uma coluna por valor distinto, e seleção múltipla
    // duplicaria o cartão entre colunas (ADR 0011).
    guardarPropriedades(PROJETO, [
      propriedade({ name: "Observação", property_type: "text" }),
      propriedade({ name: "Percepção", property_type: "multi_select" }),
    ]);

    expect(propriedadesAgrupaveis(PROJETO)).toEqual([]);
  });
});
