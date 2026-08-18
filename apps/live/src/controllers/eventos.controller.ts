/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: o canal que avisa a tela de que algo mudou (ADR 0013).
//
// Rota: `/live/eventos/?workspaceSlug=<slug>[&projectId=<uuid>]`.
//
// **O projeto é opcional**, e essa é a diferença entre os dois usos:
//
// * COM projeto — o quadro e a página de tarefa. Entra na sala do projeto e
//   recebe os avisos de tarefa.
// * SEM projeto — a caixa de entrada. O sino vive fora de qualquer quadro, e a
//   notificação é de uma PESSOA, não de um projeto.
//
// Toda conexão entra na sala da própria pessoa, com ou sem projeto: é por ela
// que a notificação chega.
//
// A conexão só entra nas salas depois de passar por três portas, nesta ordem, da
// mais barata para a mais cara:
//
//   1. **Origem.** A autenticação aqui é por cookie, e cookie o navegador manda
//      sozinho — inclusive a partir de uma página de terceiro que abra um
//      WebSocket para cá (*cross-site WebSocket hijacking*). O `cors()` do
//      Express NÃO cobre isto: a negociação de WebSocket não faz preflight.
//   2. **Identidade.** O cookie é de alguém que a API reconhece?
//   3. **Acesso ao projeto.** Esse alguém participa deste projeto? Só se
//      aplica havendo projeto — sem ele, a identidade já basta, porque a sala
//      da pessoa entrega o que é dela e nada mais.
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

// Os dois parâmetros entram no CAMINHO de uma requisição à API, e vêm da URL de
// quem conecta. Sem validar a forma, `projectId = "../../users/me"` normaliza
// para outro endpoint — um que responde 200 para qualquer sessão —, e a porta de
// acesso ao projeto abre sozinha.
//
// Hoje o estrago pararia aí, porque a sala passaria a se chamar `"../../users/me"`
// e o Django só publica UUID: nenhum evento casaria. Mas isso é acidente de
// igualdade de string, não desenho, e uma refatoração do nome da sala o
// transformaria em vazamento. Encontrado pelo CodeQL (js/request-forgery).
//
// Validar a FORMA, e não escapar: as duas são conhecidas — UUID e slug do
// Django (`SlugField`, 48 caracteres) —, e recusar o que não se parece com elas
// é mais estreito do que confiar num escape estar certo em todo caminho.
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const SLUG = /^[A-Za-z0-9_-]{1,48}$/;

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
    // Sem projeto é caso legítimo: a caixa de entrada conecta assim, porque o
    // sino vive fora de qualquer quadro. Essa conexão entra só na sala da
    // pessoa e recebe apenas os avisos de notificação.
    const projectId = req.query.projectId ? String(req.query.projectId) : undefined;
    const cookie = req.headers.cookie;

    if (!origemConfere(req.headers.origin)) {
      logger.warn(`EVENTOS: origem recusada: ${req.headers.origin}`);
      ws.close(1008, "Origin not allowed");
      return;
    }
    if (!workspaceSlug || !cookie) {
      ws.close(1008, "Missing parameters");
      return;
    }
    if (!SLUG.test(workspaceSlug) || (projectId !== undefined && !UUID.test(projectId))) {
      logger.warn(`EVENTOS: parâmetro fora de forma recusado: ${workspaceSlug} / ${projectId}`);
      ws.close(1008, "Malformed parameters");
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

    // A porta do projeto só faz sentido havendo projeto. Sem ele, a identidade
    // já basta: a sala da pessoa entrega o que é dela, e nada mais.
    if (projectId && !(await this.projectService.podeVer(cookie, workspaceSlug, projectId))) {
      logger.warn(`EVENTOS: ${userId} sem acesso ao projeto ${projectId}`);
      ws.close(1008, "Forbidden");
      return;
    }

    // A porta pode ter sido fechada enquanto as checagens corriam. Entrar na
    // sala agora deixaria um socket morto recebendo mensagem para sempre,
    // porque o `close` abaixo ainda nem foi registrado. 1 === OPEN.
    if (ws.readyState !== 1) return;

    await salasDeEventos.entrar(projectId, userId, ws);
    logger.info(`EVENTOS: ${userId} entrou — projeto ${projectId ?? "(nenhum)"}`);

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
      salasDeEventos.sair(projectId, userId, ws);
    };

    ws.on("close", encerrar);
    ws.on("error", (erro: Error) => {
      logger.error("EVENTOS: erro na conexão", erro);
      encerrar();
      ws.close(1011, "Internal server error");
    });
  }
}
