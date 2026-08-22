/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// plane imports
import { useTranslation } from "@plane/i18n";
// services
import type { TCobranca } from "@/services/faturamento.service";
// local imports
import { emData, emReais } from "./formato";

type Props = { cobrancas: TCobranca[] };

/**
 * O que já foi cobrado (ADR 0021).
 *
 * Sai do espelho local, não do Asaas: a tela não pode depender de uma chamada
 * externa para carregar, e o espelho é alimentado por webhook e corrigido pela
 * conciliação diária. O link, esse sim, leva para o Asaas — a nota e o
 * comprovante moram lá.
 */
export const HistoricoDeCobrancas = observer(function HistoricoDeCobrancas({ cobrancas }: Props) {
  const { t } = useTranslation();
  const raiz = "workspace_settings.settings.billing_and_plans.historico";

  return (
    <div className="rounded-lg border border-subtle bg-layer-2 px-4 py-3">
      <p className="mb-2 text-14 font-semibold text-primary">{t(`${raiz}.titulo`)}</p>

      {cobrancas.length === 0 ? (
        <p className="text-13 text-secondary">{t(`${raiz}.vazio`)}</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-13">
            <thead>
              <tr className="text-left text-11 tracking-wide text-tertiary uppercase">
                <th className="py-1 pr-4 font-medium">{t(`${raiz}.vencimento`)}</th>
                <th className="py-1 pr-4 font-medium">{t(`${raiz}.valor`)}</th>
                <th className="py-1 pr-4 font-medium">{t(`${raiz}.situacao`)}</th>
                <th className="py-1 font-medium" />
              </tr>
            </thead>
            <tbody>
              {cobrancas.map((cobranca) => (
                <tr key={cobranca.id} className="border-t border-subtle">
                  <td className="py-1.5 pr-4 text-secondary tabular-nums">{emData(cobranca.vencimento)}</td>
                  <td className="py-1.5 pr-4 text-primary tabular-nums">{emReais(cobranca.valor)}</td>
                  <td className="py-1.5 pr-4 text-secondary">{cobranca.status}</td>
                  <td className="py-1.5">
                    {cobranca.link ? (
                      <a
                        href={cobranca.link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-accent-secondary hover:underline"
                      >
                        {t(`${raiz}.abrir`)}
                      </a>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
});
