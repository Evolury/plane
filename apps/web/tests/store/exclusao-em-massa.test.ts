/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: as contas da exclusão em massa (ADR 0018).
//
// A tela não é a guarda — o servidor recusa o pedido inteiro se alguma tarefa
// não for de quem pediu. O que estas funções decidem é o que a barra OFERECE, e
// errar aqui não dá erro: dá um botão que promete e falha, ou um botão que some
// para quem tinha direito a ele.

import { describe, expect, it } from "vitest";
import type { TIssue } from "@plane/types";
import {
  TETO_DE_EXCLUSAO_EM_MASSA,
  agruparPorProjeto,
  passouDoTeto,
  podeExcluir,
  separarElegiveis,
} from "@/components/issues/bulk-operations/exclusao";

const tarefa = (id: string, project_id: string | null, created_by: string) =>
  ({ id, project_id, created_by }) as TIssue;

const NINGUEM_E_ADMIN = { usuarioId: "eu", ehAdminEm: () => false };

describe("quem pode excluir", () => {
  it("administrador do projeto exclui o que não é dele", () => {
    const permissao = { usuarioId: "eu", ehAdminEm: () => true };
    expect(podeExcluir(tarefa("1", "p1", "outra-pessoa"), permissao)).toBe(true);
  });

  it("membro exclui o que criou", () => {
    expect(podeExcluir(tarefa("1", "p1", "eu"), NINGUEM_E_ADMIN)).toBe(true);
  });

  it("membro não exclui o que é de outra pessoa", () => {
    expect(podeExcluir(tarefa("1", "p1", "outra-pessoa"), NINGUEM_E_ADMIN)).toBe(false);
  });

  it("sem usuário conhecido, ninguém exclui nada", () => {
    const permissao = { usuarioId: undefined, ehAdminEm: () => false };
    expect(podeExcluir(tarefa("1", "p1", "eu"), permissao)).toBe(false);
  });

  it("ser administrador é por PROJETO, e a seleção atravessa projetos", () => {
    // O caso de "Minhas tarefas": administradora num projeto, membro no outro.
    const permissao = { usuarioId: "eu", ehAdminEm: (p: string | undefined | null) => p === "p1" };
    expect(podeExcluir(tarefa("1", "p1", "outra-pessoa"), permissao)).toBe(true);
    expect(podeExcluir(tarefa("2", "p2", "outra-pessoa"), permissao)).toBe(false);
  });
});

describe("a separação do que dá para excluir", () => {
  it("separa sem perder nenhuma", () => {
    const minhas = [tarefa("1", "p1", "eu"), tarefa("2", "p1", "eu")];
    const alheia = tarefa("3", "p1", "outra-pessoa");
    const { elegiveis, bloqueadas } = separarElegiveis([...minhas, alheia], NINGUEM_E_ADMIN);
    expect(elegiveis).toEqual(minhas);
    expect(bloqueadas).toEqual([alheia]);
  });
});

describe("um pedido por projeto", () => {
  it("agrupa pelas tarefas de cada projeto", () => {
    const grupos = agruparPorProjeto([tarefa("1", "p1", "eu"), tarefa("2", "p2", "eu"), tarefa("3", "p1", "eu")]);
    expect(grupos).toEqual({ p1: ["1", "3"], p2: ["2"] });
  });

  it("tarefa sem projeto fica de fora — não há endpoint para onde mandá-la", () => {
    expect(agruparPorProjeto([tarefa("1", null, "eu")])).toEqual({});
  });
});

describe("o teto", () => {
  const muitas = (quantas: number, projeto: string) =>
    Array.from({ length: quantas }, (_, i) => tarefa(`${projeto}-${i}`, projeto, "eu"));

  it("é por projeto, e não pela soma", () => {
    // Dois projetos com metade do teto cada: o total passa, cada pedido não.
    const grupos = agruparPorProjeto([
      ...muitas(TETO_DE_EXCLUSAO_EM_MASSA, "p1"),
      ...muitas(TETO_DE_EXCLUSAO_EM_MASSA, "p2"),
    ]);
    expect(passouDoTeto(grupos)).toBe(false);
  });

  it("acusa quando um projeto passa sozinho", () => {
    const grupos = agruparPorProjeto(muitas(TETO_DE_EXCLUSAO_EM_MASSA + 1, "p1"));
    expect(passouDoTeto(grupos)).toBe(true);
  });
});
