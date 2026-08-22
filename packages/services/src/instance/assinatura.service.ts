/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { API_BASE_URL } from "@plane/constants";
import { APIService } from "../api.service";

/** Uma linha do painel de assinaturas do god-mode (ADR 0021). */
export type TAssinaturaDaInstancia = {
  id: string;
  workspace_id: string;
  nome: string;
  slug: string;
  plano: string;
  ciclo: string;
  status: string;
  pago_ate: string | null;
  proxima_cobranca_em: string | null;
  promocao_termina_em: string | null;
  remover_dados_em: string | null;
  assentos_incluidos: number;
  assentos_extras: number;
  membros: number;
  excedente: number;
  convidados: number;
  convidados_cota: number;
  valor: number;
  asaas_subscription_id: string;
};

export type TSaudeDoFaturamento = {
  ultimo_evento_em: string | null;
  alarme: string | null;
  por_status: Record<string, number>;
  planos: string[];
  estados: string[];
};

export type TResumoDoFaturamento = {
  receita_recorrente_mensal: number;
  por_plano: Record<string, number>;
  assinaturas_cobrando: number;
  inadimplentes: number;
  excedentes: number;
  promocoes_a_vencer: number;
};

export type TAcaoDeAssinatura = {
  acao: "bloquear" | "liberar" | "atribuir_plano" | "conceder_cortesia";
  motivo: string;
  plano?: string;
  ciclo?: string;
  dias?: number;
  /** Assentos além do plano. Em cortesia o preço por assento é zero, então
   *  isto é capacidade pura — é o que a conta interna ajusta. */
  assentos_extras?: number;
};

/**
 * O painel de assinaturas da instância.
 *
 * Vive em `@plane/services` como as outras chamadas do god-mode — o admin não
 * tem camada de serviço própria, e criar uma só para isto seria um segundo
 * padrão para o mesmo problema.
 */
export class InstanceAssinaturaService extends APIService {
  constructor(BASE_URL?: string) {
    super(BASE_URL || API_BASE_URL);
  }

  async list(params: { cursor?: string; status?: string; search?: string; excedentes?: string } = {}) {
    return this.get(`/api/instances/assinaturas/`, { params })
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async saude(): Promise<TSaudeDoFaturamento> {
    return this.get(`/api/instances/assinaturas/saude/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async resumo(): Promise<TResumoDoFaturamento> {
    return this.get(`/api/instances/assinaturas/resumo/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async historico(workspaceId: string) {
    return this.get(`/api/instances/assinaturas/${workspaceId}/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async agir(workspaceId: string, acao: TAcaoDeAssinatura) {
    return this.patch(`/api/instances/assinaturas/${workspaceId}/`, acao)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }
}
