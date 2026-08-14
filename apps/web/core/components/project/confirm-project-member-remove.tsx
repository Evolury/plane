/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import { useParams } from "next/navigation";
import useSWR from "swr";
import { AlertTriangle, Repeat } from "lucide-react";
// types
import { Button } from "@plane/propel/button";
import type { IUserLite } from "@plane/types";
// ui
import { EModalPosition, EModalWidth, ModalCore } from "@plane/ui";
// hooks
import { useMember } from "@/hooks/store/use-member";
import { useProject } from "@/hooks/store/use-project";
import { useUser } from "@/hooks/store/user";
import { useTranslation } from "@plane/i18n";
// Evolury: remover alguém não desfaz atribuições — a recorrência dele
// continuaria carimbando toda ocorrência futura (ADR 0010)
import { RecurringWorkItemService } from "@/services/recurring-work-item.service";

const servicoRecorrente = new RecurringWorkItemService();

type Props = {
  data: Partial<IUserLite>;
  onSubmit: () => Promise<void>;
  isOpen: boolean;
  onClose: () => void;
};

export const ConfirmProjectMemberRemove = observer(function ConfirmProjectMemberRemove(props: Props) {
  const { t } = useTranslation();
  const { data, onSubmit, isOpen, onClose } = props;
  // router
  const { projectId } = useParams();
  // router
  const { workspaceSlug } = useParams();
  // states
  const [isDeleteLoading, setIsDeleteLoading] = useState(false);
  const [novoResponsavel, setNovoResponsavel] = useState<string>("");
  // store hooks
  const { data: currentUser } = useUser();
  const { getProjectById } = useProject();
  const {
    project: { getProjectMemberIds, getProjectMemberDetails },
  } = useMember();

  // Evolury: quantas recorrentes ficam sem responsável — o ato não é travado,
  // mas deixa de ser silencioso, e a transferência acontece aqui mesmo.
  const { data: recorrentes } = useSWR(
    isOpen && workspaceSlug && projectId && data?.id ? `RECURRING_FOR_MEMBER_${projectId}_${data.id}` : null,
    () => servicoRecorrente.forMember(workspaceSlug!.toString(), projectId!.toString(), data.id!)
  );
  const afetadas = recorrentes?.count ?? 0;

  const outrosMembros = (getProjectMemberIds(projectId?.toString() ?? "", false) ?? []).filter((id) => id !== data?.id);

  const handleClose = () => {
    onClose();
    setIsDeleteLoading(false);
    setNovoResponsavel("");
  };

  const handleDeletion = async () => {
    setIsDeleteLoading(true);

    // A transferência vem ANTES: se a remoção falhar, ninguém fica com uma
    // atribuição fantasma; se a transferência falhar, a remoção segue mesmo
    // assim — ato de governança não fica refém de metadado.
    if (afetadas > 0 && workspaceSlug && projectId && data?.id) {
      try {
        await servicoRecorrente.transferAssignee(
          workspaceSlug.toString(),
          projectId.toString(),
          data.id,
          novoResponsavel || undefined
        );
      } catch {
        // segue adiante de propósito
      }
    }

    await onSubmit();

    handleClose();
  };

  if (!projectId) return <></>;

  const isCurrentUser = currentUser?.id === data?.id;
  const currentProjectDetails = getProjectById(projectId.toString());

  return (
    <ModalCore isOpen={isOpen} handleClose={handleClose} position={EModalPosition.CENTER} width={EModalWidth.XXL}>
      <div className="bg-surface-1 px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
        <div className="sm:flex sm:items-start">
          <div className="mx-auto flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-danger-subtle sm:mx-0 sm:h-10 sm:w-10">
            <AlertTriangle className="h-6 w-6 text-danger-primary" aria-hidden="true" />
          </div>
          <div className="mt-3 text-center sm:mt-0 sm:ml-4 sm:text-left">
            <h3 className="text-16 leading-6 font-medium text-primary">
              {isCurrentUser
                ? t("ui.leave_project_2")
                : t("remove_member_confirmation_title", { name: data?.display_name ?? "" })}
            </h3>
            <div className="mt-2">
              {/* Evolury: nome do projeto/membro em negrito no meio da frase — padrão prefix/suffix do repo */}
              <p className="text-13 text-secondary">
                {isCurrentUser ? (
                  <>
                    {t("project_settings.members.leave_confirmation.prefix")}{" "}
                    <span className="font-bold">{currentProjectDetails?.name}</span>
                    {t("project_settings.members.leave_confirmation.suffix")}
                  </>
                ) : (
                  <>
                    {t("project_settings.members.remove_confirmation.prefix")}{" "}
                    <span className="font-bold">{data?.display_name}</span>
                    {t("project_settings.members.remove_confirmation.suffix")}
                  </>
                )}
              </p>
            </div>

            {/* Evolury: as recorrentes afetadas, com transferência (ADR 0010) */}
            {afetadas > 0 && (
              <div className="mt-4 space-y-2 rounded-md bg-warning-subtle p-3 text-left">
                <div className="flex items-start gap-2 text-12 text-warning-primary">
                  <Repeat className="mt-0.5 size-3.5 shrink-0" />
                  <span>{t("recurring_work_items.member_removal.warning", { count: afetadas })}</span>
                </div>
                <p className="text-11 text-tertiary">{t("recurring_work_items.member_removal.explanation")}</p>
                <label className="flex flex-wrap items-center gap-2 text-12">
                  <span className="text-secondary">{t("recurring_work_items.member_removal.transfer_label")}</span>
                  <select
                    value={novoResponsavel}
                    onChange={(e) => setNovoResponsavel(e.target.value)}
                    className="rounded-md border border-subtle bg-surface-1 px-2 py-1"
                  >
                    <option value="">{t("recurring_work_items.member_removal.transfer_none")}</option>
                    {outrosMembros.map((id) => (
                      <option key={id} value={id}>
                        {getProjectMemberDetails(id, projectId!.toString())?.member?.display_name ?? id}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
            )}
          </div>
        </div>
      </div>
      <div className="flex justify-end gap-2 p-4 sm:px-6">
        <Button variant="secondary" size="lg" onClick={handleClose}>
          {t("cancel")}
        </Button>
        <Button variant="error-fill" size="lg" tabIndex={1} onClick={handleDeletion} loading={isDeleteLoading}>
          {isCurrentUser
            ? isDeleteLoading
              ? t("leaving")
              : t("leave")
            : isDeleteLoading
              ? t("removing")
              : t("remove")}
        </Button>
      </div>
    </ModalCore>
  );
});
