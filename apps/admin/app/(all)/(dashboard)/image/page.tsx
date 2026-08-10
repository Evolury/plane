/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import useSWR from "swr";
import { Loader } from "@plane/ui";
// components
import { PageWrapper } from "@/components/common/page-wrapper";
// hooks
import { useInstance } from "@/hooks/store";
// types
import type { Route } from "./+types/page";
// local
import { InstanceImageConfigForm } from "./form";
import { translate, useTranslation } from "@plane/i18n";

const InstanceImagePage = observer(function InstanceImagePage(_props: Route.ComponentProps) {
  const { t } = useTranslation();
  // store
  const { formattedConfig, fetchInstanceConfigurations } = useInstance();

  useSWR("INSTANCE_CONFIGURATIONS", () => fetchInstanceConfigurations());

  return (
    <PageWrapper
      header={{
        title: "Third-party image libraries",
        description: t("instance_admin.let_your_users_search_and_choose_images_from_thi"),
      }}
    >
      {formattedConfig ? (
        <InstanceImageConfigForm config={formattedConfig} />
      ) : (
        <Loader className="space-y-8">
          <Loader.Item height="50px" width="50%" />
          <Loader.Item height="50px" width="20%" />
        </Loader>
      )}
    </PageWrapper>
  );
});

export const meta: Route.MetaFunction = () => [{ title: translate("instance_admin.images_settings_god_mode") }];

export default InstanceImagePage;
