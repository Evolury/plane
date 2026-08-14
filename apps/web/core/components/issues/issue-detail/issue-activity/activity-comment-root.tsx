/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: comentários e atividades deixaram de ser um fluxo único.
//
// Misturados, o histórico automático — mudou estado, trocou responsável —
// afogava a conversa, que é a parte que as pessoas escrevem e leem. Agora são
// duas listas: comentários primeiro, atividade depois e recortada.

import { useState } from "react";
import { observer } from "mobx-react";
// plane imports
import type { E_SORT_ORDER, TActivityFilters, EActivityFilterType } from "@plane/constants";
import { BASE_ACTIVITY_FILTER_TYPES, filterActivityOnSelectedFilters } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import type { TCommentsOperations } from "@plane/types";
// components
import { CommentCard } from "@/components/comments/card/root";
// hooks
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
// local imports
import { IssueActivityItem } from "./activity/activity-list";
import { IssueActivityLoader } from "./loader";

/** Quantas linhas de atividade aparecem antes do "Carregar mais". */
export const ATIVIDADES_POR_PAGINA = 10;

/** Quantos comentários aparecem antes do "Carregar mais".
 *
 * Menor que o das atividades de propósito: comentário é um cartão com autor,
 * texto e ações — ocupa várias vezes a altura de uma linha de "mudou o
 * estado". Cinco cobre a conversa recente sem empurrar a caixa de escrita
 * para fora da tela.
 */
export const COMENTARIOS_POR_PAGINA = 5;

type TIssueCommentsList = {
  workspaceSlug: string;
  projectId: string;
  isIntakeIssue: boolean;
  issueId: string;
  activityOperations: TCommentsOperations;
  showAccessSpecifier?: boolean;
  disabled?: boolean;
  sortOrder: E_SORT_ORDER;
};

export const IssueCommentsList = observer(function IssueCommentsList(props: TIssueCommentsList) {
  const {
    workspaceSlug,
    isIntakeIssue,
    issueId,
    activityOperations,
    showAccessSpecifier,
    projectId,
    disabled,
    sortOrder,
  } = props;
  const { t } = useTranslation();
  // states
  const [visiveis, setVisiveis] = useState(COMENTARIOS_POR_PAGINA);
  // store hooks
  const {
    activity: { getActivityAndCommentsByIssueId },
    comment: { getCommentById },
  } = useIssueDetail();
  // derived values
  const activityAndComments = getActivityAndCommentsByIssueId(issueId, sortOrder);

  if (!activityAndComments) return null;

  const comentarios = activityAndComments.filter((item) => item.activity_type === "COMMENT");
  if (comentarios.length <= 0) return null;

  // Mesma regra da atividade: o recorte guarda os mais RECENTES, e o botão de
  // revelar fica ACIMA deles — é de onde a conversa continua para trás.
  const escondidos = Math.max(0, comentarios.length - visiveis);
  const recortados = sortOrder === "asc" ? comentarios.slice(escondidos) : comentarios.slice(0, visiveis);

  return (
    <div>
      {escondidos > 0 && (
        <button
          type="button"
          onClick={() => setVisiveis((atual) => atual + COMENTARIOS_POR_PAGINA)}
          className="mb-2 text-12 text-secondary underline-offset-2 hover:text-primary hover:underline"
        >
          {t("common.load_more")} ({escondidos})
        </button>
      )}
      {recortados.map((activityComment, index) => (
        <CommentCard
          key={activityComment.id}
          workspaceSlug={workspaceSlug}
          entityId={issueId}
          comment={getCommentById(activityComment.id)}
          activityOperations={activityOperations}
          ends={index === 0 ? "top" : index === recortados.length - 1 ? "bottom" : undefined}
          showAccessSpecifier={!!showAccessSpecifier}
          showCopyLinkOption={!isIntakeIssue}
          disabled={disabled}
          projectId={projectId}
          enableReplies
        />
      ))}
    </div>
  );
});

type TIssueActivityList = {
  issueId: string;
  selectedFilters: TActivityFilters[];
  sortOrder: E_SORT_ORDER;
};

export const IssueActivityList = observer(function IssueActivityList(props: TIssueActivityList) {
  const { issueId, selectedFilters, sortOrder } = props;
  const { t } = useTranslation();
  // states
  const [visiveis, setVisiveis] = useState(ATIVIDADES_POR_PAGINA);
  // store hooks
  const {
    activity: { getActivityAndCommentsByIssueId },
  } = useIssueDetail();
  // derived values
  const activityAndComments = getActivityAndCommentsByIssueId(issueId, sortOrder);

  if (!activityAndComments) return <IssueActivityLoader />;

  const atividades = filterActivityOnSelectedFilters(activityAndComments, selectedFilters).filter((item) =>
    BASE_ACTIVITY_FILTER_TYPES.includes(item.activity_type as EActivityFilterType)
  );
  if (atividades.length <= 0) return null;

  // O recorte guarda sempre as mais RECENTES, independentemente da ordenação
  // escolhida: com as antigas primeiro, cortar o começo esconderia o que
  // acabou de acontecer, que é o oposto do que se quer ver de relance.
  const escondidas = Math.max(0, atividades.length - visiveis);
  const recortadas = sortOrder === "asc" ? atividades.slice(escondidas) : atividades.slice(0, visiveis);

  return (
    <div>
      {escondidas > 0 && (
        <button
          type="button"
          onClick={() => setVisiveis((atual) => atual + ATIVIDADES_POR_PAGINA)}
          className="mb-2 text-12 text-secondary underline-offset-2 hover:text-primary hover:underline"
        >
          {t("common.load_more")} ({escondidas})
        </button>
      )}
      {recortadas.map((activityComment, index) => (
        <IssueActivityItem
          key={activityComment.id}
          activityId={activityComment.id}
          ends={index === 0 ? "top" : index === recortadas.length - 1 ? "bottom" : undefined}
        />
      ))}
    </div>
  );
});
