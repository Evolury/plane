/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/**
 * Dinheiro e data na tela de faturamento (ADR 0021).
 *
 * O servidor manda centavos inteiros; quem divide por cem é a tela, uma vez só
 * e neste arquivo. Espalhar `/ 100` pelos componentes é como um deles acaba
 * dividindo duas vezes.
 */

export const emReais = (centavos: number | null | undefined): string =>
  ((centavos ?? 0) / 100).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });

export const emData = (iso: string | null | undefined): string => {
  if (!iso) return "—";
  const [ano, mes, dia] = iso.slice(0, 10).split("-");
  return `${dia}/${mes}/${ano}`;
};
