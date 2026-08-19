/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { AppError } from "@/lib/errors";
import { PageService } from "./extended.service";

interface PersonalPageServiceParams {
  workspaceSlug: string | null;
  cookie: string | null;
  [key: string]: unknown;
}

/**
 * Evolury: página pessoal de "Minhas tarefas" (ADR 0015).
 *
 * Só muda o caminho base — não há projeto na rota porque não há projeto. Quem
 * decide se a pessoa pode abrir o documento continua sendo a API: este serviço
 * repassa o cookie, e quem não é dono toma 404.
 */
export class PersonalPageService extends PageService {
  protected basePath: string;

  constructor(params: PersonalPageServiceParams) {
    super();
    const { workspaceSlug } = params;
    if (!workspaceSlug) throw new AppError("Missing required fields.");
    if (!params.cookie) throw new AppError("Cookie is required.");
    this.setHeader("Cookie", params.cookie);
    this.basePath = `/api/workspaces/${workspaceSlug}/my-tasks`;
  }
}
