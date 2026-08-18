/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: a caixa de entrada acompanha sozinha (ADR 0013).
//
// O sino só buscava ao abrir a tela: uma notificação que chegasse com o produto
// aberto ficava invisível até alguém recarregar ou navegar. É o mesmo defeito do
// cartão, num lugar em que dói mais — notificação é justamente o que existe para
// avisar.
//
// Duas diferenças em relação ao gancho do quadro, e as duas vêm do mesmo fato:
// **notificação é de uma PESSOA, não de um projeto**.
//
// 1. A conexão vai SEM `projectId`. O sino vive na barra lateral, presente em
//    página que não tem quadro nenhum — exigir um projeto obrigaria a inventar
//    um.
// 2. O roteamento é pela sala da pessoa, do lado do `live`. O aviso que chega
//    aqui é só `{tipo: "notificacao"}`: quem mais foi avisado não é assunto de
//    quem recebe.

import { useEffect, useRef } from "react";
import { useWorkspaceNotifications } from "@/hooks/store/notifications";
import { useCanalDeEventos } from "@/hooks/use-canal-de-eventos";

/**
 * Espera antes de recontar.
 *
 * Folgada de propósito: uma automação que avisa uma equipe inteira, ou uma
 * tarefa com muitos inscritos, dispara vários avisos quase juntos — e a resposta
 * a todos eles é a mesma pergunta ao servidor.
 */
const AGRUPAMENTO_MS = 800;

export const useEventosDaCaixa = (workspaceSlug: string | undefined) => {
  const { getUnreadNotificationsCount } = useWorkspaceNotifications();

  const recontarRef = useRef(getUnreadNotificationsCount);
  const agrupamentoRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const vivoRef = useRef(true);

  // Escrita de ref em efeito, e não no render — ver o canal.
  useEffect(() => {
    recontarRef.current = getUnreadNotificationsCount;
  });

  useEffect(() => {
    vivoRef.current = true;
    return () => {
      vivoRef.current = false;
      if (agrupamentoRef.current) clearTimeout(agrupamentoRef.current);
    };
  }, []);

  useCanalDeEventos(workspaceSlug, undefined, (aviso) => {
    if (aviso.tipo !== "notificacao" || !workspaceSlug) return;

    if (agrupamentoRef.current) clearTimeout(agrupamentoRef.current);
    agrupamentoRef.current = setTimeout(() => {
      if (!vivoRef.current) return;
      // Só a contagem: é o que o sino mostra. A lista, quando aberta, tem
      // revalidação própria — e recarregá-la aqui gastaria uma requisição de
      // página inteira para atualizar um número.
      void recontarRef.current(workspaceSlug);
    }, AGRUPAMENTO_MS);
  });
};
