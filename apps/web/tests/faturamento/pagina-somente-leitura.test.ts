/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Espaço em somente leitura não aceita digitação na página (ADR 0021).
//
// A trava do servidor já pega a gravação — a página salva chamando a API de
// volta pelo `apps/live` —, mas o usuário só descobriria **depois de escrever**,
// com um "Unable to save the page". Somente leitura que perde trabalho digitado
// é o oposto do que a degradação existe para fazer, e foi o item que a matriz
// de compatibilidade marcou como obrigatório desta entrega.
//
// O teste monta a página com um root store de mentira, porque o que se prova
// aqui é uma conta: `isContentEditable` tem de olhar para o estado da
// assinatura, e não só para papel, arquivamento e cadeado.

import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/services/page/personal-page.service", () => ({
  PersonalPageService: class {
    update = vi.fn();
    updateDescription = vi.fn();
    updateAccess = vi.fn();
    lock = vi.fn();
    unlock = vi.fn();
    archive = vi.fn();
    restore = vi.fn();
    duplicate = vi.fn();
    remove = vi.fn();
    fetchDescriptionBinary = vi.fn();
  },
}));

const { PersonalPage } = await import("@/store/pages/personal-page");

const USUARIO = "usuario-1";

function rootStoreFalso(podeEscrever: boolean) {
  return {
    router: { workspaceSlug: "espaco" },
    user: { data: { id: USUARIO } },
    faturamento: { podeEscrever: () => podeEscrever },
  } as any;
}

const PAGINA = {
  id: "pagina-1",
  name: "Anotações",
  owned_by: USUARIO,
  access: 0,
  archived_at: null,
  is_locked: false,
  created_by: USUARIO,
} as any;

describe("edição de página e estado da assinatura", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("espaço que escreve deixa editar", () => {
    const pagina = new PersonalPage(rootStoreFalso(true), PAGINA);
    expect(pagina.isContentEditable).toBe(true);
  });

  it("espaço em somente leitura não deixa — e a decisão é antes de digitar", () => {
    const pagina = new PersonalPage(rootStoreFalso(false), PAGINA);
    expect(pagina.isContentEditable).toBe(false);
  });

  it("o cadeado da própria página continua valendo", () => {
    const pagina = new PersonalPage(rootStoreFalso(true), { ...PAGINA, is_locked: true });
    expect(pagina.isContentEditable).toBe(false);
  });

  it("página arquivada continua sem edição", () => {
    const pagina = new PersonalPage(rootStoreFalso(true), { ...PAGINA, archived_at: "2026-01-01" });
    expect(pagina.isContentEditable).toBe(false);
  });
});
