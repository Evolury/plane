/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: o canal que avisa o quadro de que uma tarefa mudou (ADR 0013).
//
// Rota: `/live/eventos/?workspaceSlug=<slug>&projectId=<uuid>`.
//
// A conexão só entra na sala depois de passar por três portas, nesta ordem, da
// mais barata para a mais cara:
//
//   1. **Origem.** A autenticação aqui é por cookie, e cookie o navegador manda
//      sozinho — inclusive a partir de uma página de terceiro que abra um
//      WebSocket para cá (*cross-site WebSocket hijacking*). O `cors()` do
//      Express NÃO cobre isto: a negociação de WebSocket não faz preflight.
//   2. **Identidade.** O cookie é de alguém que a API reconhece?
//   3. **Acesso ao projeto.** Esse alguém participa deste projeto?
//
// A terceira porta é a que não existia no serviço: `onAuthenticate`, do caminho
// de documentos, lê `projectId` do parâmetro da URL sem validar — o que lá é
// coberto adiante, na busca da página, e aqui não seria por nada.

import type { Request } from "express";
import type { WebSocket } from "ws";
import { Controller, WebSocket as WSDecorator } from "@plane/decorators";
import { logger } from "@plane/logger";
import { env } from "@/env";
import { salasDeEventos } from "@/lib/eventos-de-tarefa";
import { ProjectService } from "@/services/project.service";
import { UserService } from "@/services/user.service";

/** De quanto em quanto tempo o servidor cutuca a conexão, em ms. */
const INTERVALO_DE_PING = 30_000;

const origensPermitidas = () =>
  env.CORS_ALLOWED_ORIGINS.split(",")
    .map((origem) => origem.trim())
    .filter(Boolean);

/**
 * Origem ausente é aceita porque cliente que não é navegador não manda o
 * cabeçalho — e ele também não carrega cookie de terceiro, que é o ataque que
 * esta porta existe para barrar. Lista vazia não abre a porta para qualquer um:
 * sem origem configurada, só passa quem não declara origem.
 */
const origemConfere = (origem: string | undefined): boolean => {
  if (!origem) return true;
  return origensPermitidas().includes(origem);
};

@Controller("/eventos")
export class EventosController {
  [key: string]: unknown;
  private readonly projectService = new ProjectService();
  private readonly userService = new UserService();

  @WSDecorator("/")
  async handleConnection(ws: WebSocket, req: Request) {
    const workspaceSlug = String(req.query.workspaceSlug ?? "");
    const projectId = String(req.query.projectId ?? "");
    const cookie = req.headers.cookie;

    if (!origemConfere(req.headers.origin)) {
      logger.warn(`EVENTOS: origem recusada: ${req.headers.origin}`);
      ws.close(1008, "Origin not allowed");
      return;
    }
    if (!workspaceSlug || !projectId || !cookie) {
      ws.close(1008, "Missing parameters");
      return;
    }

    // `handleAuthentication` do caminho de documentos não serve aqui: ela exige
    // o `userId` de antemão, para conferir contra o do cookie. Ali o cliente o
    // declara no token do Hocuspocus; aqui não há token, e a identidade é o que
    // se quer descobrir — não confirmar.
    let userId: string;
    try {
      const usuario = await this.userService.currentUser(cookie);
      if (!usuario?.id) throw new Error("sem usuário");
      userId = usuario.id;
    } catch {
      ws.close(1008, "Unauthorized");
      return;
    }

    if (!(await this.projectService.podeVer(cookie, workspaceSlug, projectId))) {
      logger.warn(`EVENTOS: ${userId} sem acesso ao projeto ${projectId}`);
      ws.close(1008, "Forbidden");
      return;
    }

    // A porta pode ter sido fechada enquanto as checagens corriam. Entrar na
    // sala agora deixaria um socket morto recebendo mensagem para sempre,
    // porque o `close` abaixo ainda nem foi registrado. 1 === OPEN.
    if (ws.readyState !== 1) return;

    await salasDeEventos.entrar(projectId, ws);
    logger.info(`EVENTOS: ${userId} entrou na sala do projeto ${projectId}`);

    // Sem isto, um proxy que corta conexão ociosa derruba o canal em silêncio: a
    // tela para de receber aviso e volta a parecer o defeito que isto corrige.
    const ping = setInterval(() => {
      if (ws.readyState !== 1) return;
      try {
        ws.ping();
      } catch {
        /* o `close` cuida da limpeza */
      }
    }, INTERVALO_DE_PING);

    const encerrar = () => {
      clearInterval(ping);
      salasDeEventos.sair(projectId, ws);
    };

    ws.on("close", encerrar);
    ws.on("error", (erro: Error) => {
      logger.error("EVENTOS: erro na conexão", erro);
      encerrar();
      ws.close(1011, "Internal server error");
    });
  }
}
