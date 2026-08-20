/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury (20/08/2026): a comparação de planos saiu.
//
// Ela vendia os planos pagos da NUVEM do Plane — Free, One, Pro, Business,
// Enterprise —, com textos como "without leaving Plane". Numa instância própria
// nenhum deles existe, e a tela mostrava ao usuário a tabela de preços de outra
// empresa dentro do produto dele.
//
// Não foi só o conteúdo: o chassi (`comparison/base.tsx`, `plan-detail.tsx`,
// `frequency-toggle.tsx`) importava `TPlanePlans`, `PLANE_PLANS` e
// `shouldRenderPlanDetail` do próprio `plans.tsx`. Não era uma tabela genérica
// esperando conteúdo; era A comparação do Plane, repartida em arquivos. A
// página de planos da Evolury terá outros planos e outro modelo de cobrança, e
// o chassi seria refeito de qualquer forma.
//
// O que fica é o que é verdade aqui: a instância é Community e não tem limite.
// Reversível pelo git, como os 17 idiomas do ADR 0004 — `git show v1.29.2` traz
// os arquivos de volta.

import { observer } from "mobx-react";
// plane imports
import { useTranslation } from "@plane/i18n";
// components
import { SettingsBoxedControlItem } from "@/components/settings/boxed-control-item";
import { SettingsHeading } from "@/components/settings/heading";

export const BillingRoot = observer(function BillingRoot() {
  const { t } = useTranslation();

  return (
    <section className="relative scrollbar-hide size-full overflow-y-auto">
      <SettingsHeading
        title={t("workspace_settings.settings.billing_and_plans.heading")}
        description={t("workspace_settings.settings.billing_and_plans.description")}
      />
      <div className="mt-6">
        <SettingsBoxedControlItem title={t("ui.community")} description={t("ui.unlimited_everything")} />
      </div>
    </section>
  );
});
