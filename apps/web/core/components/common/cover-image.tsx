/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { NANO_BLUE } from "@plane/constants";
import { cn } from "@plane/utils";
// helpers
import { getCoverImageDisplayURL, DEFAULT_COVER_IMAGE_URL } from "@/helpers/cover-image.helper";

type TCoverImageProps = {
  /** The cover image URL - can be static, uploaded, or external */
  src: string | null | undefined;
  /**
   * Evolury: `true` enquanto a entidade ainda está sendo carregada.
   *
   * Sem isto não dá para distinguir "ainda não sei" de "não tem capa": os dois
   * chegavam como `src` vazio, e o componente mostrava esqueleto para ambos —
   * um projeto sem capa ficava pulsando para sempre.
   */
  carregando?: boolean;
  /** Alt text for the image */
  alt?: string;
  /** Additional className for the image or skeleton */
  className?: string;
  /**
   * @deprecated Evolury: sem efeito. Capa vazia passou a ser o azul da marca,
   * e não uma imagem padrão — a prop fica para não quebrar os chamadores.
   */
  showDefaultWhenEmpty?: boolean;
  /** Custom fallback URL to use instead of DEFAULT_COVER_IMAGE_URL */
  fallbackUrl?: string;
} & React.ComponentProps<"img">;

/**
 * A reusable cover image component that handles:
 * - Loading states with skeleton
 * - Static images (local assets)
 * - Uploaded images (processed through getFileURL)
 * - External URLs
 * - Fallback to default cover image
 */
export function CoverImage(props: TCoverImageProps) {
  const {
    src,
    alt = "Cover image",
    className,
    carregando = false,
    showDefaultWhenEmpty = false,
    fallbackUrl = DEFAULT_COVER_IMAGE_URL,
    ...restProps
  } = props;

  if (carregando) {
    return <div className={cn("animate-pulse bg-layer-2", className)} />;
  }

  // Evolury: sem capa, o azul da marca — e não uma foto sorteada nem um
  // esqueleto eterno. É o que faz projeto novo e perfil novo nascerem com a
  // mesma cara; pôr imagem vira escolha de quem usa (brandbook 1.02, NanoBlue).
  if (!src) {
    return <div className={cn(className)} style={{ backgroundColor: NANO_BLUE }} aria-label={alt} role="img" />;
  }

  const displayUrl = getCoverImageDisplayURL(src, fallbackUrl);

  return <img src={displayUrl} alt={alt} className={cn("object-cover", className)} {...restProps} />;
}
