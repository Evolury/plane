/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { createContext, useContext, useMemo } from "react";

export type TEditorTranslate = (key: string, fallback: string) => string;

/**
 * Tradução dentro do @plane/editor.
 *
 * O pacote NÃO depende de @plane/i18n — nenhum pacote compartilhado depende, e
 * isso é deliberado no upstream. Quem sabe traduzir é o app, então ele injeta a
 * função via prop `translate` do editor e o contexto a distribui para os
 * componentes internos, evitando enfiar a mesma prop em dezenas de níveis.
 *
 * Toda chamada exige um `fallback` em inglês: sem provider — ou num app que não
 * passe `translate` — o editor continua exibindo o texto original, em vez de
 * vazar a chave crua na tela.
 */
const defaultTranslate: TEditorTranslate = (_key, fallback) => fallback;

const EditorTranslationContext = createContext<TEditorTranslate>(defaultTranslate);

type Props = {
  children: React.ReactNode;
  translate?: (key: string) => string;
};

export function EditorTranslationProvider({ children, translate }: Props) {
  const value = useMemo<TEditorTranslate>(() => {
    if (!translate) return defaultTranslate;
    return (key, fallback) => {
      const translated = translate(key);
      // O t() do app devolve a própria chave quando ela não existe; nesse caso
      // o texto em inglês é melhor do que mostrar "editor.slash.text".
      return !translated || translated === key ? fallback : translated;
    };
  }, [translate]);

  return <EditorTranslationContext.Provider value={value}>{children}</EditorTranslationContext.Provider>;
}

export const useEditorTranslation = (): TEditorTranslate => useContext(EditorTranslationContext);
