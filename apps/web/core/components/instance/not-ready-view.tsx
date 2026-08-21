/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import Link from "next/link";
import { GOD_MODE_URL } from "@plane/constants";
// assets
import GradientLogo from "@/app/assets/auth/gradient-logo.webp?url";
import GradientBgLogo from "@/app/assets/auth/gradient-bg-logo.webp?url";
import DefaultLayout from "@/layouts/default-layout";
import { QooWorkLockup } from "@plane/propel/icons";
import { Button } from "@plane/propel/button";
import { useTranslation } from "@plane/i18n";

export function InstanceNotReady() {
  const { t } = useTranslation();
  return (
    <DefaultLayout>
      <div className="relative z-10 flex h-screen w-screen overflow-hidden">
        {/* Background decorations */}
        <img
          src={GradientBgLogo}
          className="pointer-events-none absolute -top-24 -left-32 h-56 w-96 opacity-15"
          alt=""
          aria-hidden="true"
        />
        <img
          src={GradientBgLogo}
          className="pointer-events-none absolute -right-20 -bottom-16 h-56 w-96 opacity-15"
          alt=""
          aria-hidden="true"
        />
        {/* Main content */}
        <div className="flex h-full w-full flex-col items-center px-8 pt-6 pb-10">
          <div className="sticky top-0 flex w-full shrink-0 items-center justify-between gap-6">
            <QooWorkLockup size={20} className="text-primary" />
          </div>
          <div className="flex h-full w-full flex-col items-center justify-center gap-7">
            <div className="flex flex-col items-center gap-11">
              <img src={GradientLogo} className="h-24 w-40 object-contain" alt="QooWork" />
              <div className="flex max-w-124 flex-col items-center gap-3">
                <h1 className="text-h2-semibold text-primary">{t("ui.welcome_to_plane")}</h1>
                <p className="text-center text-body-md-regular text-secondary">{t("ui.setup_instance_description")}</p>
              </div>
            </div>
            <a href={GOD_MODE_URL} className="w-72">
              <Button variant="primary" className="w-full" size="xl">
                {t("common.get_started")}
              </Button>
            </a>
          </div>
        </div>
      </div>
    </DefaultLayout>
  );
}
