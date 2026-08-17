/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: `/convert-document/` é servidor-a-servidor (revisão do upstream, 16/08/2026).
//
// Antes desta guarda, o endpoint respondia a qualquer um na internet — comprovado
// em produção com um POST anônimo chegando até a validação de esquema. Conversão
// HTML→Y.js é cara, e era processamento de graça para quem quisesse.
//
// O teste olha os METADADOS do decorator, e não uma resposta HTTP, porque o que
// pode regredir aqui é exatamente alguém remover a linha `@Middleware(...)`. Uma
// chamada de rede provaria menos e quebraria por dez outros motivos.

// `reflect-metadata` estende o `Reflect` global. Ele chega em tempo de execução
// pelo @plane/decorators, mas o compilador precisa vê-lo declarado aqui — por
// isso o import explícito e a dependência de desenvolvimento no package.json.
import "reflect-metadata";
import { describe, expect, it } from "vitest";
import { DocumentController } from "@/controllers/document.controller";
import { requireSecretKey } from "@/lib/auth-middleware";

describe("DocumentController", () => {
  it("exige a chave de servidor em /convert-document/", () => {
    const middlewares = Reflect.getMetadata("middlewares", DocumentController.prototype, "convertDocument") ?? [];

    expect(middlewares).toContain(requireSecretKey);
  });
});

describe("requireSecretKey", () => {
  const resposta = () => {
    const r: { codigo?: number; corpo?: unknown } = {};
    return {
      r,
      status(codigo: number) {
        r.codigo = codigo;
        return this;
      },
      json(corpo: unknown) {
        r.corpo = corpo;
        return this;
      },
    };
  };

  it("recusa sem a chave", () => {
    const res = resposta();
    let seguiu = false;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    requireSecretKey({ headers: {}, path: "/", method: "POST" } as any, res as any, () => {
      seguiu = true;
    });

    expect(seguiu).toBe(false);
    expect(res.r.codigo).toBe(401);
  });

  it("recusa com a chave errada", () => {
    const res = resposta();
    let seguiu = false;
    requireSecretKey(
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      { headers: { "live-server-secret-key": "chute" }, path: "/", method: "POST" } as any,
      res as any,
      () => {
        seguiu = true;
      }
    );

    expect(seguiu).toBe(false);
    expect(res.r.codigo).toBe(401);
  });
});
