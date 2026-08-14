/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: as próximas datas, com pular e desfazer (ADR 0010, F9).
//
// Aqui, e não no formulário, de propósito: o formulário edita a AGENDA e tem
// salvar e cancelar; pular é exceção a uma data e vale no clique. Misturar as
// duas coisas numa caixa só seria oferecer, lado a lado, "pule esta data" e
// "mude a agenda", que descarta os pulos.
//
// Sem confirmação em passo nenhum: nada foi criado, ninguém foi notificado,
// nenhum trabalho se perdeu. Modal para o que é barato ensina a confirmar sem
// ler, e gasta a modal que importa — a de desativar a recorrência.

import { useState } from "react";
import { observer } from "mobx-react";
import { useTranslation } from "@plane/i18n";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import type { TRecurringWorkItem } from "@plane/types";
import { cn, renderFormattedDate } from "@plane/utils";
// services
import { RecurringWorkItemService } from "@/services/recurring-work-item.service";

const servico = new RecurringWorkItemService();

type TProps = {
  workspaceSlug: string;
  projectId: string;
  regra: TRecurringWorkItem;
  /** Recarrega a regra depois de gravar — é daí que vem a verdade. */
  onChange: () => Promise<unknown> | void;
};

export const NextOccurrences = observer(function NextOccurrences(props: TProps) {
  const { workspaceSlug, projectId, regra, onChange } = props;
  const { t } = useTranslation();
  // O que o clique prometeu, até o servidor confirmar. É o que faz a data ser
  // riscada na hora em vez de depois da ida e volta.
  const [emVoo, setEmVoo] = useState<Record<string, boolean>>({});

  const puladas = new Set(regra.skipped_occurrences ?? []);
  const estaPulada = (data: string) => (data in emVoo ? emVoo[data] : puladas.has(data));

  const alternar = async (data: string) => {
    const alvo = !estaPulada(data);
    setEmVoo((atual) => ({ ...atual, [data]: alvo }));
    try {
      await servico.skipOccurrence(workspaceSlug, projectId, regra.id, data, alvo);
      await onChange();
    } catch {
      setToast({ type: TOAST_TYPE.ERROR, title: t("toast.error"), message: t("common.something_went_wrong") });
    } finally {
      // Só depois de a regra recarregar: limpar antes devolveria a data ao
      // estado antigo por um instante, e o pisca-pisca leria como falha.
      setEmVoo((atual) => {
        const { [data]: _, ...resto } = atual;
        return resto;
      });
    }
  };

  return (
    <ul className="mt-1.5 space-y-0.5">
      {regra.next_occurrences.map((data) => {
        const pulada = estaPulada(data);
        return (
          <li key={data} className="flex items-center justify-between gap-2 text-12">
            <span className={cn("min-w-0 truncate text-secondary", { "text-tertiary line-through": pulada })}>
              {renderFormattedDate(data)}
            </span>
            <button
              type="button"
              onClick={() => alternar(data)}
              className="shrink-0 rounded-sm px-1.5 py-0.5 text-11 text-tertiary hover:bg-layer-1 hover:text-primary"
            >
              {t(pulada ? "recurring_work_items.skip.undo" : "recurring_work_items.skip.action")}
            </button>
          </li>
        );
      })}
    </ul>
  );
});
