/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: a frase que o servidor mandou, e não "algo deu errado".
//
// A API recusa com uma frase escrita para quem lê — "Preencha: Local." — e a
// tela trocava isso por um genérico. O motivo é que a recusa chega em formatos
// diferentes conforme quem recusou:
//
//   { "property_values": "Preencha: Local." }   nossos endpoints (ADR 0011)
//   { "error": "..." }                           o padrão da app API
//   { "detail": "..." }                          o padrão do DRF
//   { "name": ["Este campo é obrigatório."] }    validação de campo do DRF
//
// Cada lugar da tela adivinhava um desses e errava nos outros. Aqui a leitura é
// uma só, e o que ela não souber ler continua caindo no texto genérico de quem
// chamou — nunca em `[object Object]`, que é o que o `String(erro)` daria.

const CHAVES_PREFERIDAS = ["error", "detail", "message"];

const frase = (valor: unknown): string | undefined => {
  if (typeof valor === "string" && valor.trim()) return valor.trim();
  // Validação de campo do DRF vem como lista de frases.
  if (Array.isArray(valor)) {
    const partes = valor.map(frase).filter(Boolean);
    return partes.length ? partes.join(" ") : undefined;
  }
  return undefined;
};

/**
 * A frase legível dentro da recusa do servidor, ou `undefined`.
 *
 * Devolve `undefined` de propósito quando não há o que mostrar: assim quem
 * chama decide o texto genérico, com a palavra certa para aquela tela.
 */
export const mensagemDoErro = (erro: unknown): string | undefined => {
  if (!erro) return undefined;
  if (typeof erro === "string") return frase(erro);

  const corpo = ((erro as { response?: { data?: unknown } })?.response?.data ?? erro) as Record<string, unknown>;
  if (typeof corpo === "string") return frase(corpo);
  if (typeof corpo !== "object") return undefined;

  for (const chave of CHAVES_PREFERIDAS) {
    const encontrada = frase(corpo[chave]);
    if (encontrada) return encontrada;
  }

  // Sem chave conhecida: a recusa é por campo, e o nome do campo não interessa
  // a quem lê — a frase já diz o que fazer ("Preencha: Local.").
  for (const valor of Object.values(corpo)) {
    const encontrada = frase(valor);
    if (encontrada) return encontrada;
  }

  return undefined;
};
