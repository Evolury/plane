/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: dois defeitos do cartão de notificação, medidos no banco de produção.
//
// 1. A ação `notify` de uma automação grava `field: "automation"` — um valor que
//    o upstream não tem, porque lá não existe automação que avise. Sem entrada
//    no mapa de conteúdo, o cartão caía no renderizador genérico, que concatena
//    `verb` com o nome do campo sem passar por tradução: "Automação created
//    automation em <texto>", em inglês, num produto em português.
//
// 2. Uma notificação gravada SEM `issue_activity` derruba a caixa de entrada
//    inteira. O #150 corrigiu a causa (o payload passou a ser um só) e pôs o
//    `?.` em `field` — mas deixou as três leituras irmãs. A linha antiga
//    continua no banco e não some sozinha; só mudou qual linha estoura.
//
// A tradução é conferida contra o JSON de verdade, e não contra o mock: já
// aconteceu de a chave existir no arquivo e mesmo assim não resolver, por estar
// num nível errado do objeto. Mock nenhum pega isso.

import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

// Lido do disco, e não importado: o `@plane/i18n` não exporta os JSON de idioma
// no `exports` do pacote. A raiz vem do `cwd` do runner (`apps/web`) porque o
// `import.meta.url` chega aqui com o prefixo `/@fs/` que o Vite usa.
const dicionario = (idioma: string) =>
  JSON.parse(readFileSync(resolve(process.cwd(), `../../packages/i18n/src/locales/${idioma}/common.json`), "utf8"));

vi.mock("@plane/i18n", () => ({
  translate: (chave: string) => chave,
}));

vi.mock("@/components/editor/lite-text", () => ({
  LiteTextEditor: () => <div data-testid="editor" />,
}));

import { NotificationContent } from "@/components/workspace-notifications/sidebar/notification-card/content";

const CHAVE = "activity_log.automation_notified";

const montar = (issueActivity: Record<string, unknown> | null) =>
  render(
    <NotificationContent
      notification={
        {
          id: "n1",
          triggered_by_details: { is_bot: true, first_name: "Automação", display_name: "Automação" },
          data: { issue: { id: "t1" }, issue_activity: issueActivity },
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
        } as any
      }
      workspaceId="w1"
      workspaceSlug="evolury"
      projectId="p1"
    />
  );

const avisoDaAutomacao = {
  id: null,
  verb: "created",
  field: "automation",
  actor: "robo",
  old_value: "",
  new_value: "Prioridade virou urgente",
  activity_time: "2026-08-17T22:49:02.179781+00:00",
};

describe("cartão de notificação de automação", () => {
  it("usa a frase traduzida, e não o campo cru concatenado ao verbo", () => {
    montar(avisoDaAutomacao);

    expect(screen.getByText(CHAVE, { exact: false })).toBeTruthy();
    // A frase exata que aparecia na tela antes da correção.
    expect(screen.queryByText(/created automation/)).toBeNull();
  });

  it("mostra o texto que a regra escreveu", () => {
    montar(avisoDaAutomacao);

    expect(screen.getByText("Prioridade virou urgente")).toBeTruthy();
  });

  it("não repete o conector antes do texto", () => {
    // `showConnector` é `true` por omissão, e o texto da regra já é uma frase
    // pronta: sem esta afirmação, o cartão leria "avisou: em <texto>".
    montar(avisoDaAutomacao);

    expect(screen.queryByText(/prep_in/)).toBeNull();
  });

  it("não estoura quando a notificação foi gravada sem `issue_activity`", () => {
    // A linha antiga do banco. Antes, `data?.issue_activity.new_value` lançava
    // TypeError e a caixa de entrada inteira ia para a tela de erro.
    expect(() => montar(null)).not.toThrow();
  });
});

describe("a chave de tradução existe onde o código a procura", () => {
  it.each(["pt-BR", "en"])("%s", (idioma) => {
    // Buscada pelo caminho que o `translate` usa, e não por `includes` no
    // arquivo: chave certa no lugar errado do objeto passa em busca de texto e
    // chega à tela como o próprio nome da chave.
    const [raiz, folha] = CHAVE.split(".");
    const valor = dicionario(idioma)[raiz]?.[folha];

    expect(typeof valor).toBe("string");
    expect(valor.length).toBeGreaterThan(0);
  });
});
