/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: a conexão com o `live`, sem opinião sobre o que fazer com o aviso
// (ADR 0013).
//
// Nasceu de uma extração: o quadro e a página de tarefa precisam da MESMA
// fiação — endereço, reconexão com recuo, leitura do JSON, reconhecimento do
// próprio eco, limpeza ao sair — e diferem só na reação. Duplicar isso seria
// duplicar também a chance de uma das cópias envelhecer sozinha.
//
// O que fica aqui é o que vale para todo consumidor. O que fazer com o aviso
// fica com quem chama.

import { useContext, useEffect, useRef } from "react";
import { LIVE_BASE_PATH, LIVE_BASE_URL } from "@plane/constants";
import { StoreContext } from "@/lib/store-context";
import { useUser } from "@/hooks/store/user";

/** Primeira espera de reconexão; dobra a cada tentativa até o teto. */
const RECONEXAO_INICIAL_MS = 1_000;
const RECONEXAO_MAXIMA_MS = 30_000;

export type TAvisoDeTarefa = {
  tipo: string;
  /** Ausente no aviso de notificação, que não fala de tarefa nenhuma. */
  tarefa: string | null;
  ator: string | null;
};

const enderecoDoCanal = (workspaceSlug: string, projectId: string | undefined): string | undefined => {
  if (typeof window === "undefined") return undefined;
  try {
    const base = LIVE_BASE_URL?.trim() || window.location.origin;
    const url = new URL(base);
    url.protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    url.pathname = `${LIVE_BASE_PATH}/eventos/`;
    url.searchParams.set("workspaceSlug", workspaceSlug);
    // Sem projeto é conexão de caixa de entrada: ela só quer os avisos da
    // própria pessoa, e o `live` a põe apenas na sala dela.
    if (projectId) url.searchParams.set("projectId", projectId);
    return url.toString();
  } catch {
    return undefined;
  }
};

/**
 * Abre o canal do projeto e entrega os avisos que sobrevivem ao filtro de eco.
 *
 * `aoReceber` pode mudar a cada render sem custo: ela é lida por referência, e
 * não entra na lista de dependências — se entrasse, a conexão cairia e
 * reabriria a cada render de quem chama.
 */
export const useCanalDeEventos = (
  workspaceSlug: string | undefined,
  /** Ausente na caixa de entrada — ver `enderecoDoCanal`. */
  projectId: string | undefined,
  aoReceber: (aviso: TAvisoDeTarefa) => void
) => {
  const { data: currentUser } = useUser();
  // O store RAIZ de tarefas: a anotação de escrita local vale para quem escreveu
  // de qualquer tela.
  const raiz = useContext(StoreContext)?.issue.issues;

  const meuIdRef = useRef(currentUser?.id);
  const raizRef = useRef(raiz);
  const aoReceberRef = useRef(aoReceber);

  // A escrita mora num efeito, e não no corpo da renderização: render precisa
  // ser puro, porque o React pode repetir ou descartar o trabalho e a escrita
  // feita ali vaza de uma tela que nunca chegou a ser confirmada.
  useEffect(() => {
    meuIdRef.current = currentUser?.id;
    raizRef.current = raiz;
    aoReceberRef.current = aoReceber;
  });

  useEffect(() => {
    if (!workspaceSlug) return;
    const endereco = enderecoDoCanal(workspaceSlug, projectId);
    if (!endereco) return;

    let socket: WebSocket | undefined;
    let esperaDeReconexao = RECONEXAO_INICIAL_MS;
    let reconexao: ReturnType<typeof setTimeout> | undefined;
    let desmontado = false;

    const aoChegar = (evento: MessageEvent) => {
      let dados: Partial<TAvisoDeTarefa>;
      try {
        dados = JSON.parse(evento.data as string);
      } catch {
        return;
      }
      // `tarefa` falta de propósito no aviso de notificação.
      if (!dados.tipo) return;

      // O próprio eco: esta aba já aplicou o efeito, e rebuscar por causa dele
      // seria requisição jogada fora — e poderia reverter na tela uma segunda
      // edição ainda a caminho.
      //
      // As DUAS perguntas são necessárias. Só a primeira confundiria "fui eu
      // nesta aba" com "fui eu na outra aba", e duas abas da mesma pessoa não
      // se enxergariam. Quem responde "nesta aba" é a anotação que a escrita
      // deixou no store raiz.
      const meuAtor = !!dados.ator && dados.ator === meuIdRef.current;
      if (meuAtor && dados.tarefa && raizRef.current?.consumirEscritaLocal(dados.tarefa)) return;

      aoReceberRef.current({ tipo: dados.tipo, tarefa: dados.tarefa ?? null, ator: dados.ator ?? null });
    };

    const conectar = () => {
      if (desmontado) return;
      try {
        socket = new WebSocket(endereco);
      } catch {
        return;
      }
      socket.onopen = () => {
        esperaDeReconexao = RECONEXAO_INICIAL_MS;
      };
      socket.onmessage = aoChegar;
      socket.onclose = (fechamento) => {
        // 1000 é saída normal e 1008 é recusa (origem, sessão, forma do
        // parâmetro ou acesso ao projeto). Reconectar depois de uma recusa só
        // repetiria a recusa.
        if (desmontado || fechamento.code === 1000 || fechamento.code === 1008) return;
        reconexao = setTimeout(conectar, esperaDeReconexao);
        esperaDeReconexao = Math.min(esperaDeReconexao * 2, RECONEXAO_MAXIMA_MS);
      };
      socket.onerror = () => socket?.close();
    };

    conectar();

    return () => {
      desmontado = true;
      if (reconexao) clearTimeout(reconexao);
      socket?.close(1000, "saiu da tela");
    };
  }, [workspaceSlug, projectId]);
};
