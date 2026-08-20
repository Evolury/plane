/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: as cores da marca, como o brandbook 1.02 as define (página 17).
//
// Um lugar só. Antes, o azul da identidade não existia no código: capa de
// projeto era uma foto sorteada entre 29, o ícone era um emoji sorteado entre
// dezenas, e o avatar caía num verde-azulado cravado (#028375) que não vem de
// lugar nenhum. Cada criação inventava uma aparência, e o resultado era ruído.
//
// Estas constantes são para o que a PLATAFORMA desenha por padrão. O tema tem
// os tokens dele (`--brand-*`), que hoje partem de um azul diferente (#006399)
// — a divergência entre o azul do produto e o azul da marca está registrada e
// é decisão à parte, maior que esta.

/** #0C91EB — o azul da marca. Fundo de capa e de avatar sem imagem. */
export const NANO_BLUE = "#0C91EB";

/** #013F6E — o azul escuro. Contrasta sobre a capa e sobre fundo claro. */
export const DEEP_BLUE = "#013F6E";

/** #F6FAFF — o branco azulado do brandbook. */
export const WHITE_BLUE = "#F6FAFF";

/**
 * O ícone que um projeto novo recebe.
 *
 * `view_kanban` porque é o que um projeto É aqui — um quadro de trabalho. Pasta
 * remete a arquivo guardado, e emoji sorteado remete a nada.
 *
 * A cor é DeepBlue, e não NanoBlue: o ícone aparece SOBRE a capa (num chip
 * translúcido) e também na barra lateral clara. NanoBlue sobre NanoBlue
 * desapareceria. É o mesmo par que o logotipo usa.
 */
export const ICONE_PADRAO_DE_PROJETO = { name: "view_kanban", color: DEEP_BLUE } as const;

/**
 * As cores que a capa pode ter, quando quem usa escolhe uma cor em vez de uma
 * imagem.
 *
 * Todas foram medidas contra texto branco: as doze passam de 5:1, exceto as
 * duas da marca, que entram por serem a identidade — NanoBlue fica em 3,35:1, e
 * é por isso que o nome sobre a capa continua com o véu escuro, em vez de
 * depender da cor crua.
 *
 * Só o tom, e nunca o nome, mora aqui: o rótulo vem da chave (ADR 0008).
 */
export type TCorDeCapa = { hex: string; i18n_nome: string };

export const CORES_DE_CAPA: readonly TCorDeCapa[] = [
  { hex: NANO_BLUE, i18n_nome: "colors.nano_blue" },
  { hex: DEEP_BLUE, i18n_nome: "colors.deep_blue" },
  { hex: "#1D4ED8", i18n_nome: "colors.blue" },
  { hex: "#4338CA", i18n_nome: "colors.indigo" },
  { hex: "#6D28D9", i18n_nome: "colors.purple" },
  { hex: "#BE185D", i18n_nome: "colors.pink" },
  { hex: "#B91C1C", i18n_nome: "colors.red" },
  { hex: "#C2410C", i18n_nome: "colors.orange" },
  { hex: "#B45309", i18n_nome: "colors.amber" },
  { hex: "#166534", i18n_nome: "colors.green" },
  { hex: "#0F5257", i18n_nome: "colors.teal" },
  { hex: "#1F2937", i18n_nome: "colors.graphite" },
] as const;

/**
 * `#RRGGBB`, e nada mais.
 *
 * A cor termina desenhada num `style`, e o valor vem do banco. Aceitar
 * "qualquer coisa que comece com #" deixaria passar `#fff);background-image:…`
 * — por isso a forma é exata, e a mesma regra existe no servidor
 * (`plane/utils/cores.py`), que é quem de fato recusa a gravação.
 */
export const FORMATO_DE_COR_DE_CAPA = /^#[0-9a-fA-F]{6}$/;

/** Distingue capa-cor de capa-imagem: os dois viajam no mesmo campo do formulário. */
export const ehCorDeCapa = (valor: string | null | undefined): boolean => !!valor && FORMATO_DE_COR_DE_CAPA.test(valor);
