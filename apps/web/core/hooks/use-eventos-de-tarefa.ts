/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: recebe do `live` o aviso de que uma tarefa mudou (ADR 0013).
//
// O quadro atualizava o cartão otimisticamente, do que ELE mesmo mandou, e não
// revalidava nem ao voltar para a aba. Mudança vinda de fora — automação, ou
// outra pessoa no mesmo quadro — só aparecia recarregando a página.
//
// O aviso traz identificadores, nunca conteúdo: quem chega aqui vai buscar a
// tarefa pela API normal, que aplica todas as permissões. Ver o ADR para o
// porquê dessa escolha valer mais que a economia de uma requisição.
//
// Fase 1: só `alterada`. `criada` e `removida` mudam a participação da tarefa na
// lista e precisam de tratamento próprio — em especial, `updateIssueList` NÃO
// avalia os filtros ricos do quadro, então acrescentar às cegas uma tarefa nova
// faria aparecer, para quem filtrou, um cartão que o filtro exclui.

import { useEffect, useRef } from "react";
import { LIVE_BASE_PATH, LIVE_BASE_URL } from "@plane/constants";
import type { EIssuesStoreType } from "@plane/types";
import { useIssues } from "@/hooks/store/use-issues";
import { useUser } from "@/hooks/store/user";
import { IssueService } from "@/services/issue";

/** Espera antes de buscar, para uma edição em lote virar uma requisição só. */
const AGRUPAMENTO_MS = 250;
/** Primeira espera de reconexão; dobra a cada tentativa até o teto. */
const RECONEXAO_INICIAL_MS = 1_000;
const RECONEXAO_MAXIMA_MS = 30_000;

const issueService = new IssueService();

/**
 * A tarefa está NESTE quadro?
 *
 * Perguntar ao mapa global de tarefas não serve, e o motivo é sutil: o mapa
 * guarda tudo que já foi carregado em qualquer tela, inclusive o que o filtro
 * deste quadro exclui. `updateIssueList` reposiciona pela DIFERENÇA entre o
 * estado anterior e o novo — se o campo do agrupamento mudou, ela ACRESCENTA a
 * tarefa ao grupo novo. Uma tarefa fora do quadro que mudasse de estado
 * apareceria, portanto, num quadro cujo filtro a exclui.
 *
 * `groupedIssueIds` tem duas formas: `{grupo: id[]}` quando agrupado e
 * `{grupo: {subgrupo: id[]}}` quando subagrupado. As duas são varridas aqui.
 */
const estaNoQuadro = (grupos: unknown, issueId: string): boolean => {
  if (!grupos || typeof grupos !== "object") return false;
  for (const valor of Object.values(grupos as Record<string, unknown>)) {
    if (Array.isArray(valor)) {
      if (valor.includes(issueId)) return true;
    } else if (valor && typeof valor === "object") {
      for (const lista of Object.values(valor as Record<string, unknown>)) {
        if (Array.isArray(lista) && lista.includes(issueId)) return true;
      }
    }
  }
  return false;
};

const enderecoDoCanal = (workspaceSlug: string, projectId: string): string | undefined => {
  if (typeof window === "undefined") return undefined;
  try {
    const base = LIVE_BASE_URL?.trim() || window.location.origin;
    const url = new URL(base);
    url.protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    url.pathname = `${LIVE_BASE_PATH}/eventos/`;
    url.searchParams.set("workspaceSlug", workspaceSlug);
    url.searchParams.set("projectId", projectId);
    return url.toString();
  } catch {
    return undefined;
  }
};

/**
 * Só os quadros presos a UM projeto.
 *
 * A sala do `live` é por projeto, então quadro que atravessa projetos — a visão
 * global do workspace, os rascunhos — precisaria de outra estratégia de
 * assinatura. Está no tipo, e não num comentário, para o erro aparecer na
 * compilação de quem tentar ligar o gancho no lugar errado.
 */
type QuadroDeProjeto =
  | EIssuesStoreType.PROJECT
  | EIssuesStoreType.CYCLE
  | EIssuesStoreType.MODULE
  | EIssuesStoreType.PROJECT_VIEW;

export const useEventosDeTarefa = (
  workspaceSlug: string | undefined,
  projectId: string | undefined,
  storeType: QuadroDeProjeto
) => {
  const { issues } = useIssues(storeType);
  const { data: currentUser } = useUser();

  // O store e o usuário entram por referência, e não pela lista de dependências
  // do efeito: o store é observável e trocaria de identidade a cada render, o
  // que derrubaria e reabriria a conexão sem parar.
  const issuesRef = useRef(issues);
  const meuIdRef = useRef(currentUser?.id);

  // A escrita mora num efeito, e não no corpo da renderização.
  //
  // Renderização precisa ser pura: o React pode repetir ou descartar o trabalho
  // de render, e uma escrita feita ali vaza de uma tela que nunca chegou a ser
  // confirmada. O valor inicial vem do próprio `useRef`, então o primeiro render
  // já enxerga o certo; deste efeito para frente, cada confirmação atualiza.
  // Este efeito é declarado ANTES do da conexão, e o React os roda nessa ordem.
  useEffect(() => {
    issuesRef.current = issues;
    meuIdRef.current = currentUser?.id;
  });

  useEffect(() => {
    if (!workspaceSlug || !projectId) return;
    const endereco = enderecoDoCanal(workspaceSlug, projectId);
    if (!endereco) return;

    let socket: WebSocket | undefined;
    let esperaDeReconexao = RECONEXAO_INICIAL_MS;
    let reconexao: ReturnType<typeof setTimeout> | undefined;
    let agrupamento: ReturnType<typeof setTimeout> | undefined;
    let desmontado = false;
    const pendentes = new Set<string>();

    const buscarPendentes = async () => {
      const ids = [...pendentes];
      pendentes.clear();
      // As duas guardas são necessárias e não se sobrepõem: esta evita a
      // requisição de quem já saiu do quadro, e a de baixo cobre quem saiu
      // DURANTE a requisição.
      if (ids.length === 0 || desmontado) return;
      try {
        const frescas = await issueService.retrieveIssues(workspaceSlug, projectId, ids);
        if (desmontado) return;
        for (const fresca of frescas ?? []) {
          // `shouldSync: false` é o ponto todo: aplica no store SEM escrever de
          // volta na API. Sem ele, receber um aviso viraria um PATCH, e dois
          // navegadores abertos ficariam se respondendo em laço.
          issuesRef.current?.issueUpdate?.(workspaceSlug, projectId, fresca.id, fresca, false);
        }
      } catch {
        // Quem não pode ver a tarefa recebe erro da API e não mostra nada — é
        // justamente o que faz o aviso poder ser cego a permissão.
      }
    };

    const aoReceber = (evento: MessageEvent) => {
      let dados: { tipo?: string; tarefa?: string; ator?: string | null };
      try {
        dados = JSON.parse(evento.data as string);
      } catch {
        return;
      }
      if (dados.tipo !== "alterada" || !dados.tarefa) return;
      // O próprio eco: quem mudou já aplicou o efeito otimisticamente, e
      // rebuscar por causa dele seria requisição jogada fora.
      //
      // LIMITE CONHECIDO DA FASE 1: o filtro é por PESSOA, e não por conexão.
      // Duas abas da mesma pessoa não se enxergam — mudar algo na primeira não
      // atualiza a segunda. Não afeta o defeito que motivou o ADR 0013 (o ator
      // da automação é o robô, e o de outra pessoa é ela), e a saída é o
      // servidor devolver um identificador de CONEXÃO para filtrar por ele.
      if (dados.ator && dados.ator === meuIdRef.current) return;
      // Tarefa que não está neste quadro não interessa — ver `estaNoQuadro`.
      if (!estaNoQuadro(issuesRef.current?.groupedIssueIds, dados.tarefa)) return;

      pendentes.add(dados.tarefa);
      if (agrupamento) clearTimeout(agrupamento);
      agrupamento = setTimeout(buscarPendentes, AGRUPAMENTO_MS);
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
      socket.onmessage = aoReceber;
      socket.onclose = (fechamento) => {
        // 1000 é saída normal e 1008 é recusa (origem, sessão ou acesso ao
        // projeto). Reconectar depois de uma recusa só repetiria a recusa.
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
      if (agrupamento) clearTimeout(agrupamento);
      socket?.close(1000, "saiu do quadro");
    };
  }, [workspaceSlug, projectId]);
};
