/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useCallback, useMemo, useState } from "react";
import { observer } from "mobx-react";
import { useParams, useRouter } from "next/navigation";
import { ArchiveRestoreIcon, FileInput, FileOutput, LockKeyhole, LockKeyholeOpen, Share2 } from "lucide-react";
// constants
import { EPageAccess } from "@plane/constants";
// plane editor
import { LinkIcon, CopyIcon, LockIcon, NewTabIcon, ArchiveIcon, TrashIcon, GlobeIcon } from "@plane/propel/icons";
// plane ui
import type { TContextMenuItem } from "@plane/ui";
import { ContextMenu, CustomMenu } from "@plane/ui";
// components
import { cn } from "@plane/utils";
import { useTranslation } from "@plane/i18n";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { PersonalPageService } from "@/services/page";
import { MovePageToProjectModal } from "@/components/my-tasks/move-page-modal";
import { SharePageModal } from "@/components/my-tasks/share-page-modal";
import { DeletePageModal } from "@/components/pages/modals/delete-page-modal";
// hooks
import { usePageOperations } from "@/hooks/use-page-operations";
// plane web hooks
import { EPageStoreType } from "@/hooks/store";
// store types
import type { TPageInstance } from "@/store/pages/base-page";

export type TPageActions =
  | "full-screen"
  | "sticky-toolbar"
  | "copy-markdown"
  | "toggle-lock"
  | "toggle-access"
  | "open-in-new-tab"
  | "copy-link"
  | "make-a-copy"
  | "archive-restore"
  | "delete"
  | "version-history"
  | "export"
  // Evolury: compartilhar e mover página pessoal (ADR 0015).
  | "share"
  | "move-to-project"
  | "move-to-personal";

type Props = {
  extraOptions?: (TContextMenuItem & { key: TPageActions })[];
  optionsOrder: TPageActions[];
  page: TPageInstance;
  parentRef?: React.RefObject<HTMLElement>;
  storeType: EPageStoreType;
};

const personalPageService = new PersonalPageService();

export const PageActions = observer(function PageActions(props: Props) {
  const { extraOptions, optionsOrder, page, parentRef, storeType } = props;
  // states
  const [deletePageModal, setDeletePageModal] = useState(false);
  const { t } = useTranslation();
  const [sharePageModal, setSharePageModal] = useState(false);
  const [moveToProjectModal, setMoveToProjectModal] = useState(false);
  // params
  const { workspaceSlug } = useParams();
  const router = useRouter();
  // page flag
  // page operations
  const { pageOperations } = usePageOperations({
    page,
  });
  // derived values
  const {
    access,
    archived_at,
    is_locked,
    canCurrentUserArchivePage,
    canCurrentUserChangeAccess,
    canCurrentUserDeletePage,
    canCurrentUserDuplicatePage,
    canCurrentUserLockPage,
    isCurrentUserOwner,
  } = page;
  // Evolury: o caminho de volta do ADR 0015. Fica aqui, e não no hook
  // compartilhado de operações, porque só existe para página de projeto do
  // próprio dono.
  const recolherParaOPessoal = useCallback(async () => {
    const projectId = page.project_ids?.[0];
    if (!workspaceSlug || !projectId || !page.id) return;
    try {
      await personalPageService.moveToPersonal(workspaceSlug.toString(), projectId, page.id);
      router.push(`/${workspaceSlug}/my-tasks/pages`);
    } catch {
      setToast({ type: TOAST_TYPE.ERROR, title: t("toast.error"), message: t("my_tasks.pages.move_failed") });
    }
  }, [page.project_ids, page.id, workspaceSlug, router, t]);

  // menu items
  const MENU_ITEMS = useMemo(
    function MENU_ITEMS() {
      const menuItems: (TContextMenuItem & { key: TPageActions })[] = [
        {
          key: "toggle-lock",
          action: () => {
            pageOperations.toggleLock();
          },
          title: is_locked ? t("unlock") : t("lock"),
          icon: is_locked ? LockKeyholeOpen : LockKeyhole,
          shouldRender: canCurrentUserLockPage,
        },
        {
          key: "toggle-access",
          action: () => {
            pageOperations.toggleAccess();
          },
          title:
            access === EPageAccess.PUBLIC
              ? t("power_k.contextual_actions.page.make_private")
              : t("power_k.contextual_actions.page.make_public"),
          icon: access === EPageAccess.PUBLIC ? LockIcon : GlobeIcon,
          shouldRender: canCurrentUserChangeAccess && !archived_at,
        },
        {
          key: "open-in-new-tab",
          action: pageOperations.openInNewTab,
          title: t("open_in_new_tab"),
          icon: NewTabIcon,
          shouldRender: true,
        },
        {
          key: "copy-link",
          action: pageOperations.copyLink,
          title: t("copy_link"),
          icon: LinkIcon,
          shouldRender: true,
        },
        {
          key: "make-a-copy",
          action: () => {
            pageOperations.duplicate();
          },
          title: t("make_a_copy"),
          icon: CopyIcon,
          shouldRender: canCurrentUserDuplicatePage,
        },
        {
          key: "archive-restore",
          action: () => {
            pageOperations.toggleArchive();
          },
          title: archived_at ? t("restore") : t("archive"),
          icon: archived_at ? ArchiveRestoreIcon : ArchiveIcon,
          shouldRender: canCurrentUserArchivePage,
        },
        {
          key: "delete",
          action: () => {
            setDeletePageModal(true);
          },
          title: t("delete"),
          icon: TrashIcon,
          shouldRender: canCurrentUserDeletePage && !!archived_at,
        },
        {
          key: "share",
          action: () => setSharePageModal(true),
          title: t("my_tasks.pages.share"),
          icon: Share2,
          // Só página pessoal, e só do dono: no projeto o acesso vem da
          // participação, e as duas fontes juntas fariam "quem pode ler isto?"
          // ter duas respostas.
          shouldRender: storeType === EPageStoreType.PERSONAL && isCurrentUserOwner && !archived_at,
        },
        {
          key: "move-to-project",
          action: () => setMoveToProjectModal(true),
          title: t("my_tasks.pages.move_to_project"),
          icon: FileOutput,
          shouldRender: storeType === EPageStoreType.PERSONAL && isCurrentUserOwner && !archived_at,
        },
        {
          key: "move-to-personal",
          action: () => {
            void recolherParaOPessoal();
          },
          title: t("my_tasks.pages.move_to_personal"),
          icon: FileInput,
          // O caminho de volta: só do projeto para o pessoal, e só do dono.
          shouldRender: storeType === EPageStoreType.PROJECT && isCurrentUserOwner && !archived_at,
        },
      ];
      if (extraOptions) {
        menuItems.push(...extraOptions);
      }
      return menuItems;
    },
    [
      extraOptions,
      is_locked,
      canCurrentUserLockPage,
      access,
      canCurrentUserChangeAccess,
      archived_at,
      canCurrentUserDuplicatePage,
      canCurrentUserArchivePage,
      canCurrentUserDeletePage,
      isCurrentUserOwner,
      storeType,
      t,
      recolherParaOPessoal,
      pageOperations,
    ]
  );
  // arrange options
  const arrangedOptions = useMemo<(TContextMenuItem & { key: TPageActions })[]>(
    () =>
      optionsOrder
        .map((key) => MENU_ITEMS.find((item) => item.key === key))
        .filter((item): item is TContextMenuItem & { key: TPageActions } => !!item),
    [optionsOrder, MENU_ITEMS]
  );

  return (
    <>
      <DeletePageModal
        isOpen={deletePageModal}
        onClose={() => setDeletePageModal(false)}
        page={page}
        storeType={storeType}
      />
      {page.id && (
        <>
          <SharePageModal isOpen={sharePageModal} onClose={() => setSharePageModal(false)} pageId={page.id} />
          <MovePageToProjectModal
            isOpen={moveToProjectModal}
            onClose={() => setMoveToProjectModal(false)}
            pageId={page.id}
            onMoved={() => router.push(`/${workspaceSlug}/my-tasks/pages`)}
          />
        </>
      )}
      {parentRef && <ContextMenu parentRef={parentRef} items={arrangedOptions} />}
      <CustomMenu placement="bottom-end" optionsClassName="max-h-[90vh]" ellipsis closeOnSelect>
        {arrangedOptions.map((item) => {
          if (item.shouldRender === false) return null;
          return (
            <CustomMenu.MenuItem
              key={item.key}
              onClick={() => {
                item.action?.();
              }}
              className={cn("flex items-center gap-2", item.className)}
              disabled={item.disabled}
            >
              {item.customContent ?? (
                <>
                  {item.icon && <item.icon className="size-3" />}
                  {item.title}
                </>
              )}
            </CustomMenu.MenuItem>
          );
        })}
      </CustomMenu>
    </>
  );
});
