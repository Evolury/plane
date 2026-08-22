/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// O servidor manda centavos inteiros; quem divide por cem é a tela, uma vez só.
// Espalhar `/ 100` pelos componentes é como um deles acaba dividindo duas vezes
// — e um preço de R$ 6,90 numa tela de assinatura passa despercebido por um
// bom tempo.

import { describe, expect, it } from "vitest";
import { emData, emReais } from "@/components/faturamento/formato";

describe("dinheiro na tela", () => {
  it.each([
    [29000, "R$ 290,00"],
    [69000, "R$ 690,00"],
    [159000, "R$ 1.590,00"],
    [290000, "R$ 2.900,00"],
    [1590000, "R$ 15.900,00"],
    [9000, "R$ 90,00"],
    [0, "R$ 0,00"],
  ])("%i centavos viram %s", (centavos, esperado) => {
    // O espaço do R$ formatado pelo Intl é não separável — normalizamos para
    // comparar, porque a diferença é invisível e o teste falharia por ela.
    expect(emReais(centavos).replace(/ /g, " ")).toBe(esperado);
  });

  it("valor ausente não vira NaN", () => {
    expect(emReais(null).replace(/ /g, " ")).toBe("R$ 0,00");
    expect(emReais(undefined).replace(/ /g, " ")).toBe("R$ 0,00");
  });
});

describe("data na tela", () => {
  it("vem ISO e sai no formato daqui", () => {
    expect(emData("2026-11-19")).toBe("19/11/2026");
    expect(emData("2026-11-19T03:00:00Z")).toBe("19/11/2026");
  });

  it("sem data, um traço — e não 'Invalid Date'", () => {
    expect(emData(null)).toBe("—");
    expect(emData("")).toBe("—");
  });
});
