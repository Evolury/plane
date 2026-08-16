/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: o cartão "QUANDO" do editor (ADR 0012).
//
// Três gatilhos na lista, e o do meio é parametrizado: "campo alterado" cobre
// estado, prioridade, responsável, etiqueta, datas, ciclo, módulo e toda
// propriedade personalizada do projeto. Foi a decisão que mais economizou —
// cinco gatilhos nomeados viraram um, e propriedade nova entra sozinha.
//
// O qualificador "para" só aparece quando o campo escolhido tem um conjunto
// fechado de destinos. Oferecê-lo para data ou texto seria oferecer uma caixa
// que só produz regra que nunca casa.

import { observer } from "mobx-react";
import { CAMPOS_DE_GATILHO } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { AUTOMATION_TRIGGER } from "@plane/types";
import type { TAutomationTrigger, TAutomationTriggerConfig, TIssueProperty } from "@plane/types";
import { CustomSelect } from "@plane/ui";
import { PRIORIDADES_DA_AUTOMACAO } from "@plane/constants";
import { useLabel } from "@/hooks/store/use-label";
import { useMember } from "@/hooks/store/use-member";
import { useProjectState } from "@/hooks/store/use-project-state";

type TProps = {
  projectId: string;
  trigger: TAutomationTrigger;
  config: TAutomationTriggerConfig;
  propriedades: TIssueProperty[];
  onChange: (trigger: TAutomationTrigger, config: TAutomationTriggerConfig) => void;
};

/** Os campos cujo "para" é escolhível numa lista fechada. */
const DESTINOS_FECHADOS = new Set(["state_id", "priority", "label_id", "assignee_id"]);

export const GatilhoDaAutomacao = observer(function GatilhoDaAutomacao(props: TProps) {
  const { projectId, trigger, config, propriedades, onChange } = props;
  const { t } = useTranslation();
  const { getProjectStates } = useProjectState();
  const { getProjectLabelIds, getLabelById } = useLabel();
  const {
    project: { getProjectMemberIds },
  } = useMember();
  const { getUserDetails } = useMember();

  const estados = getProjectStates(projectId) ?? [];
  const etiquetas = (getProjectLabelIds(projectId) ?? []).map((id) => getLabelById(id)).filter(Boolean);
  const membros = (getProjectMemberIds(projectId, false) ?? []).map((id) => getUserDetails(id)).filter(Boolean);

  const campos = [
    ...CAMPOS_DE_GATILHO.map((item) => ({ valor: item.valor as string, rotulo: t(item.i18n) })),
    ...propriedades.map((item) => ({ valor: `property_${item.id}`, rotulo: item.name })),
  ];

  const destinos = () => {
    switch (config.field) {
      case "state_id":
        return estados.map((estado) => ({ valor: estado.id, rotulo: estado.name }));
      case "priority":
        return PRIORIDADES_DA_AUTOMACAO.map((valor) => ({ valor, rotulo: t(valor) }));
      case "label_id":
        return etiquetas.map((etiqueta) => ({ valor: etiqueta!.id, rotulo: etiqueta!.name }));
      case "assignee_id":
        return membros.map((membro) => ({ valor: membro!.id, rotulo: membro!.display_name }));
      default:
        return [];
    }
  };

  const rotuloDoGatilho = () => {
    if (trigger === AUTOMATION_TRIGGER.WORK_ITEM_CREATED) return t("automations.trigger_option.created");
    if (trigger === AUTOMATION_TRIGGER.COMMENT_ADDED) return t("automations.trigger_option.commented");
    return t("automations.trigger_option.field_changed");
  };

  const escolhidos = new Set(config.to ?? []);
  const alternarDestino = (valor: string) => {
    const proximos = new Set(escolhidos);
    if (proximos.has(valor)) proximos.delete(valor);
    else proximos.add(valor);
    onChange(trigger, { ...config, to: Array.from(proximos) });
  };

  return (
    <div className="flex flex-col gap-3">
      <CustomSelect
        value={trigger}
        label={rotuloDoGatilho()}
        onChange={(valor: TAutomationTrigger) =>
          onChange(valor, valor === AUTOMATION_TRIGGER.FIELD_CHANGED ? { field: "", to: [] } : {})
        }
        input
      >
        <CustomSelect.Option value={AUTOMATION_TRIGGER.WORK_ITEM_CREATED}>
          {t("automations.trigger_option.created")}
        </CustomSelect.Option>
        <CustomSelect.Option value={AUTOMATION_TRIGGER.FIELD_CHANGED}>
          {t("automations.trigger_option.field_changed")}
        </CustomSelect.Option>
        <CustomSelect.Option value={AUTOMATION_TRIGGER.COMMENT_ADDED}>
          {t("automations.trigger_option.commented")}
        </CustomSelect.Option>
      </CustomSelect>

      {trigger === AUTOMATION_TRIGGER.FIELD_CHANGED && (
        <div className="flex flex-col gap-3 border-l-2 border-subtle pl-3">
          <div>
            <label className="mb-1 block text-12 text-tertiary">{t("automations.trigger_field_label")}</label>
            <CustomSelect
              value={config.field ?? ""}
              label={
                config.field
                  ? (campos.find((item) => item.valor === config.field)?.rotulo ?? config.field)
                  : t("automations.trigger_field_placeholder")
              }
              onChange={(valor: string) => onChange(trigger, { field: valor, to: [] })}
              input
              maxHeight="lg"
            >
              {campos.map((item) => (
                <CustomSelect.Option key={item.valor} value={item.valor}>
                  {item.rotulo}
                </CustomSelect.Option>
              ))}
            </CustomSelect>
          </div>

          {config.field && DESTINOS_FECHADOS.has(config.field) && (
            <div>
              <label className="mb-1 block text-12 text-tertiary">{t("automations.trigger_to_label")}</label>
              <div className="flex flex-wrap gap-1.5">
                {destinos().map((item) => (
                  <button
                    key={item.valor}
                    type="button"
                    onClick={() => alternarDestino(item.valor)}
                    className={
                      escolhidos.has(item.valor)
                        ? "border-accent-primary rounded-sm border bg-accent-primary/10 px-2 py-1 text-12 text-accent-primary"
                        : "rounded-sm border border-subtle px-2 py-1 text-12 text-secondary hover:bg-layer-1"
                    }
                  >
                    {item.rotulo}
                  </button>
                ))}
              </div>
              <p className="mt-1 text-11 text-tertiary">{t("automations.trigger_to_hint")}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
});
