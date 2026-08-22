/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

type ComNome = { first_name?: string | null; last_name?: string | null } | null | undefined;

/**
 * O nome de uma pessoa, sem repetir o sobrenome.
 *
 * A tela pedia `first_name` e `last_name` em campos separados, e oito lugares
 * do produto juntavam os dois com um espaço no meio. Só que muita gente lê
 * "Nome" e digita o nome inteiro — e aí a saudação virava
 * **"Boas-vindas ao QooWork, Tássio Câmara Câmara"** (medido em 22/08/2026, com
 * `first_name="Tássio Câmara"` e `last_name="Câmara"` no banco).
 *
 * A regra é estreita de propósito: o sobrenome só é acrescentado quando o nome
 * ainda **não termina** nele. Nada de tentar adivinhar nome do meio, corrigir
 * ordem ou remover repetição no miolo — heurística esperta erra com nome de
 * gente, e errar o nome de alguém na tela de boas-vindas é pior que repetir.
 *
 * A comparação ignora caixa e espaço em excesso, e respeita limite de palavra:
 * `first_name="Ana Maria"` com `last_name="Maria"` devolve "Ana Maria", mas
 * `first_name="Anamaria"` com `last_name="Maria"` devolve "Anamaria Maria" —
 * ali são nomes diferentes, não repetição.
 */
export const nomeCompleto = (pessoa: ComNome): string => {
  const nome = (pessoa?.first_name ?? "").trim().replace(/\s+/g, " ");
  const sobrenome = (pessoa?.last_name ?? "").trim().replace(/\s+/g, " ");

  if (!sobrenome) return nome;
  if (!nome) return sobrenome;

  const fim = nome.toLocaleLowerCase();
  const cauda = sobrenome.toLocaleLowerCase();
  const jaTermina = fim === cauda || fim.endsWith(` ${cauda}`);

  return jaTermina ? nome : `${nome} ${sobrenome}`;
};
