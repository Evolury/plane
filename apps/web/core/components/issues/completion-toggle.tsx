/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: botão de concluir tarefa (ADR 0009). Não existe caminho próprio de
// conclusão: o botão resolve QUAL estado usar e delega a troca ao mesmo
// `update` que o seletor de estado já usa — por isso histórico, webhooks,
// notificações e contadores de ciclo e módulo seguem corretos sem adaptação.

import { useEffect, useState } from "react";
import { observer } from "mobx-react";
import { CheckIcon, RotateCcw } from "lucide-react";
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { Tooltip } from "@plane/propel/tooltip";
import type { TIssue } from "@plane/types";
import { cn } from "@plane/utils";
// hooks
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
import { useProjectState } from "@/hooks/store/use-project-state";
import { useCompletionTargets, useIsIssueCompleted } from "@/hooks/use-issue-completed";
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
  const { workspaceSlug, projectId, issueId, stateId, onChange, disabled = false, size = "base", className } = props;
  const { t } = useTranslation();
  const { getCompletionState, getReopenState } = useCompletionTargets();
  const { getStateById } = useProjectState();
  const {
    issue: { getIssueById },
    subIssues: subIssuesStore,
    toggleCompletionModal,
  } = useIssueDetail();
  // states
  const [subtarefasAbertas, setSubtarefasAbertas] = useState<TIssue[]>([]);
  const [concluindoTudo, setConcluindoTudo] = useState(false);

  // O peek se fecha ao clique fora, e o modal é portado para fora do painel —
  // avisar a loja é o que o mantém aberto enquanto a confirmação está na tela.
  const abrirConfirmacao = (abertas: TIssue[]) => {
    toggleCompletionModal(issueId);
    setSubtarefasAbertas(abertas);
  };

  const fecharConfirmacao = () => {
    toggleCompletionModal(null);
    setSubtarefasAbertas([]);
  };

  // Desmontar com a marca acesa deixaria o peek preso aberto para sempre.
  useEffect(() => () => toggleCompletionModal(null), [toggleCompletionModal]);

  const concluida = useIsIssueCompleted(stateId);
  const tarefa = getIssueById(issueId);
  const destino = concluida ? getReopenState(projectId) : getCompletionState(projectId);

  // Só as subtarefas diretas: quem tem filha aberta é perguntado por sua vez,
  // ao ser concluída. Cancelada também não conta como aberta.
  const listarSubtarefasAbertas = (): TIssue[] => {
    const ids = subIssuesStore.subIssuesByIssueId(issueId) ?? [];
    return ids
      .map((id) => getIssueById(id))
      .filter((sub): sub is TIssue => {
        if (!sub) return false;
        const grupo = getStateById(sub.state_id ?? undefined)?.group;
        return grupo !== "completed" && grupo !== "cancelled";
      });
  };

  const handleClick = async () => {
    if (!destino) return;
    // Reabrir não pergunta nada: só a conclusão se propaga para as subtarefas.
    if (concluida || !projectId || (tarefa?.sub_issues_count ?? 0) === 0) {
      onChange(destino.id);
      return;
    }
    // As subtarefas podem ainda não ter sido carregadas — o widget só busca
    // quando é aberto — então garante a lista antes de decidir se pergunta.
    if (!subIssuesStore.subIssuesByIssueId(issueId)) {
      setConcluindoTudo(true);
      try {
        await subIssuesStore.fetchSubIssues(workspaceSlug, projectId, issueId);
      } finally {
        setConcluindoTudo(false);
      }
    }
    const abertas = listarSubtarefasAbertas();
    if (abertas.length === 0) {
      onChange(destino.id);
      return;
    }
    abrirConfirmacao(abertas);
  };

  const concluirTudo = async () => {
    if (!destino || !projectId) return;
    setConcluindoTudo(true);
    try {
      await Promise.all(
        subtarefasAbertas.map((sub) => {
          // Cada subtarefa resolve o destino no PRÓPRIO projeto: subtarefa de
          // outro projeto tem outros estados.
          const alvo = sub.project_id ? getCompletionState(sub.project_id) : undefined;
          if (!alvo || !sub.project_id) return Promise.resolve();
          return subIssuesStore.updateSubIssue(
            workspaceSlug,
            sub.project_id,
            issueId,
            sub.id,
            { state_id: alvo.id },
            { state_id: sub.state_id }
          );
        })
      );
      onChange(destino.id);
    } finally {
      setConcluindoTudo(false);
      fecharConfirmacao();
    }
  };

  const concluirSomenteEsta = () => {
    if (!destino) return;
    onChange(destino.id);
    fecharConfirmacao();
  };

  // Sem destino não há botão: projeto sem estado no grupo necessário.
  if (!destino) return null;

  return (
    <>
      <CompletionSubIssuesModal
        isOpen={subtarefasAbertas.length > 0}
        openSubIssuesCount={subtarefasAbertas.length}
        isSubmitting={concluindoTudo}
        onClose={fecharConfirmacao}
        onCompleteAll={concluirTudo}
        onCompleteParentOnly={concluirSomenteEsta}
      />
      <Tooltip
        tooltipContent={concluida ? t("issue.completion.reopen_tooltip") : t("issue.completion.complete_tooltip")}
      >
        <Button
          variant={concluida ? "secondary" : "primary"}
          size={size}
          onClick={handleClick}
          disabled={disabled || concluindoTudo}
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
