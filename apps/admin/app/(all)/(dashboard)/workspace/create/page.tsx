/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// components
import { PageWrapper } from "@/components/common/page-wrapper";
// types
import type { Route } from "./+types/page";
// local
import { WorkspaceCreateForm } from "./form";
import { translate, useTranslation } from "@plane/i18n";

const WorkspaceCreatePage = observer(function WorkspaceCreatePage(_props: Route.ComponentProps) {
  const { t } = useTranslation();
  return (
    <PageWrapper
      header={{
        title: t("instance_admin.create_a_new_workspace_on_this_instance"),
        description: t("instance_admin.you_will_need_to_invite_users_from_workspace_set"),
      }}
    >
      <WorkspaceCreateForm />
    </PageWrapper>
  );
});

export const meta: Route.MetaFunction = () => [{ title: translate("instance_admin.create_workspace_god_mode") }];

export default WorkspaceCreatePage;
