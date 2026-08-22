/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { EFileAssetType } from "./enums";

export type TFileMetaDataLite = {
  name: string;
  // file size in bytes
  size: number;
  type: string;
};

export type TFileEntityInfo = {
  entity_identifier: string;
  entity_type: EFileAssetType;
};

export type TFileMetaData = TFileMetaDataLite & TFileEntityInfo;

export type TFileSignedURLResponse = {
  asset_id: string;
  asset_url: string;
  /**
   * Envio direto ao armazenamento, com PUT assinado.
   *
   * Era POST assinado (com `fields` de política) até 22/08/2026. O Cloudflare
   * R2 não implementa POST assinado — devolve 501 — e nenhum upload funcionava.
   * PUT funciona no R2 e no S3, então é um caminho só.
   *
   * Os `headers` precisam ir na requisição exatamente como vieram: o
   * `Content-Type` faz parte do que foi assinado.
   */
  upload_data: {
    url: string;
    method: "PUT";
    headers: Record<string, string>;
  };
};

export type TDuplicateAssetData = {
  entity_id: string;
  entity_type: EFileAssetType;
  project_id?: string;
  asset_ids: string[];
};

export type TDuplicateAssetResponse = Record<string, string>; // asset_id -> new_asset_id
