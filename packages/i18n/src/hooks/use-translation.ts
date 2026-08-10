/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useCallback } from "react";
import { useTranslation as useI18nextTranslation } from "react-i18next";
import { SUPPORTED_LANGUAGES, LANGUAGE_STORAGE_KEY } from "../constants/language";
// Crash guard compartilhado com `translate`, para as duas vias de tradução se
// comportarem igual diante de chave inexistente ou de nó de namespace.
import { coerceToString } from "../core/translate";
import type { TLanguage, ILanguageOption } from "../types";

export type TTranslationStore = {
  t: (key: string, params?: Record<string, unknown>) => string;
  currentLocale: TLanguage;
  changeLanguage: (lng: TLanguage) => void;
  languages: ILanguageOption[];
};

export function useTranslation(): TTranslationStore {
  // No namespace arg — fallbackNS in the i18next config ensures all namespaces
  // are searched for any key. Passing NAMESPACES here would trigger concurrent
  // async loads per component, causing a re-render cascade.
  const { t, i18n } = useI18nextTranslation();

  // Memoized so the returned `t` is referentially stable across renders. Without
  // this it was a fresh arrow function every render, which made every
  // useCallback/useMemo/useEffect that translates report `t` as a missing
  // dependency — and adding it to the deps would then re-run them on every
  // render. i18next's own `t` is stable and only changes on language change, so
  // depending on it keeps translations correct when the user switches language.
  const translate = useCallback(
    (key: string, params?: Record<string, unknown>) =>
      coerceToString(key, params === undefined ? t(key) : t(key, params)),
    [t]
  );

  const changeLanguage = useCallback(
    (lng: TLanguage) => {
      void (async () => {
        try {
          await i18n.changeLanguage(lng);
          if (typeof window === "undefined") return;
          localStorage.setItem(LANGUAGE_STORAGE_KEY, lng);
          document.documentElement.lang = lng;
        } catch (err) {
          console.error("Failed to change language:", err);
        }
      })();
    },
    [i18n]
  );

  return {
    t: translate,
    currentLocale: i18n.language as TLanguage,
    changeLanguage,
    languages: SUPPORTED_LANGUAGES,
  };
}
