/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
// plane imports
import { CICLO_ANUAL, CICLO_MENSAL, ORDEM_DOS_PLANOS, PLANOS, precoAnual } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { Input } from "@plane/ui";
import { cn } from "@plane/utils";
// services
import type { TCupom, TRetratoDoPlano } from "@/services/faturamento.service";
import { FaturamentoService } from "@/services/faturamento.service";
// local imports
import { emReais } from "@/components/faturamento/formato";

const servico = new FaturamentoService();

type Props = { workspaceSlug: string; retrato: TRetratoDoPlano; aoMudar: () => void };

/**
 * Escolher plano, ciclo e forma de pagamento (ADR 0021).
 *
 * Duas portas, porque o Asaas impõe duas: cartão vai para a página hospedada
 * dele — o dado do cartão nunca passa por aqui —, e PIX vira assinatura com
 * cobrança a cada ciclo.
 *
 * O botão **não** libera acesso: ele devolve um link. Quem prova pagamento é o
 * webhook, e essa distinção está na frase que a tela mostra depois.
 */
export const EscolherPlano = observer(function EscolherPlano({ workspaceSlug, retrato, aoMudar }: Props) {
  const { t } = useTranslation();
  const raiz = "workspace_settings.settings.billing_and_plans";
  const [ciclo, setCiclo] = useState<string>(retrato.ciclo || CICLO_MENSAL);
  const [forma, setForma] = useState<string>("pix");
  const [codigo, setCodigo] = useState("");
  const [cupom, setCupom] = useState<TCupom | undefined>();
  const [ocupado, setOcupado] = useState<string | undefined>();

  const jaContratou = Boolean(retrato.plano);

  const aplicarCupom = async () => {
    try {
      const encontrado = await servico.conferirCupom(workspaceSlug, codigo);
      setCupom(encontrado);
      setToast({ type: TOAST_TYPE.SUCCESS, title: t(`${raiz}.cupom.aplicado`, { codigo: encontrado.codigo }) });
    } catch (erro: any) {
      const mapa: Record<string, string> = {
        CUPOM_INVALIDO: `${raiz}.cupom.invalido`,
        CUPOM_VENCIDO: `${raiz}.cupom.vencido`,
        CUPOM_ESGOTADO: `${raiz}.cupom.esgotado`,
      };
      setCupom(undefined);
      setToast({ type: TOAST_TYPE.ERROR, title: t(mapa[erro?.error_message] ?? `${raiz}.cupom.invalido`) });
    }
  };

  const escolher = async (chave: string) => {
    setOcupado(chave);
    try {
      if (jaContratou) {
        const troca = await servico.trocarPlano(workspaceSlug, { plano: chave, ciclo });
        setToast({
          type: TOAST_TYPE.SUCCESS,
          title: t(troca.imediato ? `${raiz}.upgrade_imediato` : `${raiz}.downgrade_agendado`),
        });
        if (troca.diferenca?.link) window.open(troca.diferenca.link, "_blank", "noopener");
        aoMudar();
        return;
      }

      const contratacao = await servico.contratar(workspaceSlug, {
        plano: chave,
        ciclo,
        forma,
        cupom: cupom?.codigo,
      });
      aoMudar();
      if (contratacao.link) {
        // Cartão vai para o checkout do Asaas; PIX abre a cobrança para pagar
        // agora. Nos dois casos, o acesso só muda quando o webhook chegar.
        window.open(contratacao.link, "_blank", "noopener");
        setToast({ type: TOAST_TYPE.INFO, title: t(`${raiz}.aguardando_pagamento`) });
      }
    } catch (erro: any) {
      if (erro?.error_message === "ACIMA_DO_TETO") {
        const itens = Object.entries(erro.precisa_sair ?? {})
          .map(([o_que, quantos]) => `${quantos} ${o_que}`)
          .join(", ");
        setToast({ type: TOAST_TYPE.ERROR, title: t(`${raiz}.acima_do_teto`, { itens }) });
        return;
      }
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t(`${raiz}.erro_no_gateway`, { detalhe: JSON.stringify(erro?.detalhe ?? erro?.error_message ?? "") }),
      });
    } finally {
      setOcupado(undefined);
    }
  };

  return (
    <div className="rounded-lg border border-subtle bg-layer-2 px-4 py-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-14 font-semibold text-primary">{t(`${raiz}.planos.titulo`)}</p>
        <div className="flex items-center gap-1 rounded-lg bg-layer-3 p-0.5">
          {[CICLO_MENSAL, CICLO_ANUAL].map((opcao) => (
            <button
              key={opcao}
              type="button"
              onClick={() => setCiclo(opcao)}
              className={cn("rounded-md px-3 py-1 text-13", {
                "shadow-sm bg-layer-1 font-medium text-primary": ciclo === opcao,
                "text-secondary": ciclo !== opcao,
              })}
            >
              {t(`${raiz}.planos.${opcao === CICLO_ANUAL ? "anual" : "mensal"}`)}
              {opcao === CICLO_ANUAL ? (
                <span className="text-success ml-1 text-11">{t(`${raiz}.planos.economia_anual`)}</span>
              ) : null}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-3 grid gap-3 md:grid-cols-3">
        {ORDEM_DOS_PLANOS.map((chave) => {
          const plano = PLANOS[chave];
          const anual = ciclo === CICLO_ANUAL;
          const preco = anual ? precoAnual(chave) : plano.mensal;
          const atual = retrato.plano === chave;

          return (
            <div
              key={chave}
              className={cn("flex flex-col rounded-lg border p-3", {
                "border-accent-primary bg-accent-primary/5": atual,
                "border-subtle": !atual,
              })}
            >
              <p className="text-14 font-semibold text-primary">{plano.nome}</p>
              <p className="mt-1 text-18 font-semibold text-primary">{emReais(preco)}</p>
              <p className="text-11 text-tertiary">{t(`${raiz}.planos.${anual ? "por_ano" : "por_mes"}`)}</p>
              <ul className="mt-2 flex-1 space-y-1 text-13 text-secondary">
                <li>{t(`${raiz}.planos.assentos_incluidos`, { quantidade: plano.assentos })}</li>
                <li>
                  {t(`${raiz}.planos.adicional`, {
                    valor: emReais(anual ? plano.adicionalMensal * 10 : plano.adicionalMensal),
                  })}
                </li>
                <li>
                  {plano.convidadosPorAssento
                    ? t(`${raiz}.planos.convidados`, { quantidade: plano.convidadosPorAssento })
                    : t(`${raiz}.planos.sem_convidados`)}
                </li>
              </ul>
              <Button
                className="mt-3"
                variant={atual ? "secondary" : "primary"}
                disabled={atual || Boolean(ocupado)}
                loading={ocupado === chave}
                onClick={() => escolher(chave)}
              >
                {atual
                  ? t(`${raiz}.planos.plano_atual`)
                  : jaContratou
                    ? t(`${raiz}.planos.trocar`)
                    : t(`${raiz}.planos.contratar`)}
              </Button>
            </div>
          );
        })}
      </div>

      {!jaContratou ? (
        <div className="mt-4 grid gap-3 border-t border-subtle pt-3 md:grid-cols-2">
          <div>
            <p className="mb-1 text-13 font-medium text-primary">{t(`${raiz}.forma.titulo`)}</p>
            {["pix", "cartao"].map((opcao) => (
              <label key={opcao} className="flex items-start gap-2 py-1 text-13 text-secondary">
                <input type="radio" className="mt-1" checked={forma === opcao} onChange={() => setForma(opcao)} />
                <span>
                  <span className="font-medium text-primary">{t(`${raiz}.forma.${opcao}`)}</span>
                  <br />
                  {t(`${raiz}.forma.${opcao}_ajuda`)}
                </span>
              </label>
            ))}
          </div>
          <div>
            <p className="mb-1 text-13 font-medium text-primary">{t(`${raiz}.cupom.titulo`)}</p>
            <div className="flex gap-2">
              <Input
                placeholder={t(`${raiz}.cupom.campo`)}
                value={codigo}
                onChange={(evento) => setCodigo(evento.target.value.toUpperCase())}
              />
              <Button variant="secondary" onClick={aplicarCupom} disabled={!codigo}>
                {t(`${raiz}.cupom.aplicar`)}
              </Button>
            </div>
            {cupom ? (
              <p className="text-success mt-1 text-13">{t(`${raiz}.cupom.aplicado`, { codigo: cupom.codigo })}</p>
            ) : null}
          </div>
        </div>
      ) : null}
    </div>
  );
});
