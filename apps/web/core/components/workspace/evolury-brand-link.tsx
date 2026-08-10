/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { useTheme } from "next-themes";
// assets
import evoluryDark from "@/app/assets/brand/evolury-dark.svg?url";
import evoluryLight from "@/app/assets/brand/evolury-light.svg?url";

const EVOLURY_URL = "https://evolury.com.br";

/**
 * Marca da Evolury no rodapé da barra lateral, no lugar do badge de edição do
 * upstream. Fica num componente próprio para que o `edition-badge.tsx` original
 * siga intocado e não conflite ao rebasear no upstream.
 */
export const EvoluryBrandLink = observer(function EvoluryBrandLink() {
  const { resolvedTheme } = useTheme();
  // A logo padrão é azul-escura e desapareceria sobre o fundo escuro do rodapé,
  // então o tema escuro usa a variante de marca branca.
  const logo = resolvedTheme === "dark" ? evoluryDark : evoluryLight;

  return (
    <a
      href={EVOLURY_URL}
      target="_blank"
      rel="noopener noreferrer"
      className="flex items-center rounded-sm opacity-90 transition-opacity hover:opacity-100"
      aria-label="Evolury"
    >
      <img src={logo} alt="Evolury" className="h-5 w-auto" />
    </a>
  );
});
