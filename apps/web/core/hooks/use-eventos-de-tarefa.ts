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
// Cada aviso tem uma resposta, e a diferença entre elas é o ponto do desenho:
//
// * **alterada** — rebusca SÓ aquela tarefa e remenda o cartão. É o caso comum
//   e o mais barato.
// * **removida** — tira do quadro. Não depende de filtro nenhum: o que saiu,
//   saiu.
// * **criada**   — rebusca a LISTA. Custa mais, e é o preço de estar certo: o
//   cliente não tem como avaliar os filtros ricos do quadro, e acrescentar às
//   cegas faria aparecer, para quem filtrou, um cartão que o filtro exclui.

import { useEffect, useRef } from "react";
import type { EIssuesStoreType } from "@plane/types";
import { revalidarValoresDoProjeto } from "@/components/issue-properties/store";
import { useCanalDeEventos } from "@/hooks/use-canal-de-eventos";
import { useIssues } from "@/hooks/store/use-issues";
import { IssueService } from "@/services/issue";

/** Espera antes de buscar, para uma edição em lote virar uma requisição só. */
const AGRUPAMENTO_MS = 250;
/** Idem para a rebusca da lista, que é bem mais cara e pode chegar em rajada. */
const AGRUPAMENTO_DE_LISTA_MS = 600;
/** O que este gancho sabe responder. O resto é ignorado sem ruído. */
const TIPOS_CONHECIDOS = new Set(["alterada", "criada", "removida", "propriedade"]);

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
  storeType: QuadroDeProjeto,
  /**
   * Como este quadro rebusca a própria lista.
   *
   * Vem de fora porque `fetchIssuesWithExistingPagination` tem assinatura
   * DIFERENTE em cada quadro — ciclo e módulo exigem o próprio id, e a visão a
   * dela, em posições que nem sequer coincidem. Quem sabe montar a chamada é o
   * quadro; forçar um tipo comum aqui seria um `cast` escondendo isso.
   *
   * Sem ela, o gancho continua tratando `alterada` e `removida`, e só deixa de
   * reagir a tarefa nova.
   */
  rebuscarQuadro?: () => void
) => {
  const { issues } = useIssues(storeType);

  const issuesRef = useRef(issues);
  const rebuscarRef = useRef(rebuscarQuadro);
  const pendentesRef = useRef(new Set<string>());
  const agrupamentoRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const listaPendenteRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const vivoRef = useRef(true);

  // Escrita de ref em efeito, e não no render — ver o canal.
  useEffect(() => {
    issuesRef.current = issues;
    rebuscarRef.current = rebuscarQuadro;
  });

  useEffect(() => {
    vivoRef.current = true;
    return () => {
      vivoRef.current = false;
      if (agrupamentoRef.current) clearTimeout(agrupamentoRef.current);
      if (listaPendenteRef.current) clearTimeout(listaPendenteRef.current);
    };
  }, []);

  useCanalDeEventos(workspaceSlug, projectId, (aviso) => {
    if (!workspaceSlug || !projectId) return;
    if (!TIPOS_CONHECIDOS.has(aviso.tipo)) return;
    // Todo tipo tratado aqui fala de uma tarefa; o aviso de notificação, que
    // não fala, é filtrado pelo `TIPOS_CONHECIDOS` acima.
    if (!aviso.tarefa) return;

    // Valor de propriedade personalizada não vive no store de tarefas: o cartão
    // o lê de uma chave PRÓPRIA, do projeto inteiro. Rebuscar a tarefa não o
    // traria — foi o defeito do #144, agora entre clientes em vez de dentro do
    // mesmo. Por isso não se pergunta se a tarefa está neste quadro: a chave é
    // do projeto.
    if (aviso.tipo === "propriedade") {
      revalidarValoresDoProjeto(projectId);
      return;
    }

    // Tarefa nova é o único caso em que "não está no quadro" não é motivo para
    // desistir — é justamente o que se quer descobrir. A rebusca é agrupada com
    // folga: criar dez tarefas de uma vez, como faz uma automação de subtarefas,
    // não pode virar dez rebuscas de página inteira.
    if (aviso.tipo === "criada") {
      if (listaPendenteRef.current) clearTimeout(listaPendenteRef.current);
      listaPendenteRef.current = setTimeout(() => {
        if (vivoRef.current) rebuscarRef.current?.();
      }, AGRUPAMENTO_DE_LISTA_MS);
      return;
    }

    // Daqui para baixo, tarefa que não está neste quadro não interessa — ver
    // `estaNoQuadro`.
    if (!estaNoQuadro(issuesRef.current?.groupedIssueIds, aviso.tarefa)) return;

    if (aviso.tipo === "removida") {
      // Tirar é exato e imediato: nada a buscar, e esperar o agrupamento só
      // deixaria na tela um cartão que já não existe.
      issuesRef.current?.removeIssueFromList?.(aviso.tarefa);
      return;
    }

    pendentesRef.current.add(aviso.tarefa);
    if (agrupamentoRef.current) clearTimeout(agrupamentoRef.current);
    agrupamentoRef.current = setTimeout(async () => {
      const ids = [...pendentesRef.current];
      pendentesRef.current.clear();
      if (ids.length === 0 || !vivoRef.current) return;
      try {
        const frescas = await issueService.retrieveIssues(workspaceSlug, projectId, ids);
        if (!vivoRef.current) return;
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
    }, AGRUPAMENTO_MS);
  });
};
