/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: marca de conclusão no card da tarefa (ADR 0009).
//
// Mesma regra do botão do cabeçalho (`useCompletionAction`), outra
// apresentação: aqui é só o círculo de check, ao lado do ID.
//
// Design: ocupa um espaço fixo, como o slot do chevron de subtarefas, para que
// os títulos continuem alinhados de linha a linha. Apagado enquanto a tarefa
// está aberta e verde quando concluída — a mesma linguagem do ícone de estado
// que a página inteira já usa, em vez de um símbolo novo.

import { observer } from "mobx-react";
import { CircleCheck } from "lucide-react";
import { useTranslation } from "@plane/i18n";
import { Tooltip } from "@plane/propel/tooltip";
import { cn } from "@plane/utils";
// hooks
import { useCompletionAction } from "@/hooks/use-completion-action";
// local imports
import { CompletionSubIssuesModal } from "./completion-sub-issues-modal";

type TCompletionCheckProps = {
  workspaceSlug: string;
  projectId: string | undefined | null;
  issueId: string;
  stateId: string | undefined | null;
  onChange: (stateId: string) => void;
  disabled?: boolean;
  className?: string;
};

export const CompletionCheck = observer(function CompletionCheck(props: TCompletionCheckProps) {
  const { disabled = false, className, ...acaoProps } = props;
  const { t } = useTranslation();
  const { concluida, destino, ocupado, acionar, modalProps } = useCompletionAction(acaoProps);

  // Sem destino não há marca: projeto sem estado no grupo necessário.
  if (!destino) return null;

  const rotulo = concluida ? t("issue.completion.reopen") : t("issue.completion.complete");

  return (
    <>
      <CompletionSubIssuesModal {...modalProps} />
      <Tooltip
        tooltipContent={concluida ? t("issue.completion.reopen_tooltip") : t("issue.completion.complete_tooltip")}
      >
        <button
          type="button"
          aria-label={rotulo}
          // O card inteiro é um link para a tarefa: sem isto, concluir abriria
          // a tarefa junto.
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            acionar();
          }}
          disabled={disabled || ocupado}
          className={cn(
            "grid size-4 flex-shrink-0 place-items-center rounded-full transition-colors",
            concluida ? "text-success-primary" : "text-placeholder hover:text-success-primary",
            { "cursor-not-allowed hover:text-placeholder": disabled },
            className
          )}
          data-completion-check={concluida ? "reopen" : "complete"}
        >
          <CircleCheck className="size-4" strokeWidth={2} />
        </button>
      </Tooltip>
    </>
  );
});
