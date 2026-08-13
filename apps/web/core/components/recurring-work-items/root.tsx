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
import { ExternalLink, Pause, Pencil, Play, Repeat, Trash2 } from "lucide-react";
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
import { chaveDaLista, chaveDaRegra } from "./section";

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

  const alternarAtiva = async (regra: TRecurringWorkItem) => {
    await servico.update(workspaceSlug, projectId, regra.id, { is_active: !regra.is_active });
    mutate();
    mutateGlobal(chaveDaRegra(regra.source_issue));
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
              className={cn(
                "group flex items-center justify-between gap-3 rounded-md border border-subtle bg-surface-1 px-4 py-3",
                { "opacity-60": !regra.is_active || !!origem?.archived_at }
              )}
            >
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
              <div className="flex flex-shrink-0 items-center gap-1">
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
          );
        })}
      </div>
    </>
  );
});
