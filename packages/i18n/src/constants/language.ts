/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TLanguage, ILanguageOption } from "../types";

// Evolury: pt-BR em vez de "en" (upstream). Define o idioma antes do login e
// enquanto o perfil não foi carregado. Pareado com o default de
// Profile.language no backend — mudar só um faz a UI trocar de idioma no login.
export const FALLBACK_LANGUAGE: TLanguage = "pt-BR";

// Evolury: idioma único (ADR 0004). Esta lista alimenta ao mesmo tempo o
// `supportedLngs` do i18next e qualquer seletor de idioma — com uma entrada
// só, o i18next recusa outros valores e não há o que selecionar.
export const SUPPORTED_LANGUAGES: ILanguageOption[] = [{ label: "Português (Brasil)", value: "pt-BR" }];

export const LANGUAGE_STORAGE_KEY = "userLanguage";
