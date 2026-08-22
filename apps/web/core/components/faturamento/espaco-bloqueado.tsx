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
import { Button } from "@plane/propel/button";
// hooks
import { useFaturamento } from "@/hooks/store/use-faturamento";
// local imports
import { emData } from "./formato";

/**
 * A tela que substitui o produto quando o espaço está bloqueado (ADR 0021).
 *
 * Diz duas coisas que fazem diferença para quem chega aqui: **os dados
 * continuam existindo** e **a exportação continua funcionando**. É o que separa
 * cobrança de sequestro de dado — e é também o que faz o cliente voltar em vez
 * de sumir.
 *
 * Encerrado é outro texto: ali o que importa é a data em que os dados vão
 * embora, porque ela é a única coisa que ainda pode ser evitada.
 */
export const EspacoBloqueado = observer(function EspacoBloqueado() {
  const { t } = useTranslation();
  const { workspaceSlug } = useParams();
  const slug = workspaceSlug?.toString() ?? "";
  const { retrato } = useFaturamento();
  const atual = retrato(slug);
  const raiz = "workspace_settings.settings.billing_and_plans.faixa";

  const encerrado = atual?.status === "encerrada" || atual?.status === "removida";
  return (
    <div className="grid size-full place-items-center p-6">
      <div className="max-w-lg text-center">
        <h2 className="text-20 font-semibold text-primary">
          {t(encerrado ? `${raiz}.encerrada_titulo` : `${raiz}.bloqueada_titulo`)}
        </h2>
        <p className="mt-2 text-14 text-secondary">
          {encerrado ? t(`${raiz}.encerrada_texto`, { data: emData(atual?.pago_ate) }) : t(`${raiz}.bloqueada_texto`)}
        </p>
        <Link href={`/${slug}/settings/billing/`}>
          <Button className="mt-4">{t(`${raiz}.ir_para_faturamento`)}</Button>
        </Link>
      </div>
    </div>
  );
});
