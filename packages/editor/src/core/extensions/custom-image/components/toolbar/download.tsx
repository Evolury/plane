/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { Download } from "lucide-react";
// plane imports
// Evolury: a barra da imagem nasce fora do provider de tradução do editor (ADR 0008)
import { translate } from "@plane/i18n";
import { Tooltip } from "@plane/propel/tooltip";

type Props = {
  src: string;
};

export function ImageDownloadAction(props: Props) {
  const { src } = props;

  return (
    <Tooltip tooltipContent={translate("editor.download")}>
      <button
        type="button"
        onClick={() => window.open(src, "_blank")}
        className="grid h-full flex-shrink-0 place-items-center text-white/60 transition-colors hover:text-white"
        aria-label={translate("editor.download_image")}
      >
        <Download className="size-3" />
      </button>
    </Tooltip>
  );
}
