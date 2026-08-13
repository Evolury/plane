/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: a regra de concluir tarefa, sem interface (ADR 0009).
//
// Existem duas apresentações — o botão do cabeçalho da tarefa e o ícone do
// card — e uma regra só: qual é o destino, o que fazer com subtarefas em
// aberto, e o que significa reabrir. Duplicar isso em dois componentes seria
// garantir que um dia divergissem.

import { useEffect, useState } from "react";
import type { TIssue } from "@plane/types";
// hooks
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
import { useProjectState } from "@/hooks/store/use-project-state";
import { useCompletionTargets, useIsIssueCompleted, useIsIssueCancelled } from "@/hooks/use-issue-completed";

type TCompletionActionArgs = {
  workspaceSlug: string;
  projectId: string | undefined | null;
  issueId: string;
  stateId: string | undefined | null;
  onChange: (stateId: string) => void;
};

export const useCompletionAction = (args: TCompletionActionArgs) => {
  const { workspaceSlug, projectId, issueId, stateId, onChange } = args;
  const { getStateById } = useProjectState();
  const { getCompletionState, getReopenState } = useCompletionTargets();
  const {
    issue: { getIssueById },
    subIssues: subIssuesStore,
    toggleCompletionModal,
  } = useIssueDetail();
  // states
  const [subtarefasAbertas, setSubtarefasAbertas] = useState<TIssue[]>([]);
  const [ocupado, setOcupado] = useState(false);

  const concluida = useIsIssueCompleted(stateId);
  // Cancelada é um fim de linha declarado: "não vai ser feita" não vira "feita"
  // por um clique. Sem destino, nem o botão nem a marca aparecem — para voltar
  // atrás existe o seletor de estado, que é onde a decisão foi tomada.
  const cancelada = useIsIssueCancelled(stateId);
  const tarefa = getIssueById(issueId);
  const destino = cancelada ? undefined : concluida ? getReopenState(projectId) : getCompletionState(projectId);

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

  const acionar = async () => {
    if (!destino) return;
    // Reabrir não pergunta nada: só a conclusão se propaga para as subtarefas.
    if (concluida || !projectId || (tarefa?.sub_issues_count ?? 0) === 0) {
      onChange(destino.id);
      return;
    }
    // As subtarefas podem ainda não ter sido carregadas — o widget só busca
    // quando é aberto — então garante a lista antes de decidir se pergunta.
    if (!subIssuesStore.subIssuesByIssueId(issueId)) {
      setOcupado(true);
      try {
        await subIssuesStore.fetchSubIssues(workspaceSlug, projectId, issueId);
      } finally {
        setOcupado(false);
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
    setOcupado(true);
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
      setOcupado(false);
      fecharConfirmacao();
    }
  };

  const concluirSomenteEsta = () => {
    if (!destino) return;
    onChange(destino.id);
    fecharConfirmacao();
  };

  return {
    /** Se a tarefa está no grupo concluído. */
    concluida,
    /** Sem destino não há o que oferecer: projeto sem estado no grupo. */
    destino,
    ocupado,
    acionar,
    /** Pronto para espalhar no <CompletionSubIssuesModal />. */
    modalProps: {
      isOpen: subtarefasAbertas.length > 0,
      openSubIssuesCount: subtarefasAbertas.length,
      isSubmitting: ocupado,
      onClose: fecharConfirmacao,
      onCompleteAll: concluirTudo,
      onCompleteParentOnly: concluirSomenteEsta,
    },
  };
};
