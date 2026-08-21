/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";

const QOOWORK_URL = "https://qoowork.com.br";

/**
 * A marca no rodapé da barra lateral, no lugar do badge de edição do upstream.
 *
 * **O logotipo é texto, e não imagem** — é o que o manual define: um wordmark
 * puro, composto na própria família da marca, com tracking negativo que cresce
 * com o tamanho. No tamanho do rodapé são 18px em peso 600 com −0,02em, os
 * números da prancha de aplicação no produto.
 *
 * Exportar isso como SVG traçado congelaria o desenho e obrigaria a manter dois
 * arquivos (claro e escuro) sincronizados com uma fonte que já está carregada
 * na página. A cor vem do tema: preto sobre fundo claro, Cloud sobre escuro.
 *
 * Fica num componente próprio para que o `edition-badge.tsx` original siga
 * intocado e não conflite ao rebasear no upstream.
 */
export const QooWorkBrandLink = observer(function QooWorkBrandLink() {
  return (
    <a
      href={QOOWORK_URL}
      target="_blank"
      rel="noopener noreferrer"
      className="flex items-center rounded-sm text-primary opacity-90 transition-opacity hover:opacity-100"
      aria-label="QooWork"
    >
      <span className="text-18 leading-none font-semibold tracking-[-0.02em]">QooWork</span>
    </a>
  );
});
