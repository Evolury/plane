/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: o editor de valor de uma propriedade personalizada (ADR 0011, P2).
//
// Um editor por tipo, e cada um com o controle nativo do tipo: data abre
// calendário, número aceita só número, seleção lista as opções com a cor que a
// configuração deu. Um campo de texto para tudo economizaria código aqui e
// custaria em todo lugar depois — é o que faz o dado chegar sujo à ordenação.
//
// O componente é controlado por quem o monta: ele não conhece tarefa nem
// serviço, só valor e `onChange`. É o que permite usá-lo igual no painel (onde
// salva a cada mudança) e no modal de criação (onde só junta o formulário).

import { useEffect, useState } from "react";
import { observer } from "mobx-react";
import type { TIssueProperty, TPropertyValue } from "@plane/types";
import { Input } from "@plane/ui";
import { cn } from "@plane/utils";

/**
 * Campo de digitar que confirma no BLUR, e não a cada tecla.
 *
 * Salvar por tecla transformava "Contrato assinado" em dezessete chamadas e
 * dezessete linhas de histórico — o histórico da tarefa virava um teclado
 * registrado, e o que mudou de verdade sumia no meio.
 *
 * Enter confirma sem sair do campo; Escape devolve o valor anterior, que é o
 * jeito de desistir sem inventar um botão de cancelar.
 */
const CampoQueConfirmaNoBlur = observer(function CampoQueConfirmaNoBlur(props: {
  valor: string;
  onCommit: (valor: string) => void;
  disabled?: boolean;
  type?: string;
  step?: number | string;
  className?: string;
}) {
  const { valor, onCommit, disabled, type, step, className } = props;
  const [rascunho, setRascunho] = useState(valor);

  // O valor do servidor manda quando muda por fora — outra pessoa editando, ou
  // a recarga depois de salvar.
  useEffect(() => setRascunho(valor), [valor]);

  const confirmar = () => {
    if (rascunho !== valor) onCommit(rascunho);
  };

  return (
    <Input
      type={type}
      step={step}
      value={rascunho}
      disabled={disabled}
      onChange={(e) => setRascunho(e.target.value)}
      onBlur={confirmar}
      onKeyDown={(e) => {
        if (e.key === "Enter") {
          e.preventDefault();
          confirmar();
        }
        if (e.key === "Escape") setRascunho(valor);
      }}
      className={className}
    />
  );
});

type TProps = {
  propriedade: TIssueProperty;
  valor: TPropertyValue;
  onChange: (valor: TPropertyValue) => void;
  disabled?: boolean;
};

export const PropertyValueEditor = observer(function PropertyValueEditor(props: TProps) {
  const { propriedade, valor, onChange, disabled } = props;

  if (propriedade.property_type === "select") {
    return (
      <select
        value={typeof valor === "string" ? valor : ""}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value || null)}
        className="w-full rounded-md border border-subtle bg-surface-1 px-2 py-1 text-12"
      >
        <option value="">—</option>
        {propriedade.options.map((opcao) => (
          <option key={opcao.id} value={opcao.id}>
            {opcao.name}
          </option>
        ))}
      </select>
    );
  }

  if (propriedade.property_type === "multi_select") {
    const escolhidas = Array.isArray(valor) ? valor : [];
    return (
      <div className="flex flex-wrap gap-1.5">
        {propriedade.options.map((opcao) => {
          const marcada = escolhidas.includes(opcao.id);
          return (
            <button
              key={opcao.id}
              type="button"
              disabled={disabled}
              onClick={() => onChange(marcada ? escolhidas.filter((id) => id !== opcao.id) : [...escolhidas, opcao.id])}
              className={cn(
                "flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-11 transition-colors",
                marcada
                  ? "border-accent-subtle-1 bg-accent-subtle text-accent-primary"
                  : "border-subtle text-secondary hover:bg-layer-1"
              )}
            >
              <span className="size-2 rounded-full" style={{ backgroundColor: opcao.color || "#6b7280" }} />
              {opcao.name}
            </button>
          );
        })}
      </div>
    );
  }

  if (propriedade.property_type === "date") {
    return (
      <CampoQueConfirmaNoBlur
        type="date"
        valor={typeof valor === "string" ? valor : ""}
        disabled={disabled}
        onCommit={(novo) => onChange(novo || null)}
        className="w-full"
      />
    );
  }

  if (propriedade.property_type === "number" || propriedade.property_type === "currency") {
    return (
      <div className="flex items-center gap-1.5">
        {propriedade.property_type === "currency" && (
          <span className="shrink-0 text-11 text-tertiary">{propriedade.currency}</span>
        )}
        <CampoQueConfirmaNoBlur
          type="number"
          step={propriedade.property_type === "currency" ? 10 ** -propriedade.decimal_places : "any"}
          valor={typeof valor === "string" || typeof valor === "number" ? String(valor) : ""}
          disabled={disabled}
          onCommit={(novo) => onChange(novo === "" ? null : novo)}
          className="w-full"
        />
      </div>
    );
  }

  return (
    <CampoQueConfirmaNoBlur
      valor={typeof valor === "string" ? valor : ""}
      disabled={disabled}
      onCommit={(novo) => onChange(novo || null)}
      className="w-full"
    />
  );
});
