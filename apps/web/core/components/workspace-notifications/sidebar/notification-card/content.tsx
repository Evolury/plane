/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { ReactNode } from "react";
// plane imports
import type { TNotification } from "@plane/types";
import {
  convertMinutesToHoursMinutesString,
  renderFormattedDate,
  sanitizeCommentForNotification,
  stripAndTruncateHTML,
} from "@plane/utils";
// components
import { LiteTextEditor } from "@/components/editor/lite-text";
import {
  ADDITIONAL_NOTIFICATION_CONTENT_MAP,
  renderAdditionalAction,
  renderAdditionalValue,
  shouldShowConnector,
} from "../../notification-card/content";
import { translate } from "@plane/i18n";

// Types
export type TNotificationFieldData = {
  field: string | undefined;
  newValue: string | undefined;
  oldValue: string | undefined;
  verb: string | undefined;
};

export type TNotificationContentDetails = {
  action?: ReactNode;
  value?: ReactNode;
  showConnector?: boolean;
};

export type TNotificationContentHandler = (data: TNotificationFieldData) => TNotificationContentDetails | null;

export type TNotificationContentMap = {
  [key: string]: TNotificationContentHandler;
};

// Base notification content map for core fields
export const BASE_NOTIFICATION_CONTENT_MAP: TNotificationContentMap = {
  duplicate: ({ verb }) => ({
    action:
      verb === "created"
        ? translate("activity_log.marked_that_this_work_item_is_a_duplicate_of")
        : translate("activity_log.marked_that_this_work_item_is_not_a_duplicate"),
    value: null,
    showConnector: false,
  }),
  assignees: ({ newValue, oldValue }) => ({
    action: newValue !== "" ? translate("activity_log.added_assignee") : translate("activity_log.removed_assignee"),
    value: newValue !== "" ? newValue : oldValue,
    showConnector: false,
  }),
  start_date: ({ newValue }) => ({
    action: newValue !== "" ? translate("activity_log.set_start_date") : "removed the start date",
    value: renderFormattedDate(newValue),
    showConnector: false,
  }),
  target_date: ({ newValue }) => ({
    action: newValue !== "" ? translate("activity_log.set_due_date") : "removed the due date",
    value: renderFormattedDate(newValue),
    showConnector: false,
  }),
  labels: ({ newValue, oldValue }) => ({
    action: newValue !== "" ? translate("activity_log.added_label") : translate("activity_log.removed_label"),
    value: newValue !== "" ? newValue : oldValue,
    showConnector: false,
  }),
  parent: ({ newValue, oldValue }) => ({
    action: newValue !== "" ? translate("activity_log.added_parent") : translate("activity_log.removed_parent"),
    value: newValue !== "" ? newValue : oldValue,
    showConnector: false,
  }),
  relates_to: () => ({
    action: translate("activity_log.marked_that_this_work_item_is_related_to"),
    value: null,
    showConnector: true,
  }),
  comment: ({ newValue }, renderCommentBox?: boolean) => ({
    action: translate("activity_log.commented"),
    value: renderCommentBox ? null : sanitizeCommentForNotification(newValue),
    showConnector: false,
  }),
  archived_at: ({ newValue }) => ({
    action:
      newValue === "restore"
        ? translate("activity_log.restored_work_item")
        : translate("activity_log.archived_work_item"),
    value: null,
    showConnector: false,
  }),
  // Evolury: o aviso da ação `notify` de uma automação (ADR 0012).
  //
  // `field` é "automation" — um valor que não existe no upstream, porque lá não
  // há automação que avise. Sem entrada aqui, a leitura caía no
  // `renderAdditionalAction`, que monta a frase concatenando `verb` com o nome
  // do campo, os dois crus: o cartão exibia "Automação created automation em
  // <texto>" num produto em português.
  //
  // O texto JÁ é a frase que a regra escreveu, então ele é o valor e não
  // precisa de conector: "Automação avisou: <texto>."
  automation: ({ newValue }) => ({
    action: translate("activity_log.automation_notified"),
    value: newValue,
    showConnector: false,
  }),
  None: () => ({
    action: null,
    value: translate("activity_log.the_work_item_and_assigned_it_to_you"),
    showConnector: false,
  }),
  // Fields below only define value - action falls through to default handler
  attachment: () => ({
    action: null,
    value: translate("activity_log.the_work_item"),
    showConnector: true,
  }),
  description: ({ newValue }) => ({
    value: stripAndTruncateHTML(newValue || "", 55),
    showConnector: true,
  }),
  estimate_time: ({ newValue, oldValue }) => ({
    value:
      newValue !== ""
        ? convertMinutesToHoursMinutesString(Number(newValue))
        : convertMinutesToHoursMinutesString(Number(oldValue)),
    showConnector: true,
  }),
};

// Helper to get content details from maps
const getNotificationContentDetails = (
  fieldData: TNotificationFieldData,
  renderCommentBox?: boolean
): TNotificationContentDetails | null => {
  const { field } = fieldData;
  if (!field) return null;

  // Check base map first
  const baseHandler = BASE_NOTIFICATION_CONTENT_MAP[field];
  if (baseHandler) {
    // Special case for comment field that needs renderCommentBox
    if (field === "comment") {
      return (baseHandler as (data: TNotificationFieldData, renderCommentBox?: boolean) => TNotificationContentDetails)(
        fieldData,
        renderCommentBox
      );
    }
    return baseHandler(fieldData);
  }

  // Check additional map from plane-web (EE extensions)
  const additionalHandler = ADDITIONAL_NOTIFICATION_CONTENT_MAP[field];
  if (additionalHandler) {
    return additionalHandler(fieldData);
  }

  return null;
};

export function NotificationContent({
  notification,
  workspaceId,
  workspaceSlug,
  projectId,
  renderCommentBox = false,
}: {
  notification: TNotification;
  workspaceId: string;
  workspaceSlug: string;
  projectId: string;
  renderCommentBox?: boolean;
}) {
  const { data, triggered_by_details: triggeredBy } = notification;
  // Evolury: o `?.` precisa estar nas QUATRO leituras, e não só na primeira.
  //
  // A correção anterior (#150) pôs o opcional em `field` e deixou as três
  // irmãs, o que só mudou qual linha estoura: uma notificação gravada sem
  // `issue_activity` continuava derrubando a caixa de entrada inteira. Há uma
  // linha assim no banco — das que foram criadas antes daquela correção —, e
  // ela não some sozinha.
  const notificationField = data?.issue_activity?.field;
  const newValue = data?.issue_activity?.new_value;
  const oldValue = data?.issue_activity?.old_value;
  const verb = data?.issue_activity?.verb;

  const fieldData: TNotificationFieldData = {
    field: notificationField,
    newValue,
    oldValue,
    verb,
  };

  const renderTriggerName = () => (
    <span className="font-medium text-primary">
      {triggeredBy?.is_bot ? triggeredBy.first_name : triggeredBy?.display_name}{" "}
    </span>
  );

  // Get content details from map
  const contentDetails = getNotificationContentDetails(fieldData, renderCommentBox);

  // Render action - use map value if defined, otherwise fall through to default handler
  // Note: undefined = fall through to default, null = explicitly no action text
  const renderAction = (): ReactNode => {
    if (!notificationField) return "";
    // Check if action is explicitly defined in map (including null)
    if (contentDetails && "action" in contentDetails) return contentDetails.action;
    // Fallback to default action handler for fields not in map or without action defined
    return renderAdditionalAction(notificationField, verb);
  };

  // Render value - use map value if defined, otherwise fall through to default handler
  const renderValue = (): ReactNode => {
    // Check if value is explicitly defined in map
    if (contentDetails && "value" in contentDetails) return contentDetails.value;
    // Fallback to default value handler for fields not in map or without value defined
    return renderAdditionalValue(notificationField, newValue, oldValue);
  };

  // Determine if connector should be shown - prefer map value, fallback to function
  const showConnector =
    contentDetails?.showConnector !== undefined ? contentDetails.showConnector : shouldShowConnector(notificationField);

  return (
    <>
      {renderTriggerName()}
      <span className="text-tertiary">{renderAction()} </span>
      {/* Evolury: `verb` vem cru da API ("deleted"), então comparar com
          translate() dava sempre verdadeiro em pt e o bloco nunca era ocultado
          numa exclusão. Comparação literal + conector traduzido. */}
      {verb !== "deleted" && (
        <>
          {showConnector && <span className="text-tertiary">{translate("activity_log.prep_in")}</span>}
          <span className="font-medium text-primary">{renderValue()}</span>
          {notificationField === "comment" && renderCommentBox && (
            <div className="origin-left scale-75">
              <LiteTextEditor
                editable={false}
                id=""
                initialValue={newValue ?? ""}
                workspaceId={workspaceId}
                workspaceSlug={workspaceSlug}
                projectId={projectId}
                displayConfig={{
                  fontSize: "small-font",
                }}
              />
            </div>
          )}
          {"."}
        </>
      )}
    </>
  );
}
