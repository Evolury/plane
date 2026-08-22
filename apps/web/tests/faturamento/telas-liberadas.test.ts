/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Duas telas atravessam o bloqueio, e some uma delas não faz barulho nenhum:
// a tela some, o cliente bloqueado deixa de conseguir exportar, e ninguém
// descobre até alguém reclamar por escrito. Aconteceu na primeira versão desta
// trava — Exportações foi escondida junto com o resto do produto.

import { describe, expect, it } from "vitest";
// Direto do módulo, e não do índice: o índice arrasta componentes que
// dependem do `next/link` da camada de compatibilidade, que não existe fora
// do aplicativo.
import { TELAS_QUE_ATRAVESSAM_O_BLOQUEIO } from "@/components/faturamento/telas-liberadas";

describe("telas que atravessam o bloqueio", () => {
  it("pagar não depende de estar pago", () => {
    expect(TELAS_QUE_ATRAVESSAM_O_BLOQUEIO).toContain("/settings/billing");
  });

  it("exportar sobrevive a todos os estados", () => {
    expect(TELAS_QUE_ATRAVESSAM_O_BLOQUEIO).toContain("/settings/exports");
  });

  it("e são só essas duas — exceção que cresce vira regra", () => {
    expect(TELAS_QUE_ATRAVESSAM_O_BLOQUEIO).toHaveLength(2);
  });
});
