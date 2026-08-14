/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: atalho do cabeçalho para a auditoria das recorrentes (ADR 0010).
//
// A página de configurações é o lugar de auditar o que o projeto gera sozinho,
// e é justamente o que falta no Asana — lá a recorrência é invisível fora da
// tarefa. Só que auditoria escondida em Configurações → Execução é auditoria
// que ninguém abre. O atalho fica onde a pessoa já está: no quadro.
//
// **Só aparece quando há recorrência ativa**, porque atalho para uma tela
// vazia é ruído permanente no cabeçalho de todo projeto que não usa o recurso.
// E **só para admin**, porque a página responde `NotAuthorizedView` para os
// demais — botão que leva a uma porta fechada é pior que botão nenhum.
//
// Não custa consulta nova: o selo "esta tarefa se repete" já pede esta mesma
// resposta a cada render do quadro, e o SWR compartilha as duas.

import { observer } from "mobx-react";
import useSWR from "swr";
import { Repeat } from "lucide-react";
import { EUserPermissions, EUserPermissionsLevel } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { IconButton } from "@plane/propel/icon-button";
import { Tooltip } from "@plane/propel/tooltip";
// hooks
import { useUserPermissions } from "@/hooks/store/user";
import { useAppRouter } from "@/hooks/use-app-router";
// services
import { RecurringWorkItemService } from "@/services/recurring-work-item.service";
// local imports
import { chaveDosSelos } from "./section";

const servico = new RecurringWorkItemService();

type TProps = {
  workspaceSlug: string;
  projectId: string;
};

export const RecurrenceShortcut = observer(function RecurrenceShortcut(props: TProps) {
  const { workspaceSlug, projectId } = props;
  const { t } = useTranslation();
  const { allowPermissions } = useUserPermissions();
  const router = useAppRouter();

  const { data: selos } = useSWR(
    workspaceSlug && projectId ? chaveDosSelos(workspaceSlug, projectId) : null,
    () => servico.badges(workspaceSlug, projectId),
    { revalidateOnFocus: false }
  );

  const ehAdmin = allowPermissions([EUserPermissions.ADMIN], EUserPermissionsLevel.PROJECT, workspaceSlug, projectId);
  if (!ehAdmin || !selos?.source_issue_ids?.length) return null;

  return (
    <Tooltip tooltipContent={t("recurring_work_items.settings.heading")}>
      <IconButton
        size="lg"
        variant="secondary"
        icon={Repeat}
        aria-label={t("recurring_work_items.settings.heading")}
        onClick={() => router.push(`/${workspaceSlug}/settings/projects/${projectId}/recurring`)}
      />
    </Tooltip>
  );
});
