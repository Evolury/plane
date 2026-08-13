/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: botão de concluir tarefa (ADR 0009). Não existe caminho próprio de
// conclusão: o botão resolve QUAL estado usar e delega a troca ao mesmo
// `update` que o seletor de estado já usa — por isso histórico, webhooks,
// notificações e contadores de ciclo e módulo seguem corretos sem adaptação.
//
// A regra mora em `useCompletionAction`, compartilhada com o ícone do card.

import { observer } from "mobx-react";
import { CheckIcon, RotateCcw } from "lucide-react";
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { Tooltip } from "@plane/propel/tooltip";
import { cn } from "@plane/utils";
// hooks
import { useCompletionAction } from "@/hooks/use-completion-action";
// local imports
import { CompletionSubIssuesModal } from "./completion-sub-issues-modal";

type TCompletionToggleProps = {
  workspaceSlug: string;
  projectId: string | undefined | null;
  issueId: string;
  stateId: string | undefined | null;
  onChange: (stateId: string) => void;
  disabled?: boolean;
  size?: "sm" | "base";
  className?: string;
};

export const CompletionToggle = observer(function CompletionToggle(props: TCompletionToggleProps) {
  const { disabled = false, size = "base", className, ...acaoProps } = props;
  const { t } = useTranslation();
  const { concluida, destino, ocupado, acionar, modalProps } = useCompletionAction(acaoProps);

  // Sem destino não há botão: projeto sem estado no grupo necessário.
  if (!destino) return null;

  return (
    <>
      <CompletionSubIssuesModal {...modalProps} />
      <Tooltip
        tooltipContent={concluida ? t("issue.completion.reopen_tooltip") : t("issue.completion.complete_tooltip")}
      >
        <Button
          variant={concluida ? "secondary" : "primary"}
          size={size}
          onClick={acionar}
          disabled={disabled || ocupado}
          prependIcon={concluida ? <RotateCcw className="size-3.5" /> : <CheckIcon className="size-3.5" />}
          className={cn("flex-shrink-0", className)}
          data-completion-toggle={concluida ? "reopen" : "complete"}
        >
          {concluida ? t("issue.completion.reopen") : t("issue.completion.complete")}
        </Button>
      </Tooltip>
    </>
  );
});
