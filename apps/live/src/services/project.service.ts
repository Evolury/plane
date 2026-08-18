/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: quem pode entrar na sala de eventos de um projeto (ADR 0013).
//
// A pergunta é respondida pela API, e não aqui. Reimplementar a regra de acesso
// no `live` seria manter duas versões da mesma política, e toda divergência
// entre elas viraria vazamento — exatamente o que o desenho do ADR evita ao
// mandar só o aviso, e não o conteúdo.
//
// `GET /projects/<id>/` responde 200 só para quem participa do projeto: quem não
// participa leva 404 (não existe), 403 (secreto) ou 409 (não é membro). Qualquer
// coisa que não seja 200 é "não entra".

import { logger } from "@plane/logger";
import { APIService } from "@/services/api.service";

export class ProjectService extends APIService {
  /**
   * Responde se o dono deste cookie enxerga o projeto.
   *
   * Nunca lança: a decisão precisa ser um sim/não para quem está abrindo a
   * conexão, e uma API instável tem de fechar a porta, não derrubar o processo.
   */
  async podeVer(cookie: string, workspaceSlug: string, projectId: string): Promise<boolean> {
    try {
      const resposta = await this.get(`/api/workspaces/${workspaceSlug}/projects/${projectId}/`, {
        headers: { Cookie: cookie },
      });
      return resposta.status === 200;
    } catch (erro) {
      logger.info(`PROJECT_SERVICE: acesso negado ao projeto ${projectId}`, erro);
      return false;
    }
  }
}
