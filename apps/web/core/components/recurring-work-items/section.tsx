/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: a seção "Repetir" do cartão da tarefa (ADR 0010, revisão 13/08/2026).
//
// A recorrência mora aqui, não num formulário paralelo: a tarefa é o molde.
// A mesma seção conta os três papéis — origem (agenda e controles), gerada
// (trava com o rastro "gerada pela recorrência de X") e nenhuma (interruptor).

import { useState } from "react";
import { observer } from "mobx-react";
import Link from "next/link";
import useSWR, { mutate as mutateGlobal } from "swr";
import { Pause, Play, Pencil, Repeat } from "lucide-react";
import { useTranslation } from "@plane/i18n";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { Tooltip } from "@plane/propel/tooltip";
import { EUserPermissions, EUserPermissionsLevel } from "@plane/constants";
import { AlertModalCore, ToggleSwitch } from "@plane/ui";
import { generateWorkItemLink, renderFormattedDate } from "@plane/utils";
// hooks
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
import { useProject } from "@/hooks/store/use-project";
import { useUserPermissions } from "@/hooks/store/user";
// services
import { RecurringWorkItemService } from "@/services/recurring-work-item.service";
// local imports
import { RecurringWorkItemForm } from "./form";

const servico = new RecurringWorkItemService();

export const chaveDaRegra = (issueId: string) => `RECURRING_ROLE_${issueId}`;
export const chaveDaLista = (workspaceSlug: string, projectId: string) =>
  `RECURRING_WORK_ITEMS_${workspaceSlug}_${projectId}`;

type TSectionProps = {
  workspaceSlug: string;
  projectId: string;
  issueId: string;
};

export const RecurrenceSection = observer(function RecurrenceSection(props: TSectionProps) {
  const { workspaceSlug, projectId, issueId } = props;
  const { t } = useTranslation();
  // states
  const [formAberto, setFormAberto] = useState(false);
  const [confirmandoDesativar, setConfirmandoDesativar] = useState(false);
  const [desativando, setDesativando] = useState(false);
  // store hooks
  const { allowPermissions } = useUserPermissions();
  const { getProjectIdentifierById } = useProject();
  const {
    issue: { getIssueById },
    toggleRecurrenceModal,
  } = useIssueDetail();

  // O modal é portado para fora do peek; sem avisar o store, o primeiro clique
  // dentro dele fecha o peek e desmonta tudo antes de o clique agir — o mesmo
  // defeito da confirmação de conclusão (ADR 0009).
  const abrirForm = (aberto: boolean) => {
    setFormAberto(aberto);
    toggleRecurrenceModal(aberto ? issueId : null);
  };
  const abrirConfirmacao = (aberto: boolean) => {
    setConfirmandoDesativar(aberto);
    toggleRecurrenceModal(aberto ? issueId : null);
  };
  // derived values
  const ehAdmin = allowPermissions([EUserPermissions.ADMIN], EUserPermissionsLevel.PROJECT, workspaceSlug, projectId);
  const tarefa = getIssueById(issueId);
  const identificador = getProjectIdentifierById(projectId);

  const { data: papel, mutate } = useSWR(workspaceSlug && projectId && issueId ? chaveDaRegra(issueId) : null, () =>
    servico.forIssue(workspaceSlug, projectId, issueId)
  );

  const atualizarTudo = () => {
    mutate();
    mutateGlobal(chaveDaLista(workspaceSlug, projectId));
  };

  if (!papel) return null;

  const regra = papel.rule;
  const rotulo = (chave: string, params?: Record<string, string>) => t(`recurring_work_items.${chave}`, params);

  // Tarefa gerada: a trava É o rastro — e o rastro é o caminho de volta.
  // Meses depois, quem está na frente da pessoa é a ocorrência da semana;
  // a origem, concluída, dorme sob o movimento do projeto. Um clique resolve.
  if (papel.role === "occurrence") {
    const origem = regra?.source_issue_detail;
    const texto = rotulo("section.generated_by", {
      id: origem ? `${identificador}-${origem.sequence_id}` : "—",
    });
    return (
      <div className="flex items-center gap-2 py-2 text-12 text-tertiary">
        <Repeat className="size-3.5 flex-shrink-0" />
        {origem && regra ? (
          <Link
            href={generateWorkItemLink({
              workspaceSlug,
              projectId,
              issueId: regra.source_issue,
              projectIdentifier: identificador,
              sequenceId: origem.sequence_id,
            })}
            className="hover:text-primary hover:underline"
          >
            {texto}
          </Link>
        ) : (
          <span>{texto}</span>
        )}
      </div>
    );
  }

  // Subtarefa não tem recorrência própria — a seção nem oferece o interruptor.
  if (papel.role === null && tarefa?.parent_id) return null;

  const alternarAtiva = async () => {
    if (!regra) return;
    await servico.update(workspaceSlug, projectId, regra.id, { is_active: !regra.is_active });
    atualizarTudo();
  };

  const desativar = async () => {
    if (!regra) return;
    setDesativando(true);
    try {
      await servico.destroy(workspaceSlug, projectId, regra.id);
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: t("toast.success"),
        message: t("recurring_work_items.toasts.delete.success.title"),
      });
      atualizarTudo();
    } catch {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("toast.error"),
        message: t("recurring_work_items.toasts.delete.error.title"),
      });
    } finally {
      setDesativando(false);
      abrirConfirmacao(false);
    }
  };

  const origemArquivada = !!regra?.source_issue_detail?.archived_at;

  return (
    <>
      <RecurringWorkItemForm
        workspaceSlug={workspaceSlug}
        projectId={projectId}
        sourceIssueId={issueId}
        regra={regra ?? undefined}
        isOpen={formAberto}
        onClose={() => abrirForm(false)}
        onSaved={atualizarTudo}
      />
      <AlertModalCore
        isOpen={confirmandoDesativar}
        handleClose={() => abrirConfirmacao(false)}
        handleSubmit={desativar}
        isSubmitting={desativando}
        title={rotulo("disable_confirmation.title")}
        content={rotulo("disable_confirmation.description")}
        primaryButtonText={{ loading: t("common.loading"), default: rotulo("disable_confirmation.title") }}
        secondaryButtonText={t("common.cancel")}
      />

      <div className="py-2">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 text-13 text-secondary">
            <Repeat className="size-3.5 flex-shrink-0" />
            <span>{rotulo("section.title")}</span>
          </div>
          <Tooltip tooltipContent={rotulo("settings.create_button.no_permission")} disabled={ehAdmin}>
            <div>
              <ToggleSwitch
                value={papel.role === "source"}
                onChange={() => {
                  if (!ehAdmin) return;
                  if (papel.role === "source") abrirConfirmacao(true);
                  else abrirForm(true);
                }}
                disabled={!ehAdmin}
                size="sm"
              />
            </div>
          </Tooltip>
        </div>

        {papel.role === "source" && regra && (
          <div className="mt-2 flex items-center justify-between gap-2 rounded-md bg-layer-2 px-3 py-2">
            <p className="min-w-0 truncate text-12 text-tertiary">
              {origemArquivada
                ? rotulo("section.archived_paused")
                : regra.is_active
                  ? regra.next_occurrences?.length
                    ? `${t("recurring_work_items.list.next")}: ${regra.next_occurrences.map((d) => renderFormattedDate(d)).join(" · ")}`
                    : t("recurring_work_items.preview.empty")
                  : t("recurring_work_items.list.paused")}
            </p>
            {ehAdmin && (
              <div className="flex flex-shrink-0 items-center gap-1">
                <Tooltip
                  tooltipContent={t(
                    regra.is_active ? "recurring_work_items.actions.pause" : "recurring_work_items.actions.resume"
                  )}
                >
                  <button
                    type="button"
                    onClick={alternarAtiva}
                    className="grid size-6 place-items-center rounded-sm text-secondary hover:bg-layer-1 hover:text-primary"
                  >
                    {regra.is_active ? <Pause className="size-3" /> : <Play className="size-3" />}
                  </button>
                </Tooltip>
                <Tooltip tooltipContent={t("recurring_work_items.actions.edit")}>
                  <button
                    type="button"
                    onClick={() => abrirForm(true)}
                    className="grid size-6 place-items-center rounded-sm text-secondary hover:bg-layer-1 hover:text-primary"
                  >
                    <Pencil className="size-3" />
                  </button>
                </Tooltip>
              </div>
            )}
          </div>
        )}
      </div>
    </>
  );
});
