/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

export enum AI_EDITOR_TASKS {
  ASK_ANYTHING = "ASK_ANYTHING",
}

// Evolury: valores viraram chaves de i18n, resolvidas no componente consumidor
export const LOADING_TEXTS = {
  [AI_EDITOR_TASKS.ASK_ANYTHING]: "ui.ai_generating",
} satisfies { [key in AI_EDITOR_TASKS]: string };
