/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: formulário de tarefa recorrente (ADR 0010).
//
// A pré-visualização não é enfeite: "mensal, última sexta, a cada 2 meses" é
// difícil de conferir de cabeça, e ler "28/08, 30/10, 26/12" resolve a dúvida
// antes de a regra começar a criar trabalho para o time.

import { useEffect, useState } from "react";
import { observer } from "mobx-react";
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import type { TRecurrenceFrequency, TRecurringWorkItem } from "@plane/types";
import { EModalWidth, Input, ModalCore } from "@plane/ui";
import { cn, getWeekDayName, renderFormattedDate } from "@plane/utils";
// services
import { RecurringWorkItemService } from "@/services/recurring-work-item.service";

const servico = new RecurringWorkItemService();

const FREQUENCIAS: TRecurrenceFrequency[] = ["daily", "weekly", "monthly", "yearly"];
const SEMANAS_DO_MES = [
  { valor: 1, chave: "first" },
  { valor: 2, chave: "second" },
  { valor: 3, chave: "third" },
  { valor: 4, chave: "fourth" },
  { valor: -1, chave: "last" },
];

type TFormProps = {
  workspaceSlug: string;
  projectId: string;
  regra?: TRecurringWorkItem;
  isOpen: boolean;
  onClose: () => void;
  onSaved: () => void;
};

const padrao = (): Partial<TRecurringWorkItem> => ({
  name: "",
  frequency: "weekly",
  interval: 1,
  weekdays: [1],
  monthly_mode: "day_of_month",
  day_of_month: 1,
  week_of_month: 1,
  weekday_of_month: 1,
  month_of_year: 1,
  time_of_day: "09:00:00",
  start_date: new Date().toISOString().slice(0, 10),
  end_mode: "never",
  generation_mode: "schedule",
  days_after_completion: 7,
  skip_while_previous_open: true,
  template_priority: "none",
});

export const RecurringWorkItemForm = observer(function RecurringWorkItemForm(props: TFormProps) {
  const { workspaceSlug, projectId, regra, isOpen, onClose, onSaved } = props;
  const { t } = useTranslation();
  // states
  const [dados, setDados] = useState<Partial<TRecurringWorkItem>>(padrao());
  const [proximas, setProximas] = useState<string[]>([]);
  const [salvando, setSalvando] = useState(false);

  useEffect(() => {
    if (isOpen) setDados(regra ? { ...regra } : padrao());
  }, [isOpen, regra]);

  // A cada mudança de agenda, o servidor responde as próximas datas — é o
  // mesmo cálculo que vai gerar as tarefas, e não uma segunda implementação
  // no front que um dia divergiria.
  useEffect(() => {
    if (!isOpen || !dados.frequency) return;
    let cancelado = false;
    const id = setTimeout(() => {
      servico
        .preview(workspaceSlug, projectId, { ...dados, name: dados.name || "—" })
        .then((resposta) => !cancelado && setProximas(resposta.next_occurrences))
        .catch(() => !cancelado && setProximas([]));
    }, 400);
    return () => {
      cancelado = true;
      clearTimeout(id);
    };
  }, [isOpen, workspaceSlug, projectId, dados]);

  const mudar = (campos: Partial<TRecurringWorkItem>) => setDados((atual) => ({ ...atual, ...campos }));

  const alternarDia = (dia: number) => {
    const atuais = dados.weekdays ?? [];
    mudar({ weekdays: atuais.includes(dia) ? atuais.filter((d) => d !== dia) : [...atuais, dia].sort() });
  };

  const salvar = async () => {
    setSalvando(true);
    try {
      if (regra) await servico.update(workspaceSlug, projectId, regra.id, dados);
      else await servico.create(workspaceSlug, projectId, dados);
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: t("toast.success"),
        message: t(
          regra
            ? "recurring_work_items.toasts.update.success.title"
            : "recurring_work_items.toasts.create.success.title"
        ),
      });
      onSaved();
      onClose();
    } catch {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("toast.error"),
        message: t(
          regra ? "recurring_work_items.toasts.update.error.title" : "recurring_work_items.toasts.create.error.title"
        ),
      });
    } finally {
      setSalvando(false);
    }
  };

  const rotulo = (chave: string) => t(`recurring_work_items.${chave}`);

  return (
    <ModalCore isOpen={isOpen} handleClose={onClose} width={EModalWidth.XXXL}>
      <div className="flex max-h-[80vh] flex-col gap-5 overflow-y-auto p-5">
        <h3 className="text-16 font-medium">
          {rotulo(regra ? "settings.update_recurring_work_item" : "settings.new_recurring_work_item")}
        </h3>

        <Input
          value={dados.name ?? ""}
          onChange={(e) => mudar({ name: e.target.value })}
          placeholder={t("issue.title.label")}
          className="w-full"
        />

        {/* ----- agenda ----- */}
        <div className="space-y-4 rounded-md border border-subtle p-4">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-13 text-secondary">{rotulo("frequency.label")}</span>
            <div className="flex gap-1 rounded-md bg-layer-3 p-1">
              {FREQUENCIAS.map((f) => (
                <button
                  key={f}
                  type="button"
                  onClick={() => mudar({ frequency: f })}
                  className={cn("rounded-sm px-2 py-1 text-11 transition-colors", {
                    "bg-layer-transparent-selected text-primary": dados.frequency === f,
                    "text-secondary hover:bg-layer-transparent-hover": dados.frequency !== f,
                  })}
                >
                  {rotulo(`frequency.${f}`)}
                </button>
              ))}
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2 text-13">
            <span className="text-secondary">{rotulo("interval.label")}</span>
            <Input
              type="number"
              min={1}
              value={String(dados.interval ?? 1)}
              onChange={(e) => mudar({ interval: Math.max(1, Number(e.target.value)) })}
              className="w-16"
            />
            <span className="text-secondary">{rotulo(`interval.${dados.frequency}`)}</span>
          </div>

          {dados.frequency === "weekly" && (
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-13 text-secondary">{rotulo("weekdays.label")}</span>
              {[0, 1, 2, 3, 4, 5, 6].map((dia) => (
                <button
                  key={dia}
                  type="button"
                  onClick={() => alternarDia(dia)}
                  className={cn("size-8 rounded-full text-11 capitalize transition-colors", {
                    "bg-accent-primary text-on-color": dados.weekdays?.includes(dia),
                    "bg-layer-3 text-secondary hover:bg-layer-3-hover": !dados.weekdays?.includes(dia),
                  })}
                >
                  {getWeekDayName(dia, true)}
                </button>
              ))}
            </div>
          )}

          {dados.frequency === "monthly" && (
            <div className="flex flex-wrap items-center gap-2 text-13">
              <select
                value={dados.monthly_mode ?? "day_of_month"}
                onChange={(e) => mudar({ monthly_mode: e.target.value as TRecurringWorkItem["monthly_mode"] })}
                className="rounded-md border border-subtle bg-surface-1 px-2 py-1"
              >
                <option value="day_of_month">{rotulo("monthly_mode.day_of_month")}</option>
                <option value="last_day">{rotulo("monthly_mode.last_day")}</option>
                <option value="weekday_of_month">{rotulo("monthly_mode.weekday_of_month")}</option>
              </select>

              {dados.monthly_mode === "weekday_of_month" ? (
                <>
                  <select
                    value={String(dados.week_of_month ?? 1)}
                    onChange={(e) => mudar({ week_of_month: Number(e.target.value) })}
                    className="rounded-md border border-subtle bg-surface-1 px-2 py-1"
                  >
                    {SEMANAS_DO_MES.map((s) => (
                      <option key={s.valor} value={s.valor}>
                        {rotulo(`week_of_month.${s.chave}`)}
                      </option>
                    ))}
                  </select>
                  <select
                    value={String(dados.weekday_of_month ?? 1)}
                    onChange={(e) => mudar({ weekday_of_month: Number(e.target.value) })}
                    className="rounded-md border border-subtle bg-surface-1 px-2 py-1 capitalize"
                  >
                    {[0, 1, 2, 3, 4, 5, 6].map((dia) => (
                      <option key={dia} value={dia}>
                        {getWeekDayName(dia)}
                      </option>
                    ))}
                  </select>
                </>
              ) : dados.monthly_mode === "last_day" ? null : (
                <>
                  <span className="text-secondary">{rotulo("day_of_month.label")}</span>
                  <Input
                    type="number"
                    min={1}
                    max={31}
                    value={String(dados.day_of_month ?? 1)}
                    onChange={(e) => mudar({ day_of_month: Number(e.target.value) })}
                    className="w-16"
                  />
                </>
              )}
            </div>
          )}

          <div className="flex flex-wrap items-center gap-4 text-13">
            <label className="flex items-center gap-2">
              <span className="text-secondary">{rotulo("time_of_day.label")}</span>
              <Input
                type="time"
                value={(dados.time_of_day ?? "09:00:00").slice(0, 5)}
                onChange={(e) => mudar({ time_of_day: `${e.target.value}:00` })}
                className="w-28"
              />
            </label>
            <label className="flex items-center gap-2">
              <span className="text-secondary">{rotulo("start_date.label")}</span>
              <Input
                type="date"
                value={dados.start_date ?? ""}
                onChange={(e) => mudar({ start_date: e.target.value })}
                className="w-40"
              />
            </label>
          </div>

          <div className="flex flex-wrap items-center gap-2 text-13">
            <span className="text-secondary">{rotulo("end.label")}</span>
            <select
              value={dados.end_mode ?? "never"}
              onChange={(e) => mudar({ end_mode: e.target.value as TRecurringWorkItem["end_mode"] })}
              className="rounded-md border border-subtle bg-surface-1 px-2 py-1"
            >
              <option value="never">{rotulo("end.never")}</option>
              <option value="on_date">{rotulo("end.on_date")}</option>
              <option value="after_count">{rotulo("end.after_count")}</option>
            </select>
            {dados.end_mode === "on_date" && (
              <Input
                type="date"
                value={dados.end_date ?? ""}
                onChange={(e) => mudar({ end_date: e.target.value })}
                className="w-40"
              />
            )}
            {dados.end_mode === "after_count" && (
              <>
                <Input
                  type="number"
                  min={1}
                  value={String(dados.end_after_count ?? 1)}
                  onChange={(e) => mudar({ end_after_count: Number(e.target.value) })}
                  className="w-20"
                />
                <span className="text-secondary">{rotulo("end.count_suffix")}</span>
              </>
            )}
          </div>
        </div>

        {/* ----- geração ----- */}
        <div className="space-y-3 rounded-md border border-subtle p-4 text-13">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-secondary">{rotulo("generation.label")}</span>
            <select
              value={dados.generation_mode ?? "schedule"}
              onChange={(e) => mudar({ generation_mode: e.target.value as TRecurringWorkItem["generation_mode"] })}
              className="rounded-md border border-subtle bg-surface-1 px-2 py-1"
            >
              <option value="schedule">{rotulo("generation.schedule")}</option>
              <option value="after_completion">{rotulo("generation.after_completion")}</option>
            </select>
            {dados.generation_mode === "after_completion" && (
              <>
                <Input
                  type="number"
                  min={1}
                  value={String(dados.days_after_completion ?? 7)}
                  onChange={(e) => mudar({ days_after_completion: Number(e.target.value) })}
                  className="w-20"
                />
                <span className="text-secondary">{rotulo("generation.days_after_completion")}</span>
              </>
            )}
          </div>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={dados.skip_while_previous_open ?? true}
              onChange={(e) => mudar({ skip_while_previous_open: e.target.checked })}
            />
            <span className="text-secondary">{rotulo("generation.skip_while_previous_open")}</span>
          </label>
        </div>

        {/* ----- pré-visualização ----- */}
        <div className="rounded-md bg-layer-2 p-3 text-13">
          <p className="mb-1 font-medium">{rotulo("preview.label")}</p>
          {proximas.length > 0 ? (
            <p className="text-secondary">{proximas.map((data) => renderFormattedDate(data)).join(" · ")}</p>
          ) : (
            <p className="text-tertiary">{rotulo("preview.empty")}</p>
          )}
        </div>

        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose} disabled={salvando}>
            {t("common.cancel")}
          </Button>
          <Button variant="primary" onClick={salvar} loading={salvando} disabled={!dados.name?.trim()}>
            {rotulo(regra ? "settings.form.button.update" : "settings.form.button.create")}
          </Button>
        </div>
      </div>
    </ModalCore>
  );
});
