/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TIssueActivity } from "@plane/types";
import { translate } from "@plane/i18n";

export const getRelationActivityContent = (activity: TIssueActivity | undefined): string | undefined => {
  if (!activity) return;

  switch (activity.field) {
    case translate("activity_log.blocking"):
      return activity.old_value === ""
        ? `${translate("activity_log.marked_this_work_item_is_blocking_work_item")} `
        : `${translate("activity_log.removed_the_blocking_work_item")} `;
    case "blocked_by":
      return activity.old_value === ""
        ? `${translate("activity_log.marked_this_work_item_is_being_blocked_by")} `
        : `${translate("activity_log.removed_this_work_item_being_blocked_by_work_ite")} `;
    case "duplicate":
      return activity.old_value === ""
        ? `${translate("activity_log.marked_this_work_item_as_duplicate_of")} `
        : `${translate("activity_log.removed_this_work_item_as_a_duplicate_of")} `;
    case "relates_to":
      return activity.old_value === "" ? `${translate("activity_log.marked_that_this_work_item_relates_to")} ` : `${translate("activity_log.removed_the_relation_from")} `;
  }

  return;
};
