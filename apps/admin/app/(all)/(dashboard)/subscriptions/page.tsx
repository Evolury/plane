/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import useSWR from "swr";
// plane internal packages
import { useTranslation } from "@plane/i18n";
import { Loader } from "@plane/ui";
// components
import { PageWrapper } from "@/components/common/page-wrapper";
import { AssinaturaListItem } from "@/components/assinatura/list-item";
import { ResumoDoFaturamento } from "@/components/assinatura/resumo";
import { SaudeDoFaturamento } from "@/components/assinatura/saude";
// hooks
import { useAssinatura } from "@/hooks/store";
// types
import type { Route } from "./+types/page";

/**
 * O painel de assinaturas (ADR 0021).
 *
 * Existe para que operar o faturamento não seja `psql`: ver quem está em qual
 * plano, bloquear quando o financeiro processa um estorno — o Asaas não
 * bloqueia nada por nós — e conceder cortesia antes de o prazo de transição
 * acabar.
 */
const SubscriptionsPage = observer(function SubscriptionsPage(_props: Route.ComponentProps) {
  const { t } = useTranslation();
  const { assinaturas, saude, resumo, carregando, buscar, buscarSaude, buscarResumo } = useAssinatura();
  const [busca, setBusca] = useState("");
  const [estado, setEstado] = useState("");
  const [soExcedentes, setSoExcedentes] = useState(false);

  useSWR("INSTANCE_ASSINATURAS", () => buscar({ search: busca, status: estado, excedentes: soExcedentes }));
  useSWR("INSTANCE_ASSINATURAS_SAUDE", () => buscarSaude());
  useSWR("INSTANCE_ASSINATURAS_RESUMO", () => buscarResumo());

  const aplicar = (mudanca: { search?: string; status?: string; excedentes?: boolean }) => {
    const proximo = { search: busca, status: estado, excedentes: soExcedentes, ...mudanca };
    setBusca(proximo.search ?? "");
    setEstado(proximo.status ?? "");
    setSoExcedentes(Boolean(proximo.excedentes));
    void buscar(proximo);
  };

  return (
    <PageWrapper
      header={{
        title: t("instance_admin.assinaturas_titulo"),
        description: t("instance_admin.assinaturas_descricao"),
      }}
      size="lg"
    >
      <div className="flex flex-col gap-4">
        <ResumoDoFaturamento resumo={resumo} />

        <SaudeDoFaturamento saude={saude} />

        <div className="flex flex-wrap items-center gap-2">
          <input
            className="w-64 rounded-md border border-subtle bg-layer-1 px-3 py-1.5 text-13 outline-none"
            placeholder={t("instance_admin.assinaturas_buscar")}
            value={busca}
            onChange={(evento) => aplicar({ search: evento.target.value })}
          />
          <select
            className="rounded-md border border-subtle bg-layer-1 px-3 py-1.5 text-13 outline-none"
            value={estado}
            onChange={(evento) => aplicar({ status: evento.target.value })}
          >
            <option value="">{t("instance_admin.assinaturas_todos_os_estados")}</option>
            {(saude?.estados ?? []).map((opcao) => (
              <option key={opcao} value={opcao}>
                {opcao}
              </option>
            ))}
          </select>
          <label className="flex items-center gap-2 text-13 text-secondary">
            <input
              type="checkbox"
              checked={soExcedentes}
              onChange={(evento) => aplicar({ excedentes: evento.target.checked })}
            />
            {t("instance_admin.assinaturas_so_excedentes")}
          </label>
        </div>

        {carregando && assinaturas.length === 0 ? (
          <Loader className="space-y-2">
            <Loader.Item height="56px" />
            <Loader.Item height="56px" />
            <Loader.Item height="56px" />
          </Loader>
        ) : assinaturas.length === 0 ? (
          <p className="text-13 text-secondary">{t("instance_admin.assinaturas_vazio")}</p>
        ) : (
          <div className="flex flex-col gap-2">
            {assinaturas.map((assinatura) => (
              <AssinaturaListItem key={assinatura.id} assinatura={assinatura} />
            ))}
          </div>
        )}
      </div>
    </PageWrapper>
  );
});

export default SubscriptionsPage;
