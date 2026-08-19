/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
// plane imports
import { useTranslation } from "@plane/i18n";
import type { TStateOperationsCallbacks } from "@plane/types";
import { cn } from "@plane/utils";

type TStateMarksAsDefault = {
  stateId: string;
  isDefault: boolean;
  markStateAsDefaultCallback: TStateOperationsCallbacks["markStateAsDefault"];
  /** Evolury: "padrão" no projeto, "entrada" em Minhas tarefas. */
  rotulos?: TStateOperationsCallbacks["rotulosDaEntrada"];
};

export const StateMarksAsDefault = observer(function StateMarksAsDefault(props: TStateMarksAsDefault) {
  const { stateId, isDefault, markStateAsDefaultCallback, rotulos } = props;
  // Evolury: os três rótulos estavam cravados em inglês
  const { t } = useTranslation();
  // states
  const [isLoading, setIsLoading] = useState(false);

  const handleMarkAsDefault = async () => {
    if (!stateId || isDefault) return;
    setIsLoading(true);

    try {
      setIsLoading(false);
      await markStateAsDefaultCallback(stateId);
      setIsLoading(false);
    } catch {
      setIsLoading(false);
    }
  };

  return (
    <button
      className={cn(
        "text-11 whitespace-nowrap transition-colors",
        isDefault ? "text-tertiary" : "text-secondary hover:text-primary"
      )}
      disabled={isDefault || isLoading}
      onClick={handleMarkAsDefault}
    >
      {isLoading
        ? (rotulos?.salvando ?? t("project_settings.states.default.marking"))
        : isDefault
          ? (rotulos?.atual ?? t("project_settings.states.default.label"))
          : (rotulos?.acao ?? t("project_settings.states.default.mark"))}
    </button>
  );
});
