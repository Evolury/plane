/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: regressão do defeito de 17/08/2026 — o cartão "SE" do editor de
// automação abria mostrando só a frase de ajuda, sem nada clicável, e não havia
// como criar a primeira condição.
//
// A causa era uma palavra ausente: `FiltersRow` inteira vive dentro de um
// `<Transition show={filter.isVisible}>`, e a visibilidade padrão de uma
// instância de filtro é "tem filtro ativo?". No quadro isso está certo — quem
// revela a linha é o botão "Filtros" do cabeçalho. No editor de automação esse
// botão não existe: a linha É a interface.
//
// O teste afirma o contrato com o HOC, não a árvore renderizada: montar o HOC de
// verdade traria os stores do quadro inteiro, e o que precisa ficar trancado é
// que ESTE componente pede `showOnMount`.

import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const propsRecebidas: Record<string, unknown>[] = [];

vi.mock("@/components/work-item-filters/filters-hoc/project-level", () => ({
  ProjectLevelWorkItemFiltersHOC: (props: Record<string, unknown>) => {
    propsRecebidas.push(props);
    return <div data-testid="hoc" />;
  },
}));

vi.mock("@/components/rich-filters/filters-row", () => ({
  FiltersRow: () => <div data-testid="linha-de-filtros" />,
}));

vi.mock("@plane/i18n", () => ({
  useTranslation: () => ({ t: (chave: string) => chave }),
}));

import { CondicaoDaAutomacao } from "@/components/automations/condicao";

const montar = () =>
  render(<CondicaoDaAutomacao workspaceSlug="evolury" projectId="projeto-1" condicao={{}} onChange={() => {}} />);

describe("CondicaoDaAutomacao", () => {
  it("pede a linha de filtros já visível", () => {
    propsRecebidas.length = 0;
    montar();

    expect(propsRecebidas).toHaveLength(1);
    // A palavra que faltava. Sem ela, condição vazia = linha invisível = cartão
    // sem nada clicável e sem caminho de saída.
    expect(propsRecebidas[0].showOnMount).toBe(true);
  });

  it("monta a instância como temporária, e não como visão de alguém", () => {
    propsRecebidas.length = 0;
    montar();

    expect(propsRecebidas[0].isTemporary).toBe(true);
  });

  it("entrega a condição recebida como filtro inicial", () => {
    propsRecebidas.length = 0;
    const condicao = { and: [{ priority__in: ["urgent"] }] };
    render(
      <CondicaoDaAutomacao
        workspaceSlug="evolury"
        projectId="projeto-1"
        condicao={condicao as never}
        onChange={() => {}}
      />
    );

    expect((propsRecebidas[0].initialWorkItemFilters as Record<string, unknown>).richFilters).toEqual(condicao);
  });

  it("mostra a frase de ajuda acima da linha", () => {
    montar();
    expect(screen.getAllByText("automations.condition_hint").length).toBeGreaterThan(0);
  });
});
