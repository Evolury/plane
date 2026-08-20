/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: excluir as tarefas selecionadas (ADR 0018).
//
// O modal existia no código e ninguém o abria — nenhum botão, nenhum atalho. O
// que faltava não era o endpoint, era o gatilho e a conversa: quantas, o que
// vai junto, e como voltar atrás.
//
// **O desfazer é a peça central, e não um enfeite.** A exclusão aqui é suave: o
// servidor marca `deleted_at` e o expurgo definitivo só passa 60 dias depois. O
// dado sempre esteve lá; faltava a porta. Por isso o aviso de sucesso carrega
// "Desfazer" e fica na tela mais tempo que um aviso comum — uma saída que some
// antes de ser vista não é uma saída.

import { useState } from "react";
import { observer } from "mobx-react";
import { useParams } from "next/navigation";
import { Trash2 } from "lucide-react";
import { EUserPermissions, EUserPermissionsLevel } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import type { TIssue } from "@plane/types";
import { AlertModalCore } from "@plane/ui";
// hooks
import { useIssues } from "@/hooks/store/use-issues";
import { useMultipleSelectStore } from "@/hooks/store/use-multiple-select-store";
import { useUser, useUserPermissions } from "@/hooks/store/user";
import { useIssueStoreType } from "@/hooks/use-issue-layout-store";
import { useIssuesActions } from "@/hooks/use-issues-actions";
// local
import { TETO_DE_EXCLUSAO_EM_MASSA, agruparPorProjeto, passouDoTeto, separarElegiveis } from "./exclusao";
import { sabeOperarEmMassa } from "./loja";

type Props = {
  selecionadas: TIssue[];
};

/** Um lote é (projeto, instante) — é assim que o desfazer sabe o que devolver. */
type TLote = { projectId: string; batch: string };

/** O aviso com "Desfazer" fica mais tempo que os 5s de um aviso de leitura. */
const TEMPO_DO_DESFAZER = 12000;

export const BotaoDeExcluir = observer(function BotaoDeExcluir(props: Props) {
  const { selecionadas } = props;
  const { t } = useTranslation();
  const { workspaceSlug, viewId } = useParams();
  const storeType = useIssueStoreType();
  const { issues } = useIssues(storeType);
  const loja = sabeOperarEmMassa(issues) ? issues : undefined;
  const { fetchIssues } = useIssuesActions(storeType);
  const { clearSelection } = useMultipleSelectStore();
  const { allowPermissions } = useUserPermissions();
  const { data: usuario } = useUser();
  // states
  const [confirmando, setConfirmando] = useState(false);
  const [excluindo, setExcluindo] = useState(false);

  const { elegiveis, bloqueadas } = separarElegiveis(selecionadas, {
    usuarioId: usuario?.id,
    ehAdminEm: (projectId) =>
      allowPermissions(
        [EUserPermissions.ADMIN],
        EUserPermissionsLevel.PROJECT,
        workspaceSlug?.toString(),
        projectId ?? undefined
      ),
  });

  // A lista volta do servidor porque só ele sabe avaliar agrupamento, ordenação
  // e filtros ricos do quadro — os mesmos motivos que fazem o aviso de "criada"
  // do tempo real rebuscar em vez de acrescentar às cegas (ADR 0013).
  const recarregarLista = async () => {
    if (!loja?.paginationOptions) return;
    await fetchIssues("mutation", loja.paginationOptions, viewId?.toString());
  };

  const desfazer = async (lotes: TLote[]) => {
    try {
      const respostas = await Promise.all(
        lotes.map((lote) => loja!.restoreBulkIssues(workspaceSlug!.toString(), lote.projectId, lote.batch))
      );
      await recarregarLista();
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: t("toast.success"),
        message: t("issue.bulk_delete.undone", {
          count: respostas.reduce((total, resposta) => total + (resposta?.restored ?? 0), 0),
        }),
      });
    } catch {
      setToast({ type: TOAST_TYPE.ERROR, title: t("toast.error"), message: t("issue.bulk_delete.undo_error") });
    }
  };

  const excluir = async () => {
    const grupos = agruparPorProjeto(elegiveis);
    if (passouDoTeto(grupos)) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("toast.error"),
        message: t("issue.bulk_delete.too_many", { limit: TETO_DE_EXCLUSAO_EM_MASSA }),
      });
      setConfirmando(false);
      return;
    }

    setExcluindo(true);
    const lotes: TLote[] = [];
    let excluidas = 0;
    let falhou = false;

    // Um pedido por projeto, e um erro num projeto não cancela os outros: o que
    // já saiu, saiu, e o desfazer precisa saber de todos os lotes que existiram.
    for (const [projectId, ids] of Object.entries(grupos)) {
      try {
        const resposta = await loja!.removeBulkIssues(workspaceSlug!.toString(), projectId, ids);
        excluidas += resposta?.deleted ?? ids.length;
        if (resposta?.batch) lotes.push({ projectId, batch: resposta.batch });
      } catch {
        falhou = true;
      }
    }

    setExcluindo(false);
    setConfirmando(false);

    if (excluidas > 0) {
      clearSelection();
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: t("toast.success"),
        message: t("issue.bulk_delete.success", { count: excluidas }),
        timeout: TEMPO_DO_DESFAZER,
        actionItems: (
          <Button variant="link" size="sm" onClick={() => desfazer(lotes)}>
            {t("issue.bulk_delete.undo")}
          </Button>
        ),
      });
    }

    if (falhou) setToast({ type: TOAST_TYPE.ERROR, title: t("toast.error"), message: t("issue.bulk_delete.error") });
  };

  // Nada que esta pessoa possa excluir: o botão não aparece, em vez de aparecer
  // e recusar. O servidor recusa de qualquer jeito — a tela só não promete.
  if (!loja || elegiveis.length === 0) return null;

  return (
    <>
      <AlertModalCore
        isOpen={confirmando}
        handleClose={() => setConfirmando(false)}
        handleSubmit={excluir}
        isSubmitting={excluindo}
        variant="danger"
        title={t("issue.bulk_delete.title", { count: elegiveis.length })}
        content={
          <>
            {t("issue.bulk_delete.description")}
            {bloqueadas.length > 0 && (
              <span className="mt-2 block">{t("issue.bulk_delete.blocked", { count: bloqueadas.length })}</span>
            )}
          </>
        }
        primaryButtonText={{
          default: t("issue.bulk_delete.confirm", { count: elegiveis.length }),
          loading: t("deleting"),
        }}
        secondaryButtonText={t("cancel")}
      />
      <Button
        variant="error-fill"
        size="base"
        prependIcon={<Trash2 className="size-3.5" />}
        onClick={() => setConfirmando(true)}
        data-bulk-delete="open"
      >
        {t("issue.bulk_delete.button")}
      </Button>
    </>
  );
});
