/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: vencimento relativo da subtarefa na recorrência (ADR 0010, F7).
//
// Aparece só nas subtarefas de uma tarefa de origem, e só para admin. A data é
// calculada a cada ciclo a partir da janela da ocorrência — nunca deslocada de
// um ciclo para o outro, que é onde o remapeamento do ClickUp falha quando a
// data do pai recua.

import { useState } from "react";
import { observer } from "mobx-react";
import { mutate as mutateGlobal } from "swr";
import { CalendarClock } from "lucide-react";
import { useTranslation } from "@plane/i18n";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import type { TRecurringWorkItem, TSubtaskDueAnchor } from "@plane/types";
import { Input } from "@plane/ui";
// services
import { RecurringWorkItemService } from "@/services/recurring-work-item.service";
// local imports
import { chaveDaLista, chaveDaRegra } from "./section";

const servico = new RecurringWorkItemService();

type TSubtaskDueProps = {
  workspaceSlug: string;
  projectId: string;
  /** A regra da tarefa PAI — a agenda pertence à série, não à subtarefa. */
  regra: TRecurringWorkItem;
  subtaskId: string;
  disabled?: boolean;
};

export const SubtaskDueField = observer(function SubtaskDueField(props: TSubtaskDueProps) {
  const { workspaceSlug, projectId, regra, subtaskId, disabled } = props;
  const { t } = useTranslation();

  const existente = regra.subtask_schedules?.find((agenda) => agenda.subtask === subtaskId);
  const [ancora, setAncora] = useState<TSubtaskDueAnchor | "">(existente?.anchor ?? "");
  const [dias, setDias] = useState<number>(existente?.offset_days ?? 0);
  const [salvando, setSalvando] = useState(false);

  const rotulo = (chave: string) => t(`recurring_work_items.subtask_due.${chave}`);

  const salvar = async (novaAncora: TSubtaskDueAnchor | "", novosDias: number) => {
    setSalvando(true);
    try {
      await servico.setSubtaskSchedule(workspaceSlug, projectId, regra.id, subtaskId, novaAncora, novosDias);
      mutateGlobal(chaveDaRegra(regra.source_issue));
      mutateGlobal(chaveDaLista(workspaceSlug, projectId));
    } catch {
      setToast({ type: TOAST_TYPE.ERROR, title: t("toast.error"), message: t("common.something_went_wrong") });
    } finally {
      setSalvando(false);
    }
  };

  return (
    <div className="flex flex-wrap items-center gap-2 text-12">
      <CalendarClock className="size-3.5 shrink-0 text-tertiary" />
      <span className="text-secondary">{rotulo("label")}</span>
      {ancora !== "" && (
        <Input
          type="number"
          min={0}
          value={String(dias)}
          disabled={disabled || salvando}
          onChange={(e) => {
            const valor = Math.max(0, Number(e.target.value));
            setDias(valor);
            salvar(ancora, valor);
          }}
          className="w-16"
        />
      )}
      {ancora !== "" && <span className="text-secondary">{rotulo("days")}</span>}
      <select
        value={ancora}
        disabled={disabled || salvando}
        onChange={(e) => {
          const valor = e.target.value as TSubtaskDueAnchor | "";
          setAncora(valor);
          salvar(valor, dias);
        }}
        className="rounded-md border border-subtle bg-surface-1 px-2 py-1"
      >
        <option value="">{rotulo("none")}</option>
        <option value="after_creation">{rotulo("after_creation")}</option>
        <option value="before_due">{rotulo("before_due")}</option>
      </select>
    </div>
  );
});
