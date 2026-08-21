/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { action, computed, makeObservable, observable, runInAction } from "mobx";
// services
import type { TRetratoDoPlano } from "@/services/faturamento.service";
import { FaturamentoService } from "@/services/faturamento.service";

/**
 * O plano do espaço, do lado do cliente (ADR 0021).
 *
 * Este store **esconde**; quem recusa é o servidor. A distinção não é
 * acadêmica: qualquer cliente pode falar com a API sem passar por aqui, e uma
 * trava que só existe na tela é decoração. O que este store evita é o botão que
 * abre uma janela para terminar em erro — ninguém precisa descobrir por 402 que
 * o plano não inclui.
 *
 * Um retrato por espaço, buscado uma vez. O servidor já responde plano, estado
 * e uso na mesma chamada, de propósito: três chamadas fariam a tela piscar em
 * ordens diferentes a cada carregamento.
 */
export interface IFaturamentoStore {
  retratos: Record<string, TRetratoDoPlano>;
  carregando: boolean;
  buscarRetrato: (workspaceSlug: string) => Promise<TRetratoDoPlano | undefined>;
  retrato: (workspaceSlug: string) => TRetratoDoPlano | undefined;
  recursoLiberado: (workspaceSlug: string, recurso: string) => boolean;
  limite: (workspaceSlug: string, limite: string) => number | null | undefined;
  podeEscrever: (workspaceSlug: string) => boolean;
}

export class FaturamentoStore implements IFaturamentoStore {
  retratos: Record<string, TRetratoDoPlano> = {};
  carregando: boolean = false;
  // services
  faturamentoService;

  constructor() {
    makeObservable(this, {
      retratos: observable,
      carregando: observable.ref,
      buscarRetrato: action,
      espacosConhecidos: computed,
    });
    this.faturamentoService = new FaturamentoService();
  }

  get espacosConhecidos() {
    return Object.keys(this.retratos);
  }

  retrato = (workspaceSlug: string) => this.retratos[workspaceSlug];

  /**
   * Enquanto o retrato não chega, a resposta é **sim**.
   *
   * O contrário faria toda navegação começar com os recursos escondidos e
   * aparecendo um instante depois — e piscar item de menu é pior do que
   * mostrar por um segundo algo que o servidor vai recusar de qualquer forma.
   */
  recursoLiberado = (workspaceSlug: string, recurso: string) => {
    const retrato = this.retratos[workspaceSlug];
    if (!retrato) return true;
    return Boolean(retrato.recursos?.[recurso]);
  };

  limite = (workspaceSlug: string, limite: string) => this.retratos[workspaceSlug]?.limites?.[limite];

  podeEscrever = (workspaceSlug: string) => {
    const retrato = this.retratos[workspaceSlug];
    if (!retrato) return true;
    return retrato.pode_escrever;
  };

  buscarRetrato = async (workspaceSlug: string) => {
    if (!workspaceSlug) return undefined;
    try {
      runInAction(() => {
        this.carregando = true;
      });
      const retrato = await this.faturamentoService.retrato(workspaceSlug);
      runInAction(() => {
        this.retratos[workspaceSlug] = retrato;
        this.carregando = false;
      });
      return retrato;
    } catch {
      // Falha de rede não pode esconder recurso: sem retrato, a tela mostra
      // tudo e o servidor continua sendo quem recusa.
      runInAction(() => {
        this.carregando = false;
      });
      return undefined;
    }
  };
}
