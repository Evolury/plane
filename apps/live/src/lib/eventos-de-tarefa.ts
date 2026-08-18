/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: as salas por projeto e o assinante do Redis (ADR 0013).
//
// O Django publica num canal único, `evolury:tarefas`, e quem separa por projeto
// é este módulo: ele já tem as conexões abertas na mão e sabe quem está olhando
// o quê. Um canal por projeto multiplicaria assinaturas no Redis sem economizar
// nada — o volume é o mesmo, e a filtragem em memória custa um `Map.get`.
//
// A conexão do assinante é uma DUPLICATA de propósito: uma conexão que entrou em
// modo de assinatura não aceita mais nenhum outro comando, então usar a
// compartilhada quebraria todo o resto do serviço.

import type Redis from "ioredis";
import type { WebSocket } from "ws";
import { logger } from "@plane/logger";
import { redisManager } from "@/redis";

/** O mesmo nome do lado do Django (`plane/utils/tempo_real.py`). */
export const CANAL = "evolury:tarefas";

type Evento = {
  tipo: string;
  projeto: string;
  tarefa: string;
  ator: string | null;
};

class SalasDeEventos {
  private salas = new Map<string, Set<WebSocket>>();
  private assinante: Redis | null = null;
  private assinaturaEmCurso: Promise<void> | null = null;

  /** Põe a conexão na sala do projeto, garantindo que o assinante esteja de pé. */
  async entrar(projetoId: string, ws: WebSocket): Promise<void> {
    await this.assinar();
    const sala = this.salas.get(projetoId) ?? new Set<WebSocket>();
    sala.add(ws);
    this.salas.set(projetoId, sala);
  }

  /**
   * Tira a conexão da sala.
   *
   * A sala vazia é apagada, e não deixada como `Set` vazio: sem isso, um
   * servidor de longa duração acumula uma entrada por projeto que alguém já
   * abriu algum dia, e o mapa só cresce.
   */
  sair(projetoId: string, ws: WebSocket): void {
    const sala = this.salas.get(projetoId);
    if (!sala) return;
    sala.delete(ws);
    if (sala.size === 0) this.salas.delete(projetoId);
  }

  /** Quantas conexões há numa sala. Existe para o teste poder afirmar. */
  tamanho(projetoId: string): number {
    return this.salas.get(projetoId)?.size ?? 0;
  }

  private async assinar(): Promise<void> {
    if (this.assinante) return;
    // Duas conexões chegando juntas não podem criar dois assinantes — o segundo
    // receberia as mesmas mensagens e o cliente veria tudo em dobro.
    if (this.assinaturaEmCurso) return this.assinaturaEmCurso;

    this.assinaturaEmCurso = (async () => {
      const cliente = redisManager.getClient();
      if (!cliente) {
        logger.warn("EVENTOS: sem Redis, o quadro não recebe aviso de mudança");
        return;
      }
      const assinante = cliente.duplicate();
      await assinante.subscribe(CANAL);
      assinante.on("message", (_canal: string, mensagem: string) => this.distribuir(mensagem));
      this.assinante = assinante;
      logger.info(`EVENTOS: assinado em ${CANAL}`);
    })();

    try {
      await this.assinaturaEmCurso;
    } finally {
      this.assinaturaEmCurso = null;
    }
  }

  private distribuir(mensagem: string): void {
    let evento: Evento;
    try {
      evento = JSON.parse(mensagem) as Evento;
    } catch {
      logger.error("EVENTOS: mensagem que não é JSON, descartada");
      return;
    }
    if (!evento?.projeto || !evento?.tarefa) return;

    const sala = this.salas.get(evento.projeto);
    if (!sala || sala.size === 0) return;

    // O que sai daqui é o que entrou, sem enriquecer: identificadores, nunca
    // conteúdo. Quem recebe busca a tarefa pela API, que aplica as permissões.
    const carga = JSON.stringify({ tipo: evento.tipo, tarefa: evento.tarefa, ator: evento.ator });
    for (const ws of sala) {
      // 1 === OPEN. Uma conexão que fechou entre o evento e este laço ainda está
      // no `Set` até o `close` disparar; mandar nela lança.
      if (ws.readyState !== 1) continue;
      try {
        ws.send(carga);
      } catch (erro) {
        logger.error("EVENTOS: falha ao enviar para uma conexão", erro);
      }
    }
  }

  /** Solta o assinante. Chamado no encerramento do servidor. */
  async encerrar(): Promise<void> {
    this.salas.clear();
    if (this.assinante) {
      await this.assinante.quit().catch(() => this.assinante?.disconnect());
      this.assinante = null;
    }
  }
}

export const salasDeEventos = new SalasDeEventos();
