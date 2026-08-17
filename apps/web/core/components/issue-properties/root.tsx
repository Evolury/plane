/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: painel das propriedades personalizadas do projeto (ADR 0011, P1).
//
// A confirmação de exclusão mostra QUANTAS TAREFAS perdem o preenchimento —
// tarefas, e não linhas, porque seleção múltipla grava uma linha por opção e o
// número maior assustaria com uma resposta que não é a da pergunta.
//
// Excluir nunca é bloqueado: bloquear criaria o incentivo perverso de sempre,
// que é apagar a propriedade inteira para se livrar do impedimento.

import { useState } from "react";
import { observer } from "mobx-react";
import useSWR from "swr";
import { AlertTriangle, Eye, Pause, Pencil, Play, Plus, Trash2 } from "lucide-react";
// Evolury: ícone da propriedade (ADR 0011)
import { iconeDaPropriedade } from "./icones";
import { useTranslation } from "@plane/i18n";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { Button } from "@plane/propel/button";
import { Tooltip } from "@plane/propel/tooltip";
import type { TIssueProperty } from "@plane/types";
import { AlertModalCore } from "@plane/ui";
import { cn } from "@plane/utils";
// services
import { IssuePropertyService } from "@/services/issue-property.service";
// local imports
import { IssuePropertyForm } from "./form";
import { revalidarValoresDoProjeto } from "./store";

const servico = new IssuePropertyService();

export const chaveDaLista = (workspaceSlug: string, projectId: string) =>
  `ISSUE_PROPERTIES_${workspaceSlug}_${projectId}`;

type TProps = {
  workspaceSlug: string;
  projectId: string;
};

export const IssuePropertiesRoot = observer(function IssuePropertiesRoot(props: TProps) {
  const { workspaceSlug, projectId } = props;
  const { t } = useTranslation();
  const [formAberto, setFormAberto] = useState(false);
  const [emEdicao, setEmEdicao] = useState<TIssueProperty | undefined>(undefined);
  const [aExcluir, setAExcluir] = useState<TIssueProperty | undefined>(undefined);
  const [excluindo, setExcluindo] = useState(false);

  const { data, mutate } = useSWR(workspaceSlug && projectId ? chaveDaLista(workspaceSlug, projectId) : null, () =>
    servico.list(workspaceSlug, projectId)
  );

  const rotulo = (chave: string, params?: Record<string, string | number>) => t(`issue_properties.${chave}`, params);

  const propriedades = data?.properties ?? [];
  const teto = data?.cap ?? 30;
  const restantes = teto - propriedades.length;

  const alternarAtiva = async (propriedade: TIssueProperty) => {
    await servico.update(workspaceSlug, projectId, propriedade.id, { is_active: !propriedade.is_active });
    revalidarValoresDoProjeto(projectId);
    mutate();
  };

  const excluir = async () => {
    if (!aExcluir) return;
    setExcluindo(true);
    try {
      await servico.destroy(workspaceSlug, projectId, aExcluir.id);
      revalidarValoresDoProjeto(projectId);
      setToast({ type: TOAST_TYPE.SUCCESS, title: t("toast.success"), message: rotulo("toast.deleted") });
      mutate();
    } catch {
      setToast({ type: TOAST_TYPE.ERROR, title: t("toast.error"), message: t("common.something_went_wrong") });
    } finally {
      setExcluindo(false);
      setAExcluir(undefined);
    }
  };

  const abrir = (propriedade?: TIssueProperty) => {
    setEmEdicao(propriedade);
    setFormAberto(true);
  };

  return (
    <>
      <IssuePropertyForm
        workspaceSlug={workspaceSlug}
        projectId={projectId}
        propriedade={emEdicao}
        isOpen={formAberto}
        onClose={() => setFormAberto(false)}
        onSaved={() => mutate()}
      />
      <AlertModalCore
        isOpen={!!aExcluir}
        handleClose={() => setAExcluir(undefined)}
        handleSubmit={excluir}
        isSubmitting={excluindo}
        title={rotulo("delete.title")}
        content={rotulo("delete.description", { count: aExcluir?.values_count ?? 0 })}
        primaryButtonText={{ loading: t("common.loading"), default: rotulo("delete.title") }}
        secondaryButtonText={t("common.cancel")}
      />

      <div className="mt-6 flex items-center justify-between gap-3">
        <p className="text-12 text-tertiary">
          {restantes <= 0
            ? rotulo("settings.cap_reached", { count: teto })
            : restantes <= 5
              ? rotulo("settings.cap_near", { count: restantes })
              : ""}
        </p>
        <Button variant="primary" size="sm" onClick={() => abrir()} disabled={restantes <= 0}>
          <Plus className="size-3.5" />
          {rotulo("settings.new")}
        </Button>
      </div>

      <div className="mt-4 space-y-2">
        {propriedades.length === 0 && (
          <div className="grid place-items-center rounded-md border border-dashed border-subtle py-12 text-13 text-tertiary">
            {rotulo("settings.empty")}
          </div>
        )}
        {propriedades.map((propriedade) => (
          <div
            key={propriedade.id}
            className={cn("group rounded-md border border-subtle bg-surface-1 px-4 py-3", {
              "opacity-60": !propriedade.is_active,
            })}
          >
            <div className="flex items-center justify-between gap-3">
              <div className="min-w-0">
                <p className="flex items-center gap-2 truncate text-13 font-medium">
                  {/* Evolury: o ícone escolhido, onde ele é escolhido (ADR 0011) */}
                  {(() => {
                    const Icone = iconeDaPropriedade(propriedade);
                    return <Icone className="size-3.5 shrink-0 text-tertiary" />;
                  })()}
                  {propriedade.name}
                  {propriedade.is_required && <span className="text-danger-primary">*</span>}
                  {propriedade.show_on_card && (
                    <Tooltip tooltipContent={rotulo("form.show_on_card")}>
                      <Eye className="size-3 text-tertiary" />
                    </Tooltip>
                  )}
                </p>
                <p className="truncate text-11 text-tertiary">
                  {rotulo(`type.${propriedade.property_type}`)}
                  {propriedade.property_type === "currency" && ` · ${propriedade.currency}`}
                  {" · "}
                  {propriedade.values_count === 0
                    ? rotulo("usage.none")
                    : rotulo("usage.some", { count: propriedade.values_count })}
                  {!propriedade.is_active && ` · ${rotulo("state.inactive")}`}
                </p>
              </div>
              <div className="flex shrink-0 items-center gap-1">
                <Tooltip tooltipContent={rotulo(propriedade.is_active ? "state.deactivate" : "state.activate")}>
                  <button
                    type="button"
                    onClick={() => alternarAtiva(propriedade)}
                    className="grid size-7 place-items-center rounded-sm text-secondary hover:bg-layer-1 hover:text-primary"
                  >
                    {propriedade.is_active ? <Pause className="size-3.5" /> : <Play className="size-3.5" />}
                  </button>
                </Tooltip>
                <button
                  type="button"
                  onClick={() => abrir(propriedade)}
                  className="grid size-7 place-items-center rounded-sm text-secondary hover:bg-layer-1 hover:text-primary"
                >
                  <Pencil className="size-3.5" />
                </button>
                <button
                  type="button"
                  onClick={() => setAExcluir(propriedade)}
                  className="grid size-7 place-items-center rounded-sm text-secondary hover:bg-danger-subtle hover:text-danger-primary"
                >
                  <Trash2 className="size-3.5" />
                </button>
              </div>
            </div>

            {!!propriedade.options?.length && (
              <div className="mt-2 flex flex-wrap gap-1.5">
                {propriedade.options.map((opcao) => (
                  <span
                    key={opcao.id}
                    className="flex items-center gap-1.5 rounded-full border border-subtle px-2 py-0.5 text-11 text-secondary"
                  >
                    <span className="size-2 rounded-full" style={{ backgroundColor: opcao.color || "#6b7280" }} />
                    {opcao.name}
                  </span>
                ))}
              </div>
            )}

            {/* Desativada preserva os valores — o aviso é o que impede alguém
                de excluir achando que desativar não guardou nada. */}
            {!propriedade.is_active && propriedade.values_count > 0 && (
              <div className="mt-2 flex items-start gap-2 rounded-md bg-warning-subtle px-3 py-2 text-12 text-warning-primary">
                <AlertTriangle className="mt-0.5 size-3.5 shrink-0" />
                <span className="min-w-0 wrap-break-word whitespace-normal">{rotulo("state.deactivate_hint")}</span>
              </div>
            )}
          </div>
        ))}
      </div>
    </>
  );
});
