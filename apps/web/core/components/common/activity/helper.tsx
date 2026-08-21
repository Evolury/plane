/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { FC, ReactNode } from "react";
import {
  RotateCcw,
  Network,
  Inbox,
  AlignLeft,
  Paperclip,
  Type,
  FileText,
  Hash,
  Clock,
  Bell,
  GitBranch,
  Timer,
  ListTodo,
  Layers,
} from "lucide-react";
// components

import {
  LinkIcon,
  ArchiveIcon,
  CycleIcon,
  GlobeIcon,
  DueDatePropertyIcon,
  EstimatePropertyIcon,
  GridLayoutIcon,
  IntakeIcon,
  LabelPropertyIcon,
  MembersPropertyIcon,
  ModuleIcon,
  PriorityPropertyIcon,
  StartDatePropertyIcon,
  StatePropertyIcon,
} from "@plane/propel/icons";
import { store } from "@/lib/store-context";
import type { TProjectActivity } from "@plane/types";
import { translate } from "@plane/i18n";

type ActivityIconMap = {
  [key: string]: FC<{ className?: string }>;
};
export const iconsMap: ActivityIconMap = {
  priority: PriorityPropertyIcon,
  archived_at: ArchiveIcon,
  restored: RotateCcw,
  link: LinkIcon,
  start_date: StartDatePropertyIcon,
  target_date: DueDatePropertyIcon,
  label: LabelPropertyIcon,
  inbox: Inbox,
  description: AlignLeft,
  assignee: MembersPropertyIcon,
  attachment: Paperclip,
  name: Type,
  state: StatePropertyIcon,
  estimate: EstimatePropertyIcon,
  cycle: CycleIcon,
  module: ModuleIcon,
  page: FileText,
  network: GlobeIcon,
  identifier: Hash,
  timezone: Clock,
  is_project_updates_enabled: Bell,
  is_epic_enabled: GridLayoutIcon,
  is_workflow_enabled: GitBranch,
  is_time_tracking_enabled: Timer,
  is_issue_type_enabled: ListTodo,
  default: Network,
  module_view: ModuleIcon,
  cycle_view: CycleIcon,
  issue_views_view: Layers,
  page_view: FileText,
  intake_view: IntakeIcon,
};

export const messages = (activity: TProjectActivity): { message: string | ReactNode; customUserName?: string } => {
  const activityType = activity.field;
  const newValue = activity.new_value;
  const oldValue = activity.old_value;
  const verb = activity.verb;
  const workspaceDetail = store.workspaceRoot.getWorkspaceById(activity.workspace);

  const getBooleanActionText = (value: string | undefined) => {
    if (value === "true") return "enabled";
    if (value === "false") return "disabled";
    return verb;
  };

  switch (activityType) {
    case "priority":
      return {
        message: (
          <>
            set the priority to <span className="font-medium text-primary">{newValue || "none"}</span>
          </>
        ),
      };
    case "archived_at":
      return {
        message:
          newValue === "restore"
            ? translate("activity_log.restored_the_project")
            : translate("activity_log.archived_the_project"),
        customUserName: newValue === "archive" ? "QooWork" : undefined,
      };
    case "name":
      return {
        message: (
          <>
            renamed the project to <span className="font-medium text-primary">{newValue}</span>
          </>
        ),
      };
    case "description":
      return {
        message: newValue
          ? translate("activity_log.updated_the_project_description")
          : translate("activity_log.removed_the_project_description"),
      };
    case "start_date":
      return {
        message: (
          <>
            {newValue ? (
              <>
                set the start date to <span className="font-medium text-primary">{newValue}</span>
              </>
            ) : (
              translate("activity_log.removed_start_date")
            )}
          </>
        ),
      };
    case "target_date":
      return {
        message: (
          <>
            {newValue ? (
              <>
                set the target date to <span className="font-medium text-primary">{newValue}</span>
              </>
            ) : (
              translate("activity_log.removed_the_target_date")
            )}
          </>
        ),
      };
    case "state":
      return {
        message: (
          <>
            set the state to <span className="font-medium text-primary">{newValue || "none"}</span>
          </>
        ),
      };
    case "estimate":
      return {
        message: (
          <>
            {newValue ? (
              <>
                {translate("activity_log.set_estimate")}
                <span className="font-medium text-primary">{newValue}</span>
              </>
            ) : (
              <>
                {translate("activity_log.removed_estimate")}
                {oldValue && (
                  <>
                    {" "}
                    <span className="font-medium text-primary">{oldValue}</span>
                  </>
                )}
              </>
            )}
          </>
        ),
      };
    case "cycles":
      return {
        message: (
          <>
            {/* Evolury: `verb` vem cru da API ("removed"), então comparar com
                translate() nunca casava em pt e o ramo de remoção jamais era
                escolhido. Comparação literal + mensagem inteira traduzida, em
                vez de colar verbo em inglês com texto traduzido. */}
            <span>
              {verb === "removed"
                ? `${translate("activity_log.removed_this_project")}${translate("activity_log.from_the_cycle")} `
                : `${translate("activity_log.added_this_project")}${translate("ui.activity_to_the_cycle")} `}
            </span>
            {verb !== "removed" ? (
              <a
                href={`/${workspaceDetail?.slug}/projects/${activity.project}/cycles/${activity.new_identifier}`}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex font-medium text-primary"
              >
                {activity.new_value}
              </a>
            ) : (
              <span className="font-medium text-primary">{activity.old_value || translate("ui.unknown_cycle")}</span>
            )}
          </>
        ),
      };
    case "modules":
      return {
        message: (
          <>
            {/* Evolury: mesma correção do bloco de ciclos */}
            <span>
              {verb === "removed"
                ? `${translate("activity_log.removed_this_project")}${translate("activity_log.from_the_module")} `
                : `${translate("activity_log.added_this_project")}${translate("activity_log.to_the_module")} `}
            </span>
            <span className="font-medium text-primary">
              {verb === "removed" ? oldValue : newValue || translate("activity_log.unknown_module")}
            </span>
          </>
        ),
      };
    case "labels":
      return {
        message: (
          <>
            {/* Evolury: idem — verbo cru em inglês virou mensagem traduzida */}
            {verb === "removed" ? translate("activity_log.removed_label") : translate("activity_log.added_label")}
            <span className="font-medium text-primary">{newValue || oldValue || translate("ui.untitled_label")}</span>
          </>
        ),
      };
    case "inbox":
      return {
        message: <>{newValue ? "enabled" : "disabled"} inbox</>,
      };
    case "page":
      return {
        message: (
          <>
            {newValue ? "created" : translate("activity_log.removed")} the project page{" "}
            <span className="font-medium text-primary">
              {newValue || oldValue || translate("templates.settings.form.page.name.placeholder")}
            </span>
          </>
        ),
      };
    case "network":
      return {
        message: <>{newValue ? "enabled" : "disabled"} network access</>,
      };
    case "identifier":
      return {
        message: (
          <>
            updated project identifier to <span className="font-medium text-primary">{newValue || "none"}</span>
          </>
        ),
      };
    case "timezone":
      return {
        message: (
          <>
            changed project timezone to <span className="font-medium text-primary">{newValue || "default"}</span>
          </>
        ),
      };
    case "module_view":
    case "cycle_view":
    case "issue_views_view":
    case "page_view":
    case "intake_view":
      return {
        message: (
          <>
            {getBooleanActionText(newValue)} {activityType.replace(/_view$/, "").replace(/_/g, " ")} view
          </>
        ),
      };
    case "is_project_updates_enabled":
      return {
        message: <>{getBooleanActionText(newValue)} project updates</>,
      };
    case "is_epic_enabled":
      return {
        message: <>{getBooleanActionText(newValue)} epics</>,
      };
    case "is_workflow_enabled":
      return {
        message: <>{getBooleanActionText(newValue)} custom workflow</>,
      };
    case "is_time_tracking_enabled":
      return {
        message: <>{getBooleanActionText(newValue)} time tracking</>,
      };
    case "is_issue_type_enabled":
      // Evolury: i18n com mensagem completa para não concatenar verbo EN fixo com tradução
      return {
        message:
          newValue === "true" ? (
            translate("activity_log.enabled_work_item_types")
          ) : newValue === "false" ? (
            translate("activity_log.disabled_work_item_types")
          ) : (
            <>
              {verb} {translate("work_item_types.label_lowercase")}
            </>
          ),
      };
    default:
      return {
        message: `${verb} ${activityType?.replace(/_/g, " ")} `,
      };
  }
};
