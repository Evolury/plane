/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// QooWork: a marca, em dois formatos (ADR 0020).
//
// **O wordmark é texto**, e não SVG traçado: o manual o define como composição
// tipográfica na própria família, com tracking negativo que cresce com o
// tamanho. Traçá-lo congelaria o desenho e obrigaria a manter arquivos claro e
// escuro sincronizados com uma fonte que já está carregada na página.
//
// A tabela de tracking é a do manual — 64px/−40, 32px/−30, 18px/−20, 12px/−5 —
// e mora aqui, num lugar só, para que nenhuma tela a redescubra por conta.

import * as React from "react";

/** O tracking que o manual manda para cada tamanho. */
const trackingPara = (tamanho: number) => {
  if (tamanho >= 48) return "-0.04em";
  if (tamanho >= 28) return "-0.03em";
  if (tamanho >= 16) return "-0.02em";
  return "-0.005em";
};

type TMarcaProps = {
  /** Altura da caixa tipográfica, em px. O mínimo do manual é 12. */
  size?: number;
  className?: string;
};

/**
 * O logotipo: a palavra, do jeito que o manual a define.
 *
 * A cor vem de quem monta (`text-*`), porque o manual pede uma cor por
 * assinatura — preto sobre claro, Cloud sobre escuro — e nunca duas.
 */
export function QooWorkLockup({ size = 20, className }: TMarcaProps) {
  return (
    <span
      className={className}
      style={{ fontSize: `${size}px`, fontWeight: 600, letterSpacing: trackingPara(size), lineHeight: 1 }}
    >
      QooWork
    </span>
  );
}

/**
 * A marca de aplicativo: o Q recortado do wordmark, num quadrado arredondado.
 *
 * As proporções são as da prancha do manual: raio 19/84 do lado e letra a
 * 50/84. É o que vira favicon, ícone de atalho e — pulsando — o sinal de
 * carregamento.
 */
export function QooWorkMark({ size = 40, className }: TMarcaProps) {
  return (
    <span
      className={className}
      style={{
        width: `${size}px`,
        height: `${size}px`,
        borderRadius: `${Math.round(size * 0.226)}px`,
        display: "grid",
        placeItems: "center",
        fontSize: `${Math.round(size * 0.595)}px`,
        fontWeight: 600,
        letterSpacing: "-0.04em",
        lineHeight: 1,
      }}
    >
      Q
    </span>
  );
}
