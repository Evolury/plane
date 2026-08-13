/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: escolha do estado de conclusão do projeto (ADR 0009).
//
// Aparece só nos estados do grupo concluído e no mesmo lugar do "Marcar como
// padrão", porque é a mesma pergunta com outro sujeito: qual desses estados
// vale como destino. Sem escolha explícita, o primeiro do grupo já é o destino
// — e o rótulo mostra isso, em vez de deixar a resposta invisível.

import { useState } from "react";
import { observer } from "mobx-react";
import { useParams } from "next/navigation";
import { useTranslation } from "@plane/i18n";
import { Tooltip } from "@plane/propel/tooltip";
import type { IState } from "@plane/types";
import { cn } from "@plane/utils";
// hooks
import { useProject } from "@/hooks/store/use-project";
import { useCompletionTargets } from "@/hooks/use-issue-completed";

type TStateMarksAsCompletion = {
  state: IState;
};

export const StateMarksAsCompletion = observer(function StateMarksAsCompletion(props: TStateMarksAsCompletion) {
  const { state } = props;
  const { t } = useTranslation();
  const { workspaceSlug } = useParams();
  const { getProjectById, updateProject } = useProject();
  const { getCompletionState } = useCompletionTargets();
  // states
  const [isLoading, setIsLoading] = useState(false);

  const projeto = getProjectById(state.project_id ?? undefined);
  const explicito = projeto?.completion_state === state.id;
  // O destino vale mesmo sem escolha explícita — quem manda é o resolvedor.
  const eDestino = getCompletionState(state.project_id)?.id === state.id;

  const handleMarkAsCompletion = async () => {
    if (!workspaceSlug || !state.project_id || explicito) return;
    setIsLoading(true);
    try {
      await updateProject(workspaceSlug.toString(), state.project_id, { completion_state: state.id });
    } finally {
      setIsLoading(false);
    }
  };

  const rotulo = isLoading
    ? t("project_settings.states.completion.marking")
    : eDestino
      ? t("project_settings.states.completion.label")
      : t("project_settings.states.completion.mark");

  return (
    <Tooltip
      tooltipContent={t("project_settings.states.completion.automatic_tooltip")}
      disabled={!eDestino || explicito}
    >
      <button
        type="button"
        className={cn(
          "text-11 whitespace-nowrap transition-colors",
          eDestino ? "text-tertiary" : "text-secondary hover:text-primary"
        )}
        disabled={eDestino || isLoading}
        onClick={handleMarkAsCompletion}
      >
        {rotulo}
      </button>
    </Tooltip>
  );
});
