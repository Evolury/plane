/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: mudança de propriedade personalizada no histórico (ADR 0011).
//
// A linha sempre foi gravada — desde a v1.13.0 — e nunca foi desenhada: as
// telas de atividade despacham por campo conhecido, e o campo aqui é o NOME de
// uma propriedade do cliente, que nenhuma lista pode conter. O verbo
// `property_updated` é o que torna a linha reconhecível sem adivinhação.
//
// O rótulo vem de `field`, e não da definição atual: é o nome de quando a
// mudança aconteceu. Renomear a propriedade não reescreve a história.

import { observer } from "mobx-react";
import { Tag } from "lucide-react";
import { useTranslation } from "@plane/i18n";
// hooks
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
// components
import { IssueActivityBlockComponent, IssueLink } from "./";

type TIssuePropertyActivity = { activityId: string; showIssue?: boolean; ends: "top" | "bottom" | undefined };

export const IssuePropertyActivity = observer(function IssuePropertyActivity(props: TIssuePropertyActivity) {
  const { activityId, showIssue = true, ends } = props;
  const { t } = useTranslation();
  const {
    activity: { getActivityById },
  } = useIssueDetail();

  const activity = getActivityById(activityId);
  if (!activity) return <></>;

  const de = activity.old_value?.trim();
  const para = activity.new_value?.trim();

  return (
    <IssueActivityBlockComponent
      icon={<Tag className="h-3.5 w-3.5 text-secondary" aria-hidden="true" />}
      activityId={activityId}
      ends={ends}
    >
      <>
        {/* Três frases, e não uma com pedaços vazios: "alterou Canal de para
            Anúncio" é o que sai quando o campo estava em branco. */}
        {para ? (
          <>
            {de ? t("activity_log.property.changed") : t("activity_log.property.set")}
            <span className="font-medium text-primary">{activity.field}</span>
            {de ? (
              <>
                {t("activity_log.property.from")}
                <span className="font-medium text-primary">{de}</span>
              </>
            ) : null}
            {/* "definiu Canal COMO Indicação" e "alterou Canal DE … PARA …":
                em português o conector muda com o verbo, e reusar "para" nos
                dois fazia a primeira frase soar traduzida. */}
            {de ? t("activity_log.property.to") : t("activity_log.property.as")}
            <span className="font-medium text-primary">{para}</span>
          </>
        ) : (
          <>
            {t("activity_log.property.cleared")}
            <span className="font-medium text-primary">{activity.field}</span>
          </>
        )}
        {showIssue ? t("activity_log.prep_in") : ``}
        {showIssue && <IssueLink activityId={activityId} />}.
      </>
    </IssueActivityBlockComponent>
  );
});
