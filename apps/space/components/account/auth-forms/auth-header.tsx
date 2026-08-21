/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// helpers
import { EAuthModes } from "@/types/auth";
import { useTranslation } from "@plane/i18n";

type TAuthHeader = {
  authMode: EAuthModes;
};

type TAuthHeaderContent = {
  header: string;
  subHeader: string;
};

// QooWork: chaves, e não textos. Montado com `translate()` no corpo do módulo,
// este objeto era avaliado antes de o i18n carregar e congelava a própria
// chave — a tela de entrada exibia "ui.sign_in_to_upvote_or_comment". A
// tradução acontece na renderização, com o `t` do componente.
const CHAVES = {
  [EAuthModes.SIGN_IN]: {
    header: "ui.sign_in_to_upvote_or_comment",
    subHeader: "ui.contribute_in_nudging_the_features_you_want_to_g",
  },
  [EAuthModes.SIGN_UP]: {
    header: "ui.view_comment_and_do_more",
    subHeader: "ui.sign_up_or_log_in_to_work_with_plane_work_items",
  },
} as const;

export function AuthHeader(props: TAuthHeader) {
  const { t } = useTranslation();
  const { authMode } = props;

  const getHeaderSubHeader = (mode: EAuthModes | null): TAuthHeaderContent => {
    if (mode) {
      return { header: t(CHAVES[mode].header), subHeader: t(CHAVES[mode].subHeader) };
    }

    return {
      header: t("ui.comment_or_react_to_work_items"),
      subHeader: t("ui.use_plane_to_add_your_valuable_inputs_to_feature"),
    };
  };

  const { header, subHeader } = getHeaderSubHeader(authMode);

  return (
    <>
      <div className="flex flex-col gap-1">
        <span className="text-20 leading-7 font-semibold text-primary">{header}</span>
        <span className="text-20 leading-7 font-semibold text-placeholder">{subHeader}</span>
      </div>
    </>
  );
}
