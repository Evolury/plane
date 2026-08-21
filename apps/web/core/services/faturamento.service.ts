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
}
