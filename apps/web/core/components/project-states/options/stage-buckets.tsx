/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: as marcações de vencimento na linha da etapa (ADR 0014).
//
// Mora aqui, ao lado de `mark-as-default` e `mark-as-completion`, porque é a
// mesma pergunta feita no mesmo lugar: "o que esta etapa é?". A diferença é que
// estas quatro são OPCIONAIS — clicar de novo desliga, e o balde fica sem
// destino, que é caso legítimo.
//
// Só aparece onde a tela sabe responder: os estados de projeto não passam os
// callbacks e não veem nada.

import { useState } from "react";
import { observer } from "mobx-react";
import { useTranslation } from "@plane/i18n";
import type { TBaldeDeVencimento, TMarcacoesDaEtapa } from "@plane/types";
import { cn } from "@plane/utils";

type TProps = {
  stageId: string;
  marcacoes: TMarcacoesDaEtapa;
  onMarcar: (balde: TBaldeDeVencimento, ativo: boolean) => Promise<void>;
  onAlternarAutomacao: (desativada: boolean) => Promise<void>;
  /** A etapa por onde a tarefa entra. Marcação como as outras — ver abaixo. */
  ehEntrada: boolean;
  onMarcarEntrada: () => Promise<void>;
  rotulosDaEntrada?: { atual: string; acao: string; salvando: string };
};

/** Balde → chave da marcação e chave de tradução do rótulo. */
const BALDES: { balde: TBaldeDeVencimento; campo: keyof TMarcacoesDaEtapa; rotulo: string }[] = [
  { balde: "vencidas", campo: "vencidas", rotulo: "my_tasks.stages.buckets.overdue" },
  { balde: "hoje", campo: "hoje", rotulo: "my_tasks.stages.buckets.today" },
  { balde: "amanha", campo: "amanha", rotulo: "my_tasks.stages.buckets.tomorrow" },
  { balde: "depois", campo: "depois", rotulo: "my_tasks.stages.buckets.later" },
];

export const StageBuckets = observer(function StageBuckets(props: TProps) {
  const { marcacoes, onMarcar, onAlternarAutomacao, ehEntrada, onMarcarEntrada, rotulosDaEntrada } = props;
  const { t } = useTranslation();
  const [emVoo, setEmVoo] = useState<string | null>(null);

  const alternar = async (chave: string, acao: () => Promise<void>) => {
    if (emVoo) return;
    setEmVoo(chave);
    try {
      await acao();
    } finally {
      setEmVoo(null);
    }
  };

  return (
    <div className="flex flex-shrink-0 items-center gap-1.5 text-11">
      {/* A entrada é marcação como as outras, e por isso mora na mesma fila e
          usa o mesmo visual. Ela estava como texto solto, visível só no hover —
          o que a fazia parecer outra categoria de coisa.

          Uma diferença permanece, e é do modelo, não do visual: a entrada é
          OBRIGATÓRIA e única, então marcá-la move a marcação de outra etapa e
          não há como desmarcar. Por isso a ativa não é clicável. */}
      <button
        type="button"
        disabled={ehEntrada || emVoo !== null}
        onClick={() => alternar("entrada", onMarcarEntrada)}
        className={cn(
          "rounded-sm px-1.5 py-0.5 whitespace-nowrap transition-colors",
          ehEntrada
            ? "text-accent-strong bg-accent-primary/10"
            : "hidden text-secondary group-hover:inline-block hover:text-primary"
        )}
      >
        {emVoo === "entrada"
          ? (rotulosDaEntrada?.salvando ?? "…")
          : ehEntrada
            ? (rotulosDaEntrada?.atual ?? "")
            : (rotulosDaEntrada?.acao ?? "")}
      </button>
      {BALDES.map(({ balde, campo, rotulo }) => {
        const ativo = marcacoes[campo];
        return (
          <button
            key={balde}
            type="button"
            disabled={emVoo !== null}
            // Clicar numa marcação ativa DESLIGA: é o que torna a marcação
            // opcional, ao contrário da etapa padrão.
            onClick={() => alternar(balde, () => onMarcar(balde, !ativo))}
            className={cn(
              "rounded-sm px-1.5 py-0.5 whitespace-nowrap transition-colors",
              // O que está MARCADO fica sempre visível: é informação, e ler a
              // configuração não pode depender de passar o mouse. O que está
              // desmarcado só aparece no hover, para a linha não virar um
              // amontoado de botões apagados.
              ativo
                ? "text-accent-strong bg-accent-primary/10"
                : "hidden text-secondary group-hover:inline-block hover:text-primary"
            )}
            title={t(ativo ? "my_tasks.stages.buckets.unmark" : "my_tasks.stages.buckets.mark")}
          >
            {t(rotulo)}
          </button>
        );
      })}
      <button
        type="button"
        disabled={emVoo !== null}
        onClick={() => alternar("automacao", () => onAlternarAutomacao(!marcacoes.semAutomacao))}
        className={cn(
          "rounded-sm px-1.5 py-0.5 whitespace-nowrap transition-colors",
          marcacoes.semAutomacao
            ? "bg-danger-primary/10 text-danger-primary"
            : "hidden text-secondary group-hover:inline-block hover:text-primary"
        )}
        // O rótulo diz "não sai daqui", e não "sem automação": a marcação vale
        // para SAIR, e chegar continua podendo.
        title={t("my_tasks.stages.buckets.locked_hint")}
      >
        {t("my_tasks.stages.buckets.locked")}
      </button>
    </div>
  );
});
