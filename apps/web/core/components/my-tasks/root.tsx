/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: raiz de "Minhas tarefas" — F2: listagem dos itens atribuídos
// agrupados por etapa pessoal, sem drag ainda. Os layouts base (lista/kanban
// com drag-drop) substituem esta renderização na F3, conforme o ADR 0002.

import { observer } from "mobx-react";
import { Link, useParams } from "react-router";
import useSWR from "swr";
// plane imports
import { useTranslation } from "@plane/i18n";
import { Spinner } from "@plane/ui";
// hooks
import { useMyTasks } from "@/hooks/use-my-tasks";
import { useProject } from "@/hooks/store/use-project";

export const MyTasksRoot = observer(function MyTasksRoot() {
  const { workspaceSlug } = useParams();
  const { t } = useTranslation();
  // store hooks
  const { stagesLoader, issuesLoader, sortedStages, groupedIssueIds, issueMap, fetchStages, fetchIssues } =
    useMyTasks();
  const { getProjectById } = useProject();

  useSWR(
    workspaceSlug ? `MY_TASKS_${workspaceSlug}` : null,
    async () => {
      if (!workspaceSlug) return;
      await Promise.all([fetchStages(workspaceSlug), fetchIssues(workspaceSlug)]);
    },
    { revalidateOnFocus: false }
  );

  if ((stagesLoader || issuesLoader) && sortedStages.length === 0) {
    return (
      <div className="grid h-full w-full place-items-center">
        <Spinner />
      </div>
    );
  }

  const totalIssues = Object.keys(issueMap).length;

  return (
    <div className="flex h-full w-full flex-col gap-6 overflow-y-auto p-6">
      {totalIssues === 0 && <p className="text-13 text-tertiary">{t("my_tasks.empty_state")}</p>}
      {sortedStages.map((stage) => {
        const issueIds = groupedIssueIds[stage.id] ?? [];
        return (
          <section key={stage.id} className="flex flex-col gap-2">
            <div className="flex items-center gap-2">
              <span
                className="size-3 flex-shrink-0 rounded-full"
                style={{ backgroundColor: stage.color }}
                aria-hidden="true"
              />
              <h2 className="text-14 font-semibold">{stage.name}</h2>
              <span className="text-12 text-tertiary">{issueIds.length}</span>
            </div>
            <div className="flex flex-col divide-y divide-subtle rounded-md border border-subtle">
              {issueIds.length === 0 ? (
                <p className="px-3 py-2 text-12 text-placeholder">—</p>
              ) : (
                issueIds.map((issueId) => {
                  const issue = issueMap[issueId];
                  if (!issue) return null;
                  const project = getProjectById(issue.project_id);
                  return (
                    <Link
                      key={issue.id}
                      to={`/${workspaceSlug}/browse/${project?.identifier}-${issue.sequence_id}/`}
                      className="flex items-center gap-3 px-3 py-2 hover:bg-layer-1-hover"
                    >
                      <span className="flex-shrink-0 text-11 font-medium text-tertiary">
                        {project?.identifier}-{issue.sequence_id}
                      </span>
                      <span className="truncate text-13">{issue.name}</span>
                    </Link>
                  );
                })
              )}
            </div>
          </section>
        );
      })}
    </div>
  );
});
