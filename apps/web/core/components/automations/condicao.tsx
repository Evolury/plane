/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: o cartão "SE" do editor (ADR 0012).
//
// Não há componente de condição próprio: o que está aqui é a LINHA DE FILTROS
// DO QUADRO, sem modificação. `FiltersRow` já recebe a instância por
// propriedade e não conhece o store do quadro, e `ProjectLevelWorkItemFiltersHOC`
// já monta a instância com estados, etiquetas, membros, ciclos, módulos e as
// propriedades personalizadas do projeto.
//
// O ganho não é economia de linhas — é que filtro e automação não podem
// divergir sobre o que "prioridade é urgente" quer dizer. Sendo o mesmo
// componente e a mesma árvore, não têm como.
//
// `isTemporary` é o que existia justamente para este caso: a instância vive só
// enquanto a tela está aberta e não é gravada como visão de ninguém.

import { observer } from "mobx-react";
import { CAMPOS_DA_CONDICAO } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { EIssuesStoreType } from "@plane/types";
import type { TWorkItemFilterExpression } from "@plane/types";
import { FiltersRow } from "@/components/rich-filters/filters-row";
import { ProjectLevelWorkItemFiltersHOC } from "@/components/work-item-filters/filters-hoc/project-level";

type TProps = {
  workspaceSlug: string;
  projectId: string;
  condicao: TWorkItemFilterExpression;
  onChange: (condicao: TWorkItemFilterExpression) => void;
};

export const CondicaoDaAutomacao = observer(function CondicaoDaAutomacao(props: TProps) {
  const { workspaceSlug, projectId, condicao, onChange } = props;
  const { t } = useTranslation();

  return (
    <div className="flex flex-col gap-2">
      <p className="text-12 text-tertiary">{t("automations.condition_hint")}</p>
      <ProjectLevelWorkItemFiltersHOC
        entityType={EIssuesStoreType.PROJECT}
        isTemporary
        filtersToShowByLayout={CAMPOS_DA_CONDICAO}
        initialWorkItemFilters={{
          richFilters: condicao,
          displayFilters: undefined,
          displayProperties: undefined,
          kanbanFilters: undefined,
        }}
        updateFilters={onChange}
        workspaceSlug={workspaceSlug}
        projectId={projectId}
      >
        {({ filter }) => (filter ? <FiltersRow filter={filter} variant="modal" /> : null)}
      </ProjectLevelWorkItemFiltersHOC>
    </div>
  );
});
