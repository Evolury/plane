/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: a ponte entre o SWR e o MobX para as propriedades (ADR 0011).
//
// As definições chegam por SWR, e quem desenha as colunas do quadro é
// `getGroupByColumns` — uma função pura, chamada de dentro de componentes
// `observer`, sem acesso a hooks. Sem esta ponte, a coluna só apareceria
// depois de um redesenho causado por outra coisa.
//
// É um mapa observável e nada mais: quem preenche é o hook que já busca as
// definições, e quem lê são os componentes que já são `observer`.

import { observable, runInAction } from "mobx";
import type { TIssueProperty } from "@plane/types";

const porProjeto = observable.map<string, TIssueProperty[]>();

export const guardarPropriedades = (projectId: string, propriedades: TIssueProperty[]) => {
  if (!projectId) return;
  const atuais = porProjeto.get(projectId);
  // Comparar antes de gravar evita um ciclo de redesenho por revalidação do
  // SWR — a resposta é nova, o conteúdo é o mesmo.
  if (atuais && atuais.length === propriedades.length && atuais.every((p, i) => p.id === propriedades[i]?.id)) {
    return;
  }
  runInAction(() => porProjeto.set(projectId, propriedades));
};

export const propriedadesDoProjeto = (projectId: string | undefined): TIssueProperty[] =>
  projectId ? (porProjeto.get(projectId) ?? []) : [];

/**
 * As que podem virar coluna do quadro: só seleção única (ADR 0011), e só a que
 * foi marcada para isso na definição.
 *
 * O servidor recusa as demais por conta própria — este filtro é só para o menu
 * não oferecer o que a consulta vai negar.
 */
export const propriedadesAgrupaveis = (projectId: string | undefined): TIssueProperty[] =>
  propriedadesDoProjeto(projectId).filter((p) => p.property_type === "select" && p.show_in_grouping);

/**
 * Acha a propriedade pelo id, com ou sem o projeto.
 *
 * Sem o projeto porque nem todo chamador o tem à mão: quem monta as colunas do
 * quadro recebe só o `group_by`. O id é UUID e único no banco, então procurar
 * em todos os projetos carregados não é ambíguo — é só menos direto.
 */
export const encontrarPropriedade = (propertyId: string, projectId?: string): TIssueProperty | undefined => {
  if (projectId) {
    const achada = porProjeto.get(projectId)?.find((p) => p.id === propertyId);
    if (achada) return achada;
  }
  for (const lista of porProjeto.values()) {
    const achada = lista.find((p) => p.id === propertyId);
    if (achada) return achada;
  }
  return undefined;
};

/** O prefixo que a API usa em `group_by` e nos filtros. */
export const chaveDePropriedade = (propertyId: string) => `property_${propertyId}` as const;

/** O id da propriedade quando a chave é de propriedade, senão `undefined`. */
export const idDaChave = (chave: string | null | undefined): string | undefined =>
  chave?.startsWith("property_") ? chave.slice("property_".length) : undefined;
