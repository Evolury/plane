/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect, useMemo } from "react";
import { observer } from "mobx-react";
import { v4 as uuidv4 } from "uuid";
// plane imports
import type { TSaveViewOptions, TUpdateViewOptions } from "@plane/constants";
import type { IWorkItemFilterInstance } from "@plane/shared-state";
import type { IIssueFilters, TWorkItemFilterExpression } from "@plane/types";
// store hooks
import { useWorkItemFilters } from "@/hooks/store/work-item-filters/use-work-item-filters";
// plane web imports
import type { TWorkItemFiltersEntityProps } from "@/hooks/work-item-filters/use-work-item-filters-config";
import { useWorkItemFiltersConfig } from "@/hooks/work-item-filters/use-work-item-filters-config";
// local imports
import type { TSharedWorkItemFiltersHOCProps, TSharedWorkItemFiltersProps } from "./shared";

type TAdditionalWorkItemFiltersProps = {
  saveViewOptions?: TSaveViewOptions<TWorkItemFilterExpression>;
  updateViewOptions?: TUpdateViewOptions<TWorkItemFilterExpression>;
} & TWorkItemFiltersEntityProps;

type TWorkItemFiltersHOCProps = TSharedWorkItemFiltersHOCProps & TAdditionalWorkItemFiltersProps;

export const WorkItemFiltersHOC = observer(function WorkItemFiltersHOC(props: TWorkItemFiltersHOCProps) {
  const { children, initialWorkItemFilters } = props;

  // Only initialize filter instance when initial work item filters are defined
  if (!initialWorkItemFilters)
    return <>{typeof children === "function" ? children({ filter: undefined }) : children}</>;

  return (
    <WorkItemFilterRoot {...props} initialWorkItemFilters={initialWorkItemFilters}>
      {children}
    </WorkItemFilterRoot>
  );
});

type TWorkItemFilterProps = TSharedWorkItemFiltersProps &
  TAdditionalWorkItemFiltersProps & {
    initialWorkItemFilters: IIssueFilters;
    children: React.ReactNode | ((props: { filter: IWorkItemFilterInstance }) => React.ReactNode);
  };

const WorkItemFilterRoot = observer(function WorkItemFilterRoot(props: TWorkItemFilterProps) {
  const {
    children,
    entityType,
    entityId,
    filtersToShowByLayout,
    initialWorkItemFilters,
    isTemporary,
    saveViewOptions,
    updateFilters,
    updateViewOptions,
    showOnMount,
    ...entityConfigProps
  } = props;
  // store hooks
  const { getFilter, getOrCreateFilter, deleteFilter } = useWorkItemFilters();
  // derived values
  const workItemEntityID = useMemo(
    () => (isTemporary ? `TEMP-${entityId ?? uuidv4()}` : entityId),
    [isTemporary, entityId]
  );
  // memoize initial values to prevent re-computations when reference changes
  const initialUserFilters = useMemo(() => initialWorkItemFilters.richFilters, [initialWorkItemFilters]);
  const workItemFiltersConfig = useWorkItemFiltersConfig({
    allowedFilters: filtersToShowByLayout ? filtersToShowByLayout : [],
    ...entityConfigProps,
  });
  // Evolury: os parâmetros num lugar só — a instância precisa ser pedida em
  // dois momentos (na renderização e ao montar), e divergir entre eles daria
  // duas instâncias com configurações diferentes.
  const parametrosDoFiltro = useMemo(
    () => ({
      entityType,
      entityId: workItemEntityID,
      initialExpression: initialUserFilters,
      onExpressionChange: updateFilters,
      expressionOptions: { saveViewOptions, updateViewOptions },
      showOnMount,
    }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [entityType, workItemEntityID, saveViewOptions, updateViewOptions, updateFilters]
  );

  // get or create filter instance
  const filtroInicial = useMemo(
    () => getOrCreateFilter(parametrosDoFiltro),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [parametrosDoFiltro]
  );

  // Evolury: a instância VIVA, lida do store a cada renderização.
  //
  // Sem isto, o seletor de filtros não abria em desenvolvimento. O `StrictMode`
  // monta, desmonta e remonta o MESMO fiber: o `cleanup` abaixo apagava a
  // instância, e o `useMemo` — que já rodou naquele fiber — não a recriava. O
  // que sobrava era uma referência órfã, e o botão só registrava
  // "filter instance not available".
  //
  // A dupla resolve o ciclo inteiro: o efeito recria ao (re)montar, e a leitura
  // do store entrega sempre a que está viva, e não a que foi memorizada.
  const workItemLayoutFilter = getFilter(entityType, workItemEntityID) ?? filtroInicial;

  useEffect(() => {
    // Recria quando o `cleanup` de uma montagem anterior a apagou. É idempotente:
    // se ainda existir, o store devolve a mesma e só atualiza os callbacks.
    getOrCreateFilter(parametrosDoFiltro);
    return () => {
      deleteFilter(entityType, workItemEntityID);
    };
  }, [getOrCreateFilter, deleteFilter, parametrosDoFiltro, entityType, workItemEntityID]);

  useEffect(() => {
    workItemLayoutFilter.configManager.setAreConfigsReady(workItemFiltersConfig.areAllConfigsInitialized);
    workItemLayoutFilter.configManager.registerAll(workItemFiltersConfig.configs);
  }, [
    workItemFiltersConfig.areAllConfigsInitialized,
    workItemFiltersConfig.configs,
    workItemLayoutFilter.configManager,
  ]);

  return <>{typeof children === "function" ? children({ filter: workItemLayoutFilter }) : children}</>;
});
