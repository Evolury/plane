/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: página de "Minhas tarefas".

import { useTranslation } from "@plane/i18n";
// components
import { PageHead } from "@/components/core/page-title";
import { MyTasksRoot } from "@/components/my-tasks/root";

export default function MyTasksPage() {
  const { t } = useTranslation();

  return (
    <>
      <PageHead title={t("sidebar.my_tasks")} />
      <div className="relative h-full w-full overflow-hidden overflow-y-auto">
        <MyTasksRoot />
      </div>
    </>
  );
}
