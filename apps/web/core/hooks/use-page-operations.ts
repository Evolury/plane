/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useMemo } from "react";
// plane imports
import { IS_FAVORITE_MENU_OPEN } from "@plane/constants";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { EPageAccess } from "@plane/types";
import { copyUrlToClipboard } from "@plane/utils";
import { useTranslation } from "@plane/i18n";
// hooks
import { useCollaborativePageActions } from "@/hooks/use-collaborative-page-actions";
// store types
import type { TPageInstance } from "@/store/pages/base-page";
// local storage
import useLocalStorage from "./use-local-storage";

export type TPageOperations = {
  toggleLock: () => void;
  toggleAccess: () => void;
  toggleFavorite: () => void;
  openInNewTab: () => void;
  copyLink: () => void;
  duplicate: () => void;
  toggleArchive: () => void;
};

type Props = {
  page: TPageInstance;
};

export const usePageOperations = (
  props: Props
): {
  pageOperations: TPageOperations;
} => {
  const { page } = props;
  // derived values
  const {
    access,
    addToFavorites,
    archived_at,
    duplicate,
    is_favorite,
    is_locked,
    getRedirectionLink,
    removePageFromFavorites,
  } = page;
  // collaborative actions
  const { executeCollaborativeAction } = useCollaborativePageActions(props);
  const { t } = useTranslation();
  // local storage
  const { setValue: toggleFavoriteMenu, storedValue: isFavoriteMenuOpen } = useLocalStorage<boolean>(
    IS_FAVORITE_MENU_OPEN,
    false
  );
  // page operations
  const pageOperations: TPageOperations = useMemo(() => {
    const pageLink = getRedirectionLink();

    return {
      copyLink: async () => {
        await copyUrlToClipboard(pageLink);
        setToast({
          type: TOAST_TYPE.SUCCESS,
          title: "Link Copied!",
          message: t("toast.page_link_copied"),
        });
      },
      duplicate: async () => {
        try {
          await duplicate();
          setToast({
            type: TOAST_TYPE.SUCCESS,
            title: t("toast.success"),
            message: t("toast.page_duplicated"),
          });
        } catch (_error) {
          setToast({
            type: TOAST_TYPE.ERROR,
            title: t("toast.error"),
            message: t("toast.page_duplicate_failed"),
          });
        }
      },
      move: async () => {},
      openInNewTab: () => window.open(pageLink, "_blank"),
      toggleAccess: async () => {
        const changedPageType = access === EPageAccess.PUBLIC ? "private" : "public";
        try {
          if (access === EPageAccess.PUBLIC)
            await executeCollaborativeAction({ type: "sendMessageToServer", message: "make-private" });
          else await executeCollaborativeAction({ type: "sendMessageToServer", message: "make-public" });
          setToast({
            type: TOAST_TYPE.SUCCESS,
            title: t("toast.success"),
            message: `The page has been marked ${changedPageType} and moved to the ${changedPageType} section.`,
          });
        } catch (_error) {
          setToast({
            type: TOAST_TYPE.ERROR,
            title: t("toast.error"),
            message: `The page couldn't be marked ${changedPageType}. Please try again.`,
          });
        }
      },
      toggleArchive: async () => {
        if (archived_at) {
          try {
            await executeCollaborativeAction({ type: "sendMessageToServer", message: "unarchive" });
            setToast({
              type: TOAST_TYPE.SUCCESS,
              title: t("toast.success"),
              message: t("toast.page_restored"),
            });
          } catch (_error) {
            setToast({
              type: TOAST_TYPE.ERROR,
              title: t("toast.error"),
              message: t("toast.page_restore_failed"),
            });
          }
        } else {
          try {
            await executeCollaborativeAction({ type: "sendMessageToServer", message: "archive" });
            setToast({
              type: TOAST_TYPE.SUCCESS,
              title: t("toast.success"),
              message: t("toast.page_archived"),
            });
          } catch (_error) {
            setToast({
              type: TOAST_TYPE.ERROR,
              title: t("toast.error"),
              message: t("toast.page_archive_failed"),
            });
          }
        }
      },
      toggleFavorite: async () => {
        if (is_favorite) {
          try {
            await removePageFromFavorites();
            setToast({
              type: TOAST_TYPE.SUCCESS,
              title: t("toast.success"),
              message: t("toast.page_unfavorited"),
            });
          } catch (_error) {
            setToast({
              type: TOAST_TYPE.ERROR,
              title: t("toast.error"),
              message: t("toast.page_unfavorite_failed"),
            });
          }
        } else {
          try {
            await addToFavorites();
            if (!isFavoriteMenuOpen) toggleFavoriteMenu(true);
            setToast({
              type: TOAST_TYPE.SUCCESS,
              title: t("toast.success"),
              message: t("toast.page_favorited"),
            });
          } catch (_error) {
            setToast({
              type: TOAST_TYPE.ERROR,
              title: t("toast.error"),
              message: t("toast.page_favorite_failed"),
            });
          }
        }
      },
      toggleLock: async () => {
        if (is_locked) {
          try {
            await executeCollaborativeAction({ type: "sendMessageToServer", message: "unlock" });
            setToast({
              type: TOAST_TYPE.SUCCESS,
              title: t("toast.success"),
              message: t("toast.page_unlocked"),
            });
          } catch (_error) {
            setToast({
              type: TOAST_TYPE.ERROR,
              title: t("toast.error"),
              message: t("toast.page_unlock_failed"),
            });
          }
        } else {
          try {
            await executeCollaborativeAction({ type: "sendMessageToServer", message: "lock" });
            setToast({
              type: TOAST_TYPE.SUCCESS,
              title: t("toast.success"),
              message: t("toast.page_locked"),
            });
          } catch (_error) {
            setToast({
              type: TOAST_TYPE.ERROR,
              title: t("toast.error"),
              message: t("toast.page_lock_failed"),
            });
          }
        }
      },
    };
  }, [
    access,
    addToFavorites,
    archived_at,
    duplicate,
    executeCollaborativeAction,
    getRedirectionLink,
    is_favorite,
    is_locked,
    isFavoriteMenuOpen,
    removePageFromFavorites,
    toggleFavoriteMenu,
  ]);
  return {
    pageOperations,
  };
};
