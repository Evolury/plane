/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/**
 * A revalidação em segundo plano não apaga o quadro.
 *
 * Toda busca de tarefas chama `clear()` antes de ir ao servidor. Na primeira
 * carga faz sentido — não há o que mostrar. Numa revalidação, não: o aviso de
 * tempo real de "tarefa criada" (ADR 0013) dispara uma rebusca da lista, e o
 * `clear` apagava os cartões que já estavam na tela.
 *
 * Medido em produção em 22/08/2026, criando uma tarefa pelo quadro:
 *
 *     t+600ms   10 cartões,  0 esqueletos
 *     t+1200ms   0 cartões, 24 esqueletos   ← o quadro sumia
 *     t+1800ms  10 cartões,  0 esqueletos
 *
 * O que este arquivo prende é o par: **a revalidação preserva** e **a primeira
 * carga continua limpando**. A segunda metade importa tanto quanto a primeira —
 * parar de limpar sempre deixaria a tela mostrar o quadro do projeto anterior
 * enquanto o novo carrega.
 */

import { describe, expect, it } from "vitest";

/**
 * O `clear` real, copiado da classe base. Instanciar o store de verdade
 * arrastaria MobX, serviços e o store raiz inteiro para um teste sobre quatro
 * atribuições — e o que se quer prender aqui é a REGRA, não a fiação.
 *
 * Se a implementação divergir, o `check:types` não avisa. Por isso o teste
 * seguinte compara o texto do arquivo com esta cópia.
 */
class QuadroFalso {
  groupedIssueIds: unknown = { grupo: ["a", "b"] };
  issuePaginationData: Record<string, unknown> = { grupo: {} };
  groupedIssueCount: Record<string, number> = { grupo: 2 };
  paginationOptions: unknown = { perPageCount: 30 };
  abortou = 0;

  clear(shouldClearPaginationOptions = true, shouldClearGroupedIds = true) {
    if (shouldClearGroupedIds) {
      this.groupedIssueIds = undefined;
      this.issuePaginationData = {};
      this.groupedIssueCount = {};
    }
    if (shouldClearPaginationOptions) {
      this.paginationOptions = undefined;
    }
    this.abortou += 1;
  }
}

describe("revalidação do quadro", () => {
  it("preserva os cartões quando a paginação já existe", () => {
    const q = new QuadroFalso();
    const jaTemPaginacao = true;
    q.clear(!jaTemPaginacao, !jaTemPaginacao);

    expect(q.groupedIssueIds).toEqual({ grupo: ["a", "b"] });
    expect(q.groupedIssueCount).toEqual({ grupo: 2 });
    expect(q.paginationOptions).toEqual({ perPageCount: 30 });
  });

  it("limpa tudo na primeira carga", () => {
    const q = new QuadroFalso();
    const jaTemPaginacao = false;
    q.clear(!jaTemPaginacao, !jaTemPaginacao);

    expect(q.groupedIssueIds).toBeUndefined();
    expect(q.groupedIssueCount).toEqual({});
    expect(q.paginationOptions).toBeUndefined();
  });

  it("cancela a requisição anterior nos dois casos", () => {
    const revalidando = new QuadroFalso();
    revalidando.clear(false, false);
    expect(revalidando.abortou).toBe(1);

    const primeira = new QuadroFalso();
    primeira.clear(true, true);
    expect(primeira.abortou).toBe(1);
  });
});

describe("a cópia não pode divergir do original", () => {
  // `import.meta.url` não é URL de arquivo sob o vitest deste app — o caminho
  // sai da raiz de execução, que é `apps/web`.
  const raiz = "core/store/issue";

  it("o `clear` da classe base tem os dois eixos, e o da lista é condicional", async () => {
    const { readFileSync } = await import("node:fs");
    const { join } = await import("node:path");
    const fonte = readFileSync(join(raiz, "helpers/base-issues.store.ts"), "utf8");

    expect(fonte).toContain("clear(shouldClearPaginationOptions = true, shouldClearGroupedIds = true)");
    expect(fonte).toContain("if (shouldClearGroupedIds) {");
    // O abort fica FORA de qualquer condição: cancelar a requisição anterior
    // vale para os dois caminhos.
    const corpo = fonte.slice(fonte.indexOf("clear(shouldClearPaginationOptions = true"));
    const ateOFim = corpo.slice(0, corpo.indexOf("\n  }"));
    expect(ateOFim).toContain("this.controller.abort();");
  });

  it("todos os stores passam os dois argumentos", async () => {
    const { readdirSync, readFileSync, statSync } = await import("node:fs");
    const { join } = await import("node:path");
    const arquivos: string[] = [];
    const varrer = (dir: string) => {
      for (const nome of readdirSync(dir)) {
        const alvo = join(dir, nome);
        if (statSync(alvo).isDirectory()) varrer(alvo);
        else if (nome.endsWith(".ts")) arquivos.push(readFileSync(alvo, "utf8"));
      }
    };
    varrer(raiz);

    const comUmArgumentoSo = arquivos.filter((f) => f.includes("this.clear(!isExistingPaginationOptions)"));
    expect(comUmArgumentoSo).toHaveLength(0);

    const comOsDois = arquivos.filter((f) =>
      f.includes("this.clear(!isExistingPaginationOptions, !isExistingPaginationOptions)")
    );
    // Oito quadros: projeto, ciclo, módulo, visão, perfil, espaço, arquivadas e
    // minhas tarefas. Se um novo aparecer sem os dois argumentos, este número
    // deixa de bater e o quadro dele volta a piscar.
    expect(comOsDois).toHaveLength(8);
  });
});
