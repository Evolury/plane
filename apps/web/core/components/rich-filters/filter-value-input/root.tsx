/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import React from "react";

import { observer } from "mobx-react";
// plane imports
import type {
  TNumberFilterFieldConfig,
  TTextFilterFieldConfig,
  TFilterConditionNode,
  TFilterValue,
  TFilterProperty,
  SingleOrArray,
  TSingleSelectFilterFieldConfig,
  TMultiSelectFilterFieldConfig,
  TDateFilterFieldConfig,
  TDateRangeFilterFieldConfig,
  TFilterConditionNodeForDisplay,
} from "@plane/types";
import { EXTENDED_FILTER_FIELD_TYPE, FILTER_FIELD_TYPE } from "@plane/types";
import type { TFilterValueInputProps } from "../shared";
import { DateRangeFilterValueInput } from "./date/range";
// Evolury: campos de digitar (ADR 0011)
import { NumeroFilterValueInput } from "./digitado/numero";
import { TextoFilterValueInput } from "./digitado/texto";
import { SingleDateFilterValueInput } from "./date/single";
import { MultiSelectFilterValueInput } from "./select/multi";
import { SingleSelectFilterValueInput } from "./select/single";
import { useTranslation } from "@plane/i18n";

export const FilterValueInput = observer(function FilterValueInput<P extends TFilterProperty, V extends TFilterValue>(
  props: TFilterValueInputProps<P, V>
) {
  const { condition, filterFieldConfig, isDisabled = false, onChange } = props;

  // Single select input
  if (filterFieldConfig?.type === FILTER_FIELD_TYPE.SINGLE_SELECT) {
    return (
      <SingleSelectFilterValueInput<P>
        config={filterFieldConfig as TSingleSelectFilterFieldConfig<string>}
        condition={condition as TFilterConditionNodeForDisplay<P, string>}
        isDisabled={isDisabled}
        onChange={(value) => onChange(value as SingleOrArray<V>)}
      />
    );
  }

  // Multi select input
  if (filterFieldConfig?.type === FILTER_FIELD_TYPE.MULTI_SELECT) {
    return (
      <MultiSelectFilterValueInput<P>
        config={filterFieldConfig as TMultiSelectFilterFieldConfig<string>}
        condition={condition as TFilterConditionNode<P, string>}
        isDisabled={isDisabled}
        onChange={(value) => onChange(value as SingleOrArray<V>)}
      />
    );
  }

  // Date filter input
  if (filterFieldConfig?.type === FILTER_FIELD_TYPE.DATE) {
    return (
      <SingleDateFilterValueInput<P>
        config={filterFieldConfig as TDateFilterFieldConfig<string>}
        condition={condition as TFilterConditionNodeForDisplay<P, string>}
        isDisabled={isDisabled}
        onChange={(value) => onChange(value as SingleOrArray<V>)}
      />
    );
  }

  // Date range filter input
  if (filterFieldConfig?.type === FILTER_FIELD_TYPE.DATE_RANGE) {
    return (
      <DateRangeFilterValueInput<P>
        config={filterFieldConfig as TDateRangeFilterFieldConfig<string>}
        condition={condition as TFilterConditionNodeForDisplay<P, string>}
        isDisabled={isDisabled}
        onChange={(value) => onChange(value as SingleOrArray<V>)}
      />
    );
  }

  // Evolury: campos de DIGITAR — texto, número e moeda (ADR 0011)
  if (filterFieldConfig?.type === EXTENDED_FILTER_FIELD_TYPE.TEXT) {
    return (
      <TextoFilterValueInput<P>
        config={filterFieldConfig as TTextFilterFieldConfig<string>}
        condition={condition as TFilterConditionNodeForDisplay<P, string>}
        isDisabled={isDisabled}
        onChange={(value) => onChange(value as SingleOrArray<V>)}
      />
    );
  }

  if (filterFieldConfig?.type === EXTENDED_FILTER_FIELD_TYPE.NUMBER) {
    return (
      <NumeroFilterValueInput<P>
        config={filterFieldConfig as TNumberFilterFieldConfig<string>}
        condition={condition as TFilterConditionNodeForDisplay<P, string>}
        isDisabled={isDisabled}
        onChange={(value) => onChange(value as SingleOrArray<V>)}
      />
    );
  }

  // Evolury: prova de exaustividade, em tempo de COMPILAÇÃO (ADR 0011).
  //
  // Se alguém acrescentar um formato de campo e esquecer o componente que o
  // desenha, o TypeScript reclama AQUI. Sem isto, o formato novo cairia no
  // fallback abaixo e a falha seria silenciosa: um filtro que aparece no
  // seletor, não aceita valor nenhum, e não acusa nada em build nem em teste.
  //
  // A variável existe só para o compilador. Se ela deixar de compilar, a
  // correção não é apagá-la — é escrever o componente que falta e ligá-lo
  // acima.
  const formatoSemComponente: never = filterFieldConfig;
  void formatoSemComponente;

  return <AdditionalFilterValueInput {...props} />;
});

export const AdditionalFilterValueInput = observer(function AdditionalFilterValueInput<
  P extends TFilterProperty,
  V extends TFilterValue,
>(props: TFilterValueInputProps<P, V>) {
  const { t } = useTranslation();
  // Evolury: a guarda acima cobre o que o compilador enxerga. Isto cobre o que
  // ele não enxerga: uma condição vinda de visão salva por uma versão mais
  // nova, com um formato que este código ainda não conhece. Sem o registro, a
  // tela mostraria "não suportado" e ninguém saberia de qual formato se trata.
  console.error("Formato de filtro sem componente:", props.filterFieldConfig?.type ?? "(sem tipo)");
  return (
    // Fallback
    <div className="flex h-full cursor-not-allowed items-center px-4 text-11 text-placeholder transition-opacity duration-200">
      {t("ui.filter_type_not_supported")}
    </div>
  );
});
