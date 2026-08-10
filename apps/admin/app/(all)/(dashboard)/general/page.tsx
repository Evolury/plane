/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// components
import { PageWrapper } from "@/components/common/page-wrapper";
// hooks
import { useInstance } from "@/hooks/store";
// local imports
import { GeneralConfigurationForm } from "./form";
// types
import type { Route } from "./+types/page";
import { translate, useTranslation } from "@plane/i18n";

function GeneralPage() {
  const { t } = useTranslation();
  const { instance, instanceAdmins } = useInstance();

  return (
    <PageWrapper
      header={{
        title: t("general_settings"),
        description:
          t("instance_admin.change_the_name_of_your_instance_and_instance_ad"),
      }}
    >
      {instance && instanceAdmins && <GeneralConfigurationForm instance={instance} instanceAdmins={instanceAdmins} />}
    </PageWrapper>
  );
}

export const meta: Route.MetaFunction = () => [{ title: translate("instance_admin.general_settings_god_mode") }];

export default observer(GeneralPage);
