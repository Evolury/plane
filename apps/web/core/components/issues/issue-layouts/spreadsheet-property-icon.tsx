/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: extraído de `utils.tsx`, que exportava um componente no meio de
// dezenas de funções — mistura que quebra o Fast Refresh do módulo inteiro.

import type { FC } from "react";
import type { ISvgIcons } from "@plane/propel/icons";
import {
  CycleIcon,
  DueDatePropertyIcon,
  EstimatePropertyIcon,
  LabelPropertyIcon,
  LinkIcon,
  MembersPropertyIcon,
  ModuleIcon,
  PriorityPropertyIcon,
  StartDatePropertyIcon,
  StatePropertyIcon,
} from "@plane/propel/icons";
import { CalendarDays, LayersIcon, Paperclip } from "lucide-react";

// Privado de propósito: só o componente abaixo o consulta, e exportar
// não-componente ao lado de componente quebra o Fast Refresh do módulo.
const SpreadSheetPropertyIconMap: Record<string, FC<ISvgIcons>> = {
  MembersPropertyIcon: MembersPropertyIcon,
  CalenderDays: CalendarDays,
  DueDatePropertyIcon: DueDatePropertyIcon,
  EstimatePropertyIcon: EstimatePropertyIcon,
  LabelPropertyIcon: LabelPropertyIcon,
  ModuleIcon: ModuleIcon,
  ContrastIcon: CycleIcon,
  PriorityPropertyIcon: PriorityPropertyIcon,
  StartDatePropertyIcon: StartDatePropertyIcon,
  StatePropertyIcon: StatePropertyIcon,
  Link2: LinkIcon,
  Paperclip: Paperclip,
  LayersIcon: LayersIcon,
};

export function SpreadSheetPropertyIcon(props: ISvgIcons & { iconKey: string }) {
  const { iconKey } = props;
  const Icon = SpreadSheetPropertyIconMap[iconKey];
  if (!Icon) return null;
  return <Icon {...props} />;
}
