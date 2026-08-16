/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: o campo de texto do filtro (ADR 0011).
//
// Confirma ao SAIR do campo, não a cada tecla — é a mesma regra do editor de
// valor da propriedade, e pela mesma razão: buscar a cada letra dispararia uma
// consulta por caractere digitado. Enter confirma, Escape devolve o que estava.

import React, { useEffect, useState } from "react";
import { observer } from "mobx-react";
import type { TFilterConditionNodeForDisplay, TFilterProperty, TTextFilterFieldConfig } from "@plane/types";
import { cn } from "@plane/utils";
import { COMMON_FILTER_ITEM_BORDER_CLASSNAME, EMPTY_FILTER_PLACEHOLDER_TEXT } from "../../shared";

type TProps<P extends TFilterProperty> = {
  config: TTextFilterFieldConfig<string>;
  condition: TFilterConditionNodeForDisplay<P, string>;
  isDisabled?: boolean;
  onChange: (value: string | null | undefined) => void;
};

export const TextoFilterValueInput = observer(function TextoFilterValueInput<P extends TFilterProperty>(
  props: TProps<P>
) {
  const { config, condition, isDisabled, onChange } = props;
  const salvo = typeof condition.value === "string" ? condition.value : "";
  const [rascunho, setRascunho] = useState(salvo);

  // O valor pode mudar por fora — ao recarregar com a visão salva, por exemplo.
  useEffect(() => setRascunho(salvo), [salvo]);

  const confirmar = () => {
    const limpo = rascunho.trim();
    if (limpo !== salvo) onChange(limpo || null);
  };

  return (
    <input
      type="text"
      value={rascunho}
      disabled={isDisabled}
      onChange={(e) => setRascunho(e.target.value)}
      onBlur={confirmar}
      onKeyDown={(e) => {
        if (e.key === "Enter") {
          e.currentTarget.blur();
        } else if (e.key === "Escape") {
          setRascunho(salvo);
          e.currentTarget.blur();
        }
      }}
      placeholder={config.placeholder ?? EMPTY_FILTER_PLACEHOLDER_TEXT}
      className={cn("h-full max-w-40 min-w-24 bg-transparent px-2 py-1 text-12 outline-none", {
        [COMMON_FILTER_ITEM_BORDER_CLASSNAME]: !isDisabled,
        "text-placeholder": !rascunho,
      })}
    />
  );
});
