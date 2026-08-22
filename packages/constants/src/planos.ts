/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/**
 * O catálogo de planos, do lado do cliente — espelho de
 * `apps/api/plane/utils/planos.py` (ADR 0021).
 *
 * Existe porque a tela precisa dizer **qual plano** libera o que ela está
 * escondendo, e perguntar isso ao servidor a cada rótulo seria uma chamada por
 * cadeado. O servidor continua sendo quem recusa; este arquivo só sabe vender.
 *
 * Dois catálogos são dois lugares para o preço divergir, e preço divergente é
 * o pior tipo de bug de cobrança — o cliente vê um número e é cobrado outro.
 * Por isso existe `apps/web/tests/planos-espelho.test.ts`, que lê o arquivo
 * Python e compara número a número.
 *
 * Valores em centavos, como no servidor.
 */

export const CICLO_MENSAL = "mensal";
export const CICLO_ANUAL = "anual";
export const MESES_DO_CICLO_ANUAL = 10;

export const RECURSO_ANALYTICS = "analytics";
export const RECURSO_API_PUBLICA = "api_publica";
export const RECURSO_WEBHOOKS = "webhooks";

export const LIMITE_PROPRIEDADES = "propriedades_por_projeto";
export const LIMITE_AUTOMACOES = "automacoes_ativas";

export type TPlano = {
  chave: string;
  nome: string;
  assentos: number;
  mensal: number;
  adicionalMensal: number;
  convidadosPorAssento: number;
  recursos: Record<string, boolean>;
  limites: Record<string, number | null>;
};

export const ESSENCIAL = "essencial";
export const PROFISSIONAL = "profissional";
export const AVANCADO = "avancado";

export const ORDEM_DOS_PLANOS = [ESSENCIAL, PROFISSIONAL, AVANCADO] as const;

export const PLANOS: Record<string, TPlano> = {
  [ESSENCIAL]: {
    chave: ESSENCIAL,
    nome: "Essencial",
    assentos: 3,
    mensal: 29000,
    adicionalMensal: 9000,
    convidadosPorAssento: 0,
    recursos: { [RECURSO_ANALYTICS]: false, [RECURSO_API_PUBLICA]: false, [RECURSO_WEBHOOKS]: false },
    limites: { [LIMITE_PROPRIEDADES]: 5, [LIMITE_AUTOMACOES]: 2 },
  },
  [PROFISSIONAL]: {
    chave: PROFISSIONAL,
    nome: "Profissional",
    assentos: 10,
    mensal: 69000,
    adicionalMensal: 6500,
    convidadosPorAssento: 2,
    recursos: { [RECURSO_ANALYTICS]: true, [RECURSO_API_PUBLICA]: true, [RECURSO_WEBHOOKS]: true },
    limites: { [LIMITE_PROPRIEDADES]: 30, [LIMITE_AUTOMACOES]: null },
  },
  [AVANCADO]: {
    chave: AVANCADO,
    nome: "Avançado",
    assentos: 30,
    mensal: 159000,
    adicionalMensal: 4900,
    convidadosPorAssento: 5,
    recursos: { [RECURSO_ANALYTICS]: true, [RECURSO_API_PUBLICA]: true, [RECURSO_WEBHOOKS]: true },
    limites: { [LIMITE_PROPRIEDADES]: 30, [LIMITE_AUTOMACOES]: null },
  },
};

/** O ciclo anual custa dez mensalidades: dois meses grátis. */
export const precoAnual = (chave: string): number => (PLANOS[chave]?.mensal ?? 0) * MESES_DO_CICLO_ANUAL;

/** Quais planos liberam o recurso, do mais barato para o mais caro. */
export const planosCom = (recurso: string): TPlano[] =>
  ORDEM_DOS_PLANOS.map((chave) => PLANOS[chave]).filter((plano) => plano.recursos[recurso]);

/**
 * O plano mais barato que libera o recurso — é o nome que o rótulo mostra.
 *
 * Apontar o mais caro seria vender errado; não apontar nenhum transformaria a
 * trava em parede.
 */
export const planoQueLibera = (recurso: string): TPlano | undefined => planosCom(recurso)[0];
