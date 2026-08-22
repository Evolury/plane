/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: a tela de faturamento de verdade (ADR 0021).
//
// Até a v1.30.0 aqui morava a comparação de planos da NUVEM do Plane — Free,
// One, Pro, Business, Enterprise —, que numa instância própria não existiam.
// Ela saiu, e o que ficou no lugar foi uma linha dizendo "Community, tudo
// ilimitado". Agora existe assinatura de verdade, e esta tela é onde ela é
// contratada, trocada e conferida.
//
// Uma decisão atravessa a tela inteira: **contratar não libera acesso**. Os
// botões devolvem um link — do checkout do Asaas ou da cobrança PIX — e quem
// prova pagamento é o webhook. Escrever "pronto, liberado" na volta do
// navegador seria mentir para metade dos casos, porque quem sai do checkout
// pode fechar a aba.

import { useState } from "react";
import { observer } from "mobx-react";
import { useParams } from "next/navigation";
import useSWR from "swr";
// plane imports
import { useTranslation } from "@plane/i18n";
// components
import { SettingsHeading } from "@/components/settings/heading";
// hooks
import { useFaturamento } from "@/hooks/store/use-faturamento";
// services
import { FaturamentoService } from "@/services/faturamento.service";
// local imports
import { DadosDeCobranca } from "./dados-de-cobranca";
import { EscolherPlano } from "./escolher-plano";
import { HistoricoDeCobrancas } from "./historico";
import { PlanoAtual } from "./plano-atual";

const servico = new FaturamentoService();

export const BillingRoot = observer(function BillingRoot() {
  const { t } = useTranslation();
  const { workspaceSlug } = useParams();
  const slug = workspaceSlug?.toString() ?? "";
  const { retrato, buscarRetrato } = useFaturamento();
  const [versao, setVersao] = useState(0);

  const { data: dados, mutate: recarregarDados } = useSWR(
    slug ? `FATURAMENTO_COBRANCA_${slug}_${versao}` : null,
    slug ? () => servico.dadosDeCobranca(slug) : null,
    { revalidateOnFocus: false }
  );

  const { data: cobrancas, mutate: recarregarCobrancas } = useSWR(
    slug ? `FATURAMENTO_COBRANCAS_${slug}_${versao}` : null,
    slug ? () => servico.cobrancas(slug) : null,
    { revalidateOnFocus: false }
  );

  const atual = retrato(slug);

  const recarregarTudo = () => {
    setVersao((anterior) => anterior + 1);
    void buscarRetrato(slug);
    void recarregarDados();
    void recarregarCobrancas();
  };

  return (
    <section className="relative scrollbar-hide size-full overflow-y-auto">
      <SettingsHeading
        title={t("workspace_settings.settings.billing_and_plans.heading")}
        description={t("workspace_settings.settings.billing_and_plans.description")}
      />

      <div className="mt-6 flex flex-col gap-4">
        {atual ? <PlanoAtual retrato={atual} /> : null}

        <DadosDeCobranca workspaceSlug={slug} dados={dados} aoSalvar={recarregarTudo} />

        {atual ? <EscolherPlano workspaceSlug={slug} retrato={atual} aoMudar={recarregarTudo} /> : null}

        <HistoricoDeCobrancas cobrancas={cobrancas ?? []} />
      </div>
    </section>
  );
});
