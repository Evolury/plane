/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// plane imports
import { useTranslation } from "@plane/i18n";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
// components
import { TimezoneSelect } from "@/components/global";
import { SettingsControlItem } from "@/components/settings/control-item";
// hooks
import { useUser } from "@/hooks/store/user";

export const ProfileSettingsLanguageAndTimezonePreferencesList = observer(
  function ProfileSettingsLanguageAndTimezonePreferencesList() {
    // store hooks
    const { data: user, updateCurrentUser } = useUser();
    // translation
    const { t } = useTranslation();

    const handleTimezoneChange = async (value: string) => {
      try {
        await updateCurrentUser({ user_timezone: value });
        setToast({
          title: t("toast.success"),
          message: t("toast.timezone_updated"),
          type: TOAST_TYPE.SUCCESS,
        });
      } catch (_error) {
        setToast({
          title: t("toast.error"),
          message: t("toast.timezone_update_failed"),
          type: TOAST_TYPE.ERROR,
        });
      }
    };

    // Evolury: idioma (ADR 0004) e início da semana (ADR 0005) saíram
    // daqui — são globais e fixos. Só o fuso horário segue configurável.
    return (
      <div className="flex flex-col gap-y-1">
        <SettingsControlItem
          title={t("timezone")}
          description={t("timezone_setting")}
          control={
            <TimezoneSelect value={user?.user_timezone || "America/Sao_Paulo"} onChange={handleTimezoneChange} />
          }
        />
      </div>
    );
  }
);
