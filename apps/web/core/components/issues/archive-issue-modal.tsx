/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { useParams } from "next/navigation";
import useSWR from "swr";
import { Repeat } from "lucide-react";
// i18n
import { useTranslation } from "@plane/i18n";
// types
import { Button } from "@plane/propel/button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import type { TDeDupeIssue, TIssue } from "@plane/types";
import { EModalPosition, EModalWidth, ModalCore } from "@plane/ui";
// hooks
import { useIssues } from "@/hooks/store/use-issues";
import { useProject } from "@/hooks/store/use-project";
// Evolury: arquivar a origem pausa a série — o ato acontece, mas não em
// silêncio (ADR 0010)
import { chaveDosSelos } from "@/components/recurring-work-items/section";
import { RecurringWorkItemService } from "@/services/recurring-work-item.service";

const servicoRecorrente = new RecurringWorkItemService();

type Props = {
  data?: TIssue | TDeDupeIssue;
  dataId?: string | null | undefined;
  handleClose: () => void;
  isOpen: boolean;
  onSubmit?: () => Promise<void>;
};

export function ArchiveIssueModal(props: Props) {
  const { dataId, data, isOpen, handleClose, onSubmit } = props;
  const { t } = useTranslation();
  const { workspaceSlug } = useParams();
  // states
  const [isArchiving, setIsArchiving] = useState(false);
  // store hooks
  const { getProjectById } = useProject();
  const { issueMap } = useIssues();

  const issue = data ? data : dataId ? issueMap[dataId] : undefined;

  // Evolury: a mesma lista enxuta que alimenta o selo do quadro responde se
  // esta tarefa é origem de recorrência.
  const projetoDaTarefa = issue?.project_id ?? null;
  const { data: selos } = useSWR(
    isOpen && workspaceSlug && projetoDaTarefa ? chaveDosSelos(workspaceSlug.toString(), projetoDaTarefa) : null,
    () => servicoRecorrente.badges(workspaceSlug!.toString(), projetoDaTarefa!)
  );
  const pausaRecorrencia = !!issue && !!selos?.source_issue_ids?.includes(issue.id);

  if (!dataId && !data) return null;
  if (!issue) return null;

  const projectDetails = getProjectById(issue.project_id);

  const onClose = () => {
    setIsArchiving(false);
    handleClose();
  };

  const handleArchiveIssue = async () => {
    if (!onSubmit) return;

    setIsArchiving(true);
    await onSubmit()
      .then(() => {
        setToast({
          type: TOAST_TYPE.SUCCESS,
          title: t("issue.archive.success.label"),
          message: t("issue.archive.success.message"),
        });
        onClose();
        return;
      })
      .catch(() =>
        setToast({
          type: TOAST_TYPE.ERROR,
          title: t("toast.error"),
          message: t("issue.archive.failed.message"),
        })
      )
      .finally(() => setIsArchiving(false));
  };

  return (
    <ModalCore isOpen={isOpen} handleClose={onClose} position={EModalPosition.CENTER} width={EModalWidth.LG}>
      <div className="px-5 py-4">
        <h3 className="text-18 font-medium 2xl:text-20">
          {t("issue.archive.label")} {projectDetails?.identifier} {issue.sequence_id}
        </h3>
        <p className="mt-3 text-13 text-secondary">{t("issue.archive.confirm_message")}</p>
        {/* Evolury: arquivar a origem pausa a série (ADR 0010) */}
        {pausaRecorrencia && (
          <div className="mt-3 flex items-start gap-2 rounded-md bg-warning-subtle px-3 py-2 text-12 text-warning-primary">
            <Repeat className="mt-0.5 size-3.5 shrink-0" />
            <span>{t("recurring_work_items.archive_warning")}</span>
          </div>
        )}
        <div className="mt-3 flex justify-end gap-2">
          <Button variant="secondary" size="lg" onClick={onClose}>
            {t("common.cancel")}
          </Button>
          <Button variant="primary" size="lg" tabIndex={1} onClick={handleArchiveIssue} loading={isArchiving}>
            {isArchiving ? t("common.archiving") : t("common.archive")}
          </Button>
        </div>
      </div>
    </ModalCore>
  );
}
