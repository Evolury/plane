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

import { execFileSync } from "node:child_process";
import { existsSync } from "node:fs";
import { join, resolve } from "node:path";
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

// O avatar sem foto tem um componente só — <Avatar> —, mas nem toda tela o usa:
// a lista de primeiros passos do Início desenhava o círculo à mão, com o
// verde-azulado cravado, e continuou verde depois que o padrão virou azul. Foi
// achado no bundle já publicado, e não na revisão; esta varredura é o que faz o
// próximo aparecer antes.
describe("o verde-azulado antigo não voltou", () => {
  it("nenhuma tela crava #028375", () => {
    // `import.meta.url` aqui vem como `/@fs/...`, do servidor do Vite, e não
    // como caminho de disco — foi o que fez a primeira versão desta varredura
    // procurar num diretório inexistente e passar sempre. A raiz vem do
    // `process.cwd()` (o `apps/web`), e a asserção do `.git` é o que impede a
    // varredura de voltar a ser vazia em silêncio.
    const raiz = resolve(process.cwd(), "..", "..");
    expect(existsSync(join(raiz, ".git"))).toBe(true);

    // `git grep` em vez de varrer o disco: ignora node_modules, .next e build
    // de graça, e só enxerga o que está versionado.
    let saida = "";
    try {
      saida = execFileSync(
        "git",
        ["grep", "-lni", "028375", "--", "apps/web/core", "apps/web/app", "packages/ui/src", "packages/propel/src"],
        { cwd: raiz, encoding: "utf8" }
      );
    } catch (erro: unknown) {
      // `git grep` sai com 1 quando não acha nada, que é o desfecho esperado.
      // Qualquer outra falha — git ausente, diretório errado — não pode passar
      // por "está limpo".
      const status = (erro as { status?: number })?.status;
      if (status !== 1) throw erro;
    }
    // O comentário histórico em avatar.tsx cita a cor para dizer que ela saiu.
    const arquivos = saida.split("\n").filter((f) => f && !f.endsWith("packages/ui/src/avatar/avatar.tsx"));
    expect(arquivos).toEqual([]);
  });
});
