/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: o editor de uma automação personalizada (ADR 0012).
//
// Tela inteira, e não modal: a regra tem três seções, a frase-resumo no topo e
// o registro de execuções ao lado. Num modal, o painel de execuções — que é a
// resposta a "por que não rodou?" — ficaria espremido justamente quando é mais
// necessário, que é durante a depuração.
//
// O id "novo" é o caminho de criação. Uma rota só para as duas coisas mantém a
// pergunta "onde se edita uma regra?" com uma resposta só.

import { observer } from "mobx-react";
import useSWR from "swr";
import { EUserPermissions, EUserPermissionsLevel } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import type { TAutomation } from "@plane/types";
import { Loader } from "@plane/ui";
import { NotAuthorizedView } from "@/components/auth-screens/not-authorized-view";
import { EditorDeAutomacao, chaveDaListaDeAutomacoes } from "@/components/automations";
import { PageHead } from "@/components/core/page-title";
import { SettingsContentWrapper } from "@/components/settings/content-wrapper";
import { useUserPermissions } from "@/hooks/store/user";
import { AutomationService } from "@/services/automation.service";
import type { Route } from "./+types/page";
import { AutomationsProjectSettingsHeader } from "../header";

const servico = new AutomationService();

function AutomationEditorPage({ params }: Route.ComponentProps) {
  const { workspaceSlug, projectId, automationId } = params;
  const { t } = useTranslation();
  const { workspaceUserInfo, allowPermissions } = useUserPermissions();

  const podeAdministrar = allowPermissions([EUserPermissions.ADMIN], EUserPermissionsLevel.PROJECT);
  const criando = automationId === "novo";

  // A lista inteira, e não um GET por id: o endpoint de detalhe não existe de
  // propósito — a lista é pequena por natureza (regras de um projeto) e o
  // cache do SWR já a tem quando se chega aqui pelo botão de editar.
  const { data, mutate } = useSWR(
    workspaceSlug && projectId && !criando ? chaveDaListaDeAutomacoes(workspaceSlug, projectId) : null,
    () => servico.list(workspaceSlug, projectId)
  );

  const regra = criando ? undefined : (data ?? []).find((item: TAutomation) => item.id === automationId);

  if (workspaceUserInfo && !podeAdministrar) {
    return <NotAuthorizedView section="settings" isProjectView className="h-auto" />;
  }

  return (
    <SettingsContentWrapper header={<AutomationsProjectSettingsHeader />} hugging>
      <PageHead title={t("automations.settings.title")} />
      <section className="w-full">
        {!criando && !data ? (
          <Loader className="flex flex-col gap-3">
            <Loader.Item height="40px" />
            <Loader.Item height="120px" />
            <Loader.Item height="120px" />
          </Loader>
        ) : (
          <EditorDeAutomacao
            workspaceSlug={workspaceSlug}
            projectId={projectId}
            regra={regra}
            onSaved={() => void mutate()}
          />
        )}
      </section>
    </SettingsContentWrapper>
  );
}

export default observer(AutomationEditorPage);
