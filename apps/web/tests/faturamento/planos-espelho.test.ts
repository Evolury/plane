/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// O catálogo existe em dois lugares, e é por isso que este teste existe.
//
// O servidor cobra pelo que está em `apps/api/plane/utils/planos.py`; a tela
// vende o que está em `packages/constants/src/planos.ts`. Dois arquivos são
// dois lugares para o número divergir, e preço divergente é o pior tipo de bug
// de cobrança: o cliente vê um valor e é debitado outro.
//
// Em vez de confiar na disciplina de quem edita, este teste **lê o arquivo
// Python** e compara campo a campo. Mudar um preço de um lado só reprova aqui.

import { existsSync, readFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { AVANCADO, ESSENCIAL, ORDEM_DOS_PLANOS, PLANOS, PROFISSIONAL } from "@plane/constants";

const raiz = resolve(process.cwd(), "..", "..");
const caminhoDoServidor = join(raiz, "apps/api/plane/utils/planos.py");

/** Lê um campo numérico de um bloco `Plano(...)` do catálogo Python. */
function campo(fonte: string, chave: string, nome: string): number | null {
  const bloco = fonte.split(`chave=${chave.toUpperCase()},`)[1];
  if (!bloco) throw new Error(`Plano ${chave} não encontrado no catálogo do servidor`);
  const trecho = bloco.split("),")[0];
  const achado = trecho.match(new RegExp(`${nome}=(None|\\d+)`));
  if (!achado) throw new Error(`Campo ${nome} não encontrado no plano ${chave}`);
  return achado[1] === "None" ? null : Number(achado[1]);
}

function limite(fonte: string, chave: string, nome: string): number | null {
  const bloco = fonte.split(`chave=${chave.toUpperCase()},`)[1];
  const trecho = bloco.split("limites={")[1].split("}")[0];
  const achado = trecho.match(new RegExp(`${nome}: (None|\\d+)`));
  if (!achado) throw new Error(`Limite ${nome} não encontrado no plano ${chave}`);
  return achado[1] === "None" ? null : Number(achado[1]);
}

function recurso(fonte: string, chave: string, nome: string): boolean {
  const bloco = fonte.split(`chave=${chave.toUpperCase()},`)[1];
  const trecho = bloco.split("recursos={")[1].split("}")[0];
  const achado = trecho.match(new RegExp(`${nome}: (True|False)`));
  if (!achado) throw new Error(`Recurso ${nome} não encontrado no plano ${chave}`);
  return achado[1] === "True";
}

describe("o catálogo da tela é espelho do catálogo do servidor", () => {
  it("o arquivo do servidor está onde este teste espera", () => {
    // Guarda contra o modo de falha mais silencioso possível: o arquivo mudar
    // de lugar, a leitura falhar e o teste passar sem comparar nada.
    expect(existsSync(caminhoDoServidor)).toBe(true);
  });

  const fonte = existsSync(caminhoDoServidor) ? readFileSync(caminhoDoServidor, "utf8") : "";

  it.each([ESSENCIAL, PROFISSIONAL, AVANCADO])("%s: preço, assentos e adicional batem", (chave) => {
    const daTela = PLANOS[chave];
    expect(daTela.mensal).toBe(campo(fonte, chave, "mensal"));
    expect(daTela.assentos).toBe(campo(fonte, chave, "assentos"));
    expect(daTela.adicionalMensal).toBe(campo(fonte, chave, "adicional_mensal"));
    expect(daTela.convidadosPorAssento).toBe(campo(fonte, chave, "convidados_por_assento"));
  });

  it.each([ESSENCIAL, PROFISSIONAL, AVANCADO])("%s: recursos e limites batem", (chave) => {
    const daTela = PLANOS[chave];
    expect(daTela.recursos.analytics).toBe(recurso(fonte, chave, "RECURSO_ANALYTICS"));
    expect(daTela.recursos.api_publica).toBe(recurso(fonte, chave, "RECURSO_API_PUBLICA"));
    expect(daTela.recursos.webhooks).toBe(recurso(fonte, chave, "RECURSO_WEBHOOKS"));
    expect(daTela.limites.propriedades_por_projeto).toBe(limite(fonte, chave, "LIMITE_PROPRIEDADES"));
    expect(daTela.limites.automacoes_ativas).toBe(limite(fonte, chave, "LIMITE_AUTOMACOES"));
  });

  it("os três planos, na mesma ordem", () => {
    expect([...ORDEM_DOS_PLANOS]).toEqual([ESSENCIAL, PROFISSIONAL, AVANCADO]);
    expect(fonte).toContain("ORDEM = (ESSENCIAL, PROFISSIONAL, AVANCADO)");
  });

  it("o anual custa dez mensalidades dos dois lados", () => {
    expect(fonte).toContain("MESES_DO_CICLO_ANUAL = 10");
  });
});
