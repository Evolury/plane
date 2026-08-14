/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: painel das tarefas recorrentes do projeto (ADR 0010, revisão).
//
// Sem botão de criar: a recorrência é ativada na própria tarefa, na seção
// "Repetir". Esta página é a auditoria — o que este projeto gera sozinho.

import { useState } from "react";
import { observer } from "mobx-react";
import Link from "next/link";
import useSWR, { mutate as mutateGlobal } from "swr";
import { AlertTriangle, ExternalLink, Pause, Pencil, Play, Repeat, Trash2 } from "lucide-react";
import { useTranslation } from "@plane/i18n";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { Tooltip } from "@plane/propel/tooltip";
import type { TRecurringWorkItem } from "@plane/types";
import { AlertModalCore } from "@plane/ui";
import { cn, generateWorkItemLink, renderFormattedDate } from "@plane/utils";
// hooks
import { useProject } from "@/hooks/store/use-project";
// services
import { RecurringWorkItemService } from "@/services/recurring-work-item.service";
// local imports
import { RecurringWorkItemForm } from "./form";
import { chaveDaLista, chaveDaRegra, chaveDosSelos } from "./section";

const servico = new RecurringWorkItemService();

type TRootProps = {
  workspaceSlug: string;
  projectId: string;
};

export const RecurringWorkItemsRoot = observer(function RecurringWorkItemsRoot(props: TRootProps) {
  const { workspaceSlug, projectId } = props;
  const { t } = useTranslation();
  const { getProjectIdentifierById } = useProject();
  // states
  const [emEdicao, setEmEdicao] = useState<TRecurringWorkItem | undefined>(undefined);
  const [aExcluir, setAExcluir] = useState<TRecurringWorkItem | undefined>(undefined);
  const [excluindo, setExcluindo] = useState(false);

  const identificador = getProjectIdentifierById(projectId);

  const { data: regras, mutate } = useSWR(
    workspaceSlug && projectId ? chaveDaLista(workspaceSlug, projectId) : null,
    () => servico.list(workspaceSlug, projectId)
  );

  const comInativo = regras?.filter((regra) => regra.inactive_assignees?.length) ?? [];

  const alternarAtiva = async (regra: TRecurringWorkItem) => {
    await servico.update(workspaceSlug, projectId, regra.id, { is_active: !regra.is_active });
    mutate();
    mutateGlobal(chaveDaRegra(regra.source_issue));
    mutateGlobal(chaveDosSelos(workspaceSlug, projectId));
  };

  // O conserto inline do alerta: tira o responsável que saiu da tarefa de
  // origem. A geração já o descartava — isto resolve a raiz.
  const removerInativo = async (regra: TRecurringWorkItem, userId: string) => {
    try {
      await servico.transferAssignee(workspaceSlug, projectId, userId);
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: t("toast.success"),
        message: t("recurring_work_items.inactive_assignee.removed"),
      });
      mutate();
      mutateGlobal(chaveDaRegra(regra.source_issue));
    } catch {
      setToast({ type: TOAST_TYPE.ERROR, title: t("toast.error"), message: t("common.something_went_wrong") });
    }
  };

  const excluir = async () => {
    if (!aExcluir) return;
    setExcluindo(true);
    try {
      await servico.destroy(workspaceSlug, projectId, aExcluir.id);
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: t("toast.success"),
        message: t("recurring_work_items.toasts.delete.success.title"),
      });
      mutate();
      mutateGlobal(chaveDaRegra(aExcluir.source_issue));
      mutateGlobal(chaveDosSelos(workspaceSlug, projectId));
    } catch {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("toast.error"),
        message: t("recurring_work_items.toasts.delete.error.title"),
      });
    } finally {
      setExcluindo(false);
      setAExcluir(undefined);
    }
  };

  return (
    <>
      <RecurringWorkItemForm
        workspaceSlug={workspaceSlug}
        projectId={projectId}
        regra={emEdicao}
        isOpen={!!emEdicao}
        onClose={() => setEmEdicao(undefined)}
        onSaved={() => mutate()}
      />
      <AlertModalCore
        isOpen={!!aExcluir}
        handleClose={() => setAExcluir(undefined)}
        handleSubmit={excluir}
        isSubmitting={excluindo}
        title={t("recurring_work_items.disable_confirmation.title")}
        content={t("recurring_work_items.disable_confirmation.description")}
        primaryButtonText={{ loading: t("common.loading"), default: t("recurring_work_items.actions.delete") }}
        secondaryButtonText={t("common.cancel")}
      />

      {!!comInativo.length && (
        <div className="mt-6 flex items-center gap-2 rounded-md bg-warning-subtle px-4 py-3 text-13 text-warning-primary">
          <AlertTriangle className="size-4 shrink-0" />
          <span>{t("recurring_work_items.inactive_assignee.counter", { count: comInativo.length })}</span>
        </div>
      )}

      <div className="mt-6 space-y-2">
        {regras?.length === 0 && (
          <div className="grid place-items-center rounded-md border border-dashed border-subtle py-12 text-13 text-tertiary">
            {t("recurring_work_items.list.empty")}
          </div>
        )}
        {regras?.map((regra) => {
          const origem = regra.source_issue_detail;
          return (
            <div
              key={regra.id}
              className={cn("group rounded-md border border-subtle bg-surface-1 px-4 py-3", {
                "opacity-60": !regra.is_active || !!origem?.archived_at,
              })}
            >
              <div className="flex items-center justify-between gap-3">
                <div className="flex min-w-0 items-center gap-3">
                  <Repeat className="size-4 flex-shrink-0 text-tertiary" />
                  <div className="min-w-0">
                    <p className="truncate text-13 font-medium">
                      {origem && (
                        <span className="font-normal mr-2 text-11 text-tertiary">
                          {identificador}-{origem.sequence_id}
                        </span>
                      )}
                      {origem?.name ?? "—"}
                    </p>
                    <p className="truncate text-11 text-tertiary">
                      {origem?.archived_at
                        ? t("recurring_work_items.section.archived_paused")
                        : regra.is_active
                          ? regra.next_occurrences?.length
                            ? `${t("recurring_work_items.list.next")}: ${regra.next_occurrences.map((d) => renderFormattedDate(d)).join(" · ")}`
                            : t("recurring_work_items.preview.empty")
                          : t("recurring_work_items.list.paused")}
                    </p>
                  </div>
                </div>
                <div className="flex shrink-0 items-center gap-1">
                  <Tooltip tooltipContent={t("recurring_work_items.list.view_task")}>
                    <Link
                      href={generateWorkItemLink({
                        workspaceSlug,
                        projectId,
                        issueId: regra.source_issue,
                        projectIdentifier: identificador,
                        sequenceId: origem?.sequence_id,
                      })}
                      className="grid size-7 place-items-center rounded-sm text-secondary hover:bg-layer-1 hover:text-primary"
                    >
                      <ExternalLink className="size-3.5" />
                    </Link>
                  </Tooltip>
                  <Tooltip
                    tooltipContent={t(
                      regra.is_active ? "recurring_work_items.actions.pause" : "recurring_work_items.actions.resume"
                    )}
                  >
                    <button
                      type="button"
                      onClick={() => alternarAtiva(regra)}
                      className="grid size-7 place-items-center rounded-sm text-secondary hover:bg-layer-1 hover:text-primary"
                    >
                      {regra.is_active ? <Pause className="size-3.5" /> : <Play className="size-3.5" />}
                    </button>
                  </Tooltip>
                  <Tooltip tooltipContent={t("recurring_work_items.actions.edit")}>
                    <button
                      type="button"
                      onClick={() => setEmEdicao(regra)}
                      className="grid size-7 place-items-center rounded-sm text-secondary hover:bg-layer-1 hover:text-primary"
                    >
                      <Pencil className="size-3.5" />
                    </button>
                  </Tooltip>
                  <Tooltip tooltipContent={t("recurring_work_items.actions.delete")}>
                    <button
                      type="button"
                      onClick={() => setAExcluir(regra)}
                      className="grid size-7 place-items-center rounded-sm text-secondary hover:bg-danger-subtle hover:text-danger-primary"
                    >
                      <Trash2 className="size-3.5" />
                    </button>
                  </Tooltip>
                </div>
              </div>
              {!!regra.inactive_assignees?.length && (
                <div className="mt-2 flex flex-wrap items-center gap-2 rounded-md bg-warning-subtle px-3 py-2 text-12 text-warning-primary">
                  <AlertTriangle className="size-3.5 shrink-0" />
                  <span>
                    {regra.inactive_assignees.length === 1
                      ? t("recurring_work_items.inactive_assignee.one", {
                          name: regra.inactive_assignees[0].display_name,
                        })
                      : t("recurring_work_items.inactive_assignee.many", {
                          names: regra.inactive_assignees.map((p) => p.display_name).join(", "),
                        })}
                  </span>
                  <span className="text-tertiary">{t("recurring_work_items.inactive_assignee.explanation")}</span>
                  {regra.inactive_assignees.map((pessoa) => (
                    <button
                      key={pessoa.id}
                      type="button"
                      onClick={() => removerInativo(regra, pessoa.id)}
                      className="rounded-sm border border-subtle px-2 py-0.5 text-11 text-secondary hover:bg-layer-1 hover:text-primary"
                    >
                      {t("recurring_work_items.inactive_assignee.remove")}
                    </button>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </>
  );
});
