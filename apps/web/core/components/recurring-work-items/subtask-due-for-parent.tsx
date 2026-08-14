/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: o invólucro que decide se o campo de vencimento relativo aparece
// (ADR 0010, F7).
//
// Existe separado do campo para que a linha da subtarefa não precise saber
// nada de recorrência: ela só monta isto, e aqui se resolve se há regra na
// raiz e se quem está olhando pode editar. Sem regra — a esmagadora maioria
// das subtarefas do produto — não renderiza nada e não custa consulta nova: o
// papel da raiz já está no cache do SWR por causa da seção "Repetir".
//
// A pergunta é sempre sobre a raiz, nunca sobre o pai imediato: a árvore
// inteira entra na cópia (F8), e a subtarefa de terceiro nível pertence à
// mesma série que a de primeiro.

import { observer } from "mobx-react";
import useSWR from "swr";
import { EUserPermissions, EUserPermissionsLevel } from "@plane/constants";
// hooks
import { useUserPermissions } from "@/hooks/store/user";
// services
import { RecurringWorkItemService } from "@/services/recurring-work-item.service";
// local imports
import { chaveDaRegra } from "./section";
import { SubtaskDueField } from "./subtask-due";

const servico = new RecurringWorkItemService();

type TProps = {
  workspaceSlug: string;
  projectId: string;
  /** A raiz da árvore — quem carrega a regra, em qualquer profundidade (F8). */
  rootIssueId: string;
  subtaskId: string;
};

export const SubtaskDueForParent = observer(function SubtaskDueForParent(props: TProps) {
  const { workspaceSlug, projectId, rootIssueId, subtaskId } = props;
  const { allowPermissions } = useUserPermissions();

  const { data: papel } = useSWR(workspaceSlug && projectId && rootIssueId ? chaveDaRegra(rootIssueId) : null, () =>
    servico.forIssue(workspaceSlug, projectId, rootIssueId)
  );

  // Só na subtarefa de uma origem: tarefa gerada e tarefa comum não têm agenda.
  if (papel?.role !== "source" || !papel.rule) return null;

  const ehAdmin = allowPermissions([EUserPermissions.ADMIN], EUserPermissionsLevel.PROJECT, workspaceSlug, projectId);
  if (!ehAdmin) return null;

  return (
    <SubtaskDueField workspaceSlug={workspaceSlug} projectId={projectId} regra={papel.rule} subtaskId={subtaskId} />
  );
});
