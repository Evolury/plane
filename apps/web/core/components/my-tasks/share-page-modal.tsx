/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: com quem esta página pessoal é dividida (ADR 0015).
//
// Compartilhar é privilégio do dono, mesmo para quem recebeu "pode editar" — a
// regra mora no servidor; aqui a tela só não oferece o que não funcionaria.

import { useState } from "react";
import { observer } from "mobx-react";
import { X } from "lucide-react";
import { useParams } from "next/navigation";
// plane imports
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import type { TPageShare } from "@plane/types";
import { PAPEL_DA_PAGINA } from "@plane/types";
import { CustomSearchSelect, EModalPosition, EModalWidth, ModalCore } from "@plane/ui";
// hooks
import { useMember } from "@/hooks/store/use-member";
// services
import { PersonalPageService } from "@/services/page";

const service = new PersonalPageService();

type Props = {
  isOpen: boolean;
  onClose: () => void;
  pageId: string;
};

export const SharePageModal = observer(function SharePageModal(props: Props) {
  const { isOpen, onClose, pageId } = props;
  const { t } = useTranslation();
  const { workspaceSlug } = useParams();
  const slug = workspaceSlug?.toString() ?? "";
  // states
  const [compartilhamentos, setCompartilhamentos] = useState<TPageShare[]>([]);
  // String vazia, e não `null`/`undefined`: o Combobox de baixo mantém um
  // input escondido, e sair de "sem valor" para um valor faz o React acusar
  // troca de não-controlado para controlado.
  const [pessoa, setPessoa] = useState("");
  const [papel, setPapel] = useState<number>(PAPEL_DA_PAGINA.LER);
  const [salvando, setSalvando] = useState(false);
  const [carregou, setCarregou] = useState(false);
  // store
  const {
    workspace: { workspaceMemberIds, getWorkspaceMemberDetails },
  } = useMember();

  if (isOpen && !carregou) {
    setCarregou(true);
    service
      .fetchShares(slug, pageId)
      .then(setCompartilhamentos)
      .catch(() => setCompartilhamentos([]));
  }

  const fechar = () => {
    setCarregou(false);
    setPessoa("");
    setPapel(PAPEL_DA_PAGINA.LER);
    onClose();
  };

  const jaTem = new Set(compartilhamentos.map((c) => c.shared_with));
  const opcoes = (workspaceMemberIds ?? [])
    .filter((id) => !jaTem.has(id))
    .map((id) => {
      const membro = getWorkspaceMemberDetails(id);
      return { value: id, query: membro?.member?.display_name ?? "", content: membro?.member?.display_name ?? "" };
    })
    .filter((opcao) => !!opcao.query);

  const compartilhar = async () => {
    if (!pessoa) return;
    setSalvando(true);
    try {
      const nova = await service.createShare(slug, pageId, { shared_with: pessoa, role: papel });
      setCompartilhamentos((atuais) => [...atuais.filter((c) => c.shared_with !== pessoa), nova]);
      setPessoa("");
    } catch {
      setToast({ type: TOAST_TYPE.ERROR, title: t("toast.error"), message: t("my_tasks.pages.share_failed") });
    } finally {
      setSalvando(false);
    }
  };

  const remover = async (shareId: string) => {
    await service.removeShare(slug, pageId, shareId);
    setCompartilhamentos((atuais) => atuais.filter((c) => c.id !== shareId));
  };

  return (
    <ModalCore isOpen={isOpen} handleClose={fechar} position={EModalPosition.CENTER} width={EModalWidth.XL}>
      <div className="space-y-4 p-5">
        <h3 className="text-16 font-medium text-primary">{t("my_tasks.pages.share_title")}</h3>

        <div className="flex items-center gap-2">
          <div className="flex-grow">
            <CustomSearchSelect
              value={pessoa}
              onChange={(valor: string) => setPessoa(valor)}
              options={opcoes}
              label={
                pessoa
                  ? (getWorkspaceMemberDetails(pessoa)?.member?.display_name ?? t("my_tasks.pages.share_search"))
                  : t("my_tasks.pages.share_search")
              }
              maxHeight="md"
            />
          </div>
          <select
            value={papel}
            onChange={(e) => setPapel(Number(e.target.value))}
            className="rounded-sm border border-subtle bg-surface-1 px-2 py-1.5 text-13 text-primary"
          >
            <option value={PAPEL_DA_PAGINA.LER}>{t("my_tasks.pages.role_read")}</option>
            <option value={PAPEL_DA_PAGINA.EDITAR}>{t("my_tasks.pages.role_write")}</option>
          </select>
          <Button variant="primary" size="sm" onClick={compartilhar} loading={salvando} disabled={!pessoa}>
            {t("my_tasks.pages.share_add")}
          </Button>
        </div>

        <div className="space-y-2">
          {compartilhamentos.length === 0 ? (
            <p className="text-13 text-secondary">{t("my_tasks.pages.share_none")}</p>
          ) : (
            compartilhamentos.map((c) => (
              <div key={c.id} className="flex items-center justify-between gap-2 rounded-sm bg-layer-1 px-3 py-2">
                <span className="text-13 text-primary">
                  {c.shared_with_detail?.display_name ?? getWorkspaceMemberDetails(c.shared_with)?.member?.display_name}
                </span>
                <div className="flex items-center gap-3">
                  <span className="text-12 text-secondary">
                    {c.role === PAPEL_DA_PAGINA.EDITAR ? t("my_tasks.pages.role_write") : t("my_tasks.pages.role_read")}
                  </span>
                  <button
                    type="button"
                    aria-label={t("my_tasks.pages.share_remove")}
                    onClick={() => remover(c.id)}
                    className="text-tertiary hover:text-primary"
                  >
                    <X className="size-3.5" />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </ModalCore>
  );
});
