/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: o selo "esta tarefa se repete" nos layouts (ADR 0010, revisão).
//
// Uma das três defesas contra o defeito do Asana de concluir a cópia por
// engano: lá nada distingue a original da gerada; aqui a origem carrega o
// selo, a gerada carrega o rastro, e as duas carregam ID próprio.

import { observer } from "mobx-react";
import { useParams } from "next/navigation";
import useSWR from "swr";
import { Repeat } from "lucide-react";
import { useTranslation } from "@plane/i18n";
import { Tooltip } from "@plane/propel/tooltip";
// services
import { RecurringWorkItemService } from "@/services/recurring-work-item.service";
// local imports
import { chaveDaLista } from "./section";

const servico = new RecurringWorkItemService();

type TBadgeProps = {
  projectId: string;
  issueId: string;
};

export const RecurrenceBadge = observer(function RecurrenceBadge(props: TBadgeProps) {
  const { projectId, issueId } = props;
  const { workspaceSlug } = useParams();
  const { t } = useTranslation();

  // Uma chamada por projeto, compartilhada entre todos os cartões pelo SWR —
  // o selo não pode custar uma consulta por linha.
  const { data: regras } = useSWR(
    workspaceSlug && projectId ? chaveDaLista(workspaceSlug.toString(), projectId) : null,
    () => servico.list(workspaceSlug!.toString(), projectId),
    { revalidateOnFocus: false }
  );

  const ehOrigem = regras?.some((regra) => regra.source_issue === issueId && regra.is_active);
  if (!ehOrigem) return null;

  return (
    <Tooltip tooltipContent={t("recurring_work_items.section.source_badge")}>
      <Repeat className="size-3 flex-shrink-0 text-tertiary" />
    </Tooltip>
  );
});
