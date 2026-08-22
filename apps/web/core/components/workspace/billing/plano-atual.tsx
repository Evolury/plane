/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// plane imports
import { useTranslation } from "@plane/i18n";
import { cn } from "@plane/utils";
// local imports
import type { TRetratoDoPlano } from "@/services/faturamento.service";
import { emData } from "./formato";

type Props = { retrato: TRetratoDoPlano };

/** Uma linha por limite: quanto já se usa, e de quanto. */
function Uso({ rotulo, usado, teto }: { rotulo: string; usado: number; teto: number | null }) {
  const { t } = useTranslation();
  const apertado = teto !== null && teto > 0 && usado / teto >= 0.8;

  return (
    <div className="flex items-center justify-between py-1.5 text-13">
      <span className="text-secondary">{rotulo}</span>
      <span className={cn("font-medium tabular-nums", apertado ? "text-warning" : "text-primary")}>
        {/* "1 de sem teto" não é frase. Sem teto, o número basta. */}
        {teto === null ? (
          <>
            {usado}{" "}
            <span className="text-tertiary">({t("workspace_settings.settings.billing_and_plans.uso.sem_teto")})</span>
          </>
        ) : (
          `${usado} ${t("workspace_settings.settings.billing_and_plans.uso.de")} ${teto}`
        )}
      </span>
    </div>
  );
}

export const PlanoAtual = observer(function PlanoAtual({ retrato }: Props) {
  const { t } = useTranslation();
  const raiz = "workspace_settings.settings.billing_and_plans";

  return (
    <div className="rounded-lg border border-subtle bg-layer-2 px-4 py-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <p className="text-11 tracking-wide text-tertiary uppercase">{t(`${raiz}.current_plan`)}</p>
          <p className="text-18 font-semibold text-primary">{retrato.nome || t(`${raiz}.estado.sem_assinatura`)}</p>
        </div>
        <span
          className={cn("rounded-2xl px-3 py-0.5 text-11 font-medium", {
            "bg-success/15 text-success": retrato.status === "ativa" || retrato.status === "em_cortesia",
            "bg-warning/15 text-warning": retrato.status === "atrasada" || retrato.status === "restrita",
            "bg-danger/15 text-danger": ["bloqueada", "encerrada", "removida"].includes(retrato.status),
            "bg-layer-3 text-secondary": ["sem_assinatura", "cancelada"].includes(retrato.status),
          })}
        >
          {t(`${raiz}.estado.${retrato.status}`)}
        </span>
      </div>

      {retrato.pago_ate ? (
        <p className="mt-1 text-13 text-secondary">{t(`${raiz}.pago_ate`, { data: emData(retrato.pago_ate) })}</p>
      ) : null}
      {retrato.proxima_cobranca_em ? (
        <p className="text-13 text-secondary">
          {t(`${raiz}.proxima_cobranca`, { data: emData(retrato.proxima_cobranca_em) })}
        </p>
      ) : null}
      {retrato.promocao_termina_em ? (
        // O fim da promoção é dito antes de acontecer, e não na fatura em que
        // o preço dobrou.
        <p className="bg-warning/10 text-warning mt-2 rounded-md px-3 py-2 text-13">
          {t(`${raiz}.promocao_termina`, { data: emData(retrato.promocao_termina_em) })}
        </p>
      ) : null}

      <div className="mt-4 border-t border-subtle pt-2">
        <p className="mb-1 text-11 tracking-wide text-tertiary uppercase">{t(`${raiz}.uso.titulo`)}</p>
        <Uso
          rotulo={t(`${raiz}.uso.assentos`)}
          usado={retrato.assentos.usados}
          teto={retrato.assentos.incluidos + retrato.assentos.extras}
        />
        <Uso rotulo={t(`${raiz}.uso.convidados`)} usado={retrato.convidados.usados} teto={retrato.convidados.cota} />
        {/* Propriedade é teto **por projeto**, e o retrato do espaço não sabe o
            uso de cada um. Mostrar "0 de 5" seria inventar um número: aqui vai
            só o limite, que é o que se compra. */}
        <div className="flex items-center justify-between py-1.5 text-13">
          <span className="text-secondary">{t(`${raiz}.uso.propriedades`)}</span>
          <span className="font-medium text-primary tabular-nums">
            {retrato.limites.propriedades_por_projeto ?? t(`${raiz}.uso.sem_teto`)}
          </span>
        </div>
        <Uso
          rotulo={t(`${raiz}.uso.automacoes`)}
          usado={retrato.automacoes_ativas}
          teto={retrato.limites.automacoes_ativas ?? null}
        />
      </div>
    </div>
  );
});
