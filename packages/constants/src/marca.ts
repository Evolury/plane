/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// QooWork: as cores da marca, como o manual as define (ADR 0020).
//
// Um lugar só, e substitui o azul da Evolury que vigorou até a 1.34: a
// plataforma passou a se chamar QooWork, com identidade própria.
//
// **A regra que manda é de proporção, não de matiz**: "preto e branco primeiro;
// Iris depois. A cor de assinatura ocupa no máximo 3% da superfície — sinal de
// ação e importância, nunca preenchimento." É por isso que a capa de um projeto
// novo é PRETA e não Iris: capa é superfície grande, e pintá-la com a cor de
// assinatura seria justamente o preenchimento que o manual proíbe.
//
// O Iris mora onde a ação mora — botão primário, estado ativo, progresso —, e
// isso não é decidido aqui: é a rampa `--brand-*` do tema, agora gerada em
// torno dele.

/** #18181B — base, texto e fundos profundos. */
export const QOO_BLACK = "#18181B";

/** #27272A — superfícies e divisores no escuro. */
export const GRAPHITE = "#27272A";

/** #71717A — texto secundário e apoio. Também o estado "bloqueado". */
export const GRAY = "#71717A";

/** #E4E4E7 — bordas e estados inativos. */
export const MIST = "#E4E4E7";

/** #FAFAFA — fundo claro e espaço negativo. */
export const CLOUD = "#FAFAFA";

/** #625BF6 — a assinatura. Ação, prioridade, progresso; no máximo 3% da tela. */
export const QOO_IRIS = "#625BF6";

/**
 * As cores de estado do manual. Sinal, nunca decoração: aparecem em ponto,
 * etiqueta ou barra de progresso — jamais como fundo de um bloco inteiro.
 */
export const CORES_DE_ESTADO = {
  em_fluxo: QOO_IRIS,
  concluido: "#0EA06E",
  atencao: "#D98A16",
  erro: "#DC4438",
  bloqueado: GRAY,
} as const;

/** A capa de quem ainda não escolheu uma. Preto, e não Iris — ver a regra dos 3%. */
export const COR_DE_CAPA_PADRAO = QOO_BLACK;

/**
 * O fundo do avatar de quem não tem foto, e a cor da inicial em cima dele.
 *
 * Mist com a inicial preta é o que o próprio manual desenha no produto (1d), e
 * é o que sobrevive à regra dos 3%: uma tela de equipe com trinta pessoas seria
 * trinta manchas Iris.
 */
export const AVATAR_SEM_FOTO = { fundo: MIST, texto: QOO_BLACK } as const;

/**
 * O ícone que um projeto novo recebe.
 *
 * `view_kanban` porque é o que um projeto É aqui — um quadro de trabalho.
 *
 * Preto, e não Iris: o ícone aparece numa placa clara sobre a capa, e medido ali
 * o Iris dá 2,98:1 contra os 10,9:1 do preto. Abaixo de 3:1 um ícone deixa de
 * ser legível para quem enxerga pouco.
 */
export const ICONE_PADRAO_DE_PROJETO = { name: "view_kanban", color: QOO_BLACK } as const;

/**
 * As cores que a capa pode receber quando quem usa escolhe uma.
 *
 * Todas saem do manual — os cinco neutros, a assinatura e as quatro de estado.
 * Nenhuma cor de fora: uma capa lilás-neon num produto que se define por "preto
 * e branco primeiro" é a primeira rachadura da identidade.
 *
 * Só o tom mora aqui, nunca o nome: o rótulo vem da chave (ADR 0008).
 */
export type TCorDeCapa = { hex: string; i18n_nome: string };

export const CORES_DE_CAPA: readonly TCorDeCapa[] = [
  { hex: QOO_BLACK, i18n_nome: "colors.qoo_black" },
  { hex: GRAPHITE, i18n_nome: "colors.graphite" },
  { hex: GRAY, i18n_nome: "colors.gray" },
  { hex: MIST, i18n_nome: "colors.mist" },
  { hex: CLOUD, i18n_nome: "colors.cloud" },
  { hex: QOO_IRIS, i18n_nome: "colors.qoo_iris" },
  { hex: CORES_DE_ESTADO.concluido, i18n_nome: "colors.green" },
  { hex: CORES_DE_ESTADO.atencao, i18n_nome: "colors.amber" },
  { hex: CORES_DE_ESTADO.erro, i18n_nome: "colors.red" },
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
