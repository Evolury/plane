/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// plane internal packages
import { useTranslation } from "@plane/i18n";
import type { TResumoDoFaturamento } from "@plane/services";
import { cn } from "@plane/utils";

type Props = { resumo: TResumoDoFaturamento | undefined };

const emReais = (centavos: number) => (centavos / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

/**
 * Os números do faturamento (ADR 0021).
 *
 * A receita é **mensalizada**: um contrato anual de R$ 6.900 vale R$ 690 aqui.
 * Somar os dois ciclos crus daria um número dez vezes maior no mês em que
 * alguém assina o anual — e ninguém perceberia o erro para menos no mês
 * seguinte.
 *
 * Cortesia conta como contrato na distribuição por plano e **não** conta na
 * receita: inflar o painel com o que não é cobrado é enganar quem o lê.
 */
export const ResumoDoFaturamento = observer(function ResumoDoFaturamento({ resumo }: Props) {
  const { t } = useTranslation();
  if (!resumo) return null;

  const cartoes = [
    { rotulo: t("instance_admin.resumo_receita"), valor: emReais(resumo.receita_recorrente_mensal) },
    { rotulo: t("instance_admin.resumo_cobrando"), valor: String(resumo.assinaturas_cobrando) },
    {
      rotulo: t("instance_admin.resumo_inadimplentes"),
      valor: String(resumo.inadimplentes),
      alerta: resumo.inadimplentes > 0,
    },
    { rotulo: t("instance_admin.resumo_excedentes"), valor: String(resumo.excedentes) },
    {
      rotulo: t("instance_admin.resumo_promocoes"),
      valor: String(resumo.promocoes_a_vencer),
      alerta: resumo.promocoes_a_vencer > 0,
    },
  ];

  return (
    <div className="flex flex-col gap-2">
      <div className="grid grid-cols-2 gap-2 md:grid-cols-5">
        {cartoes.map((cartao) => (
          <div key={cartao.rotulo} className="rounded-lg border border-subtle bg-layer-1 px-3 py-2">
            <p className="text-11 tracking-wide text-tertiary uppercase">{cartao.rotulo}</p>
            <p className={cn("text-16 font-semibold tabular-nums", cartao.alerta ? "text-warning" : "text-primary")}>
              {cartao.valor}
            </p>
          </div>
        ))}
      </div>

      <div className="flex flex-wrap gap-x-4 gap-y-1 text-11 text-tertiary">
        {Object.entries(resumo.por_plano).map(([plano, total]) => (
          <span key={plano}>
            {plano}: <span className="font-medium">{total}</span>
          </span>
        ))}
      </div>
    </div>
  );
});
