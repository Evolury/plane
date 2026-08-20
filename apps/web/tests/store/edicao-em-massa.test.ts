/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: as contas do preenchimento em massa (ADR 0019).
//
// Duas delas decidem se o painel mente. `projetoUnico` diz quais campos podem
// ser oferecidos — oferecer estado numa seleção que atravessa projetos manda o
// estado do projeto A para a tarefa do B, e o servidor recusa tudo. E
// `valorComum` decide se o campo abre em "Vários" — abrir com o valor da
// primeira tarefa é como se apaga o das outras sem perceber.

import { describe, expect, it } from "vitest";
import type { TIssue } from "@plane/types";
import {
  MODO_PADRAO,
  datasDoRascunhoSaoCoerentes,
  podeEditar,
  projetoUnico,
  quantasMudancas,
  separarEditaveis,
  valorComum,
} from "@/components/issues/bulk-operations/edicao";

const tarefa = (id: string, project_id: string | null, extras: Partial<TIssue> = {}) =>
  ({ id, project_id, ...extras }) as TIssue;

describe("o projeto da seleção", () => {
  it("é o projeto quando todas são dele", () => {
    expect(projetoUnico([tarefa("1", "p1"), tarefa("2", "p1")])).toBe("p1");
  });

  it("é indefinido quando a seleção atravessa projetos", () => {
    expect(projetoUnico([tarefa("1", "p1"), tarefa("2", "p2")])).toBeUndefined();
  });

  it("é indefinido quando não há seleção", () => {
    expect(projetoUnico([])).toBeUndefined();
  });
});

describe("o valor que todas compartilham", () => {
  it("é o valor quando ninguém discorda", () => {
    expect(valorComum(["urgent", "urgent"])).toEqual({ misto: false, valor: "urgent" });
  });

  it("é misto quando discordam", () => {
    expect(valorComum(["urgent", "low"]).misto).toBe(true);
  });

  it("não devolve valor nenhum quando é misto — senão o campo abriria no da primeira", () => {
    expect(valorComum(["urgent", "low"]).valor).toBeUndefined();
  });

  it("compara lista pelo conteúdo, e não pela ordem", () => {
    expect(
      valorComum([
        ["a", "b"],
        ["b", "a"],
      ]).misto
    ).toBe(false);
  });

  it("trata vazio e ausente como a mesma coisa", () => {
    expect(valorComum([null, undefined]).misto).toBe(false);
  });
});

describe("as datas do rascunho", () => {
  it("aceitam início antes do vencimento", () => {
    expect(datasDoRascunhoSaoCoerentes({ start_date: "2026-08-01", target_date: "2026-08-10" })).toBe(true);
  });

  it("recusam início depois do vencimento", () => {
    expect(datasDoRascunhoSaoCoerentes({ start_date: "2026-08-20", target_date: "2026-08-10" })).toBe(false);
  });

  it("não opinam quando só uma foi escolhida — quem sabe da outra é o servidor", () => {
    expect(datasDoRascunhoSaoCoerentes({ start_date: "2026-08-20" })).toBe(true);
  });
});

describe("quem pode editar", () => {
  const SEM_PAPEL = { usuarioId: "eu", ehEditorEm: () => false };

  it("membro do projeto edita o que não é dele", () => {
    expect(podeEditar(tarefa("1", "p1", { created_by: "outra" }), { usuarioId: "eu", ehEditorEm: () => true })).toBe(
      true
    );
  });

  it("convidado edita o que criou", () => {
    expect(podeEditar(tarefa("1", "p1", { created_by: "eu" }), SEM_PAPEL)).toBe(true);
  });

  it("convidado não edita o que é de outra pessoa", () => {
    expect(podeEditar(tarefa("1", "p1", { created_by: "outra" }), SEM_PAPEL)).toBe(false);
  });

  it("separa sem perder nenhuma", () => {
    const minha = tarefa("1", "p1", { created_by: "eu" });
    const alheia = tarefa("2", "p1", { created_by: "outra" });
    expect(separarEditaveis([minha, alheia], SEM_PAPEL)).toEqual({ editaveis: [minha], bloqueadas: [alheia] });
  });
});

describe("o número no botão", () => {
  it("soma campos nativos e propriedades personalizadas", () => {
    expect(quantasMudancas({ priority: "urgent" }, { "prop-1": "x" })).toBe(2);
  });

  it("é zero quando não se mexeu em nada — e é o que desabilita o botão", () => {
    expect(quantasMudancas({}, {})).toBe(0);
  });
});

describe("o padrão do campo de lista", () => {
  it("é acrescentar, e não substituir", () => {
    // Substituir por padrão é o que fez gente apagar etiqueta no Jira achando
    // que estava somando (JRA-30729).
    expect(MODO_PADRAO).toBe("add");
  });
});
