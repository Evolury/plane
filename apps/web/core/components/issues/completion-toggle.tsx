/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: botão de concluir tarefa (ADR 0009). Não existe caminho próprio de
// conclusão: o botão resolve QUAL estado usar e delega a troca ao mesmo
// `update` que o seletor de estado já usa — por isso histórico, webhooks,
// notificações e contadores de ciclo e módulo seguem corretos sem adaptação.

import { useMemo } from "react";
import { observer } from "mobx-react";
import { CheckIcon, RotateCcw } from "lucide-react";
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { Tooltip } from "@plane/propel/tooltip";
import { cn } from "@plane/utils";
// hooks
import { useProject } from "@/hooks/store/use-project";
import { useProjectState } from "@/hooks/store/use-project-state";

type TCompletionToggleProps = {
  projectId: string | undefined | null;
  stateId: string | undefined | null;
  onChange: (stateId: string) => void;
  disabled?: boolean;
  size?: "sm" | "base";
  className?: string;
};

export const CompletionToggle = observer(function CompletionToggle(props: TCompletionToggleProps) {
  const { projectId, stateId, onChange, disabled = false, size = "base", className } = props;
  const { t } = useTranslation();
  const { getProjectStates, getStateById } = useProjectState();
  const { getProjectById } = useProject();

  const estadoAtual = getStateById(stateId ?? undefined);
  const projeto = getProjectById(projectId ?? undefined);
  const concluida = estadoAtual?.group === "completed";

  // Espelha o resolvedor do backend (get_completion_state): o configurado no
  // projeto quando válido, senão o primeiro do grupo concluído por sequence.
  const destinoConclusao = useMemo(() => {
    const estados = getProjectStates(projectId ?? undefined) ?? [];
    const concluidos = estados.filter((e) => e.group === "completed").sort((a, b) => a.sequence - b.sequence);
    const configurado = concluidos.find((e) => e.id === projeto?.completion_state);
    return configurado ?? concluidos[0];
  }, [getProjectStates, projectId, projeto?.completion_state]);

  // Reabrir devolve ao estado padrão do projeto — o mesmo destino de um item
  // recém-criado. Se ele for concluído ou não existir, usa o primeiro não
  // concluído, para nunca "reabrir" para um estado que segue concluído.
  const destinoReabertura = useMemo(() => {
    const estados = getProjectStates(projectId ?? undefined) ?? [];
    const naoConcluidos = estados
      .filter((e) => e.group !== "completed" && e.group !== "cancelled")
      .sort((a, b) => a.sequence - b.sequence);
    const padrao = naoConcluidos.find((e) => e.default);
    return padrao ?? naoConcluidos[0];
  }, [getProjectStates, projectId]);

  const destino = concluida ? destinoReabertura : destinoConclusao;

  // Sem destino não há botão: projeto sem estado no grupo necessário.
  if (!destino || !estadoAtual) return null;

  const rotulo = concluida ? t("issue.completion.reopen") : t("issue.completion.complete");

  return (
    <Tooltip tooltipContent={concluida ? t("issue.completion.reopen_tooltip") : t("issue.completion.complete_tooltip")}>
      <Button
        variant={concluida ? "secondary" : "primary"}
        size={size}
        onClick={() => onChange(destino.id)}
        disabled={disabled}
        prependIcon={concluida ? <RotateCcw className="size-3.5" /> : <CheckIcon className="size-3.5" />}
        className={cn("flex-shrink-0", className)}
        data-completion-toggle={concluida ? "reopen" : "complete"}
      >
        {rotulo}
      </Button>
    </Tooltip>
  );
});
