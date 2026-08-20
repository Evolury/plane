/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { ICONE_PADRAO_DE_PROJETO } from "@plane/constants";
import type { IProject } from "@plane/types";

// Evolury: projeto novo nasce com a identidade da casa, não com um sorteio.
//
// Antes, cada projeto recebia uma FOTO sorteada entre 29 capas e um EMOJI
// sorteado entre dezenas. Dois projetos criados no mesmo minuto não tinham
// nada em comum, e a lista de projetos virava um mosaico sem sentido — o
// usuário não escolheu nada daquilo.
//
// Agora não há capa: a tela pinta o azul da marca onde ela falta. E o ícone é
// o mesmo para todos, no azul escuro do brandbook.
//
// Pôr uma imagem ou trocar o ícone continua possível, e passa a ser o que
// sempre deveria ter sido: uma decisão de quem cria.
export const getProjectFormValues = (): Partial<IProject> => ({
  cover_image_url: undefined,
  description: "",
  logo_props: {
    in_use: "icon",
    icon: { ...ICONE_PADRAO_DE_PROJETO },
  },
  identifier: "",
  name: "",
  network: 2,
  project_lead: null,
});
