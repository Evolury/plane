/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: preencher campos de muitas tarefas de uma vez (ADR 0019).
//
// **As mudanças ficam represadas até "Aplicar".** É o desenho da nuvem do Plane
// — "until you click this button, your changes won't be saved" — e é o que
// dispensa diálogo de confirmação: o próprio botão é o freio. Dropdown que
// aplica na hora, em cima de trinta tarefas, é irreversível por acidente.
//
// **Campo que a seleção não pode receber não aparece.** Estado, responsável,
// etiqueta e propriedade personalizada são do PROJETO; numa seleção que
// atravessa projetos, oferecê-los seria prometer o que o servidor recusa.
//
// **Campo com valores diferentes abre em "Vários", e não no valor da primeira.**
// Mostrar o da primeira é como se apaga o das outras sem perceber.

import { useMemo, useState } from "react";
import { observer } from "mobx-react";
import { useParams } from "next/navigation";
import { PencilLine } from "lucide-react";
import { Popover } from "@headlessui/react";
import { EUserPermissions, EUserPermissionsLevel } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { Button, getButtonStyling } from "@plane/propel/button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import type { TIssue, TIssuePriorities, TPropertyValue } from "@plane/types";
import { cn } from "@plane/utils";
// components
import { DateDropdown } from "@/components/dropdowns/date";
import { AssigneeDropdown } from "@/components/dropdowns/member/assignee";
import { PriorityDropdown } from "@/components/dropdowns/priority";
import { StateDropdown } from "@/components/dropdowns/state/dropdown";
import {
  revalidarValoresDoProjeto,
  usePropriedadesDoProjeto,
  useValoresDasTarefas,
} from "@/components/issue-properties/store";
import { PropertyValueEditor } from "@/components/issue-properties/value-editor";
import { IssueLabelSelect } from "@/components/issues/select/dropdown";
// hooks
import { useIssues } from "@/hooks/store/use-issues";
import { useMultipleSelectStore } from "@/hooks/store/use-multiple-select-store";
import { useUser, useUserPermissions } from "@/hooks/store/user";
import { useIssueStoreType } from "@/hooks/use-issue-layout-store";
import { useIssuesActions } from "@/hooks/use-issues-actions";
// services
import { IssuePropertyService } from "@/services/issue-property.service";
// local
import {
  MODOS_DE_LISTA,
  MODO_PADRAO,
  TETO_DE_EDICAO_EM_MASSA,
  agruparPorProjeto,
  datasDoRascunhoSaoCoerentes,
  projetoUnico,
  quantasMudancas,
  separarEditaveis,
  valorComum,
  type TModoDeLista,
  type TRascunho,
} from "./edicao";
import { sabeOperarEmMassa } from "./loja";

type Props = {
  selecionadas: TIssue[];
};

const servicoDePropriedades = new IssuePropertyService();

export const BotaoDeEditar = observer(function BotaoDeEditar(props: Props) {
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
  const [aberto, setAberto] = useState(false);
  const [rascunho, setRascunho] = useState<TRascunho>({});
  const [modos, setModos] = useState<Record<string, TModoDeLista>>({});
  const [valoresDeProp, setValoresDeProp] = useState<Record<string, TPropertyValue>>({});
  const [aplicando, setAplicando] = useState(false);

  const { editaveis, bloqueadas } = separarEditaveis(selecionadas, {
    usuarioId: usuario?.id,
    ehEditorEm: (projectId) =>
      allowPermissions(
        [EUserPermissions.ADMIN, EUserPermissions.MEMBER],
        EUserPermissionsLevel.PROJECT,
        workspaceSlug?.toString(),
        projectId ?? undefined
      ),
  });

  const projeto = projetoUnico(editaveis);
  const ids = useMemo(() => editaveis.map((tarefa) => tarefa.id), [editaveis]);

  // Propriedades personalizadas: definições e valores atuais, para o campo
  // abrir em "Vários" quando as tarefas discordam.
  const propriedades = usePropriedadesDoProjeto(workspaceSlug?.toString() ?? "", projeto ?? "");
  const valoresAtuais = useValoresDasTarefas(workspaceSlug?.toString() ?? "", projeto ?? "", projeto ? ids : []);

  const comum = <T,>(leitor: (tarefa: TIssue) => T) => valorComum(editaveis.map(leitor));

  const mudancas = quantasMudancas(rascunho, valoresDeProp);

  const limpar = () => {
    setRascunho({});
    setModos({});
    setValoresDeProp({});
  };

  const recarregarLista = async () => {
    if (!loja?.paginationOptions) return;
    await fetchIssues("mutation", loja.paginationOptions, viewId?.toString());
  };

  const aplicar = async () => {
    if (!datasDoRascunhoSaoCoerentes(rascunho)) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("toast.error"),
        message: t("bulk_operations.error_details.invalid_issue_start_date.message"),
      });
      return;
    }

    const grupos = agruparPorProjeto(editaveis);
    if (Object.values(grupos).some((lista) => lista.length > TETO_DE_EDICAO_EM_MASSA)) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("toast.error"),
        message: t("issue.bulk_edit.too_many", { limit: TETO_DE_EDICAO_EM_MASSA }),
      });
      return;
    }

    setAplicando(true);
    let falhou = false;

    for (const [projectId, lista] of Object.entries(grupos)) {
      try {
        if (Object.keys(rascunho).length > 0) {
          await loja!.bulkUpdateProperties(workspaceSlug!.toString(), projectId, {
            issue_ids: lista,
            properties: rascunho,
            modes: modos,
          });
        }
        // Propriedade personalizada é um pedido por propriedade: o endpoint
        // grava UM valor, e é ele que valida contra a definição.
        for (const [propertyId, valor] of Object.entries(valoresDeProp)) {
          await servicoDePropriedades.setValuesForIssues(workspaceSlug!.toString(), projectId, {
            issue_ids: lista,
            property: propertyId,
            value: valor,
          });
        }
      } catch {
        falhou = true;
      }
    }

    if (Object.keys(valoresDeProp).length > 0 && projeto) revalidarValoresDoProjeto(projeto);
    await recarregarLista();

    setAplicando(false);
    setAberto(false);
    limpar();

    if (!falhou) {
      clearSelection();
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: t("toast.success"),
        message: t("issue.bulk_edit.success", { count: editaveis.length }),
      });
    } else {
      setToast({ type: TOAST_TYPE.ERROR, title: t("toast.error"), message: t("issue.bulk_edit.error") });
    }
  };

  if (!loja || editaveis.length === 0) return null;

  const rotuloDoModo = (modo: TModoDeLista) => t(`issue.bulk_edit.modes.${modo}` as never);

  return (
    <Popover className="relative">
      <Popover.Button
        className={getButtonStyling("secondary", "base")}
        onClick={() => setAberto((antes) => !antes)}
        data-bulk-edit="open"
      >
        <PencilLine className="size-3.5" aria-hidden="true" />
        {t("issue.bulk_edit.button")}
      </Popover.Button>

      {aberto && (
        <Popover.Panel static className="absolute right-0 bottom-full z-20 mb-2 w-80 md:w-96">
          {/* Teto de altura com rolagem interna: um projeto com muitas
              propriedades personalizadas fazia o painel passar do alto da tela,
              e o botão "Aplicar" saía junto — o freio sumia da vista. */}
          <div className="vertical-scrollbar flex scrollbar-sm max-h-[70vh] flex-col gap-3 overflow-y-auto rounded-md border border-subtle bg-surface-1 p-4 shadow-raised-200">
            <p className="text-13 font-medium text-primary">
              {t("issue.bulk_edit.title", { count: editaveis.length })}
            </p>

            {bloqueadas.length > 0 && (
              <p className="text-11 text-secondary">{t("issue.bulk_edit.blocked", { count: bloqueadas.length })}</p>
            )}

            {!projeto && <p className="text-11 text-secondary">{t("issue.bulk_edit.cross_project")}</p>}

            <div className="flex flex-wrap items-center gap-2">
              {projeto && (
                <StateDropdown
                  projectId={projeto}
                  value={rascunho.state_id ?? comum((tarefa) => tarefa.state_id).valor ?? ""}
                  onChange={(state_id) => setRascunho((antes) => ({ ...antes, state_id }))}
                  buttonVariant="border-with-text"
                />
              )}

              <PriorityDropdown
                value={(rascunho.priority ?? comum((tarefa) => tarefa.priority).valor) as TIssuePriorities}
                onChange={(priority) => setRascunho((antes) => ({ ...antes, priority }))}
                buttonVariant="border-with-text"
              />

              {projeto && (
                <AssigneeDropdown
                  projectId={projeto}
                  value={rascunho.assignee_ids ?? comum((tarefa) => tarefa.assignee_ids).valor ?? []}
                  onChange={(assignee_ids) => setRascunho((antes) => ({ ...antes, assignee_ids }))}
                  buttonVariant="border-with-text"
                />
              )}

              <DateDropdown
                value={rascunho.start_date ?? null}
                onChange={(data) => setRascunho((antes) => ({ ...antes, start_date: data ? renderData(data) : null }))}
                placeholder={t("common.order_by.start_date")}
                buttonVariant="border-with-text"
              />

              <DateDropdown
                value={rascunho.target_date ?? null}
                onChange={(data) => setRascunho((antes) => ({ ...antes, target_date: data ? renderData(data) : null }))}
                placeholder={t("common.order_by.due_date")}
                buttonVariant="border-with-text"
              />
            </div>

            {projeto && (
              <div className="flex flex-col gap-2">
                <div className="flex items-center gap-2">
                  <IssueLabelSelect
                    projectId={projeto}
                    value={rascunho.label_ids ?? []}
                    onChange={(label_ids) => setRascunho((antes) => ({ ...antes, label_ids }))}
                  />
                  {/* O modo fica ao lado do campo, e não escondido: é ele que
                      decide se a etiqueta soma ou apaga o que já estava. */}
                  <div className="flex overflow-hidden rounded border border-subtle">
                    {MODOS_DE_LISTA.map((modo) => (
                      <button
                        key={modo}
                        type="button"
                        onClick={() => setModos((antes) => ({ ...antes, label_ids: modo }))}
                        className={cn("px-2 py-1 text-11 text-secondary hover:bg-layer-2", {
                          "bg-layer-3 font-medium text-primary": (modos.label_ids ?? MODO_PADRAO) === modo,
                        })}
                      >
                        {rotuloDoModo(modo)}
                      </button>
                    ))}
                  </div>
                </div>

                {propriedades.map((propriedade) => {
                  const atuais = ids.map((id) => valoresAtuais[id]?.[propriedade.id]);
                  const { misto } = valorComum(atuais);
                  return (
                    <div key={propriedade.id} className="flex items-center gap-2">
                      <span className="w-28 flex-shrink-0 truncate text-11 text-secondary">{propriedade.name}</span>
                      <div className="flex flex-1 items-center gap-2">
                        <PropertyValueEditor
                          propriedade={propriedade}
                          valor={valoresDeProp[propriedade.id] ?? (misto ? null : (atuais[0] ?? null))}
                          onChange={(valor) => setValoresDeProp((antes) => ({ ...antes, [propriedade.id]: valor }))}
                        />
                        {/* O editor não tem placeholder próprio: o aviso de
                            "Vários" fica ao lado, e some assim que a pessoa
                            escolhe — a partir daí o valor É o mesmo para todas. */}
                        {misto && valoresDeProp[propriedade.id] === undefined && (
                          <span className="flex-shrink-0 text-11 text-placeholder">{t("issue.bulk_edit.mixed")}</span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            <div className="flex items-center justify-end gap-2 pt-1">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setAberto(false);
                  limpar();
                }}
                disabled={aplicando}
              >
                {t("cancel")}
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={aplicar}
                disabled={mudancas === 0}
                loading={aplicando}
                data-bulk-edit="apply"
              >
                {/* Sem mudança nenhuma o botão diz só "Aplicar": em pt-BR o
                    plural do zero é o singular, e "Aplicar 0 mudança" é uma
                    frase que ninguém escreveria. */}
                {mudancas === 0 ? t("issue.bulk_edit.apply_none") : t("issue.bulk_edit.apply", { count: mudancas })}
              </Button>
            </div>
          </div>
        </Popover.Panel>
      )}
    </Popover>
  );
});

/** `Date` → `YYYY-MM-DD`, que é o formato que a API guarda. */
const renderData = (data: Date) =>
  `${data.getFullYear()}-${String(data.getMonth() + 1).padStart(2, "0")}-${String(data.getDate()).padStart(2, "0")}`;
