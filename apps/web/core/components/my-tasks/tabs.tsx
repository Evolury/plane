/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: abas do topo de "Minhas tarefas" — Tarefas e Páginas (ADR 0015).
//
// Mesmo desenho das abas de páginas de projeto: sublinhado na ativa, e clique
// na aba já ativa não navega.

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslation } from "@plane/i18n";
import { cn } from "@plane/utils";

export type TAbaDeMinhasTarefas = "tarefas" | "paginas" | "compartilhado";

type Props = {
  workspaceSlug: string;
};

export function MyTasksTabs(props: Props) {
  const { workspaceSlug } = props;
  const { t } = useTranslation();
  const pathname = usePathname();

  const abas: { chave: TAbaDeMinhasTarefas; rotulo: string; href: string }[] = [
    {
      chave: "tarefas",
      rotulo: t("my_tasks.tabs.tasks"),
      href: `/${workspaceSlug}/my-tasks`,
    },
    {
      chave: "paginas",
      rotulo: t("my_tasks.tabs.pages"),
      href: `/${workspaceSlug}/my-tasks/pages`,
    },
    {
      chave: "compartilhado",
      rotulo: t("my_tasks.tabs.shared"),
      href: `/${workspaceSlug}/my-tasks/shared`,
    },
  ];

  const ativa: TAbaDeMinhasTarefas = pathname?.includes("/my-tasks/shared")
    ? "compartilhado"
    : pathname?.includes("/my-tasks/pages")
      ? "paginas"
      : "tarefas";

  return (
    <div className="relative flex h-full items-center">
      {abas.map((aba) => (
        <Link
          key={aba.chave}
          href={aba.href}
          onClick={(e) => {
            if (aba.chave === ativa) e.preventDefault();
          }}
          className="flex h-full flex-col"
        >
          <div
            className={cn("flex flex-1 items-center justify-center px-4 text-13 font-medium transition-all", {
              "text-accent-primary": aba.chave === ativa,
            })}
          >
            {aba.rotulo}
          </div>
          <div
            className={cn("w-full rounded-t border-t-2 border-transparent transition-all", {
              "border-accent-strong": aba.chave === ativa,
            })}
          />
        </Link>
      ))}
    </div>
  );
}
