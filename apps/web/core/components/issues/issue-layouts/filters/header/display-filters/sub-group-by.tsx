/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import React, { useState } from "react";
import { observer } from "mobx-react";
import { useParams } from "next/navigation";
import { useTranslation } from "@plane/i18n";
import type { IIssueDisplayFilterOptions, TIssueGroupByOptions } from "@plane/types";
// helpers
import { useGroupByOptions } from "../../../utils";
// components
import { FilterHeader, FilterOption } from "@/components/issues/issue-layouts/filters";

type Props = {
  displayFilters: IIssueDisplayFilterOptions;
  handleUpdate: (val: TIssueGroupByOptions) => void;
  subGroupByOptions: TIssueGroupByOptions[];
  ignoreGroupedFilters: Partial<TIssueGroupByOptions>[];
};

export const FilterSubGroupBy = observer(function FilterSubGroupBy(props: Props) {
  // hooks
  const { t } = useTranslation();

  const { displayFilters, handleUpdate, subGroupByOptions, ignoreGroupedFilters } = props;

  const [previewEnabled, setPreviewEnabled] = useState(true);

  const selectedGroupBy = displayFilters.group_by ?? null;
  const selectedSubGroupBy = displayFilters.sub_group_by ?? null;

  // Evolury: o projeto entra para o menu oferecer as propriedades dele — o
  // mesmo montador do "Agrupar por" (ADR 0011). O servidor já subagrupava por
  // propriedade desde o começo; só este menu não oferecia.
  const { projectId } = useParams();
  const options = useGroupByOptions(subGroupByOptions, projectId?.toString());

  return (
    <>
      <FilterHeader
        title={t("common.sub_group_by")}
        isPreviewEnabled={previewEnabled}
        handleIsPreviewEnabled={() => setPreviewEnabled(!previewEnabled)}
      />
      {previewEnabled && (
        <div>
          {options.map((subGroupBy) => {
            if (selectedGroupBy !== null && subGroupBy.key === selectedGroupBy) return null;
            if (ignoreGroupedFilters.includes(subGroupBy?.key)) return null;

            return (
              <FilterOption
                key={subGroupBy?.key}
                isChecked={selectedSubGroupBy === subGroupBy?.key ? true : false}
                onClick={() => handleUpdate(subGroupBy.key)}
                title={subGroupBy.title ?? t(subGroupBy.titleTranslationKey)}
                multiple={false}
              />
            );
          })}
        </div>
      )}
    </>
  );
});
