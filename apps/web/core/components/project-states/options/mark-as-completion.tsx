/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: escolha do destino da conclusão (ADR 0009).
//
// Aparece só nos estados do grupo concluído e no mesmo lugar do "Marcar como
// padrão", porque é a mesma pergunta com outro sujeito: qual deles vale como
// destino. O componente não sabe QUEM responde — o projeto grava em
// `completion_state`, "Minhas tarefas" marca a etapa pessoal —, ele só mostra
// e delega.

import { useState } from "react";
import { observer } from "mobx-react";
import { useTranslation } from "@plane/i18n";
import { Tooltip } from "@plane/propel/tooltip";
import { cn } from "@plane/utils";

type TStateMarksAsCompletion = {
  /** É o destino de fato, por marcação explícita ou por ser o primeiro do grupo. */
  isCompletion: boolean;
  /** Foi escolhido a dedo, e não resolvido automaticamente. */
  isExplicit: boolean;
  onMark: () => Promise<void>;
};

export const StateMarksAsCompletion = observer(function StateMarksAsCompletion(props: TStateMarksAsCompletion) {
  const { isCompletion, isExplicit, onMark } = props;
  const { t } = useTranslation();
  // states
  const [isLoading, setIsLoading] = useState(false);

  const handleMark = async () => {
    if (isCompletion) return;
    setIsLoading(true);
    try {
      await onMark();
    } finally {
      setIsLoading(false);
    }
  };

  const rotulo = isLoading
    ? t("project_settings.states.completion.marking")
    : isCompletion
      ? t("project_settings.states.completion.label")
      : t("project_settings.states.completion.mark");

  return (
    <Tooltip
      tooltipContent={t("project_settings.states.completion.automatic_tooltip")}
      disabled={!isCompletion || isExplicit}
    >
      <button
        type="button"
        className={cn(
          "text-11 whitespace-nowrap transition-colors",
          isCompletion ? "text-tertiary" : "text-secondary hover:text-primary"
        )}
        disabled={isCompletion || isLoading}
        onClick={handleMark}
      >
        {rotulo}
      </button>
    </Tooltip>
  );
});
