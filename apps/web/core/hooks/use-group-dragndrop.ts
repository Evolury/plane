/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useParams } from "next/navigation";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { ehChaveDePropriedade } from "@plane/constants";
import type { EIssuesStoreType, TIssue, TIssueGroupByOptions, TIssueOrderByOptions } from "@plane/types";
import { translate, useTranslation } from "@plane/i18n";
// Evolury: propriedade personalizada (ADR 0011)
import { idDaChave } from "@/components/issue-properties/cache";
import { revalidarValoresDoProjeto } from "@/components/issue-properties/store";
import type { GroupDropLocation } from "@/components/issues/issue-layouts/utils";
import { handleGroupDragDrop } from "@/components/issues/issue-layouts/utils";
import { IssuePropertyService } from "@/services/issue-property.service";
import { ISSUE_FILTER_DEFAULT_DATA } from "@/store/issue/helpers/base-issues.store";
import { useIssueDetail } from "./store/use-issue-detail";
import { useIssues } from "./store/use-issues";
import { useIssuesActions } from "./use-issues-actions";

const servicoDePropriedade = new IssuePropertyService();

type DNDStoreType =
  | EIssuesStoreType.PROJECT
  | EIssuesStoreType.MODULE
  | EIssuesStoreType.CYCLE
  | EIssuesStoreType.PROJECT_VIEW
  | EIssuesStoreType.PROFILE
  | EIssuesStoreType.ARCHIVED
  | EIssuesStoreType.WORKSPACE_DRAFT
  | EIssuesStoreType.TEAM
  | EIssuesStoreType.TEAM_VIEW
  | EIssuesStoreType.EPIC
  | EIssuesStoreType.TEAM_PROJECT_WORK_ITEMS
  // Evolury: quadro de "Minhas tarefas" (drag entre etapas pessoais, ADR 0002)
  | EIssuesStoreType.MY_TASKS;

export const useGroupIssuesDragNDrop = (
  storeType: DNDStoreType,
  orderBy: TIssueOrderByOptions | undefined,
  groupBy: TIssueGroupByOptions | undefined,
  subGroupBy?: TIssueGroupByOptions
) => {
  const { workspaceSlug } = useParams();
  const { t } = useTranslation();

  const {
    issue: { getIssueById },
  } = useIssueDetail();
  const { updateIssue } = useIssuesActions(storeType);
  const { issues } = useIssues(storeType);
  // A loja inteira, e não só os métodos: mover cartão entre colunas de
  // propriedade precisa de `issueUpdate` com `shouldSync: false` — o mesmo
  // caminho que a etapa pessoal usa para atualizar a tela sem PATCH.
  const { getIssueIds, addCycleToIssue, removeCycleFromIssue, changeModulesInIssue } = issues;

  /**
   * Evolury: grava o valor da propriedade que o arrasto escolheu (ADR 0011).
   *
   * A tela se move primeiro, e por um caminho que não faz requisição:
   * `issueUpdate` com `shouldSync: false` grava o campo anotado no store e
   * deixa `updateIssueList` reagrupar o cartão. É o mesmo caminho da etapa
   * pessoal de "Minhas tarefas".
   *
   * Depois vem a gravação de verdade. Se ela falhar, o cartão volta para a
   * coluna de origem — sem isso, o quadro mostraria uma organização que o
   * banco não tem.
   */
  const gravarPropriedadeDoArrasto = async (
    projectId: string,
    issueId: string,
    chave: string,
    destino: string | null,
    errorToastProps: Parameters<typeof setToast>[0]
  ) => {
    const propertyId = idDaChave(chave);
    if (!propertyId || !workspaceSlug) return;
    // Rascunhos de workspace são a única loja sem `issueUpdate`, e também a
    // única sem projeto na rota — sem projeto não há propriedade a oferecer,
    // então este caminho não é alcançável de lá. A guarda existe para o
    // compilador provar isso, e não por dúvida.
    if (!("issueUpdate" in issues)) return;
    const slug = workspaceSlug.toString();
    const anterior = (getIssueById(issueId) as Record<string, unknown> | undefined)?.[chave] ?? null;

    await issues.issueUpdate(slug, projectId, issueId, { [chave]: destino } as Partial<TIssue>, false);
    try {
      // "Nenhum" chega como null, e escrever vazio é como o servidor apaga.
      await servicoDePropriedade.setValue(slug, projectId, issueId, propertyId, destino);
      // A pastilha do cartão lê de uma chave própria, do projeto inteiro: sem
      // isto o cartão mudaria de coluna e continuaria com a pastilha antiga.
      revalidarValoresDoProjeto(projectId);
    } catch {
      await issues.issueUpdate(slug, projectId, issueId, { [chave]: anterior } as Partial<TIssue>, false);
      setToast(errorToastProps);
    }
  };

  /**
   * update Issue on Drop, checks if modules or cycles are changed and then calls appropriate functions
   * @param projectId
   * @param issueId
   * @param data
   * @param issueUpdates
   */
  const updateIssueOnDrop = async (
    projectId: string,
    issueId: string,
    data: Partial<TIssue>,
    issueUpdates: {
      [groupKey: string]: {
        ADD: string[];
        REMOVE: string[];
      };
    }
  ) => {
    const errorToastProps = {
      type: TOAST_TYPE.ERROR,
      title: t("toast.error"),
      message: translate("ui.error_while_updating_work_item"),
    };
    const moduleKey = ISSUE_FILTER_DEFAULT_DATA["module"];
    const cycleKey = ISSUE_FILTER_DEFAULT_DATA["cycle"];

    const isModuleChanged = Object.keys(data).includes(moduleKey);
    const isCycleChanged = Object.keys(data).includes(cycleKey);

    if (isCycleChanged && workspaceSlug) {
      if (data[cycleKey]) {
        addCycleToIssue(workspaceSlug.toString(), projectId, data[cycleKey]?.toString() ?? "", issueId).catch(() =>
          setToast(errorToastProps)
        );
      } else {
        removeCycleFromIssue(workspaceSlug.toString(), projectId, issueId).catch(() => setToast(errorToastProps));
      }
      delete data[cycleKey];
    }

    if (isModuleChanged && workspaceSlug && issueUpdates[moduleKey]) {
      changeModulesInIssue(
        workspaceSlug.toString(),
        projectId,
        issueId,
        issueUpdates[moduleKey].ADD,
        issueUpdates[moduleKey].REMOVE
      ).catch(() => setToast(errorToastProps));
      delete data[moduleKey];
    }

    // Evolury: quadro agrupado por propriedade personalizada (ADR 0011).
    //
    // Sai do PATCH pelo mesmo motivo de ciclo e módulo acima: o valor não é
    // campo da tarefa, e o endpoint próprio é quem registra o histórico e
    // acorda as automações. O que fica em `data` é o `sort_order`, que é campo
    // e preserva a ordenação manual dentro da coluna.
    //
    // Trata TODAS as chaves: com quadro agrupado e subagrupado por duas
    // propriedades, um arrasto muda as duas.
    const destinosDePropriedade = Object.keys(data)
      .filter(ehChaveDePropriedade)
      .map((chave) => ({ chave, destino: (data as Record<string, unknown>)[chave] as string | null }));
    for (const { chave } of destinosDePropriedade) delete (data as Record<string, unknown>)[chave];
    await Promise.all(
      destinosDePropriedade.map(({ chave, destino }) =>
        gravarPropriedadeDoArrasto(projectId, issueId, chave, destino, errorToastProps)
      )
    );

    updateIssue && updateIssue(projectId, issueId, data).catch(() => setToast(errorToastProps));
  };

  const handleOnDrop = async (source: GroupDropLocation, destination: GroupDropLocation) => {
    if (
      source.columnId &&
      destination.columnId &&
      destination.columnId === source.columnId &&
      destination.id === source.id
    )
      return;

    await handleGroupDragDrop(
      source,
      destination,
      getIssueById,
      getIssueIds,
      updateIssueOnDrop,
      groupBy,
      subGroupBy,
      orderBy !== "sort_order"
    ).catch((err) => {
      setToast({
        title: t("toast.error"),
        type: TOAST_TYPE.ERROR,
        message: err?.detail ?? translate("ui.failed_to_perform_this_action"),
      });
    });
  };

  return handleOnDrop;
};
