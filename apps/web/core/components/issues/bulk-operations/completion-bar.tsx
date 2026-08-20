/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: a barra da seleção múltipla. Ocupa o lugar da faixa de upsell que o
// Plane mostrava ao selecionar itens — a seleção já existia inteira no código,
// só não tinha nenhuma ação disponível nesta edição.
//
// Duas ações moram aqui: **concluir** (ADR 0009) e **excluir** (ADR 0018). A
// conta de cada uma é diferente e nenhuma é do componente: concluir ignora o
// que já está concluído, excluir ignora o que não é de quem pediu.
//
// Não há endpoint de operação em massa aqui (`bulk-operation-issues` é da
// edição paga), então a barra repete a MESMA atualização de estado item a item,
// em lotes, pelo caminho comum do layout.

import { useState } from "react";
import { observer } from "mobx-react";
import { CheckIcon } from "lucide-react";
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import type { TIssue } from "@plane/types";
import { EIssuesStoreType } from "@plane/types";
import { cn } from "@plane/utils";
// hooks
import { useIssues } from "@/hooks/store/use-issues";
import { useMultipleSelectStore } from "@/hooks/store/use-multiple-select-store";
import { useProjectState } from "@/hooks/store/use-project-state";
import { useIssueStoreType } from "@/hooks/use-issue-layout-store";
import { useCompletionTargets } from "@/hooks/use-issue-completed";
import { useIssuesActions } from "@/hooks/use-issues-actions";
// local
import { BotaoDeEditar } from "./editar";
import { BotaoDeExcluir } from "./excluir";

type Props = {
  className?: string;
};

const TAMANHO_DO_LOTE = 5;

export const CompletionBulkBar = observer(function CompletionBulkBar(props: Props) {
  const { className } = props;
  const { t } = useTranslation();
  const storeType = useIssueStoreType();
  const { updateIssue } = useIssuesActions(storeType);
  const { selectedEntityIds, clearSelection } = useMultipleSelectStore();
  const { issueMap } = useIssues();
  const { getCompletionState } = useCompletionTargets();
  const { getStateById } = useProjectState();
  // states
  const [concluindo, setConcluindo] = useState(false);

  const selecionadas = selectedEntityIds.map((id) => issueMap[id]).filter((issue): issue is TIssue => !!issue);
  // Já concluída não entra na conta: o rótulo do botão precisa dizer quantas
  // realmente vão mudar.
  const aConcluir = selecionadas.filter((issue) => {
    const grupo = getStateById(issue.state_id ?? undefined)?.group;
    return grupo !== "completed" && !!issue.project_id && !!getCompletionState(issue.project_id);
  });

  const concluirSelecionadas = async () => {
    if (!updateIssue || aConcluir.length === 0) return;
    setConcluindo(true);
    let concluidas = 0;
    let falhou = false;
    // Em lotes para não disparar dezenas de requisições ao mesmo tempo.
    for (let i = 0; i < aConcluir.length; i += TAMANHO_DO_LOTE) {
      const lote = aConcluir.slice(i, i + TAMANHO_DO_LOTE);
      const resultados = await Promise.allSettled(
        lote.map((issue) => {
          const alvo = getCompletionState(issue.project_id);
          if (!alvo) return Promise.reject(new Error("sem estado de conclusão"));
          return updateIssue(issue.project_id, issue.id, { state_id: alvo.id });
        })
      );
      resultados.forEach((resultado) => {
        if (resultado.status === "fulfilled") concluidas += 1;
        else falhou = true;
      });
    }
    setConcluindo(false);
    if (concluidas > 0) {
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: t("toast.success"),
        message: t("issue.completion.bulk.success", { count: concluidas }),
      });
      clearSelection();
    }
    if (falhou)
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("toast.error"),
        message: t("issue.completion.bulk.error"),
      });
  };

  // Arquivados e rascunhos não se concluem, e sem caminho de atualização não há
  // o que oferecer.
  if (!updateIssue || storeType === EIssuesStoreType.ARCHIVED || storeType === EIssuesStoreType.WORKSPACE_DRAFT)
    return null;

  return (
    <div className={cn("sticky bottom-0 left-0 z-[2] grid h-20 place-items-center px-3.5", className)}>
      <div className="flex h-14 w-full items-center justify-between gap-2 rounded-md border-[0.5px] border-strong bg-surface-1 px-3.5 py-4 shadow-raised-200">
        <p className="font-medium text-primary">
          {t("issue.completion.bulk.selected", { count: selecionadas.length })}
        </p>
        <div className="flex flex-shrink-0 items-center gap-2">
          <Button variant="ghost" size="base" onClick={clearSelection} disabled={concluindo}>
            {t("issue.completion.bulk.clear")}
          </Button>
          <Button
            variant="primary"
            size="base"
            prependIcon={<CheckIcon className="size-3.5" />}
            onClick={concluirSelecionadas}
            disabled={aConcluir.length === 0}
            loading={concluindo}
            data-completion-bulk="complete"
          >
            {t("issue.completion.complete")}
          </Button>
          <BotaoDeEditar selecionadas={selecionadas} />
          <BotaoDeExcluir selecionadas={selecionadas} />
        </div>
      </div>
    </div>
  );
});
