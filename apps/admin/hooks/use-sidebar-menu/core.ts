/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { Image, BrainCog, Cog, CreditCard, Mail } from "lucide-react";
// plane imports
import { LockIcon, WorkspaceIcon } from "@plane/propel/icons";
// types
import type { TSidebarMenuItem } from "./types";
import { translate } from "@plane/i18n";

export type TCoreSidebarMenuKey =
  | "general"
  | "email"
  | "workspace"
  // Evolury: painel de assinaturas (ADR 0021)
  | "assinaturas"
  | "authentication"
  | "ai"
  | "image";

export const coreSidebarMenuLinks: Record<TCoreSidebarMenuKey, TSidebarMenuItem> = {
  general: {
    Icon: Cog,
    name: "General",
    description: translate("instance_admin.identify_your_instances_and_get_key_details"),
    href: `/general/`,
  },
  email: {
    Icon: Mail,
    name: "Email",
    description: translate("instance_admin.configure_your_smtp_controls"),
    href: `/email/`,
  },
  workspace: {
    Icon: WorkspaceIcon,
    name: "Workspaces",
    description: translate("instance_admin.manage_all_workspaces_on_this_instance"),
    href: `/workspace/`,
  },
  // Evolury: painel de assinaturas (ADR 0021). Fica ao lado de Workspaces
  // porque é a mesma lista vista pelo outro lado — o do contrato.
  assinaturas: {
    Icon: CreditCard,
    name: "Assinaturas",
    description: translate("instance_admin.assinaturas_descricao"),
    href: `/subscriptions/`,
  },
  authentication: {
    Icon: LockIcon,
    name: "Authentication",
    description: "Configure authentication modes.",
    href: `/authentication/`,
  },
  ai: {
    Icon: BrainCog,
    name: "Artificial intelligence",
    description: translate("instance_admin.configure_your_openai_creds"),
    href: `/ai/`,
  },
  image: {
    Icon: Image,
    name: "Images in Plane",
    description: "Allow third-party image libraries.",
    href: `/image/`,
  },
};
