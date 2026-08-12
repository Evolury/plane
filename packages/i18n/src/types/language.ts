/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: produto pt-BR único (ADR 0004). A união tinha os 19 idiomas do
// upstream; reduzi-la faz o compilador recusar qualquer outro valor, que é a
// trava mais barata que existe para isso. O locale `en` continua no disco
// como fonte das chaves para as ferramentas do pacote, mas não é um idioma
// selecionável nem um valor válido em runtime.
export type TLanguage = "pt-BR";

export interface ILanguageOption {
  label: string;
  value: TLanguage;
}
