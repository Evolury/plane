/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { ListTodo } from "lucide-react";
import { useParams } from "next/navigation";
// plane imports
import { useTranslation } from "@plane/i18n";
import { PageIcon } from "@plane/propel/icons";
import type { ICustomSearchSelectOption } from "@plane/types";
import { Breadcrumbs, BreadcrumbNavigationSearchDropdown, Header } from "@plane/ui";
import { getPageName } from "@plane/utils";
// components
import { BreadcrumbLink } from "@/components/common/breadcrumb-link";
import { SwitcherIcon, SwitcherLabel } from "@/components/common/switcher-label";
import { PageHeaderActions } from "@/components/pages/header/actions";
import { PageSyncingBadge } from "@/components/pages/header/syncing-badge";
// hooks
import { EPageStoreType, usePage, usePageStore } from "@/hooks/store";
import { useAppRouter } from "@/hooks/use-app-router";

const storeType = EPageStoreType.PERSONAL;

export const PaginaPessoalHeader = observer(function PaginaPessoalHeader() {
  const { t } = useTranslation();
  const router = useAppRouter();
  const { workspaceSlug, pageId } = useParams();
  // store
  const { getPageById, getCurrentProjectPageIdsByTab } = usePageStore(storeType);
  const page = usePage({ pageId: pageId?.toString() ?? "", storeType });
  // derived
  const opcoes = (getCurrentProjectPageIdsByTab("private") ?? [])
    .map((id) => {
      const outra = id === pageId ? page : getPageById(id);
      if (!outra) return;
      return {
        value: outra.id,
        query: outra.name,
        content: <SwitcherLabel logo_props={outra.logo_props} name={getPageName(outra.name)} LabelIcon={PageIcon} />,
      };
    })
    .filter((opcao) => opcao !== undefined) as ICustomSearchSelectOption[];

  if (!page) return null;

  return (
    <Header>
      <Header.LeftItem>
        <Breadcrumbs>
          <Breadcrumbs.Item
            component={
              <BreadcrumbLink
                label={t("sidebar.my_tasks")}
                href={`/${workspaceSlug}/my-tasks`}
                icon={<ListTodo className="size-4 text-secondary" />}
              />
            }
          />
          <Breadcrumbs.Item
            component={
              <BreadcrumbLink
                label={t("my_tasks.tabs.pages")}
                href={`/${workspaceSlug}/my-tasks/pages`}
                icon={<PageIcon className="h-4 w-4 text-tertiary" />}
              />
            }
          />
          <Breadcrumbs.Item
            component={
              <BreadcrumbNavigationSearchDropdown
                selectedItem={pageId?.toString() ?? ""}
                navigationItems={opcoes}
                onChange={(value: string) => router.push(`/${workspaceSlug}/my-tasks/pages/${value}`)}
                title={getPageName(page?.name)}
                icon={
                  <Breadcrumbs.Icon>
                    <SwitcherIcon logo_props={page.logo_props} LabelIcon={PageIcon} size={16} />
                  </Breadcrumbs.Icon>
                }
                isLast
              />
            }
          />
        </Breadcrumbs>
      </Header.LeftItem>
      <Header.RightItem>
        <PageSyncingBadge syncStatus={page.isSyncingWithServer} />
        <PageHeaderActions page={page} storeType={storeType} />
      </Header.RightItem>
    </Header>
  );
});
