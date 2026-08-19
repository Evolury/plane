/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: mover página entre o espaço pessoal e um projeto (ADR 0015).
//
// No sentido pessoal → projeto o aviso não é decoração: os compartilhamentos
// caem, porque dentro do projeto quem manda é o projeto.

import { useState } from "react";
import { observer } from "mobx-react";
import { useParams } from "next/navigation";
// plane imports
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { CustomSearchSelect, EModalPosition, EModalWidth, ModalCore } from "@plane/ui";
// hooks
import { useProject } from "@/hooks/store/use-project";
// services
import { PersonalPageService } from "@/services/page";

const service = new PersonalPageService();

type Props = {
  isOpen: boolean;
  onClose: () => void;
  pageId: string;
  onMoved?: () => void;
};

export const MovePageToProjectModal = observer(function MovePageToProjectModal(props: Props) {
  const { isOpen, onClose, pageId, onMoved } = props;
  const { t } = useTranslation();
  const { workspaceSlug } = useParams();
  const slug = workspaceSlug?.toString() ?? "";
  const [projeto, setProjeto] = useState("");
  const [movendo, setMovendo] = useState(false);
  // Quantas pessoas perdem o acesso — contado no servidor, não deduzido.
  const [compartilhamentos, setCompartilhamentos] = useState(0);
  const [contou, setContou] = useState(false);

  if (isOpen && !contou) {
    setContou(true);
    service
      .fetchShares(slug, pageId)
      .then((lista) => setCompartilhamentos(lista.length))
      .catch(() => setCompartilhamentos(0));
  }
  if (!isOpen && contou) setContou(false);
  const { joinedProjectIds, getProjectById } = useProject();

  const opcoes = (joinedProjectIds ?? []).map((id) => {
    const p = getProjectById(id);
    return { value: id, query: p?.name ?? "", content: p?.name ?? "" };
  });

  const mover = async () => {
    if (!projeto) return;
    setMovendo(true);
    try {
      await service.moveToProject(slug, pageId, projeto);
      onMoved?.();
      onClose();
    } catch {
      setToast({ type: TOAST_TYPE.ERROR, title: t("toast.error"), message: t("my_tasks.pages.move_failed") });
    } finally {
      setMovendo(false);
    }
  };

  return (
    <ModalCore isOpen={isOpen} handleClose={onClose} position={EModalPosition.CENTER} width={EModalWidth.XL}>
      <div className="space-y-4 p-5">
        <h3 className="text-16 font-medium text-primary">{t("my_tasks.pages.move_title")}</h3>
        <CustomSearchSelect
          value={projeto}
          onChange={(valor: string) => setProjeto(valor)}
          options={opcoes}
          label={projeto ? (getProjectById(projeto)?.name ?? "") : t("my_tasks.pages.move_project")}
          maxHeight="md"
        />
        {compartilhamentos > 0 && (
          <p className="text-warning text-13">
            {compartilhamentos === 1
              ? t("my_tasks.pages.move_warning_one")
              : t("my_tasks.pages.move_warning_many", { count: compartilhamentos })}
          </p>
        )}
        <div className="flex justify-end gap-2">
          <Button variant="secondary" size="sm" onClick={onClose}>
            {t("cancel")}
          </Button>
          <Button variant="primary" size="sm" onClick={mover} loading={movendo} disabled={!projeto}>
            {t("my_tasks.pages.move_confirm")}
          </Button>
        </div>
      </div>
    </ModalCore>
  );
});
