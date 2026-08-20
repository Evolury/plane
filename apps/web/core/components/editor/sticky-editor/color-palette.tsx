/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TSticky } from "@plane/types";
import { useTranslation } from "@plane/i18n";

// Evolury: o nome da cor virou chave, e passou a ser DESENHADO. Ele existia
// como texto em inglês e nunca chegava à tela: os quadradinhos eram botões sem
// rótulo nenhum — invisíveis para leitor de tela, e um "escolha a cor" que só
// funciona para quem enxerga a cor.
export const STICKY_COLORS_LIST: {
  key: string;
  i18n_label: string;
  backgroundColor: string;
}[] = [
  {
    key: "gray",
    i18n_label: "colors.gray",
    backgroundColor: "var(--editor-colors-gray-background)",
  },
  {
    key: "peach",
    i18n_label: "colors.peach",
    backgroundColor: "var(--editor-colors-peach-background)",
  },
  {
    key: "pink",
    i18n_label: "colors.pink",
    backgroundColor: "var(--editor-colors-pink-background)",
  },
  {
    key: "orange",
    i18n_label: "colors.orange",
    backgroundColor: "var(--editor-colors-orange-background)",
  },
  {
    key: "green",
    i18n_label: "colors.green",
    backgroundColor: "var(--editor-colors-green-background)",
  },
  {
    key: "light-blue",
    i18n_label: "colors.light_blue",
    backgroundColor: "var(--editor-colors-light-blue-background)",
  },
  {
    key: "dark-blue",
    i18n_label: "colors.dark_blue",
    backgroundColor: "var(--editor-colors-dark-blue-background)",
  },
  {
    key: "purple",
    i18n_label: "colors.purple",
    backgroundColor: "var(--editor-colors-purple-background)",
  },
];

type TProps = {
  handleUpdate: (data: Partial<TSticky>) => Promise<void>;
};

export function ColorPalette(props: TProps) {
  const { handleUpdate } = props;
  const { t } = useTranslation();
  return (
    <div className="shadow absolute bottom-5 left-0 z-10 mb-2 w-56 rounded-md bg-surface-1 p-2">
      <div className="mb-2 text-13 font-semibold text-placeholder">{t("editor.background_colors")}</div>
      <div className="flex flex-wrap gap-2">
        {STICKY_COLORS_LIST.map((color) => (
          <button
            key={color.key}
            type="button"
            onClick={() => {
              handleUpdate({
                background_color: color.key,
              });
            }}
            title={t(color.i18n_label)}
            aria-label={t(color.i18n_label)}
            className="h-6 w-6 rounded-md transition-all hover:ring-2 hover:ring-accent-strong focus:ring-2 focus:ring-accent-strong focus:outline-none"
            style={{
              backgroundColor: color.backgroundColor,
            }}
          />
        ))}
      </div>
    </div>
  );
}
