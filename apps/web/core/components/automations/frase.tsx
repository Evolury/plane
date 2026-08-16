/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: a regra dita em português corrente (ADR 0012).
//
// É o que dá à cadeia de cartões a legibilidade da "receita" do monday sem a
// rigidez dela: a pessoa monta com seletores e lê a frase, viva, enquanto edita.
// Sem isso, entender uma regra da lista exige abrir a regra — e uma lista que
// não pode ser lida não é uma lista, é um índice.
//
// A frase é montada em pedaços, e não por uma chave de tradução com marcadores,
// porque cada pedaço tem ênfase própria na tela: o que a pessoa escolheu vem em
// destaque, as conjunções não.

import React from "react";
import { useTranslation } from "@plane/i18n";
import { AUTOMATION_TRIGGER } from "@plane/types";
import type { TAutomation, TAutomationAction } from "@plane/types";
import { cn } from "@plane/utils";
import type { TRotulos } from "./rotulos";

type TProps = {
  regra: Pick<TAutomation, "trigger_type" | "trigger_config" | "condition" | "actions">;
  rotulos: TRotulos;
  className?: string;
};

const Destaque = ({ children }: { children: React.ReactNode }) => (
  <span className="font-medium text-primary">{children}</span>
);

export const FraseDaAutomacao = function FraseDaAutomacao(props: TProps) {
  const { regra, rotulos, className } = props;
  const { t } = useTranslation();

  const lista = (itens: string[]) => itens.join(", ");

  const quando = () => {
    const config = regra.trigger_config ?? {};
    switch (regra.trigger_type) {
      case AUTOMATION_TRIGGER.WORK_ITEM_CREATED:
        return <Destaque>{t("automations.sentence.created")}</Destaque>;
      case AUTOMATION_TRIGGER.COMMENT_ADDED:
        return <Destaque>{t("automations.sentence.commented")}</Destaque>;
      case AUTOMATION_TRIGGER.FIELD_CHANGED: {
        const campo = <Destaque>{rotulos.campo(config.field)}</Destaque>;
        const destinos = (config.to ?? []).map((valor) => rotulos.valorDoCampo(config.field, valor));
        if (destinos.length === 0)
          return (
            <>
              {t("automations.sentence.field_changed")} {campo}
            </>
          );
        return (
          <>
            {t("automations.sentence.field_changed")} {campo} {t("automations.sentence.to")}{" "}
            <Destaque>{lista(destinos)}</Destaque>
          </>
        );
      }
      default:
        return <Destaque>{rotulos.campo(undefined)}</Destaque>;
    }
  };

  const acao = (item: TAutomationAction) => {
    const config = item.config ?? {};
    switch (item.type) {
      case "set_state":
        return (
          <>
            {t("automations.sentence.set_state")}{" "}
            <Destaque>{rotulos.valorDoCampo("state_id", config.state_id ?? "")}</Destaque>
          </>
        );
      case "set_priority":
        return (
          <>
            {t("automations.sentence.set_priority")}{" "}
            <Destaque>{rotulos.valorDoCampo("priority", config.priority ?? "")}</Destaque>
          </>
        );
      case "set_assignees": {
        const pessoas = (config.assignees ?? []).map((id) => rotulos.valorDoCampo("assignee_id", id));
        const papeis = (config.especiais ?? []).map((papel) => t(`automations.special.${papel}`));
        const alvo = lista([...pessoas, ...papeis]);
        const verbo = config.mode === "remove" ? "remove_assignee" : "add_assignee";
        return (
          <>
            {t(`automations.sentence.${verbo}`)} <Destaque>{alvo || "—"}</Destaque>
          </>
        );
      }
      case "set_labels": {
        const etiquetas = lista((config.labels ?? []).map((id) => rotulos.valorDoCampo("label_id", id)));
        const verbo = config.mode === "remove" ? "remove_label" : "add_label";
        return (
          <>
            {t(`automations.sentence.${verbo}`)} <Destaque>{etiquetas || "—"}</Destaque>
          </>
        );
      }
      case "set_date": {
        const campo = t(`automations.field.${config.field === "start_date" ? "start_date" : "target_date"}`);
        const quandoData =
          config.date_mode !== "fixed"
            ? t("automations.sentence.relative_days", { dias: config.offset_days ?? 0 })
            : (config.date ?? "—");
        return (
          <>
            {t("automations.sentence.set_date")} <Destaque>{campo}</Destaque> {t("automations.sentence.to")}{" "}
            <Destaque>{quandoData}</Destaque>
          </>
        );
      }
      case "set_property":
        return (
          <>
            {t("automations.sentence.set_property")} <Destaque>{rotulos.propriedade(config.property_id)}</Destaque>
          </>
        );
      default:
        return <>{item.type}</>;
    }
  };

  const temCondicao = Boolean(regra.condition && Object.keys(regra.condition as object).length > 0);
  const acoes = regra.actions ?? [];

  return (
    <p className={cn("text-13 text-secondary", className)}>
      <span className="text-tertiary">{t("automations.sentence.when")} </span>
      {quando()}
      {temCondicao && (
        <>
          <span className="text-tertiary">, {t("automations.conjunctions.if").toLowerCase()} </span>
          <Destaque>{t("automations.sentence.conditions_match")}</Destaque>
        </>
      )}
      <span className="text-tertiary">, {t("automations.conjunctions.then").toLowerCase()} </span>
      {acoes.length === 0 ? (
        <span className="text-tertiary">{t("automations.sentence.no_action")}</span>
      ) : (
        acoes.map((item, indice) => (
          <React.Fragment key={`${item.type}-${indice}`}>
            {indice > 0 && <span className="text-tertiary"> {t("automations.conjunctions.and").toLowerCase()} </span>}
            {acao(item)}
          </React.Fragment>
        ))
      )}
      <span className="text-tertiary">.</span>
    </p>
  );
};
