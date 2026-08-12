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
import { StartOfWeekPreference } from "@/components/profile/start-of-week-preference";
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

    // Evolury: a seleção de idioma saiu daqui — o produto é pt-BR único
    // (ADR 0004). Fuso horário e início da semana continuam configuráveis.
    return (
      <div className="flex flex-col gap-y-1">
        <SettingsControlItem
          title={t("timezone")}
          description={t("timezone_setting")}
          control={<TimezoneSelect value={user?.user_timezone || "Asia/Kolkata"} onChange={handleTimezoneChange} />}
        />
        <StartOfWeekPreference
          option={{
            title: t("ui.first_day_of_week"),
            description: t("ui.calendar_appearance_note"),
          }}
        />
      </div>
    );
  }
);
