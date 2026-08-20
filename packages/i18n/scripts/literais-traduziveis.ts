/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: acha texto em inglês no código que JÁ TEM tradução pronta.
//
// Por que existe: os outros dois scripts cuidam das chaves. O `sync-check`
// compara os idiomas entre si; o `chaves-usadas` acha chave que o código pede e
// o pt-BR não tem. Nenhum dos dois vê o defeito mais comum aqui — a tradução
// existe, está correta, e o componente simplesmente não a consulta.
//
// A medição que motivou o script: 5468 chaves no pt-BR, apenas 2% idênticas ao
// inglês (nomes próprios), e ainda assim ciclos, analytics e estimativas
// apareciam em inglês na tela. O texto não faltava; faltava ser lido.
//
// A prova é IGUALDADE EXATA contra os valores do `en`, e não heurística de "isto
// parece inglês". É o mesmo princípio que o `chaves-usadas` registra: falso
// positivo em verificação automática é o que ensina a ignorá-la. Se o literal
// bate letra por letra com algo que já traduzimos, não há dúvida a resolver.
//
// O que NÃO faz: achar inglês que nunca teve chave. Para esse não existe prova
// automática — "Status of the cycle" e um identificador interno têm a mesma
// cara para um script. Esse caso continua sendo trabalho de quem olha a tela.
//
// Uso:
//   tsx packages/i18n/scripts/literais-traduziveis.ts        # relatório
//   tsx packages/i18n/scripts/literais-traduziveis.ts --ci   # sai 1 se achar

import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative } from "node:path";

const RAIZ = join(import.meta.dirname, "../../..");
const LOCALE_EN = join(RAIZ, "packages/i18n/src/locales/en");
const ONDE_PROCURAR = [
  "apps/web/core",
  "apps/web/app",
  "packages/constants/src",
  "packages/propel/src",
  "packages/ui/src",
];
const EXTENSOES = [".ts", ".tsx"];

/** Storybook, listas de ícone e testes não viram tela de usuário. */
const IGNORAR = [
  ".stories.",
  "/icons.ts",
  "lucide-icons",
  "/tests/",
  ".test.",
  "/dist/",
  // Evolury (20/08/2026): a comparação de planos herdada vende os planos pagos
  // da NUVEM do Plane, que não existem neste fork. As 69 strings dela vivem em
  // `comparison/plans.tsx`, o arquivo que será substituído quando a página de
  // planos da Evolury for construída — traduzi-las agora é trabalho jogado
  // fora. O chassi (tabela, coluna, alternador) fica e será reaproveitado.
  // Esta exclusão sai junto com o conteúdo novo.
  "/workspace/billing/",
  // Catálogo de ilustrações do Storybook: o `title` de cada entrada é a
  // legenda da vitrine, e o único consumidor é `assets-showcase.stories.tsx`.
  // Não chega a nenhuma tela de usuário.
  "/empty-state/assets/",
  // Constantes de dashboard herdadas do upstream: `DURATION_FILTER_OPTIONS`,
  // `FILTERED_ISSUES_TABS_LIST` e `UNFILTERED_ISSUES_TABS_LIST` não têm
  // consumidor vivo — o único helper que lê a primeira também não é importado
  // por ninguém. Traduzir texto morto é trabalho jogado fora, e editar o
  // arquivo cria conflito de sincronização com o upstream sem ganho nenhum.
  // Conferido em 20/08/2026.
  "constants/src/dashboard.ts",
  // Nomes de ícone do Material Symbols: `name: "delete"` é o identificador do
  // desenho, não um rótulo. Par de `lucide-icons`, logo acima.
  "material-icons",
  // Tamanhos de papel — "Letter", "Legal", "Tabloid", "A4". São formatos, e o
  // "Legal" daqui não tem relação com o "Jurídico" que a chave homônima
  // traduz. Traduzi-los tornaria a lista errada.
  "export-page-modal",
];

/**
 * Texto que fica em inglês de propósito.
 *
 * Curta e comentada por regra: lista de exceção que cresce sem justificativa
 * vira o lugar onde o problema se esconde.
 */
const NOMES_PROPRIOS = new Set([
  "Evotask", // o produto
  "Fibonacci", // o matemático — o pt-BR também diz "Fibonacci"
  "Linear", // idem: a sequência linear se chama assim nos dois idiomas
  "T-Shirt Sizes", // a técnica, conhecida por este nome
]);

/** Todos os textos que já existem traduzidos, na forma como o inglês os escreve. */
function textosTraduzidos(): Set<string> {
  const valores = new Set<string>();
  const achatar = (obj: unknown) => {
    if (typeof obj !== "object" || obj === null) return;
    for (const v of Object.values(obj)) {
      if (typeof v === "object" && v !== null) achatar(v);
      else if (typeof v === "string" && v.trim().length >= 3) valores.add(v.trim());
    }
  };
  for (const arquivo of readdirSync(LOCALE_EN)) {
    if (!arquivo.endsWith(".json")) continue;
    achatar(JSON.parse(readFileSync(join(LOCALE_EN, arquivo), "utf8")));
  }
  return valores;
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

/**
 * Onde um literal de fato vira tela: rótulo de objeto de configuração,
 * propriedade de componente, ou texto solto no JSX.
 */
const PADROES: RegExp[] = [
  /\b(?:label|title|placeholder|tooltipContent|heading|buttonText|name|text)\s*:\s*"([^"\n]{3,70})"/g,
  /\b(?:label|title|placeholder|tooltipContent|text)\s*=\s*"([^"\n]{3,70})"/g,
  />\s*([A-Z][a-z]+(?:[ \w'/-]{0,60}?))\s*</g,
];

type Achado = { arquivo: string; linha: number; texto: string };

/**
 * Apaga comentários preservando o comprimento do arquivo.
 *
 * Preservar o comprimento importa: o número da linha sai de contar quebras até
 * o índice do casamento, e substituir por vazio deslocaria todos os números
 * depois do primeiro comentário.
 *
 * Existe porque código comentado é o falso positivo mais comum aqui — em
 * `constants/src/auth/index.ts`, três dos quatro rótulos estavam dentro de um
 * bloco desativado. Denunciar texto que não roda é o começo do fim de uma
 * verificação: ela vira ruído e ninguém mais lê.
 */
function semComentarios(fonte: string): string {
  return fonte
    .replace(/\/\*[\s\S]*?\*\//g, (m) => m.replace(/[^\n]/g, " "))
    .replace(/^([^\n"'`]*?)\/\/[^\n]*/gm, (_m, antes: string) => antes + " ".repeat(_m.length - antes.length));
}

function main() {
  const traduzidos = textosTraduzidos();
  const achados: Achado[] = [];

  for (const raiz of ONDE_PROCURAR) {
    for (const arquivo of arquivos(join(RAIZ, raiz))) {
      const curto = relative(RAIZ, arquivo);
      if (IGNORAR.some((x) => curto.includes(x)) || curto.endsWith(".d.ts")) continue;
      const fonte = semComentarios(readFileSync(arquivo, "utf8"));
      const vistos = new Set<number>();
      for (const padrao of PADROES) {
        for (const m of fonte.matchAll(padrao)) {
          const texto = m[1]?.trim() ?? "";
          if (!texto || vistos.has(m.index)) continue;
          if (!traduzidos.has(texto) || NOMES_PROPRIOS.has(texto)) continue;
          vistos.add(m.index);
          achados.push({ arquivo: curto, linha: fonte.slice(0, m.index).split("\n").length, texto });
        }
      }
    }
  }

  console.log(`Textos traduzidos conhecidos: ${traduzidos.size}`);
  if (achados.length === 0) {
    console.log("Nenhum literal em inglês com tradução pronta no código.");
    return;
  }

  console.log(`\n${achados.length} literal(is) em inglês com tradução JÁ PRONTA:\n`);
  const porArquivo = new Map<string, Achado[]>();
  for (const a of achados) porArquivo.set(a.arquivo, [...(porArquivo.get(a.arquivo) ?? []), a]);
  for (const [arquivo, itens] of [...porArquivo].sort((a, b) => b[1].length - a[1].length)) {
    console.log(`  ${arquivo}`);
    for (const i of itens) console.log(`    ${i.linha}: ${i.texto}`);
  }
  console.log("\nA tradução existe — troque o literal pela chave correspondente.");
  if (process.argv.includes("--ci")) process.exit(1);
}

main();
