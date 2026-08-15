/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: carrega as definições de propriedade da rota (ADR 0011).
//
// Não desenha nada. Existe porque quem monta as colunas do quadro é uma função
// pura, que lê a ponte para o MobX — e a ponte só era preenchida por dentro do
// cartão. Agrupar por propriedade caía num impasse: sem coluna não há cartão,
// e sem cartão a ponte ficava vazia.
//
// Fica no layout da rota, que monta antes de qualquer layout de tarefa.

import { observer } from "mobx-react";
import { useParams } from "next/navigation";
import { usePropriedadesDoProjeto } from "./store";

export const IssuePropertiesPrefetch = observer(function IssuePropertiesPrefetch() {
  const { workspaceSlug, projectId } = useParams();
  usePropriedadesDoProjeto(workspaceSlug?.toString() ?? "", projectId?.toString() ?? "");
  return null;
});
