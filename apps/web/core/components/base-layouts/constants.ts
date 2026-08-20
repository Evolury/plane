/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { BoardLayoutIcon, ListLayoutIcon, TimelineLayoutIcon } from "@plane/propel/icons";
import type { IBaseLayoutConfig } from "@plane/types";

export const BASE_LAYOUTS: IBaseLayoutConfig[] = [
  {
    key: "list",
    icon: ListLayoutIcon,
    i18n_label: "issue.layouts.title.list",
  },
  {
    key: "kanban",
    icon: BoardLayoutIcon,
    i18n_label: "issue.layouts.title.kanban",
  },
  {
    key: "gantt",
    icon: TimelineLayoutIcon,
    i18n_label: "issue.layouts.title.gantt",
  },
];
