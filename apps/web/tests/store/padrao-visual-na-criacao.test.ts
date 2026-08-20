/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: projeto novo nasce com a identidade da casa, não com um sorteio.
//
// O upstream sorteia a capa entre 29 fotos e o ícone entre dezenas de emojis, e
// é o tipo de coisa que uma sincronização devolve sem ninguém notar — o defeito
// não quebra nada, só faz a lista de projetos virar um mosaico. Por isso a
// regra é vigiada: se voltar a sortear, estes testes falham.

import { describe, expect, it, vi } from "vitest";
import { NANO_BLUE, DEEP_BLUE, ICONE_PADRAO_DE_PROJETO } from "@plane/constants";

vi.mock("@/services/issue", () => ({ IssueService: vi.fn() }));

const { getProjectFormValues } = await import("@/components/projects/create/utils");

describe("padrão visual do projeto novo", () => {
  it("não sorteia: duas criações seguidas são idênticas", () => {
    const a = getProjectFormValues();
    const b = getProjectFormValues();
    expect(a).toEqual(b);
  });

  it("nasce sem capa — quem pinta o azul é a tela", () => {
    expect(getProjectFormValues().cover_image_url).toBeUndefined();
  });

  it("nasce com ícone, e não com emoji", () => {
    const { logo_props } = getProjectFormValues();
    expect(logo_props?.in_use).toBe("icon");
    expect(logo_props?.emoji).toBeUndefined();
    expect(logo_props?.icon?.name).toBe(ICONE_PADRAO_DE_PROJETO.name);
  });

  it("o ícone contrasta com a capa: DeepBlue sobre NanoBlue, nunca azul sobre azul", () => {
    expect(getProjectFormValues().logo_props?.icon?.color).toBe(DEEP_BLUE);
    expect(DEEP_BLUE).not.toBe(NANO_BLUE);
  });
});

describe("cores da marca", () => {
  it("são as do brandbook 1.02, página 17", () => {
    expect(NANO_BLUE).toBe("#0C91EB");
    expect(DEEP_BLUE).toBe("#013F6E");
  });
});
