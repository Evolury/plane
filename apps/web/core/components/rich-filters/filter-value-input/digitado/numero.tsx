/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: o campo numérico do filtro — número e moeda (ADR 0011).
//
// Dois formatos no mesmo componente: um campo para "é", dois para "entre". A
// faixa viaja como "início,fim", que é o que o backend traduz para o par
// `gte`/`lte` — o mesmo formato da data, para não existirem dois.
//
// Moeda mostra o símbolo como prefixo: número sem moeda, num campo que soma,
// é convite a erro.

import React, { useEffect, useState } from "react";
import { observer } from "mobx-react";
import type { TFilterConditionNodeForDisplay, TFilterProperty, TNumberFilterFieldConfig } from "@plane/types";
import { cn } from "@plane/utils";
import { COMMON_FILTER_ITEM_BORDER_CLASSNAME } from "../../shared";

type TProps<P extends TFilterProperty> = {
  config: TNumberFilterFieldConfig<string>;
  condition: TFilterConditionNodeForDisplay<P, string>;
  isDisabled?: boolean;
  onChange: (value: string | null | undefined) => void;
};

/** Só dígitos, um separador decimal e o sinal — teclar letra não faz nada. */
const somenteNumero = (bruto: string) => bruto.replace(/[^0-9.,-]/g, "").replace(",", ".");

export const NumeroFilterValueInput = observer(function NumeroFilterValueInput<P extends TFilterProperty>(
  props: TProps<P>
) {
  const { config, condition, isDisabled, onChange } = props;
  const salvo = typeof condition.value === "string" ? condition.value : "";
  const faixa = config.faixa === true;

  const [inicio, fim] = faixa ? [salvo.split(",")[0] ?? "", salvo.split(",")[1] ?? ""] : [salvo, ""];
  const [rascunhoInicio, setRascunhoInicio] = useState(inicio);
  const [rascunhoFim, setRascunhoFim] = useState(fim);

  useEffect(() => {
    setRascunhoInicio(inicio);
    setRascunhoFim(fim);
  }, [inicio, fim]);

  const confirmar = () => {
    const a = somenteNumero(rascunhoInicio).trim();
    const b = somenteNumero(rascunhoFim).trim();
    if (!faixa) {
      if (a !== salvo) onChange(a || null);
      return;
    }
    // A faixa só vale inteira: com uma ponta só, o filtro ficaria pela metade
    // e a tela mostraria um resultado que ninguém pediu.
    const novo = a && b ? `${a},${b}` : null;
    if ((novo ?? "") !== salvo) onChange(novo);
  };

  const campo = (valor: string, set: (v: string) => void, dica: string) => (
    <input
      type="text"
      inputMode="decimal"
      value={valor}
      disabled={isDisabled}
      onChange={(e) => set(somenteNumero(e.target.value))}
      onBlur={confirmar}
      onKeyDown={(e) => {
        if (e.key === "Enter") e.currentTarget.blur();
        else if (e.key === "Escape") {
          setRascunhoInicio(inicio);
          setRascunhoFim(fim);
          e.currentTarget.blur();
        }
      }}
      placeholder={dica}
      className={cn("h-full w-16 bg-transparent px-1 py-1 text-right text-12 outline-none", {
        "text-placeholder": !valor,
      })}
    />
  );

  return (
    <div
      className={cn("flex h-full items-center gap-0.5 px-1", {
        [COMMON_FILTER_ITEM_BORDER_CLASSNAME]: !isDisabled,
      })}
    >
      {config.prefixo && <span className="text-11 text-tertiary">{config.prefixo}</span>}
      {campo(rascunhoInicio, setRascunhoInicio, faixa ? "de" : (config.placeholder ?? "valor"))}
      {faixa && (
        <>
          <span className="text-11 text-tertiary">–</span>
          {campo(rascunhoFim, setRascunhoFim, "até")}
        </>
      )}
    </div>
  );
});
