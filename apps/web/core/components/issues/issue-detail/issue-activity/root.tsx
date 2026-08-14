/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useMemo } from "react";
import uniq from "lodash-es/uniq";
import { observer } from "mobx-react";
// plane package imports
import type { TActivityFilters } from "@plane/constants";
import { E_SORT_ORDER, defaultActivityFilters } from "@plane/constants";
import { useLocalStorage } from "@plane/hooks";
// i18n
import { useTranslation } from "@plane/i18n";
//types
import type { TFileSignedURLResponse, TIssueComment } from "@plane/types";
// components
import { CommentCreate } from "@/components/comments/comment-create";
// hooks
import { useProject } from "@/hooks/store/use-project";
// local imports
import { IssueActivityList, IssueCommentsList } from "./activity-comment-root";
import { useWorkItemCommentOperations } from "./helper";
import { ActivitySortRoot } from "./sort-root";
import { ActivityFilterRoot } from "./filter-root";

type TIssueActivity = {
  workspaceSlug: string;
  projectId: string;
  issueId: string;
  disabled?: boolean;
  isIntakeIssue?: boolean;
};

export type TActivityOperations = {
  createComment: (data: Partial<TIssueComment>) => Promise<TIssueComment>;
  updateComment: (commentId: string, data: Partial<TIssueComment>) => Promise<void>;
  removeComment: (commentId: string) => Promise<void>;
  uploadCommentAsset: (blockId: string, file: File, commentId?: string) => Promise<TFileSignedURLResponse>;
};

export const IssueActivity = observer(function IssueActivity(props: TIssueActivity) {
  const { workspaceSlug, projectId, issueId, disabled = false, isIntakeIssue = false } = props;
  // i18n
  const { t } = useTranslation();
  // hooks
  const { setValue: setFilterValue, storedValue: selectedFilters } = useLocalStorage(
    "issue_activity_filters",
    defaultActivityFilters
  );
  const { setValue: setSortOrder, storedValue: sortOrder } = useLocalStorage("activity_sort_order", E_SORT_ORDER.ASC);

  const { getProjectById } = useProject();

  // toggle filter
  const toggleFilter = (filter: TActivityFilters) => {
    if (!selectedFilters) return;
    let _filters = [];
    if (selectedFilters.includes(filter)) {
      if (selectedFilters.length === 1) return selectedFilters; // Ensure at least one filter is applied
      _filters = selectedFilters.filter((f) => f !== filter);
    } else {
      _filters = [...selectedFilters, filter];
    }

    setFilterValue(uniq(_filters));
  };

  const toggleSortOrder = () => {
    setSortOrder(sortOrder === E_SORT_ORDER.ASC ? E_SORT_ORDER.DESC : E_SORT_ORDER.ASC);
  };

  // helper hooks
  const activityOperations = useWorkItemCommentOperations(workspaceSlug, projectId, issueId);

  const project = getProjectById(projectId);
  const renderCommentCreationBox = useMemo(
    () => (
      <CommentCreate
        workspaceSlug={workspaceSlug}
        entityId={issueId}
        activityOperations={activityOperations}
        showToolbarInitially
        projectId={projectId}
      />
    ),
    [workspaceSlug, issueId, activityOperations, projectId]
  );
  if (!project) return <></>;

  return (
    // Evolury: a conversa vem primeiro; o histórico automático vem depois e
    // recortado. Misturados, as linhas de "mudou o estado" afogavam os
    // comentários, que são a parte que alguém escreveu para ser lida.
    <div className="space-y-8">
      {/* comentários */}
      <div className="space-y-4">
        <div className="text-h5-medium text-primary">{t("common.comments")}</div>
        <div className="space-y-3">
          {!disabled && sortOrder === E_SORT_ORDER.DESC && renderCommentCreationBox}
          <IssueCommentsList
            projectId={projectId}
            workspaceSlug={workspaceSlug}
            isIntakeIssue={isIntakeIssue}
            issueId={issueId}
            activityOperations={activityOperations}
            showAccessSpecifier={!!project.anchor}
            disabled={disabled}
            sortOrder={sortOrder || E_SORT_ORDER.ASC}
          />
          {!disabled && sortOrder === E_SORT_ORDER.ASC && renderCommentCreationBox}
        </div>
      </div>

      {/* atividade */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="text-h5-medium text-primary">{t("common.activity")}</div>
          <div className="flex items-center gap-2">
            <ActivitySortRoot sortOrder={sortOrder || E_SORT_ORDER.ASC} toggleSort={toggleSortOrder} />
            <ActivityFilterRoot
              selectedFilters={selectedFilters || defaultActivityFilters}
              toggleFilter={toggleFilter}
              isIntakeIssue={isIntakeIssue}
              projectId={projectId}
            />
          </div>
        </div>
        <IssueActivityList
          issueId={issueId}
          selectedFilters={selectedFilters || defaultActivityFilters}
          sortOrder={sortOrder || E_SORT_ORDER.ASC}
        />
      </div>
    </div>
  );
});
