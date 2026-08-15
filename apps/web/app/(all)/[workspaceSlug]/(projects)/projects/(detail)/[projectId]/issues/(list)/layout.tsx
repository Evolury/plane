/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// components
import { Outlet } from "react-router";
import { AppHeader } from "@/components/core/app-header";
import { ContentWrapper } from "@/components/core/content-wrapper";
// Evolury: propriedades personalizadas (ADR 0011)
import { IssuePropertiesPrefetch } from "@/components/issue-properties/prefetch";
import { ProjectIssuesHeader } from "./header";
import { ProjectIssuesMobileHeader } from "./mobile-header";

export default function ProjectIssuesLayout() {
  return (
    <>
      {/* Evolury: carrega as definições antes de qualquer layout — sem elas o
          agrupamento por propriedade não teria colunas para desenhar. */}
      <IssuePropertiesPrefetch />
      <AppHeader header={<ProjectIssuesHeader />} mobileHeader={<ProjectIssuesMobileHeader />} />
      <ContentWrapper>
        <Outlet />
      </ContentWrapper>
    </>
  );
}
