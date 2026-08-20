/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: a capa pode ser uma cor, e cor e imagem viajam no MESMO campo.
//
// É um seletor só, e o que ele devolve é uma string. Toda a separação acontece
// em duas bordas: no envio, cada uma vai para o campo dela; na tela, quem
// desenha decide entre pintar e carregar. Se a borda do envio errar, o pedido
// vai com uma cor num campo de URL — que o servidor recusa — ou com as duas
// capas gravadas ao mesmo tempo, e aí "qual vale?" passa a depender de quem
// desenha.

import { describe, expect, it, vi } from "vitest";
import { CORES_DE_CAPA, NANO_BLUE, ehCorDeCapa } from "@plane/constants";
import { EFileAssetType } from "@plane/types";

vi.mock("@/services/file.service", () => ({ FileService: class {} }));

const { getCoverImageType, handleCoverImageChange, capaDe } = await import("@/helpers/cover-image.helper");

const envio = { entityIdentifier: "", entityType: EFileAssetType.PROJECT_COVER, workspaceSlug: "evolury" };

describe("o que conta como cor", () => {
  it("aceita a forma exata, e só ela", () => {
    expect(ehCorDeCapa("#0C91EB")).toBe(true);
    expect(ehCorDeCapa("#0c91eb")).toBe(true);
    expect(ehCorDeCapa("#fff")).toBe(false);
    expect(ehCorDeCapa("red")).toBe(false);
    expect(ehCorDeCapa(null)).toBe(false);
  });

  it("recusa CSS disfarçado de cor — o valor vai para um `style`", () => {
    expect(ehCorDeCapa("#fff);background-image:url(https://exemplo.invalido/x.png")).toBe(false);
  });

  it("cor não é confundida com endereço", () => {
    expect(getCoverImageType("#0C91EB")).toBe("color");
    expect(getCoverImageType("https://images.unsplash.com/photo-1")).toBe("unsplash");
  });
});

describe("o envio separa cor de imagem", () => {
  it("escolher cor grava a cor e apaga a imagem", async () => {
    const payload = await handleCoverImageChange(undefined, "#0c91eb", envio);
    expect(payload).toEqual({
      cover_color: "#0C91EB",
      cover_image: null,
      cover_image_url: null,
      cover_image_asset: null,
    });
  });

  it("escolher imagem apaga a cor — capa é uma coisa só", async () => {
    const payload = await handleCoverImageChange("#0C91EB", "https://exemplo.invalido/capa.jpg", envio);
    expect(payload?.cover_color).toBeNull();
    expect(payload?.cover_image_url).toBe("https://exemplo.invalido/capa.jpg");
  });

  it("limpar a capa limpa as duas", async () => {
    const payload = await handleCoverImageChange("#0C91EB", null, envio);
    expect(payload).toEqual({
      cover_image: null,
      cover_image_url: null,
      cover_image_asset: null,
      cover_color: null,
    });
  });

  it("cor não sobe arquivo nenhum", async () => {
    // `uploadCoverImage` faz `fetch` da imagem; se a cor entrasse no caminho de
    // upload, este teste estouraria em vez de devolver o payload.
    const buscar = vi.fn();
    vi.stubGlobal("fetch", buscar);
    await handleCoverImageChange(undefined, "#166534", envio);
    expect(buscar).not.toHaveBeenCalled();
    vi.unstubAllGlobals();
  });
});

describe("qual capa vale", () => {
  it("cor preenchida manda sobre imagem", () => {
    expect(capaDe({ cover_color: "#166534", cover_image_url: "https://exemplo.invalido/x.jpg" })).toBe("#166534");
  });

  it("sem cor, vale a imagem", () => {
    expect(capaDe({ cover_color: null, cover_image_url: "https://exemplo.invalido/x.jpg" })).toBe(
      "https://exemplo.invalido/x.jpg"
    );
  });

  it("sem nada, é indefinido — quem pinta o azul da marca é a tela", () => {
    expect(capaDe({})).toBeUndefined();
    expect(capaDe(null)).toBeUndefined();
  });
});

describe("a paleta", () => {
  it("começa pelo azul da marca", () => {
    expect(CORES_DE_CAPA[0].hex).toBe(NANO_BLUE);
  });

  it("só tem cores na forma exata, e nenhuma repetida", () => {
    const hexes = CORES_DE_CAPA.map((c) => c.hex);
    hexes.forEach((hex) => expect(ehCorDeCapa(hex)).toBe(true));
    expect(new Set(hexes).size).toBe(hexes.length);
  });

  it("carrega chave, e nunca o nome pronto (ADR 0008)", () => {
    CORES_DE_CAPA.forEach((cor) => expect(cor.i18n_nome).toMatch(/^colors\./));
  });
});
