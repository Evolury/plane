/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// helpers
import { EAuthModes } from "@/types/auth";
import { translate, useTranslation } from "@plane/i18n";

type TAuthHeader = {
  authMode: EAuthModes;
};

type TAuthHeaderContent = {
  header: string;
  subHeader: string;
};

type TAuthHeaderDetails = {
  [mode in EAuthModes]: TAuthHeaderContent;
};

const Titles: TAuthHeaderDetails = {
  [EAuthModes.SIGN_IN]: {
    header: translate("ui.sign_in_to_upvote_or_comment"),
    subHeader: translate("ui.contribute_in_nudging_the_features_you_want_to_g"),
  },
  [EAuthModes.SIGN_UP]: {
    header: translate("ui.view_comment_and_do_more"),
    subHeader: translate("ui.sign_up_or_log_in_to_work_with_plane_work_items"),
  },
};

export function AuthHeader(props: TAuthHeader) {
  const { t } = useTranslation();
  const { authMode } = props;

  const getHeaderSubHeader = (mode: EAuthModes | null): TAuthHeaderContent => {
    if (mode) {
      return Titles[mode];
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
