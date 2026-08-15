/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: o valor de uma propriedade, só de leitura (ADR 0011, P3).
//
// É o que aparece no cartão dos layouts e na coluna da tabela. Só leitura de
// propósito: o cartão é para reconhecer, não para editar — editar é no painel,
// onde cabe o campo inteiro e o rótulo do que se está mudando.
//
// Seleção mostra a COR configurada, que é o que faz o quadro ser lido de
// relance; moeda mostra a moeda declarada, porque número sem moeda numa coluna
// que soma é convite a erro.

import { observer } from "mobx-react";
import type { TIssueProperty, TPropertyValue } from "@plane/types";
import { renderFormattedDate } from "@plane/utils";

type TProps = {
  propriedade: TIssueProperty;
  valor: TPropertyValue;
};

const Pastilha = ({ nome, cor }: { nome: string; cor: string }) => (
  <span className="flex max-w-full items-center gap-1 truncate rounded-full border border-subtle px-1.5 py-0.5 text-11 text-secondary">
    <span className="size-1.5 shrink-0 rounded-full" style={{ backgroundColor: cor || "#6b7280" }} />
    <span className="truncate">{nome}</span>
  </span>
);

export const PropertyValueChip = observer(function PropertyValueChip(props: TProps) {
  const { propriedade, valor } = props;

  if (valor === null || valor === undefined || (Array.isArray(valor) && valor.length === 0)) return null;

  if (propriedade.property_type === "select" || propriedade.property_type === "multi_select") {
    const ids = Array.isArray(valor) ? valor : [valor];
    const escolhidas = propriedade.options.filter((o) => ids.includes(o.id));
    if (escolhidas.length === 0) return null;
    return (
      <span className="flex min-w-0 flex-wrap items-center gap-1">
        {escolhidas.map((opcao) => (
          <Pastilha key={opcao.id} nome={opcao.name} cor={opcao.color} />
        ))}
      </span>
    );
  }

  if (propriedade.property_type === "date") {
    return <span className="truncate text-11 text-secondary">{renderFormattedDate(String(valor))}</span>;
  }

  if (propriedade.property_type === "currency") {
    const numero = Number(valor);
    const formatado = Number.isFinite(numero)
      ? numero.toLocaleString("pt-BR", {
          minimumFractionDigits: propriedade.decimal_places,
          maximumFractionDigits: propriedade.decimal_places,
        })
      : String(valor);
    return (
      <span className="truncate text-11 text-secondary">
        {propriedade.currency} {formatado}
      </span>
    );
  }

  return <span className="truncate text-11 text-secondary">{String(valor)}</span>;
});
