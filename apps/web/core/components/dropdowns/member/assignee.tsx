/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: o seletor de responsável de uma tarefa (ADR 0016).
//
// A tarefa tem UM responsável. Quem chama continua falando em vetor, porque é
// isso que `TIssue.assignee_ids` e a API são — mudar o tipo espalharia a
// mudança por dezenas de arquivos sem ganho. A tradução entre "vetor de no
// máximo um" e "um ou nenhum" mora aqui, e só aqui: assim o dia em que a regra
// mudar tem um lugar para ser mudada.

import { observer } from "mobx-react";
import { MemberDropdown } from "./dropdown";
import type { TMemberDropdownProps } from "./dropdown";

// `Omit` direto sobre a união come as propriedades comuns — `keyof (A | B)` é a
// interseção das chaves. Por isso o `Extract` primeiro: escolhe o ramo de valor
// único e só então tira o que este componente passa a decidir.
type Props = Omit<Extract<TMemberDropdownProps, { multiple: false }>, "multiple" | "value" | "onChange"> & {
  value: string[] | undefined | null;
  onChange: (val: string[]) => void;
};

export const AssigneeDropdown = observer(function AssigneeDropdown(props: Props) {
  const { value, onChange, ...resto } = props;

  return (
    <MemberDropdown
      {...resto}
      multiple={false}
      value={value?.[0] ?? null}
      // Escolher alguém substitui quem estava, e escolher de novo a mesma
      // pessoa esvazia — é o que um seletor de valor único faz, e o que
      // arrastar entre colunas do quadro já fazia.
      onChange={(escolhido) => onChange(escolhido ? [escolhido] : [])}
    />
  );
});
