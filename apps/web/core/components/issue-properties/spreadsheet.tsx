/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: as propriedades personalizadas no layout de tabela (ADR 0011, P3).
//
// Duas peças que se acoplam ao maquinário existente pela ponta, sem alterá-lo:
// o cabeçalho monta as células depois das colunas fixas, e a linha monta as
// suas na mesma ordem. As colunas fixas são um tipo fechado
// (`keyof IIssueDisplayProperties`), e alargá-lo para caber id de propriedade
// obrigaria a mexer em quatro arquivos herdados do caminho quente.
//
// Nenhuma das duas recebe as definições por prop: as duas leem o mesmo hook, e
// o SWR entrega uma chamada por projeto para a tabela inteira.
//
// **Só em projeto**, nunca no nível do workspace: lá convivem projetos com
// configurações diferentes, e uma coluna "Canal" que existe em três dos oito
// projetos da tela seria uma coluna que mente.

import { createContext, useContext } from "react";
import { observer } from "mobx-react";
import { useParams } from "next/navigation";
import type { TIssue, TPropertyValue } from "@plane/types";
// local imports
import { usePropriedadesDoProjeto, useValoresDasTarefas } from "./store";
import { PropertyValueChip } from "./value-chip";

/**
 * Os valores da PÁGINA, buscados uma vez por quem conhece os ids.
 *
 * O contexto existe porque a linha não sabe em que página está: sem ele, cada
 * linha pediria os próprios valores e a tabela viraria o N+1 que o ADR 0011
 * proibiu. Fora do provedor as células não renderizam nada — é o que impede
 * alguém de montá-las por engano num lugar sem a carga em bloco.
 */
const ValoresDaPagina = createContext<Record<string, Record<string, TPropertyValue>> | null>(null);

export const IssuePropertyValuesProvider = observer(function IssuePropertyValuesProvider(props: {
  issueIds: string[];
  children: React.ReactNode;
}) {
  const { issueIds, children } = props;
  const { workspaceSlug, projectId } = useParams();
  const slug = workspaceSlug?.toString() ?? "";
  const projeto = projectId?.toString() ?? "";

  const propriedades = usePropriedadesDoProjeto(slug, projeto);
  const valores = useValoresDasTarefas(slug, projeto, propriedades.length > 0 ? issueIds : []);

  return <ValoresDaPagina.Provider value={valores}>{children}</ValoresDaPagina.Provider>;
});

/** As células de cabeçalho, uma por propriedade ativa. */
export const SpreadsheetPropertyHeaders = observer(function SpreadsheetPropertyHeaders() {
  const { workspaceSlug, projectId } = useParams();
  const slug = workspaceSlug?.toString() ?? "";
  const projeto = projectId?.toString() ?? "";

  const propriedades = usePropriedadesDoProjeto(slug, projeto);
  if (!projeto || propriedades.length === 0) return null;

  return (
    <>
      {propriedades.map((propriedade) => (
        <th
          key={propriedade.id}
          className="h-11 min-w-36 items-center border border-t-0 border-b-0 border-subtle bg-layer-1 py-1 text-13 font-medium"
        >
          <span className="flex h-full w-full items-center gap-1.5 px-page-x text-secondary">
            <span className="truncate">{propriedade.name}</span>
          </span>
        </th>
      ))}
    </>
  );
});

type TCellsProps = {
  issue: TIssue;
};

/** As células de uma linha, na mesma ordem do cabeçalho. */
export const SpreadsheetPropertyCells = observer(function SpreadsheetPropertyCells(props: TCellsProps) {
  const { issue } = props;
  const { workspaceSlug, projectId } = useParams();
  const slug = workspaceSlug?.toString() ?? "";
  const projeto = projectId?.toString() ?? "";

  const propriedades = usePropriedadesDoProjeto(slug, projeto);
  const valores = useContext(ValoresDaPagina);

  if (!projeto || propriedades.length === 0 || valores === null) return null;
  const meus = valores[issue.id] ?? {};

  return (
    <>
      {propriedades.map((propriedade) => (
        <td
          key={propriedade.id}
          className="h-11 min-w-36 border-r-[1px] border-subtle text-13 after:absolute after:bottom-[-1px] after:w-full after:border after:border-subtle"
        >
          <span className="flex h-full w-full items-center px-page-x">
            <PropertyValueChip propriedade={propriedade} valor={meus[propriedade.id] ?? null} />
          </span>
        </td>
      ))}
    </>
  );
});
