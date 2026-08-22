/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import axios from "axios";
// plane imports
import type { TFileSignedURLResponse } from "@plane/types";
// api service
import { APIService } from "../api.service";

/**
 * Service class for handling file upload operations
 * Handles file uploads
 * @extends {APIService}
 */
export class FileUploadService extends APIService {
  private cancelSource: any;

  constructor() {
    super("");
  }

  /**
   * Envia o arquivo direto ao armazenamento, com PUT assinado.
   *
   * Era POST multipart até 22/08/2026, quando se mediu que o Cloudflare R2 não
   * implementa POST assinado: devolve `501 NotImplemented`, e com isso nenhum
   * upload funcionava — nem avatar, nem logo, nem anexo de tarefa. PUT funciona
   * nos dois provedores.
   *
   * O corpo é o arquivo cru, sem `FormData`. Os cabeçalhos vão como vieram do
   * servidor: o `Content-Type` faz parte da assinatura, e trocá-lo invalida a
   * URL.
   */
  async uploadFile(uploadData: TFileSignedURLResponse["upload_data"], file: File): Promise<void> {
    this.cancelSource = axios.CancelToken.source();
    return this.put(uploadData.url, file, {
      headers: uploadData.headers,
      cancelToken: this.cancelSource.token,
      withCredentials: false,
    })
      .then((response) => response?.data)
      .catch((error) => {
        if (axios.isCancel(error)) {
          console.log(error.message);
        } else {
          throw error?.response?.data;
        }
      });
  }

  /**
   * Cancels the upload
   */
  cancelUpload() {
    this.cancelSource.cancel("Upload canceled");
  }
}
