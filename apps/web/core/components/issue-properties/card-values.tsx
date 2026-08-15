/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: os valores marcados para aparecer no cartão (ADR 0011, P3).
//
// **Só as marcadas com "mostrar no cartão"**, e não todas. Trinta propriedades
// no cartão fariam do quadro uma planilha ruim — quem quer todas tem o layout
// de tabela, que é onde a largura existe.
//
// A leitura é compartilhada por toda a página pelo SWR: um pedido por cartão
// seria o N+1 que o ADR proibiu.

import { observer } from "mobx-react";
import { useParams } from "next/navigation";
// local imports
import { usePropriedadesDoProjeto, useValoresDeCartao } from "./store";
import { PropertyValueChip } from "./value-chip";

type TProps = {
  projectId: string;
  issueId: string;
};

export const IssuePropertyCardValues = observer(function IssuePropertyCardValues(props: TProps) {
  const { projectId, issueId } = props;
  const { workspaceSlug } = useParams();
  const slug = workspaceSlug?.toString() ?? "";

  const propriedades = usePropriedadesDoProjeto(slug, projectId).filter((p) => p.show_on_card);
  const valores = useValoresDeCartao(slug, projectId, propriedades.length > 0);

  if (propriedades.length === 0) return null;
  const meus = valores[issueId] ?? {};

  return (
    <>
      {propriedades.map((propriedade) => (
        <PropertyValueChip key={propriedade.id} propriedade={propriedade} valor={meus[propriedade.id] ?? null} />
      ))}
    </>
  );
});
