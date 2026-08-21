/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// QooWork: o sinal de carregamento é a marca da casa pulsando (ADR 0020).
//
// Eram dois GIFs do Plane — a marca de outra empresa aparecendo em toda
// transição de página, que é justamente quando a pessoa olha para a tela
// esperando. Aqui é o Q do wordmark, com uma pulsação de opacidade: sem
// gradiente, sem sombra e sem arquivo para carregar, como o manual pede.

import { QooWorkMark } from "@plane/propel/icons";

export function LogoSpinner() {
  return (
    <div className="flex items-center justify-center" role="status" aria-label="Carregando">
      <QooWorkMark size={44} className="text-on-inverse animate-pulse bg-inverse" />
    </div>
  );
}
