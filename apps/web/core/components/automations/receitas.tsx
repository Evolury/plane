/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: as receitas prontas do estado vazio (ADR 0012, F3.7).
//
// Existem por ADOÇÃO, não por poder. A lição do monday é que quem chega numa
// tela de automação em branco não sabe o que é possível: a tela explica a
// sintaxe e não o repertório. Uma receita preenchida ensina o modelo inteiro num
// clique — e ensina, de quebra, a diferença entre reagir e repetir, que é a
// confusão mais cara deste recurso.
//
// Elas não são um tipo especial de regra. Abrem o MESMO editor, já respondido, e
// deixam em aberto exatamente o que depende do projeto (qual estado, qual
// etiqueta) — adivinhar isso produziria uma regra errada com cara de pronta.

import { observer } from "mobx-react";
import { Sparkles } from "lucide-react";
import { RECEITAS_DE_AUTOMACAO } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { cn } from "@plane/utils";

type TProps = {
  /**
   * Abre o editor com esta receita.
   *
   * Passa a CHAVE, e não a regra montada: o catálogo já é a fonte da verdade, e
   * mandar o conteúdo por aqui criaria uma segunda cópia dele viajando pela
   * tela. A chave também cabe na URL, o que torna a receita compartilhável.
   */
  onEscolher: (chave: string) => void;
  className?: string;
};

/** O gatilho da receita, dito no mesmo vocabulário do seletor. */
const RESUMO_DO_GATILHO: Record<string, string> = {
  work_item_created: "created",
  field_changed: "field_changed",
  comment_added: "commented",
  scheduled: "scheduled",
};

export const ReceitasDeAutomacao = observer(function ReceitasDeAutomacao(props: TProps) {
  const { onEscolher, className } = props;
  const { t } = useTranslation();

  return (
    <div className={cn("flex flex-col gap-3", className)}>
      <div className="flex items-center gap-1.5 text-12 text-tertiary">
        <Sparkles className="size-3.5" />
        {t("automations.recipes.heading")}
      </div>

      <div className="grid gap-2 sm:grid-cols-2">
        {RECEITAS_DE_AUTOMACAO.map((receita) => (
          <button
            key={receita.chave}
            type="button"
            onClick={() => onEscolher(receita.chave)}
            className="hover:border-accent-primary rounded-md border border-subtle bg-surface-1 px-3 py-2.5 text-left transition-colors hover:bg-layer-1"
          >
            <span className="block text-13 text-primary">{t(receita.i18n)}</span>
            <span className="mt-0.5 block text-11 text-tertiary">
              {t(`automations.trigger_option.${RESUMO_DO_GATILHO[receita.trigger_type]}`)}
            </span>
          </button>
        ))}
      </div>

      <p className="text-11 text-tertiary">{t("automations.recipes.hint")}</p>
    </div>
  );
});
