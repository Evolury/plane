/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: configurações de tarefas recorrentes (ADR 0010).

import { observer } from "mobx-react";
import { EUserPermissions, EUserPermissionsLevel } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { NotAuthorizedView } from "@/components/auth-screens/not-authorized-view";
import { PageHead } from "@/components/core/page-title";
import { RecurringWorkItemsRoot } from "@/components/recurring-work-items/root";
import { SettingsContentWrapper } from "@/components/settings/content-wrapper";
import { SettingsHeading } from "@/components/settings/heading";
import { useProject } from "@/hooks/store/use-project";
import { useUserPermissions } from "@/hooks/store/user";
import type { Route } from "./+types/page";
import { RecurringProjectSettingsHeader } from "./header";

function RecurringSettingsPage({ params }: Route.ComponentProps) {
  const { workspaceSlug, projectId } = params;
  const { t } = useTranslation();
  const { workspaceUserInfo, allowPermissions } = useUserPermissions();
  const { currentProjectDetails } = useProject();

  const podeAdministrar = allowPermissions([EUserPermissions.ADMIN], EUserPermissionsLevel.PROJECT);

  if (workspaceUserInfo && !podeAdministrar) {
    return <NotAuthorizedView section="settings" isProjectView className="h-auto" />;
  }

  return (
    <SettingsContentWrapper header={<RecurringProjectSettingsHeader />} hugging>
      <PageHead
        title={
          currentProjectDetails?.name
            ? `${currentProjectDetails.name} - ${t("recurring_work_items.settings.heading")}`
            : undefined
        }
      />
      <section className="w-full">
        <SettingsHeading
          title={t("recurring_work_items.settings.heading")}
          description={t("recurring_work_items.settings.description")}
        />
        <RecurringWorkItemsRoot workspaceSlug={workspaceSlug} projectId={projectId} />
      </section>
    </SettingsContentWrapper>
  );
}

export default observer(RecurringSettingsPage);
