/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
// plane internal packages
import { WEB_BASE_URL } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import type { TAcaoDeAssinatura, TAssinaturaDaInstancia } from "@plane/services";
import { cn } from "@plane/utils";
// hooks
import { useAssinatura } from "@/hooks/store";

type Props = { assinatura: TAssinaturaDaInstancia };

const emReais = (centavos: number) => (centavos / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

const emData = (iso: string | null) => {
  if (!iso) return "—";
  // Sem `reverse()` nem `toReversed()`: o primeiro o lint recusa, o segundo não
  // existe no alvo de TypeScript deste app. Fatiar resolve os dois.
  const [ano, mes, dia] = iso.slice(0, 10).split("-");
  return `${dia}/${mes}/${ano}`;
};

/**
 * Uma linha do painel, com o que o operador faz nela (ADR 0021).
 *
 * **Nenhum ato sem motivo.** O campo é obrigatório porque histórico sem
 * explicação é o mesmo que não ter histórico — e cada linha destas mexe em
 * dinheiro de cliente.
 */
export const AssinaturaListItem = observer(function AssinaturaListItem({ assinatura }: Props) {
  const { t } = useTranslation();
  const { agir, historico } = useAssinatura();
  const [aberto, setAberto] = useState(false);
  const [motivo, setMotivo] = useState("");
  const [dias, setDias] = useState(30);
  const [ocupado, setOcupado] = useState(false);
  const [linhas, setLinhas] = useState<any[] | undefined>();

  const bloqueado = ["bloqueada", "encerrada", "removida"].includes(assinatura.status);

  const executar = async (acao: TAcaoDeAssinatura) => {
    if (!acao.motivo.trim()) {
      setToast({ type: TOAST_TYPE.ERROR, title: t("instance_admin.assinaturas_sem_motivo") });
      return;
    }
    setOcupado(true);
    try {
      await agir(assinatura.workspace_id, acao);
      setToast({ type: TOAST_TYPE.SUCCESS, title: t("instance_admin.assinaturas_feito") });
      setMotivo("");
    } catch (erro: any) {
      setToast({ type: TOAST_TYPE.ERROR, title: String(erro?.error ?? erro?.error_message ?? "") });
    } finally {
      setOcupado(false);
    }
  };

  const verHistorico = async () => {
    setAberto(!aberto);
    if (!linhas) setLinhas(await historico(assinatura.workspace_id));
  };

  return (
    <div className="rounded-lg border border-subtle bg-layer-1 px-4 py-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-48">
          <a
            href={`${WEB_BASE_URL}/${encodeURIComponent(assinatura.slug)}`}
            target="_blank"
            rel="noreferrer"
            className="text-14 font-medium text-primary hover:underline"
          >
            {assinatura.nome}
          </a>
          <p className="text-11 text-tertiary">{assinatura.slug}</p>
        </div>

        <div className="flex flex-wrap items-center gap-x-5 gap-y-1 text-13">
          <span className="text-secondary">{assinatura.plano || t("instance_admin.assinaturas_sem_plano")}</span>
          <span
            className={cn("rounded-2xl px-2 py-0.5 text-11 font-medium", {
              "bg-success/15 text-success": ["ativa", "em_cortesia"].includes(assinatura.status),
              "bg-warning/15 text-warning": ["atrasada", "restrita"].includes(assinatura.status),
              "bg-danger/15 text-danger": bloqueado,
              "bg-layer-3 text-secondary": ["sem_assinatura", "cancelada"].includes(assinatura.status),
            })}
          >
            {assinatura.status}
          </span>
          <span className="text-secondary tabular-nums">
            {assinatura.membros}/{assinatura.assentos_incluidos + assinatura.assentos_extras}
          </span>
          {assinatura.excedente > 0 ? (
            <span className="bg-warning/15 text-warning rounded-2xl px-2 py-0.5 text-11 font-medium">
              {t("instance_admin.assinaturas_excedente", { quantidade: assinatura.excedente })}
            </span>
          ) : null}
          <span className="text-secondary tabular-nums">{emReais(assinatura.valor)}</span>
          <span className="text-tertiary tabular-nums">{emData(assinatura.pago_ate)}</span>
        </div>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <input
          className="w-64 rounded-md border border-subtle bg-layer-2 px-3 py-1 text-13 outline-none"
          placeholder={t("instance_admin.assinaturas_motivo")}
          value={motivo}
          onChange={(evento) => setMotivo(evento.target.value)}
        />
        {bloqueado ? (
          <Button
            size="sm"
            variant="secondary"
            disabled={ocupado}
            onClick={() => executar({ acao: "liberar", motivo })}
          >
            {t("instance_admin.assinaturas_liberar")}
          </Button>
        ) : (
          <Button
            size="sm"
            variant="error-outline"
            disabled={ocupado}
            onClick={() => executar({ acao: "bloquear", motivo })}
          >
            {t("instance_admin.assinaturas_bloquear")}
          </Button>
        )}
        <input
          type="number"
          min={1}
          className="w-20 rounded-md border border-subtle bg-layer-2 px-2 py-1 text-13 outline-none"
          value={dias}
          onChange={(evento) => setDias(Number(evento.target.value))}
          aria-label={t("instance_admin.assinaturas_dias")}
        />
        <Button
          size="sm"
          variant="secondary"
          disabled={ocupado}
          onClick={() => executar({ acao: "conceder_cortesia", motivo, dias })}
        >
          {t("instance_admin.assinaturas_cortesia")}
        </Button>
        <Button size="sm" variant="link" onClick={verHistorico}>
          {t("instance_admin.assinaturas_historico")}
        </Button>
      </div>

      {aberto ? (
        <div className="mt-3 border-t border-subtle pt-2">
          {(linhas ?? []).map((linha) => (
            <div key={linha.id} className="flex flex-wrap gap-x-3 py-1 text-11 text-tertiary">
              <span className="tabular-nums">{new Date(linha.quando).toLocaleString("pt-BR")}</span>
              <span className="font-medium text-secondary">{linha.evento}</span>
              {linha.de || linha.para ? (
                <span>
                  {linha.de || "—"} → {linha.para || "—"}
                </span>
              ) : null}
              <span>{linha.quem}</span>
              {linha.motivo ? <span className="italic">“{linha.motivo}”</span> : null}
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
});
