/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: o registro de execuções (ADR 0012).
//
// Responde à pergunta número um de todo produto que tem esse recurso: "por que
// a minha regra não rodou?". A resposta honesta sem este painel seria "não
// sei", porque uma condição que não casa para em silêncio — e deve mesmo parar.
//
// Por isso o painel mostra as três metades do problema, e não só a que deu
// certo: executou, parou na condição, falhou. E dentro da que executou, o que
// cada ação fez — inclusive "já estava assim", que é o que explica a regra que
// roda todo dia e não muda nada.

import { observer } from "mobx-react";
import useSWR from "swr";
import { CheckCircle2, CircleSlash, XCircle } from "lucide-react";
import { useTranslation } from "@plane/i18n";
import type { TAutomationRun, TAutomationRunStatus } from "@plane/types";
import { Loader } from "@plane/ui";
import { renderFormattedDate } from "@plane/utils";
import { AutomationService } from "@/services/automation.service";

const servico = new AutomationService();

type TProps = {
  workspaceSlug: string;
  projectId: string;
  automationId: string;
};

const ICONE: Record<TAutomationRunStatus, React.ReactNode> = {
  matched: <CheckCircle2 className="text-success size-3.5" />,
  skipped: <CircleSlash className="size-3.5 text-tertiary" />,
  failed: <XCircle className="text-danger size-3.5" />,
};

export const ExecucoesDaAutomacao = observer(function ExecucoesDaAutomacao(props: TProps) {
  const { workspaceSlug, projectId, automationId } = props;
  const { t } = useTranslation();

  const { data, isLoading } = useSWR(
    workspaceSlug && projectId && automationId ? `AUTOMATION_RUNS_${automationId}` : null,
    () => servico.runs(workspaceSlug, projectId, automationId),
    { revalidateOnFocus: false }
  );

  if (isLoading)
    return (
      <Loader className="flex flex-col gap-2">
        <Loader.Item height="32px" />
        <Loader.Item height="32px" />
        <Loader.Item height="32px" />
      </Loader>
    );

  const execucoes = data ?? [];
  if (execucoes.length === 0)
    return <p className="py-6 text-center text-13 text-tertiary">{t("automations.runs.empty")}</p>;

  return (
    <ul className="flex flex-col divide-y divide-subtle">
      {execucoes.map((execucao: TAutomationRun) => (
        <li key={execucao.id} className="flex flex-col gap-1 py-2.5">
          <div className="flex items-center gap-2">
            {ICONE[execucao.status]}
            <span className="text-13 text-primary">{t(`automations.runs.status.${execucao.status}`)}</span>
            {execucao.issue_detail && (
              <span className="text-12 text-tertiary">
                #{execucao.issue_detail.sequence_id} {execucao.issue_detail.name}
              </span>
            )}
            <span className="ml-auto text-11 text-tertiary">{renderFormattedDate(execucao.created_at)}</span>
          </div>

          {execucao.error && <p className="text-danger pl-5 text-12">{execucao.error}</p>}

          {execucao.actions_result.length > 0 && (
            <ul className="pl-5">
              {execucao.actions_result.map((resultado, indice) => (
                <li key={`${resultado.tipo}-${indice}`} className="text-12 text-secondary">
                  <span className="text-tertiary">{t(`automations.action_option.${resultado.tipo}`)}: </span>
                  {t(`automations.runs.result.${resultado.status}`)}
                  {resultado.detalhe && <span className="text-tertiary"> — {resultado.detalhe}</span>}
                </li>
              ))}
            </ul>
          )}
        </li>
      ))}
    </ul>
  );
});
