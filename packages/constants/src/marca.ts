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
