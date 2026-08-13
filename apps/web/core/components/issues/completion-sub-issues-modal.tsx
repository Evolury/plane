/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: confirmação ao concluir tarefa com subtarefas em aberto (ADR 0009).
// São três saídas, e não duas, porque nenhuma delas é a óbvia: concluir só a
// tarefa pai é legítimo (a subtarefa pode ter virado outra coisa), e concluir
// tudo junto é o atalho que a pessoa espera de um botão de concluir.

import { CheckIcon } from "lucide-react";
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { EModalPosition, EModalWidth, ModalCore } from "@plane/ui";

type TCompletionSubIssuesModalProps = {
  isOpen: boolean;
  openSubIssuesCount: number;
  isSubmitting: boolean;
  onClose: () => void;
  onCompleteAll: () => void;
  onCompleteParentOnly: () => void;
};

export function CompletionSubIssuesModal(props: TCompletionSubIssuesModalProps) {
  const { isOpen, openSubIssuesCount, isSubmitting, onClose, onCompleteAll, onCompleteParentOnly } = props;
  const { t } = useTranslation();

  return (
    <ModalCore isOpen={isOpen} handleClose={onClose} position={EModalPosition.CENTER} width={EModalWidth.XL}>
      <div className="flex flex-col items-center gap-4 p-5 sm:flex-row sm:items-start">
        <span className="grid size-12 flex-shrink-0 place-items-center rounded-full bg-accent-primary/20 text-accent-primary sm:size-10">
          <CheckIcon className="size-5" aria-hidden="true" />
        </span>
        <div className="text-center sm:text-left">
          <h3 className="text-16 font-medium">{t("issue.completion.sub_issues.title")}</h3>
          <p className="mt-1 text-13 text-secondary">
            {t("issue.completion.sub_issues.description", { count: openSubIssuesCount })}
          </p>
        </div>
      </div>
      <div className="flex flex-col-reverse gap-2 border-t-[0.5px] border-subtle px-5 py-4 sm:flex-row sm:justify-end">
        <Button variant="ghost" onClick={onClose} disabled={isSubmitting}>
          {t("common.cancel")}
        </Button>
        <Button variant="secondary" onClick={onCompleteParentOnly} disabled={isSubmitting}>
          {t("issue.completion.sub_issues.parent_only")}
        </Button>
        <Button variant="primary" onClick={onCompleteAll} loading={isSubmitting}>
          {t("issue.completion.sub_issues.complete_all", { count: openSubIssuesCount })}
        </Button>
      </div>
    </ModalCore>
  );
}
