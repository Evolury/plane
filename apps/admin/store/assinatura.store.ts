/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { action, makeObservable, observable, runInAction } from "mobx";
// plane internal packages
import type {
  TAcaoDeAssinatura,
  TAssinaturaDaInstancia,
  TResumoDoFaturamento,
  TSaudeDoFaturamento,
} from "@plane/services";
import { InstanceAssinaturaService } from "@plane/services";

export type TFiltroDeAssinaturas = { status?: string; search?: string; excedentes?: boolean };

export interface IAssinaturaStore {
  assinaturas: TAssinaturaDaInstancia[];
  saude: TSaudeDoFaturamento | undefined;
  resumo: TResumoDoFaturamento | undefined;
  carregando: boolean;
  filtro: TFiltroDeAssinaturas;
  buscar: (filtro?: TFiltroDeAssinaturas) => Promise<void>;
  buscarSaude: () => Promise<void>;
  buscarResumo: () => Promise<void>;
  agir: (workspaceId: string, acao: TAcaoDeAssinatura) => Promise<void>;
  historico: (workspaceId: string) => Promise<any[]>;
}

/**
 * O painel de assinaturas (ADR 0021).
 *
 * Guarda a lista e o filtro juntos de propósito: agir sobre uma linha recarrega
 * a lista **com o mesmo filtro**, senão bloquear um espaço na lista de
 * "atrasados" faria a página inteira voltar ao começo — e o operador perderia
 * o lugar exatamente quando está trabalhando em série.
 */
export class AssinaturaStore implements IAssinaturaStore {
  assinaturas: TAssinaturaDaInstancia[] = [];
  saude: TSaudeDoFaturamento | undefined = undefined;
  resumo: TResumoDoFaturamento | undefined = undefined;
  carregando = false;
  filtro: TFiltroDeAssinaturas = {};
  // services
  service;

  constructor() {
    makeObservable(this, {
      assinaturas: observable,
      saude: observable,
      resumo: observable,
      carregando: observable.ref,
      filtro: observable,
      buscar: action,
      buscarSaude: action,
      buscarResumo: action,
      agir: action,
    });
    this.service = new InstanceAssinaturaService();
  }

  buscar = async (filtro?: TFiltroDeAssinaturas) => {
    const usado = filtro ?? this.filtro;
    runInAction(() => {
      this.carregando = true;
      this.filtro = usado;
    });
    try {
      const resposta = await this.service.list({
        status: usado.status || undefined,
        search: usado.search || undefined,
        excedentes: usado.excedentes ? "1" : undefined,
      });
      runInAction(() => {
        this.assinaturas = resposta?.results ?? [];
      });
    } finally {
      runInAction(() => {
        this.carregando = false;
      });
    }
  };

  buscarSaude = async () => {
    const saude = await this.service.saude();
    runInAction(() => {
      this.saude = saude;
    });
  };

  buscarResumo = async () => {
    const resumo = await this.service.resumo();
    runInAction(() => {
      this.resumo = resumo;
    });
  };

  agir = async (workspaceId: string, acao: TAcaoDeAssinatura) => {
    await this.service.agir(workspaceId, acao);
    await this.buscar();
    await this.buscarSaude();
    await this.buscarResumo();
  };

  historico = async (workspaceId: string) => this.service.historico(workspaceId);
}
