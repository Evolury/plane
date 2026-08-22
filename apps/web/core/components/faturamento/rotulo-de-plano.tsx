/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
// O mesmo `useParams` que a barra lateral e o invólucro do espaço usam. O de
// `react-router` devolve vazio fora de um elemento de rota, e slug vazio faz
// este selo sumir em silêncio — medido no navegador, com o plano Essencial e
// nenhum rótulo aparecendo.
import { useParams } from "next/navigation";
// plane imports
import { planoQueLibera } from "@plane/constants";
import { cn } from "@plane/utils";
// hooks
import { useFaturamento } from "@/hooks/store/use-faturamento";

type TRotuloDePlano = {
  /** O recurso que o item representa. Sem ele, não há o que rotular. */
  recurso?: string;
  className?: string;
  size?: "sm" | "md";
};

/**
 * Diz **qual plano** libera o que está ali (ADR 0021).
 *
 * Some quando o plano já inclui o recurso — e some também quando ninguém sabe
 * ainda qual é o plano, porque piscar rótulo de venda em quem já pagou é o
 * jeito mais rápido de ensinar o cliente a ignorá-lo.
 *
 * Substitui o selo "Pro" que o upstream mostrava fixo em todo item do menu:
 * ele vendia um plano da nuvem do Plane que aqui nunca existiu, e aparecia até
 * em recurso que a instância já tinha.
 */
export const RotuloDePlano = observer(function RotuloDePlano(props: TRotuloDePlano) {
  const { recurso, className, size = "sm" } = props;
  const { workspaceSlug } = useParams();
  const { recursoLiberado } = useFaturamento();

  if (!recurso) return null;
  if (recursoLiberado(workspaceSlug?.toString() ?? "", recurso)) return null;

  const plano = planoQueLibera(recurso);
  if (!plano) return null;

  return (
    <div
      className={cn(
        "w-fit cursor-pointer rounded-2xl bg-accent-primary/20 text-center font-medium text-accent-secondary outline-none",
        {
          "px-3 text-13": size === "md",
          "px-2 text-11": size === "sm",
        },
        className
      )}
    >
      {plano.nome}
    </div>
  );
});
