/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { i18nInstance } from "./instance";

/**
 * Crash guard shared with `useTranslation`: i18next-icu unconditionally returns
 * raw objects when t() is called with a branch (namespace-node) key, regardless
 * of returnObjects:false. Strings pass through; numbers/booleans are stringified;
 * objects/null/undefined fall back to the key itself plus a dev-mode warning.
 */
export function coerceToString(key: string, value: unknown): string {
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  if (process.env.NODE_ENV !== "production") {
    // eslint-disable-next-line no-console
    console.warn(
      `[i18n] Translation for key "${key}" is not a string (got ${
        value === null ? "null" : typeof value
      }). This is likely a missing key or a namespace-node lookup. Returning the key as fallback.`
    );
  }
  return key;
}

/**
 * Translate outside of React.
 *
 * `useTranslation` is the right tool inside components — it re-renders them when
 * the language changes. This one reads the language at call time and does not
 * subscribe to anything, so use it only where a hook is impossible: MobX stores,
 * route metadata, and other module-level code.
 *
 * The value must be consumed immediately (a toast message, a document title).
 * Storing the result and rendering it later would freeze the string in whatever
 * language was active when it was computed.
 */
export function translate(key: string, params?: Record<string, unknown>): string {
  const value = params === undefined ? i18nInstance.t(key) : i18nInstance.t(key, params);
  return coerceToString(key, value);
}
