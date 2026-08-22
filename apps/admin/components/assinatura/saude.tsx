/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// plane internal packages
import { useTranslation } from "@plane/i18n";
import type { TSaudeDoFaturamento } from "@plane/services";
import { cn } from "@plane/utils";

type Props = { saude: TSaudeDoFaturamento | undefined };

/**
 * A saúde da integração com o Asaas (ADR 0021).
 *
 * Fila interrompida é silenciosa por natureza: o Asaas para de enviar depois de
 * 15 falhas seguidas e ninguém avisa. Sem alguém olhando o relógio, quem
 * descobre é o cliente que não conseguiu pagar — este é o lugar onde alguém vê.
 */
export const SaudeDoFaturamento = observer(function SaudeDoFaturamento({ saude }: Props) {
  const { t } = useTranslation();
  if (!saude) return null;

  const quando = saude.ultimo_evento_em ? new Date(saude.ultimo_evento_em).toLocaleString("pt-BR") : undefined;

  return (
    <div
      className={cn("rounded-lg border px-4 py-3 text-13", {
        "border-danger/40 bg-danger/10 text-danger": Boolean(saude.alarme),
        "border-subtle bg-layer-1 text-secondary": !saude.alarme,
      })}
    >
      {saude.alarme ? (
        <p className="font-medium">{t("instance_admin.assinaturas_alarme", { alarme: saude.alarme })}</p>
      ) : quando ? (
        <p>{t("instance_admin.assinaturas_ultimo_evento", { quando })}</p>
      ) : (
        <p>{t("instance_admin.assinaturas_sem_evento")}</p>
      )}

      <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-11 text-tertiary">
        {Object.entries(saude.por_status)
          .filter(([, total]) => total > 0)
          .map(([estado, total]) => (
            <span key={estado}>
              {estado}: <span className="font-medium">{total}</span>
            </span>
          ))}
      </div>
    </div>
  );
});
