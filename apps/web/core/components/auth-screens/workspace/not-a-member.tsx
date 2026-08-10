/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import Link from "next/link";
// ui
import { Button } from "@plane/propel/button";
import { useTranslation } from "@plane/i18n";
// layouts
import DefaultLayout from "@/layouts/default-layout";

export function NotAWorkspaceMember() {
  const { t } = useTranslation();
  return (
    <DefaultLayout>
      <div className="grid h-full place-items-center p-4">
        <div className="space-y-8 text-center">
          <div className="space-y-2">
            <h3 className="text-16 font-semibold">{t("ui.not_authorized")}</h3>
            <p className="mx-auto w-1/2 text-13 text-secondary">
              You{"'"}re not a member of this workspace. Please contact the workspace admin to get an invitation or
              check your pending invitations.
            </p>
          </div>
          <div className="flex items-center justify-center gap-2">
            <Link href="/invitations">
              <span>
                <Button variant="secondary">Check pending invites</Button>
              </span>
            </Link>
            <Link href="/create-workspace">
              <span>
                <Button variant="primary">{t("ui.create_new_workspace")}</Button>
              </span>
            </Link>
          </div>
        </div>
      </div>
    </DefaultLayout>
  );
}
