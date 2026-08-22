/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// O formato de placeholder desta base é ICU com chave simples — `{data}`.
//
// Este teste existe porque o erro aconteceu: a tela de faturamento nasceu com
// `{{data}}`, no formato do i18next puro. Tudo passou — tipos, lint, testes de
// unidade, testes de contrato — e a tela mostrou, literalmente, "Em dia até
// {{data}}". Nenhuma camada automática viu, porque o texto **existe** e a chave
// **é encontrada**; só a substituição não acontece.
//
// A prova é boba e é exatamente por isso que funciona: chave dupla não é
// sintaxe válida aqui, em nenhum idioma, em nenhum arquivo.

import { readFileSync, readdirSync } from "node:fs";
import { join, resolve } from "node:path";
import { describe, expect, it } from "vitest";

const raiz = resolve(process.cwd(), "..", "..");
const locales = join(raiz, "packages/i18n/src/locales");

const idiomas = readdirSync(locales);

// A única exceção, e ela é real: em `automation.json` a chave dupla é a
// **sintaxe do produto** — o texto ensina a escrever `{{tarefa}}` dentro do
// comentário de uma automação (ver `plane/utils/automacoes/variaveis.py`).
// Não é placeholder de tradução; é exemplo de uso.
const EXCECOES = new Set(["automation.json"]);

describe("placeholders das traduções", () => {
  it("os idiomas estão onde este teste espera", () => {
    // Guarda contra o modo de falha mais silencioso: a pasta mudar de lugar,
    // a varredura não achar nada e o teste passar sem conferir coisa alguma.
    expect(idiomas).toContain("pt-BR");
    expect(idiomas).toContain("en");
  });

  it.each(idiomas)("%s não usa chave dupla como placeholder", (idioma) => {
    const pasta = join(locales, idioma);
    const suspeitos: string[] = [];

    for (const arquivo of readdirSync(pasta).filter((nome) => nome.endsWith(".json"))) {
      if (EXCECOES.has(arquivo)) continue;
      const conteudo = readFileSync(join(pasta, arquivo), "utf8");
      // `{{nome}}` — abre e fecha duplo — é a forma do i18next puro, que esta
      // base não usa. Note que `other {{count} …}` NÃO casa: ali o duplo vem
      // do aninhamento de plural do ICU, e fecha simples.
      const achados = conteudo.match(/\{\{\s*\w+\s*\}\}/g);
      if (achados) suspeitos.push(`${arquivo}: ${achados.join(", ")}`);
    }

    expect(suspeitos).toEqual([]);
  });
});
