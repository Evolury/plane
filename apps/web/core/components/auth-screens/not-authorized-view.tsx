/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import React from "react";
import { observer } from "mobx-react";
// assets
import { cn } from "@plane/utils";
import { useTranslation } from "@plane/i18n";
import ProjectNotAuthorizedImg from "@/app/assets/auth/project-not-authorized.svg?url";
import Unauthorized from "@/app/assets/auth/unauthorized.svg?url";
import WorkspaceNotAuthorizedImg from "@/app/assets/auth/workspace-not-authorized.svg?url";
// layouts
import DefaultLayout from "@/layouts/default-layout";

type Props = {
  actionButton?: React.ReactNode;
  section?: "settings" | "general";
  isProjectView?: boolean;
  className?: string;
};

export const NotAuthorizedView = observer(function NotAuthorizedView(props: Props) {
  const { t } = useTranslation();
  const { actionButton, section = "general", isProjectView = false, className } = props;

  // assets
  const settingAsset = isProjectView ? ProjectNotAuthorizedImg : WorkspaceNotAuthorizedImg;
  const asset = section === "settings" ? settingAsset : Unauthorized;

  return (
    <DefaultLayout className={cn("bg-surface-1", className)}>
      <div className="flex h-full w-full flex-col items-center justify-center gap-y-5 text-center">
        <div className="h-44 w-72">
          {/* Evolury: texto alternativo descritivo e traduzido no lugar do identificador */}
          <img
            src={asset}
            className="h-[176px] w-[288px] object-contain"
            alt={t("aria_labels.errors.not_authorized_illustration")}
          />
        </div>
        <h1 className="text-18 font-medium text-primary">{t("ui.not_authorized_view_page")}</h1>
        {actionButton}
      </div>
    </DefaultLayout>
  );
});
