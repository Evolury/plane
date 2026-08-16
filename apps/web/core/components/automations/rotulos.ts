/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: os nomes por trás dos ids de uma regra (ADR 0012).
//
// A regra guarda id, nunca rótulo — é o que a mantém viva quando alguém
// renomeia um estado ou uma propriedade. O preço é que a tela precisa traduzir
// de volta, e é isto que faz aqui, num lugar só: a frase-resumo da lista e o
// editor mostram exatamente os mesmos nomes.
//
// Id que não resolve vira "—", e não some da frase: um destino apagado tem de
// aparecer como buraco, senão a regra parece dizer menos do que faz.

import { useCallback } from "react";
import { useTranslation } from "@plane/i18n";
import { CAMPOS_DE_GATILHO } from "@plane/constants";
import type { TIssueProperty } from "@plane/types";
import { usePropriedadesDoProjeto } from "@/components/issue-properties/store";
import { useLabel } from "@/hooks/store/use-label";
import { useMember } from "@/hooks/store/use-member";
import { useProjectState } from "@/hooks/store/use-project-state";

const VAZIO = "—";

export type TRotulos = {
  campo: (chave: string | undefined) => string;
  valorDoCampo: (chave: string | undefined, valor: string) => string;
  propriedade: (id: string | undefined) => string;
  propriedades: TIssueProperty[];
};

export const useRotulos = (workspaceSlug: string, projectId: string): TRotulos => {
  const { t } = useTranslation();
  const { getStateById } = useProjectState();
  const { getLabelById } = useLabel();
  const { getUserDetails } = useMember();
  const propriedades = usePropriedadesDoProjeto(workspaceSlug, projectId);

  const propriedade = useCallback(
    (id: string | undefined) => propriedades.find((item: TIssueProperty) => item.id === id)?.name ?? VAZIO,
    [propriedades]
  );

  const campo = useCallback(
    (chave: string | undefined) => {
      if (!chave) return VAZIO;
      if (chave.startsWith("property_")) return propriedade(chave.slice("property_".length));
      const conhecido = CAMPOS_DE_GATILHO.find((item) => item.valor === chave);
      return conhecido ? t(conhecido.i18n) : chave;
    },
    [propriedade, t]
  );

  const valorDoCampo = useCallback(
    (chave: string | undefined, valor: string) => {
      if (!valor) return VAZIO;
      switch (chave) {
        case "state_id":
          return getStateById(valor)?.name ?? VAZIO;
        case "label_id":
          return getLabelById(valor)?.name ?? VAZIO;
        case "assignee_id":
          return getUserDetails(valor)?.display_name ?? VAZIO;
        case "priority":
          // As prioridades já são traduzidas pelo produto sob a própria chave.
          return t(valor);
        default:
          return valor;
      }
    },
    [getStateById, getLabelById, getUserDetails, t]
  );

  return { campo, valorDoCampo, propriedade, propriedades };
};
