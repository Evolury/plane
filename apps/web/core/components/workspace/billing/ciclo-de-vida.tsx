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
import type { TRetratoDoPlano } from "@/services/faturamento.service";
import { FaturamentoService } from "@/services/faturamento.service";
// local imports
import { emData } from "@/components/faturamento/formato";

const servico = new FaturamentoService();

type Props = { workspaceSlug: string; retrato: TRetratoDoPlano; aoMudar: () => void };

/**
 * Cancelar, reativar e pedir reembolso (ADR 0021).
 *
 * Prender quem quer sair é o caminho mais rápido para um estorno, que custa
 * mais que a mensalidade perdida. Por isso os três atos ficam à vista, e o
 * cancelamento diz **até quando** o acesso vale antes de acontecer.
 */
export const CicloDeVida = observer(function CicloDeVida({ workspaceSlug, retrato, aoMudar }: Props) {
  const { t } = useTranslation();
  const raiz = "workspace_settings.settings.billing_and_plans";
  const [motivo, setMotivo] = useState("");
  const [motivoDoReembolso, setMotivoDoReembolso] = useState("");
  const [ocupado, setOcupado] = useState<string | undefined>();

  const cancelada = retrato.status === "cancelada" || retrato.status === "encerrada";
  const removida = retrato.status === "removida";

  const cancelar = async () => {
    setOcupado("cancelar");
    try {
      const resultado = await servico.cancelar(workspaceSlug, motivo);
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: t(`${raiz}.cancelar.cancelada`, { data: emData(resultado.acesso_ate) }),
      });
      aoMudar();
    } catch (erro: any) {
      setToast({ type: TOAST_TYPE.ERROR, title: JSON.stringify(erro?.detalhe ?? erro?.error_message ?? "") });
    } finally {
      setOcupado(undefined);
    }
  };

  const reativar = async () => {
    setOcupado("reativar");
    try {
      await servico.reativar(workspaceSlug);
      setToast({ type: TOAST_TYPE.SUCCESS, title: t(`${raiz}.cancelar.reativada`) });
      aoMudar();
    } catch (erro: any) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title:
          erro?.error_message === "DADOS_REMOVIDOS"
            ? t(`${raiz}.cancelar.dados_removidos`)
            : String(erro?.error_message ?? ""),
      });
    } finally {
      setOcupado(undefined);
    }
  };

  const pedirReembolso = async () => {
    if (!motivoDoReembolso.trim()) {
      setToast({ type: TOAST_TYPE.ERROR, title: t(`${raiz}.reembolso.sem_motivo`) });
      return;
    }
    setOcupado("reembolso");
    try {
      await servico.pedirReembolso(workspaceSlug, motivoDoReembolso);
      setToast({ type: TOAST_TYPE.SUCCESS, title: t(`${raiz}.reembolso.enviado`) });
      setMotivoDoReembolso("");
      aoMudar();
    } catch (erro: any) {
      setToast({ type: TOAST_TYPE.ERROR, title: String(erro?.error_message ?? "") });
    } finally {
      setOcupado(undefined);
    }
  };

  return (
    <div className="grid gap-4 md:grid-cols-2">
      <div className="rounded-lg border border-subtle bg-layer-2 px-4 py-3">
        <p className="text-14 font-semibold text-primary">{t(`${raiz}.cancelar.titulo`)}</p>
        <p className="mb-3 text-13 text-secondary">{t(`${raiz}.cancelar.descricao`)}</p>

        {cancelada || removida ? (
          <Button variant="secondary" onClick={reativar} loading={ocupado === "reativar"} disabled={removida}>
            {removida ? t(`${raiz}.cancelar.dados_removidos`) : t(`${raiz}.cancelar.reativar`)}
          </Button>
        ) : (
          <>
            <Input
              placeholder={t(`${raiz}.cancelar.motivo`)}
              value={motivo}
              onChange={(evento) => setMotivo(evento.target.value)}
            />
            {retrato.pago_ate ? (
              <p className="mt-2 text-13 text-tertiary">
                {t(`${raiz}.cancelar.confirmar`, { data: emData(retrato.pago_ate) })}
              </p>
            ) : null}
            <Button className="mt-2" variant="error-outline" onClick={cancelar} loading={ocupado === "cancelar"}>
              {t(`${raiz}.cancelar.acao`)}
            </Button>
          </>
        )}
      </div>

      <div className="rounded-lg border border-subtle bg-layer-2 px-4 py-3">
        <p className="text-14 font-semibold text-primary">{t(`${raiz}.reembolso.titulo`)}</p>
        <p className="text-13 text-secondary">{t(`${raiz}.reembolso.descricao`)}</p>
        {/* Dito antes de o cliente pedir, e não depois de o estorno cair: o
            reembolso encerra o espaço. */}
        <p className="text-warning mt-1 mb-3 text-13">{t(`${raiz}.reembolso.aviso`)}</p>

        <Input
          placeholder={t(`${raiz}.reembolso.motivo`)}
          value={motivoDoReembolso}
          onChange={(evento) => setMotivoDoReembolso(evento.target.value)}
        />
        <Button className="mt-2" variant="secondary" onClick={pedirReembolso} loading={ocupado === "reembolso"}>
          {t(`${raiz}.reembolso.acao`)}
        </Button>
      </div>
    </div>
  );
});
