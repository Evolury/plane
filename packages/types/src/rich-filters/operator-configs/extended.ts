/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { TFilterValue } from "../expression";
// Evolury: campos de digitar (ADR 0011)
import type { TNumberFilterFieldConfig, TTextFilterFieldConfig } from "../field-types";

// ----------------------------- EXACT Operator -----------------------------
export type TExtendedExactOperatorConfigs =
  | TTextFilterFieldConfig<TFilterValue>
  | TNumberFilterFieldConfig<TFilterValue>;

// ----------------------------- IN Operator -----------------------------
export type TExtendedInOperatorConfigs = never;

// ----------------------------- RANGE Operator -----------------------------
export type TExtendedRangeOperatorConfigs = TNumberFilterFieldConfig<TFilterValue>;

// ----------------------------- Extended Operator Specific Configs -----------------------------
export type TExtendedOperatorSpecificConfigs = unknown;
