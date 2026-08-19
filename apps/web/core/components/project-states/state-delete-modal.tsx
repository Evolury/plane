/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import { useParams } from "next/navigation";
// Plane imports
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import type { IState } from "@plane/types";
// ui
import { AlertModalCore } from "@plane/ui";
import { useTranslation } from "@plane/i18n";
// hooks
import { useProjectState } from "@/hooks/store/use-project-state";

type TStateDeleteModal = {
  isOpen: boolean;
  onClose: () => void;
  data: IState | null;
};

export const StateDeleteModal = observer(function StateDeleteModal(props: TStateDeleteModal) {
  const { isOpen, onClose, data } = props;
  // states
  const [isDeleteLoading, setIsDeleteLoading] = useState(false);
  const { t } = useTranslation();
  // router
  const { workspaceSlug } = useParams();
  const { deleteState } = useProjectState();

  const handleClose = () => {
    onClose();
    setIsDeleteLoading(false);
  };

  const handleDeletion = async () => {
    if (!workspaceSlug || !data) return;

    setIsDeleteLoading(true);

    await deleteState(workspaceSlug.toString(), data.project_id, data.id)
      .then(() => {
        handleClose();
      })
      .catch((err) => {
        if (err.status === 400)
          setToast({
            type: TOAST_TYPE.ERROR,
            title: t("toast.error"),
            message: t("toast.state_has_work_items"),
          });
        else
          setToast({
            type: TOAST_TYPE.ERROR,
            title: t("toast.error"),
            message: t("toast.state_delete_failed"),
          });
      })
      .finally(() => {
        setIsDeleteLoading(false);
      });
  };

  return (
    <AlertModalCore
      handleClose={handleClose}
      handleSubmit={handleDeletion}
      isSubmitting={isDeleteLoading}
      isOpen={isOpen}
      title={t("ui.delete_state")}
      content={
        // Evolury: o texto estava cravado em inglês num produto em português.
        //
        // A redação nova não diz "estado" nem "etapa": o mesmo modal serve às
        // duas telas, e o nome do item já aparece na frase. Repetir a categoria
        // não acrescenta nada e obrigaria a arrastar um rótulo por seis
        // componentes só para trocar um substantivo.
        <>
          {t("ui.delete_state_confirm_before")}
          <span className="font-medium text-primary">{data?.name}</span>
          {t("ui.delete_state_confirm_after")}
        </>
      }
    />
  );
});
