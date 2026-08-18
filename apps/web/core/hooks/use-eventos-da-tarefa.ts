/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: a página de UMA tarefa, aberta por link direto (ADR 0013).
//
// O painel que abre sobre o quadro já acompanhava de graça: ele lê do mesmo
// mapa que o receptor do quadro atualiza, e é montado dentro do quadro, então
// aquele gancho continua no ar. A página `/browse/<identificador>` não — é rota
// própria, sem root de layout, e nenhum gancho era montado. Abrir uma tarefa
// por link e deixá-la aberta não recebia aviso nenhum.
//
// A fiação é a mesma do quadro e vem de `useCanalDeEventos`. O que muda é a
// reação, e ela é bem mais simples: só existe UMA tarefa em jogo, não há lista
// para reposicionar e não há filtro para avaliar.

import { useContext, useEffect, useRef } from "react";
import { revalidarValoresDoProjeto } from "@/components/issue-properties/store";
import { useCanalDeEventos } from "@/hooks/use-canal-de-eventos";
import { StoreContext } from "@/lib/store-context";
import { IssueService } from "@/services/issue";

const issueService = new IssueService();

/** Espera antes de buscar: várias mudanças seguidas viram uma requisição só. */
const AGRUPAMENTO_MS = 250;

export const useEventosDaTarefa = (
  workspaceSlug: string | undefined,
  projectId: string | undefined,
  issueId: string | undefined
) => {
  const raiz = useContext(StoreContext)?.issue.issues;

  const raizRef = useRef(raiz);
  const issueIdRef = useRef(issueId);
  const agrupamentoRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const vivoRef = useRef(true);

  // Escrita de ref em efeito, e não no render — ver o canal.
  useEffect(() => {
    raizRef.current = raiz;
    issueIdRef.current = issueId;
  });

  useEffect(() => {
    vivoRef.current = true;
    return () => {
      vivoRef.current = false;
      if (agrupamentoRef.current) clearTimeout(agrupamentoRef.current);
    };
  }, []);

  useCanalDeEventos(workspaceSlug, projectId, (aviso) => {
    if (!workspaceSlug || !projectId) return;

    // A chave dos valores é do PROJETO, não da tarefa — então este aviso vale
    // mesmo quando é de outra tarefa: a resposta do endereço muda igual.
    if (aviso.tipo === "propriedade") {
      revalidarValoresDoProjeto(projectId);
      return;
    }

    // Só esta tarefa interessa: a página mostra uma só.
    if (!aviso.tarefa || aviso.tarefa !== issueIdRef.current) return;

    // `criada` não faz sentido aqui — não há lista. E `removida` fica de fora
    // DE PROPÓSITO: tirar a tarefa da tela significaria navegar a pessoa para
    // outro lugar no meio da leitura, e isso é decisão de produto, não de
    // sincronismo. Fica declarado no ADR em vez de acontecer por acidente.
    if (aviso.tipo !== "alterada") return;

    if (agrupamentoRef.current) clearTimeout(agrupamentoRef.current);
    agrupamentoRef.current = setTimeout(async () => {
      const alvo = issueIdRef.current;
      if (!alvo || !vivoRef.current) return;
      try {
        const fresca = await issueService.retrieve(workspaceSlug, projectId, alvo);
        if (!vivoRef.current || !fresca) return;
        // `addIssue` mescla no mapa raiz, que é de onde esta página lê. Não há
        // `issueUpdate` aqui porque não há store de quadro — e não faz falta:
        // sem lista, não há o que reposicionar.
        raizRef.current?.addIssue([fresca]);
      } catch {
        // Quem não pode mais ver a tarefa recebe erro e a tela fica como está.
      }
    }, AGRUPAMENTO_MS);
  });
};
