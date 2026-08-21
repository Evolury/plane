/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { WEBSITE_URL } from "@plane/constants";

type TPoweredBy = {
  disabled?: boolean;
};

export function PoweredBy(props: TPoweredBy) {
  // props
  const { disabled = false } = props;

  if (disabled || !WEBSITE_URL) return null;

  return (
    <a
      href={WEBSITE_URL}
      className="fixed right-5 bottom-2.5 !z-[999999] flex items-center gap-1 rounded-sm border border-subtle bg-layer-3 px-2 py-1 shadow-raised-100"
      target="_blank"
      rel="noreferrer noopener"
    >
      {/* QooWork: era o logotipo do Plane com link para plane.so — a marca de
          outra empresa no rodapé do quadro público de quem usa o nosso produto.
          O selo agora é o wordmark, do jeito que o manual o define (ADR 0020). */}
      <div className="text-11">
        Feito com <span className="font-semibold tracking-[-0.02em]">QooWork</span>
      </div>
    </a>
  );
}
