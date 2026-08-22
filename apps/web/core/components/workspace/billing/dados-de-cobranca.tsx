/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
// plane imports
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { Input } from "@plane/ui";
// services
import type { TDadosDeCobranca } from "@/services/faturamento.service";
import { FaturamentoService } from "@/services/faturamento.service";

const servico = new FaturamentoService();

type Props = { workspaceSlug: string; dados: TDadosDeCobranca | undefined; aoSalvar: () => void };

/**
 * Quem paga (ADR 0021).
 *
 * O CPF ou CNPJ é exigência do Asaas para criar o cliente, e não existia em
 * lugar nenhum do produto. A conferência acontece no servidor — aqui a tela só
 * mostra o motivo que ele devolveu, em vez do erro de gateway que apareceria
 * três telas adiante.
 */
export const DadosDeCobranca = observer(function DadosDeCobranca({ workspaceSlug, dados, aoSalvar }: Props) {
  const { t } = useTranslation();
  const raiz = "workspace_settings.settings.billing_and_plans.cobranca";
  const [nome, setNome] = useState(dados?.nome ?? "");
  const [documento, setDocumento] = useState(dados?.cpf_cnpj ?? "");
  const [email, setEmail] = useState(dados?.email ?? "");
  const [telefone, setTelefone] = useState(dados?.telefone ?? "");
  const [salvando, setSalvando] = useState(false);

  const salvar = async () => {
    setSalvando(true);
    try {
      await servico.salvarDadosDeCobranca(workspaceSlug, {
        nome,
        cpf_cnpj: documento,
        email,
        telefone,
      });
      setToast({ type: TOAST_TYPE.SUCCESS, title: t(`${raiz}.salvo`) });
      aoSalvar();
    } catch (erro: any) {
      const codigo = erro?.error_message;
      setToast({
        type: TOAST_TYPE.ERROR,
        title:
          codigo === "DOCUMENTO_INVALIDO"
            ? t(`${raiz}.documento_invalido`)
            : codigo === "DADOS_INCOMPLETOS"
              ? t(`${raiz}.incompleto`)
              : t(`${raiz}.incompleto`),
      });
    } finally {
      setSalvando(false);
    }
  };

  return (
    <div className="rounded-lg border border-subtle bg-layer-2 px-4 py-3">
      <p className="text-14 font-semibold text-primary">{t(`${raiz}.titulo`)}</p>
      <p className="mb-3 text-13 text-secondary">{t(`${raiz}.descricao`)}</p>

      <div className="grid gap-3 md:grid-cols-2">
        <label className="flex flex-col gap-1 text-13 text-secondary">
          {t(`${raiz}.nome`)}
          <Input value={nome} onChange={(evento) => setNome(evento.target.value)} />
        </label>
        <label className="flex flex-col gap-1 text-13 text-secondary">
          {t(`${raiz}.documento`)}
          <Input value={documento} onChange={(evento) => setDocumento(evento.target.value)} />
        </label>
        <label className="flex flex-col gap-1 text-13 text-secondary">
          {t(`${raiz}.email`)}
          <Input value={email} onChange={(evento) => setEmail(evento.target.value)} />
        </label>
        <label className="flex flex-col gap-1 text-13 text-secondary">
          {t(`${raiz}.telefone`)}
          <Input value={telefone} onChange={(evento) => setTelefone(evento.target.value)} />
        </label>
      </div>

      <Button className="mt-3" onClick={salvar} loading={salvando} disabled={salvando}>
        {t(`${raiz}.salvar`)}
      </Button>
    </div>
  );
});
