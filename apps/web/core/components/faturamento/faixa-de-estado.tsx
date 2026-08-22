/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import Link from "next/link";
import { useParams } from "next/navigation";
// plane imports
import { useTranslation } from "@plane/i18n";
import { cn } from "@plane/utils";
// hooks
import { useFaturamento } from "@/hooks/store/use-faturamento";
// local imports
import { emData } from "./formato";

/**
 * O aviso dentro do produto (ADR 0021).
 *
 * É o canal que o cliente inadimplente lê: as réguas de mercado medem 12% a 17%
 * de recuperação a mais só por avisar aqui, e não apenas por e-mail. Os avisos
 * de cobrança em si saem pelo Asaas, que já entrega por e-mail, SMS e WhatsApp.
 *
 * A faixa diz **quando** o próximo aperto acontece, e não "sua conta está
 * irregular" — data é o que faz alguém agir hoje.
 */
export const FaixaDeEstado = observer(function FaixaDeEstado() {
  const { t } = useTranslation();
  const { workspaceSlug } = useParams();
  const slug = workspaceSlug?.toString() ?? "";
  const { retrato } = useFaturamento();
  const atual = retrato(slug);
  const raiz = "workspace_settings.settings.billing_and_plans.faixa";

  if (!atual) return null;
  if (atual.status !== "atrasada" && atual.status !== "restrita") return null;

  const marco = atual.proximo_marco;
  return (
    <div
      className={cn("flex flex-wrap items-center justify-center gap-x-2 gap-y-1 px-4 py-1.5 text-13", {
        "bg-warning/15 text-warning": atual.status === "atrasada",
        "bg-danger/15 text-danger": atual.status === "restrita",
      })}
    >
      <span>{t(`${raiz}.${atual.status}`)}</span>
      {marco ? (
        <span className="opacity-80">
          {t(marco.estado === "restrita" ? `${raiz}.aviso_de_restricao` : `${raiz}.aviso_de_bloqueio`, {
            data: emData(marco.data),
          })}
        </span>
      ) : null}
      <Link href={`/${slug}/settings/billing/`} className="font-medium underline underline-offset-2">
        {t(`${raiz}.regularizar`)}
      </Link>
    </div>
  );
});
