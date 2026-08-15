/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: as propriedades personalizadas no modal de criação (ADR 0011, P2).
//
// Elas precisam estar aqui, e não só no painel, porque a obrigatória barra a
// CRIAÇÃO: sem os campos no modal, todo projeto que marcasse uma propriedade
// como obrigatória ficaria sem conseguir criar tarefa pela interface.
//
// Some inteiro quando o projeto não configurou nada.

import { useEffect } from "react";
import { observer } from "mobx-react";
import useSWR from "swr";
import { useTranslation } from "@plane/i18n";
import type { TIssueProperty, TPropertyValue } from "@plane/types";
// services
import { IssuePropertyService } from "@/services/issue-property.service";
// local imports
import { chaveDasDefinicoes } from "./store";
import { PropertyValueEditor } from "./value-editor";

const servico = new IssuePropertyService();

/** Os nomes das obrigatórias que ainda estão vazias — a mensagem do bloqueio. */
export const obrigatoriasFaltando = (
  propriedades: TIssueProperty[],
  valores: Record<string, TPropertyValue>
): string[] =>
  propriedades
    .filter((p) => p.is_required)
    .filter((p) => {
      const valor = valores[p.id];
      if (valor === null || valor === undefined) return true;
      if (Array.isArray(valor)) return valor.length === 0;
      return String(valor).trim() === "";
    })
    .map((p) => p.name);

type TProps = {
  workspaceSlug: string;
  projectId: string;
  valores: Record<string, TPropertyValue>;
  onChange: (valores: Record<string, TPropertyValue>) => void;
  /** Recebe as definições para quem monta poder validar antes de enviar. */
  onDefinitions?: (propriedades: TIssueProperty[]) => void;
};

export const IssuePropertiesCreateFields = observer(function IssuePropertiesCreateFields(props: TProps) {
  const { workspaceSlug, projectId, valores, onChange, onDefinitions } = props;
  const { t } = useTranslation();

  const { data } = useSWR(workspaceSlug && projectId ? chaveDasDefinicoes(workspaceSlug, projectId) : null, () =>
    servico.list(workspaceSlug, projectId)
  );

  // Só as ativas: desativada preserva valor e some dos formulários.
  const propriedades = (data?.properties ?? []).filter((p) => p.is_active);

  useEffect(() => {
    onDefinitions?.(propriedades);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data]);

  if (propriedades.length === 0) return null;

  return (
    <div className="space-y-2 border-t-[0.5px] border-subtle pt-3">
      <p className="text-12 text-tertiary">{t("issue_properties.settings.heading")}</p>
      {propriedades.map((propriedade) => (
        <div key={propriedade.id} className="flex items-start gap-2 text-12">
          <span className="w-1/3 min-w-0 shrink-0 truncate pt-1 text-tertiary">
            {propriedade.name}
            {propriedade.is_required && <span className="text-danger-primary"> *</span>}
          </span>
          <div className="min-w-0 flex-1">
            <PropertyValueEditor
              propriedade={propriedade}
              valor={valores[propriedade.id] ?? null}
              onChange={(valor) => onChange({ ...valores, [propriedade.id]: valor })}
            />
          </div>
        </div>
      ))}
    </div>
  );
});
