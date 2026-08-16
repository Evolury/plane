/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: acha chave de tradução que o código usa e o pt-BR não tem.
//
// Por que existe: o `sync-check` compara os idiomas ENTRE SI. Ele pega chave
// que falta num idioma e sobra no outro — e não pega a que não existe em lugar
// nenhum. Essa aparece na tela como o próprio identificador ("common.save"),
// sem quebrar nada, sem alarme em teste, sem erro de compilação. Já aconteceu
// aqui, e só foi descoberto olhando a tela.
//
// O que faz: varre as chamadas de tradução no código, resolve o prefixo quando
// ele é constante, e confere cada chave contra o pt-BR — o idioma do produto
// (ADR 0004).
//
// O que NÃO faz: chave montada em tempo de execução (`t(\`tipo.${x}\`)`) é
// ignorada de propósito. Tentar adivinhar o valor daria falso positivo, e
// falso positivo em verificação automática é o que ensina a ignorá-la.
//
// Uso:
//   tsx packages/i18n/scripts/chaves-usadas.ts        # relatório
//   tsx packages/i18n/scripts/chaves-usadas.ts --ci   # sai 1 se faltar chave

import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative } from "node:path";

const RAIZ = join(import.meta.dirname, "../../..");
const LOCALE_PT = join(RAIZ, "packages/i18n/src/locales/pt-BR");
const ONDE_PROCURAR = ["apps/web/core", "apps/space/core", "apps/admin/core", "packages/propel/src", "packages/ui/src"];
const EXTENSOES = [".ts", ".tsx"];

/** Todas as chaves do pt-BR, achatadas em "a.b.c". */
function chavesDoIdioma(): Set<string> {
  const chaves = new Set<string>();
  const achatar = (obj: unknown, prefixo: string) => {
    if (typeof obj !== "object" || obj === null) return;
    for (const [k, v] of Object.entries(obj)) {
      const caminho = prefixo ? `${prefixo}.${k}` : k;
      if (typeof v === "object" && v !== null) achatar(v, caminho);
      else chaves.add(caminho);
    }
  };
  for (const arquivo of readdirSync(LOCALE_PT)) {
    if (!arquivo.endsWith(".json")) continue;
    achatar(JSON.parse(readFileSync(join(LOCALE_PT, arquivo), "utf8")), "");
  }
  return chaves;
}

function arquivos(dir: string): string[] {
  const saida: string[] = [];
  const caminhar = (d: string) => {
    for (const nome of readdirSync(d)) {
      const p = join(d, nome);
      if (nome === "node_modules" || nome.startsWith(".")) continue;
      if (statSync(p).isDirectory()) caminhar(p);
      else if (EXTENSOES.some((e) => nome.endsWith(e))) saida.push(p);
    }
  };
  try {
    caminhar(dir);
  } catch {
    // diretório que não existe neste recorte do repositório
  }
  return saida;
}

const USO_DIRETO = /\bt\(\s*"([a-z0-9_]+(?:\.[a-z0-9_]+)+)"/gi;

function main() {
  const conhecidas = chavesDoIdioma();
  const faltando = new Map<string, string[]>();

  for (const raiz of ONDE_PROCURAR) {
    for (const arquivo of arquivos(join(RAIZ, raiz))) {
      const fonte = readFileSync(arquivo, "utf8");
      for (const [, chave] of fonte.matchAll(USO_DIRETO)) {
        if (conhecidas.has(chave)) continue;
        const onde = faltando.get(chave) ?? [];
        onde.push(relative(RAIZ, arquivo));
        faltando.set(chave, onde);
      }
    }
  }

  console.log(`Chaves no pt-BR: ${conhecidas.size}`);
  if (faltando.size === 0) {
    console.log("Nenhuma chave usada no código está faltando no pt-BR.");
    return;
  }

  console.log(`\n${faltando.size} chave(s) usada(s) no código e ausente(s) no pt-BR:\n`);
  for (const [chave, onde] of faltando) {
    console.log(`  ${chave}`);
    for (const arquivo of onde.slice(0, 3)) console.log(`    ${arquivo}`);
  }
  console.log("\nNa tela, cada uma aparece como o próprio identificador.");
  if (process.argv.includes("--ci")) process.exit(1);
}

main();
