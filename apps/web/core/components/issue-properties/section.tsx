/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: as propriedades personalizadas no painel da tarefa (ADR 0011, P2).
//
// Salva a cada mudança, sem botão. É o comportamento do resto do painel —
// prioridade, responsável e etapa também salvam no clique —, e um "salvar" só
// aqui criaria a dúvida de quem edita: *este* campo eu preciso confirmar?
//
// Some inteira quando o projeto não configurou nada, para não deixar um título
// vazio no painel de todo projeto que não usa o recurso.

import { useState } from "react";
import { observer } from "mobx-react";
import useSWR from "swr";
import { useTranslation } from "@plane/i18n";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import type { TIssueProperty, TPropertyValue } from "@plane/types";
// services
import { IssuePropertyService } from "@/services/issue-property.service";
// local imports
// Evolury: ícone da propriedade (ADR 0011)
import { iconeDaPropriedade } from "./icones";
import { PropertyValueEditor } from "./value-editor";

const servico = new IssuePropertyService();

export const chaveDosValores = (issueId: string) => `ISSUE_PROPERTY_VALUES_${issueId}`;

type TProps = {
  workspaceSlug: string;
  projectId: string;
  issueId: string;
  disabled?: boolean;
};

export const IssuePropertiesSection = observer(function IssuePropertiesSection(props: TProps) {
  const { workspaceSlug, projectId, issueId, disabled } = props;
  const { t } = useTranslation();
  // O que o clique prometeu, até o servidor confirmar — é o que faz o campo
  // responder na hora em vez de esperar a ida e volta.
  const [emVoo, setEmVoo] = useState<Record<string, TPropertyValue>>({});

  const { data, mutate } = useSWR(workspaceSlug && projectId && issueId ? chaveDosValores(issueId) : null, () =>
    servico.valuesForIssue(workspaceSlug, projectId, issueId)
  );

  const propriedades = data?.properties ?? [];
  if (propriedades.length === 0) return null;

  const valorDe = (propriedadeId: string): TPropertyValue =>
    propriedadeId in emVoo ? emVoo[propriedadeId] : (data?.values?.[propriedadeId] ?? null);

  const gravar = async (propriedadeId: string, valor: TPropertyValue) => {
    setEmVoo((atual) => ({ ...atual, [propriedadeId]: valor }));
    try {
      await servico.setValue(workspaceSlug, projectId, issueId, propriedadeId, valor);
      await mutate();
    } catch (erro) {
      const mensagem = (erro as Record<string, string>)?.value ?? t("common.something_went_wrong");
      setToast({ type: TOAST_TYPE.ERROR, title: t("toast.error"), message: String(mensagem) });
      await mutate();
      // Repropaga para o editor devolver o último valor salvo: recusa que
      // apaga o campo faz a pessoa perder o número novo E o antigo.
      throw erro;
    } finally {
      setEmVoo((atual) => {
        const { [propriedadeId]: _, ...resto } = atual;
        return resto;
      });
    }
  };

  return (
    <div className="py-2">
      <p className="mb-2 text-13 text-secondary">{t("issue_properties.settings.heading")}</p>
      <div className="space-y-2">
        {propriedades.map((propriedade: TIssueProperty) => (
          <div key={propriedade.id} className="flex items-start gap-2 text-12">
            <span className="flex w-1/3 min-w-0 shrink-0 items-center gap-1.5 truncate pt-1 text-tertiary">
              {/* Evolury: o ícone do campo (ADR 0011) */}
              {(() => {
                const Icone = iconeDaPropriedade(propriedade);
                return <Icone className="size-3.5 shrink-0" />;
              })()}
              <span className="truncate">{propriedade.name}</span>
              {propriedade.is_required && <span className="text-danger-primary"> *</span>}
            </span>
            <div className="min-w-0 flex-1">
              <PropertyValueEditor
                propriedade={propriedade}
                valor={valorDe(propriedade.id)}
                disabled={disabled}
                onChange={(valor) => gravar(propriedade.id, valor)}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
});
