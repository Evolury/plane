/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { API_BASE_URL } from "@plane/constants";
// services
import { APIService } from "@/services/api.service";

/** O retrato do plano de um espaço — plano, estado e uso, numa chamada só. */
export type TRetratoDoPlano = {
  plano: string;
  nome: string;
  ciclo: string;
  status: string;
  pode_escrever: boolean;
  pago_ate: string | null;
  proxima_cobranca_em: string | null;
  promocao_termina_em: string | null;
  proximo_marco: { data: string; estado: string } | null;
  recursos: Record<string, boolean>;
  limites: Record<string, number | null>;
  assentos: { incluidos: number; extras: number; usados: number };
  convidados: { cota: number; usados: number };
  automacoes_ativas: number;
};

export type TDadosDeCobranca = {
  nome: string;
  cpf_cnpj: string;
  email: string;
  telefone: string;
  completo: boolean;
};

export type TCupom = {
  codigo: string;
  tipo: "percentual" | "cortesia";
  valor: number;
  ciclos: number | null;
  descricao: string;
};

export type TCobranca = {
  id: string;
  status: string;
  forma: string;
  valor: number;
  vencimento: string;
  pago_em: string | null;
  link: string;
};

export type TContratacao = { forma: string; link: string; id: string };

export type TTrocaDePlano = {
  plano: string;
  imediato: boolean;
  diferenca: { link: string | null; valor: number | null } | null;
};

export class FaturamentoService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  async retrato(workspaceSlug: string): Promise<TRetratoDoPlano> {
    return this.get(`/api/workspaces/${workspaceSlug}/faturamento/plano/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async dadosDeCobranca(workspaceSlug: string): Promise<TDadosDeCobranca> {
    return this.get(`/api/workspaces/${workspaceSlug}/faturamento/dados-de-cobranca/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async salvarDadosDeCobranca(workspaceSlug: string, dados: Partial<TDadosDeCobranca>): Promise<{ completo: boolean }> {
    return this.post(`/api/workspaces/${workspaceSlug}/faturamento/dados-de-cobranca/`, dados)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async conferirCupom(workspaceSlug: string, codigo: string): Promise<TCupom> {
    return this.post(`/api/workspaces/${workspaceSlug}/faturamento/cupom/`, { codigo })
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async contratar(
    workspaceSlug: string,
    escolha: { plano: string; ciclo: string; forma: string; cupom?: string }
  ): Promise<TContratacao> {
    return this.post(`/api/workspaces/${workspaceSlug}/faturamento/contratar/`, escolha)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async trocarPlano(workspaceSlug: string, escolha: { plano: string; ciclo?: string }): Promise<TTrocaDePlano> {
    return this.post(`/api/workspaces/${workspaceSlug}/faturamento/trocar-plano/`, escolha)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async cobrancas(workspaceSlug: string): Promise<TCobranca[]> {
    return this.get(`/api/workspaces/${workspaceSlug}/faturamento/cobrancas/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }
}
