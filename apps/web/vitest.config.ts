/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: o `apps/web` não tinha runner de teste nenhum.
//
// Dois defeitos de interface corrigidos em 17/08/2026 — o cartão de condição
// que abria vazio e a criação rápida que engolia a mensagem do servidor — foram
// verificados dirigindo o navegador à mão. Isso prova a correção uma vez e não
// protege dela voltar: nada na CI reexecuta um navegador.
//
// Configuração separada do `vite.config.ts` de propósito: aquele carrega o
// `reactRouter()`, que espera o servidor de desenvolvimento e atrapalha em teste.

import path from "node:path";
import { defineConfig } from "vitest/config";
import tsconfigPaths from "vite-tsconfig-paths";

export default defineConfig({
  plugins: [tsconfigPaths({ projects: [path.resolve(__dirname, "tsconfig.json")] })],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./tests/setup.ts"],
    include: ["tests/**/*.test.ts", "tests/**/*.test.tsx"],
  },
});
