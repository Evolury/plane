/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { Outlet } from "react-router";
import { translate } from "@plane/i18n";
import type { Route } from "./+types/layout";

export default function InvitationsLayout() {
  return <Outlet />;
}

// Evolury: o título da aba do navegador também é texto de tela. Fora do
// React aqui, então `translate` e não o hook (ADR 0008).
export const meta: Route.MetaFunction = () => [{ title: translate("invitations") }];
