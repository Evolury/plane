/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: a lista de automações personalizadas do projeto (ADR 0012).
//
// Cada linha mostra a regra DITA, e não os seus campos: "Quando a prioridade
// mudar para Urgente, então atribuir a quem disparou". Uma lista de nomes
// obrigaria a abrir cada regra para saber o que ela faz, e ninguém audita o
// próprio processo assim.
//
// Quando o motor desliga uma regra sozinho (teto de execuções), o motivo
// aparece na linha. Regra que emudece sem explicação é pior do que regra que
// erra.

import { useState } from "react";
import { observer } from "mobx-react";
import { useNavigate } from "react-router";
import useSWR from "swr";
import { AlertTriangle, Pencil, Plus, Trash2 } from "lucide-react";
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import type { TAutomation } from "@plane/types";
import { AlertModalCore, Loader, ToggleSwitch } from "@plane/ui";
import { renderFormattedDate } from "@plane/utils";
import { AutomationService } from "@/services/automation.service";
import { FraseDaAutomacao } from "./frase";
import { useRotulos } from "./rotulos";

const servico = new AutomationService();

export const chaveDaListaDeAutomacoes = (workspaceSlug: string, projectId: string) =>
  `AUTOMATIONS_${workspaceSlug}_${projectId}`;

type TProps = {
  workspaceSlug: string;
  projectId: string;
};

export const ListaDeAutomacoes = observer(function ListaDeAutomacoes(props: TProps) {
  const { workspaceSlug, projectId } = props;
  const { t } = useTranslation();
  const navigate = useNavigate();
  const rotulos = useRotulos(workspaceSlug, projectId);
  const [aExcluir, setAExcluir] = useState<TAutomation | undefined>(undefined);
  const [excluindo, setExcluindo] = useState(false);

  const { data, isLoading, mutate } = useSWR(
    workspaceSlug && projectId ? chaveDaListaDeAutomacoes(workspaceSlug, projectId) : null,
    () => servico.list(workspaceSlug, projectId)
  );

  const regras = data ?? [];

  const alternarAtiva = async (regra: TAutomation) => {
    try {
      await servico.update(workspaceSlug, projectId, regra.id, { is_active: !regra.is_active });
      void mutate();
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
        title: t("automations.toasts.delete.success.title"),
        message: t("automations.toasts.delete.success.message", { name: aExcluir.name }),
      });
      void mutate();
    } catch {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("automations.toasts.delete.error.title"),
        message: t("automations.toasts.delete.error.message"),
      });
    } finally {
      setExcluindo(false);
      setAExcluir(undefined);
    }
  };

  const abrir = (automationId: string) =>
    navigate(`/${workspaceSlug}/settings/projects/${projectId}/automations/${automationId}/`);

  return (
    <>
      <AlertModalCore
        isOpen={Boolean(aExcluir)}
        handleClose={() => setAExcluir(undefined)}
        handleSubmit={() => void excluir()}
        isSubmitting={excluindo}
        title={t("automations.delete_modal.heading")}
        content={aExcluir?.name ?? ""}
      />

      <div className="mt-8 border-t border-subtle pt-6">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h3 className="text-15 font-medium text-primary">{t("automations.settings.title")}</h3>
            <p className="text-13 text-tertiary">{t("automations.settings.description")}</p>
          </div>
          <Button variant="primary" size="sm" onClick={() => abrir("novo")}>
            <Plus className="size-3.5" />
            {t("automations.settings.create_automation")}
          </Button>
        </div>

        {isLoading ? (
          <Loader className="flex flex-col gap-2">
            <Loader.Item height="56px" />
            <Loader.Item height="56px" />
          </Loader>
        ) : regras.length === 0 ? (
          <div className="rounded-md border border-dashed border-subtle px-6 py-10 text-center">
            <p className="text-13 font-medium text-secondary">{t("automations.empty_state.no_automations.title")}</p>
            <p className="mx-auto mt-1 max-w-lg text-12 text-tertiary">
              {t("automations.empty_state.no_automations.description")}
            </p>
          </div>
        ) : (
          <ul className="flex flex-col divide-y divide-subtle rounded-md border border-subtle">
            {regras.map((regra: TAutomation) => (
              <li key={regra.id} className="flex items-start gap-3 px-4 py-3">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="truncate text-13 font-medium text-primary">{regra.name}</span>
                    {regra.disabled_reason && (
                      <span className="text-warning flex items-center gap-1 text-11">
                        <AlertTriangle className="size-3" />
                        {regra.disabled_reason}
                      </span>
                    )}
                  </div>
                  <FraseDaAutomacao regra={regra} rotulos={rotulos} className="mt-0.5" />
                  {regra.last_run_at && (
                    <p className="mt-0.5 text-11 text-tertiary">
                      {t("automations.table.last_run_on")}: {renderFormattedDate(regra.last_run_at)}
                    </p>
                  )}
                </div>

                <div className="flex shrink-0 items-center gap-3">
                  <ToggleSwitch value={regra.is_active} onChange={() => void alternarAtiva(regra)} size="sm" />
                  <button
                    type="button"
                    onClick={() => abrir(regra.id)}
                    className="text-tertiary hover:text-primary"
                    aria-label={t("common.edit")}
                  >
                    <Pencil className="size-3.5" />
                  </button>
                  <button
                    type="button"
                    onClick={() => setAExcluir(regra)}
                    className="hover:text-danger text-tertiary"
                    aria-label={t("common.delete")}
                  >
                    <Trash2 className="size-3.5" />
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </>
  );
});
