/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { useParams } from "next/navigation";
// ui
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { AlertModalCore } from "@plane/ui";
import { useTranslation } from "@plane/i18n";
// hooks
import { useWebhook } from "@/hooks/store/use-webhook";
import { useAppRouter } from "@/hooks/use-app-router";

interface IDeleteWebhook {
  isOpen: boolean;
  onClose: () => void;
}

export function DeleteWebhookModal(props: IDeleteWebhook) {
  const { isOpen, onClose } = props;
  // states
  const [isDeleting, setIsDeleting] = useState(false);
  const { t } = useTranslation();
  // router
  const router = useAppRouter();
  // store hooks
  const { removeWebhook } = useWebhook();

  const { workspaceSlug, webhookId } = useParams();

  const handleClose = () => {
    onClose();
  };

  const handleDelete = async () => {
    if (!workspaceSlug || !webhookId) return;
    setIsDeleting(true);
    try {
      await removeWebhook(workspaceSlug.toString(), webhookId.toString());
      router.replace(`/${workspaceSlug}/settings/webhooks/`);
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: t("toast.success"),
        message: t("toast.webhook_deleted"),
      });
    } catch (_error) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("toast.error"),
        message: t("toast.webhook_delete_failed"),
      });
    }
    setIsDeleting(false);
  };

  return (
    <AlertModalCore
      handleClose={handleClose}
      handleSubmit={handleDelete}
      isSubmitting={isDeleting}
      isOpen={isOpen}
      title="Delete webhook"
      content={
        <>
          Are you sure you want to delete this webhook? Future events will not be delivered to this webhook. This action
          cannot be undone.
        </>
      }
    />
  );
}
