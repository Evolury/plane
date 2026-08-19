/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: página de "Minhas tarefas".

import { useParams } from "next/navigation";
import { useTranslation } from "@plane/i18n";
import { EHeaderVariant, Header } from "@plane/ui";
// components
import { PageHead } from "@/components/core/page-title";
import { MyTasksRoot } from "@/components/my-tasks/root";
import { MyTasksTabs } from "@/components/my-tasks/tabs";

export default function MyTasksPage() {
  const { t } = useTranslation();
  const { workspaceSlug } = useParams();

  return (
    <>
      <PageHead title={t("sidebar.my_tasks")} />
      <div className="relative flex h-full w-full flex-col overflow-hidden">
        <Header variant={EHeaderVariant.SECONDARY}>
          <Header.LeftItem>
            <MyTasksTabs workspaceSlug={workspaceSlug?.toString() ?? ""} />
          </Header.LeftItem>
        </Header>
        <div className="relative h-full w-full overflow-hidden overflow-y-auto">
          <MyTasksRoot />
        </div>
      </div>
    </>
  );
}
