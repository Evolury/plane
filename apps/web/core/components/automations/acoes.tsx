/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: o cartão "ENTÃO" do editor (ADR 0012).
//
// Seis ações, todas sobre campos que o produto já sabe escrever. A ordem
// importa e é editável: mudar o estado antes de comentar muda o que o
// comentário diz.
//
// Não há linguagem de expressão. Onde o Jira oferece "smart values" — uma
// mini-linguagem com depurador próprio —, aqui há seletores e, para responsável,
// dois PAPÉIS resolvidos na execução: "quem criou" e "quem disparou". Papel, e
// não pessoa, porque guardar o id congelaria quem era responsável no dia em que
// a regra foi escrita.

import { observer } from "mobx-react";
import { Plus, Trash2 } from "lucide-react";
import { PRIORIDADES_DA_AUTOMACAO, VARIAVEIS_DA_AUTOMACAO } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { AUTOMATION_ACTION, AUTOMATION_TRIGGER } from "@plane/types";
import type { TAutomationAction, TAutomationActionType, TAutomationTrigger, TIssueProperty } from "@plane/types";
import { Button } from "@plane/propel/button";
import { CustomSelect, Input, TextArea } from "@plane/ui";
import { useInstance } from "@/hooks/store/use-instance";
import { useLabel } from "@/hooks/store/use-label";
import { useMember } from "@/hooks/store/use-member";
import { useModule } from "@/hooks/store/use-module";
import { useProjectState } from "@/hooks/store/use-project-state";

type TProps = {
  projectId: string;
  acoes: TAutomationAction[];
  propriedades: TIssueProperty[];
  /** O gatilho da regra — é ele que decide se criar tarefa está no cardápio. */
  trigger: TAutomationTrigger;
  onChange: (acoes: TAutomationAction[]) => void;
};

/**
 * Criar só existe em gatilho de EVENTO.
 *
 * Agendado + criar É recorrência, e o produto já tem Tarefas recorrentes, com
 * calendário, antecedência e controle de ocorrência aberta. Esconder a opção é
 * melhor do que oferecê-la com um aviso: aviso a pessoa fecha, cardápio ela lê.
 */
/**
 * A caixa "notificar por e-mail" nasce marcada?
 *
 * Evolury: ela vinha marcada sempre, e sem SMTP configurado quem criava uma
 * regra pedia um e-mail enfileirado para nunca sair — sem erro, sem aviso.
 *
 * A regra tem duas metades: escolha explícita vence, e na ausência dela o
 * padrão segue a instância. Assim, no dia em que houver SMTP a caixa volta a
 * nascer marcada sozinha, sem ninguém tocar em código.
 *
 * Exportada para o teste afirmar ESTA decisão, e não uma cópia dela.
 */
export const caixaDeEmailMarcada = (email: boolean | undefined, smtpConfigurado: boolean): boolean =>
  email === true || (email !== false && smtpConfigurado);

const ACOES_DE_CRIACAO = new Set<string>([AUTOMATION_ACTION.CREATE_WORK_ITEM, AUTOMATION_ACTION.CREATE_SUBTASKS]);

const PADRAO_POR_TIPO: Record<TAutomationActionType, TAutomationAction["config"]> = {
  set_state: { state_id: "" },
  set_priority: { priority: "medium" },
  set_assignees: { mode: "add", assignees: [], especiais: [] },
  set_labels: { mode: "add", labels: [] },
  set_date: { field: "target_date", date_mode: "relative", offset_days: 0 },
  set_property: { property_id: "", value: "" },
  add_comment: { text: "" },
  notify: { users: [], especiais: ["assignees"], text: "", email: true },
  // Arquivar e ciclo não têm o que configurar: a primeira age na tarefa que
  // disparou, a segunda usa o ciclo ATIVO — um id fixo aqui envelheceria na
  // virada do próximo ciclo.
  archive: {},
  add_to_cycle: {},
  add_to_module: { module_id: "" },
  create_work_item: { name: "", herdar_responsaveis: false },
  create_subtasks: { names: [""], herdar_responsaveis: true },
};

export const AcoesDaAutomacao = observer(function AcoesDaAutomacao(props: TProps) {
  const { projectId, acoes, propriedades, trigger, onChange } = props;
  const { t } = useTranslation();
  const { getProjectStates } = useProjectState();
  const { getProjectLabelIds, getLabelById } = useLabel();
  const {
    project: { getProjectMemberIds },
  } = useMember();
  const { getUserDetails } = useMember();
  const { getProjectModuleIds, getModuleById } = useModule();
  const { config } = useInstance();
  const smtpConfigurado = config?.is_smtp_configured ?? false;

  const estados = getProjectStates(projectId) ?? [];
  const etiquetas = (getProjectLabelIds(projectId) ?? []).map((id) => getLabelById(id)).filter(Boolean);
  const membros = (getProjectMemberIds(projectId, false) ?? []).map((id) => getUserDetails(id)).filter(Boolean);
  const modulos = (getProjectModuleIds(projectId) ?? []).map((id) => getModuleById(id)).filter(Boolean);

  const atualizar = (indice: number, mudanca: Partial<TAutomationAction>) =>
    onChange(acoes.map((acao, i) => (i === indice ? { ...acao, ...mudanca } : acao)));

  const atualizarConfig = (indice: number, mudanca: Record<string, unknown>) =>
    atualizar(indice, { config: { ...acoes[indice].config, ...mudanca } });

  const remover = (indice: number) => onChange(acoes.filter((_, i) => i !== indice));

  const acrescentar = (tipo: TAutomationActionType) =>
    onChange([...acoes, { type: tipo, config: { ...PADRAO_POR_TIPO[tipo] } }]);

  const rotuloDoTipo = (tipo: TAutomationActionType) => t(`automations.action_option.${tipo}`);

  type TChaveDeLista = "assignees" | "labels" | "especiais" | "users";

  const alternarNaLista = (indice: number, chave: TChaveDeLista, valor: string) => {
    const atual = new Set((acoes[indice].config[chave] as string[] | undefined) ?? []);
    if (atual.has(valor)) atual.delete(valor);
    else atual.add(valor);
    atualizarConfig(indice, { [chave]: Array.from(atual) });
  };

  const fichas = (indice: number, chave: TChaveDeLista, itens: { valor: string; rotulo: string }[]) => {
    const escolhidos = new Set((acoes[indice].config[chave] as string[] | undefined) ?? []);
    return (
      <div className="flex flex-wrap gap-1.5">
        {itens.map((item) => (
          <button
            key={item.valor}
            type="button"
            onClick={() => alternarNaLista(indice, chave, item.valor)}
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
    );
  };

  const seletorDeModo = (indice: number) => (
    <CustomSelect
      value={acoes[indice].config.mode ?? "add"}
      label={t(`automations.mode.${acoes[indice].config.mode ?? "add"}`)}
      onChange={(valor: string) => atualizarConfig(indice, { mode: valor })}
      input
    >
      <CustomSelect.Option value="add">{t("automations.mode.add")}</CustomSelect.Option>
      <CustomSelect.Option value="remove">{t("automations.mode.remove")}</CustomSelect.Option>
      <CustomSelect.Option value="replace">{t("automations.mode.replace")}</CustomSelect.Option>
    </CustomSelect>
  );

  const corpo = (acao: TAutomationAction, indice: number) => {
    const config = acao.config ?? {};
    switch (acao.type) {
      case AUTOMATION_ACTION.SET_STATE:
        return (
          <CustomSelect
            value={config.state_id ?? ""}
            label={estados.find((estado) => estado.id === config.state_id)?.name ?? t("automations.pick_state")}
            onChange={(valor: string) => atualizarConfig(indice, { state_id: valor })}
            input
          >
            {estados.map((estado) => (
              <CustomSelect.Option key={estado.id} value={estado.id}>
                {estado.name}
              </CustomSelect.Option>
            ))}
          </CustomSelect>
        );

      case AUTOMATION_ACTION.SET_PRIORITY:
        return (
          <CustomSelect
            value={config.priority ?? ""}
            label={config.priority ? t(config.priority) : t("automations.pick_priority")}
            onChange={(valor: string) => atualizarConfig(indice, { priority: valor })}
            input
          >
            {PRIORIDADES_DA_AUTOMACAO.map((prioridade) => (
              <CustomSelect.Option key={prioridade} value={prioridade}>
                {t(prioridade)}
              </CustomSelect.Option>
            ))}
          </CustomSelect>
        );

      case AUTOMATION_ACTION.SET_ASSIGNEES:
        return (
          <div className="flex flex-col gap-2">
            {seletorDeModo(indice)}
            {fichas(indice, "especiais", [
              { valor: "creator", rotulo: t("automations.special.creator") },
              { valor: "trigger_actor", rotulo: t("automations.special.trigger_actor") },
            ])}
            {fichas(
              indice,
              "assignees",
              membros.map((membro) => ({ valor: membro!.id, rotulo: membro!.display_name }))
            )}
          </div>
        );

      case AUTOMATION_ACTION.SET_LABELS:
        return (
          <div className="flex flex-col gap-2">
            {seletorDeModo(indice)}
            {fichas(
              indice,
              "labels",
              etiquetas.map((etiqueta) => ({ valor: etiqueta!.id, rotulo: etiqueta!.name }))
            )}
          </div>
        );

      case AUTOMATION_ACTION.SET_DATE:
        return (
          <div className="flex flex-wrap items-center gap-2">
            <CustomSelect
              value={config.field ?? "target_date"}
              label={t(`automations.field.${config.field === "start_date" ? "start_date" : "target_date"}`)}
              onChange={(valor: string) => atualizarConfig(indice, { field: valor })}
              input
            >
              <CustomSelect.Option value="target_date">{t("automations.field.target_date")}</CustomSelect.Option>
              <CustomSelect.Option value="start_date">{t("automations.field.start_date")}</CustomSelect.Option>
            </CustomSelect>
            <CustomSelect
              value={config.date_mode ?? "relative"}
              label={t(`automations.date_mode.${config.date_mode === "fixed" ? "fixed" : "relative"}`)}
              onChange={(valor: string) => atualizarConfig(indice, { date_mode: valor })}
              input
            >
              <CustomSelect.Option value="relative">{t("automations.date_mode.relative")}</CustomSelect.Option>
              <CustomSelect.Option value="fixed">{t("automations.date_mode.fixed")}</CustomSelect.Option>
            </CustomSelect>
            {config.date_mode === "fixed" ? (
              <Input
                type="date"
                value={config.date ?? ""}
                onChange={(evento) => atualizarConfig(indice, { date: evento.target.value })}
                className="w-40"
              />
            ) : (
              <Input
                type="number"
                value={String(config.offset_days ?? 0)}
                onChange={(evento) => atualizarConfig(indice, { offset_days: Number(evento.target.value) })}
                className="w-24"
                placeholder={t("automations.days")}
              />
            )}
          </div>
        );

      case AUTOMATION_ACTION.SET_PROPERTY:
        return (
          <div className="flex flex-wrap items-center gap-2">
            <CustomSelect
              value={config.property_id ?? ""}
              label={
                propriedades.find((item) => item.id === config.property_id)?.name ?? t("automations.pick_property")
              }
              onChange={(valor: string) => atualizarConfig(indice, { property_id: valor, value: "" })}
              input
              maxHeight="lg"
            >
              {propriedades.map((item) => (
                <CustomSelect.Option key={item.id} value={item.id}>
                  {item.name}
                </CustomSelect.Option>
              ))}
            </CustomSelect>
            <ValorDaPropriedade
              propriedade={propriedades.find((item) => item.id === config.property_id)}
              valor={config.value}
              onChange={(valor) => atualizarConfig(indice, { value: valor })}
            />
          </div>
        );

      case AUTOMATION_ACTION.ADD_COMMENT:
        return (
          <div className="flex flex-col gap-1">
            <TextArea
              value={config.text ?? ""}
              onChange={(evento) => atualizarConfig(indice, { text: evento.target.value })}
              placeholder={t("automations.comment_placeholder")}
              rows={3}
            />
            <AjudaDeVariaveis />
          </div>
        );

      case AUTOMATION_ACTION.NOTIFY:
        return (
          <div className="flex flex-col gap-2">
            {fichas(indice, "especiais", [
              { valor: "assignees", rotulo: t("automations.notify_target.assignees") },
              { valor: "creator", rotulo: t("automations.special.creator") },
              { valor: "trigger_actor", rotulo: t("automations.special.trigger_actor") },
            ])}
            {fichas(
              indice,
              "users",
              membros.map((membro) => ({ valor: membro!.id, rotulo: membro!.display_name }))
            )}
            <TextArea
              value={config.text ?? ""}
              onChange={(evento) => atualizarConfig(indice, { text: evento.target.value })}
              placeholder={t("automations.notify_placeholder")}
              rows={2}
            />
            <AjudaDeVariaveis />
            {/* Evolury: a caixa não pode prometer o que a instância não entrega.
                Sem SMTP configurado ela nasce DESMARCADA e diz por quê — antes,
                vinha marcada por padrão e a mensagem era enfileirada para nunca
                sair, sem aviso nenhum. Continua clicável de propósito: quem está
                configurando o SMTP agora deve poder deixar a regra pronta. */}
            <label className="flex items-center gap-2 text-12 text-secondary">
              <input
                type="checkbox"
                checked={caixaDeEmailMarcada(config.email as boolean | undefined, smtpConfigurado)}
                onChange={(evento) => atualizarConfig(indice, { email: evento.target.checked })}
              />
              {t("automations.notify_email")}
            </label>
            {!smtpConfigurado && <p className="text-11 text-tertiary">{t("automations.notify_email_sem_smtp")}</p>}
          </div>
        );

      case AUTOMATION_ACTION.CREATE_WORK_ITEM:
        return (
          <div className="flex flex-col gap-2">
            <Input
              value={config.name ?? ""}
              onChange={(evento) => atualizarConfig(indice, { name: evento.target.value })}
              placeholder={t("automations.create_name_placeholder")}
            />
            <AjudaDeVariaveis />
            <OpcoesDaCriacao indice={indice} config={config} atualizarConfig={atualizarConfig} />
          </div>
        );

      case AUTOMATION_ACTION.CREATE_SUBTASKS:
        return (
          <div className="flex flex-col gap-2">
            <ListaDeSubtarefas nomes={config.names ?? [""]} onChange={(names) => atualizarConfig(indice, { names })} />
            <AjudaDeVariaveis />
            <OpcoesDaCriacao indice={indice} config={config} atualizarConfig={atualizarConfig} />
            <p className="text-11 text-tertiary">{t("automations.create_idempotency_hint")}</p>
          </div>
        );

      case AUTOMATION_ACTION.ARCHIVE:
        return <p className="text-12 text-tertiary">{t("automations.archive_hint")}</p>;

      case AUTOMATION_ACTION.ADD_TO_CYCLE:
        return <p className="text-12 text-tertiary">{t("automations.cycle_hint")}</p>;

      case AUTOMATION_ACTION.ADD_TO_MODULE:
        return (
          <div className="flex flex-col gap-1">
            <CustomSelect
              value={config.module_id ?? ""}
              label={modulos.find((m) => m!.id === config.module_id)?.name ?? t("automations.pick_module")}
              onChange={(valor: string) => atualizarConfig(indice, { module_id: valor })}
              input
              maxHeight="lg"
            >
              {modulos.map((modulo) => (
                <CustomSelect.Option key={modulo!.id} value={modulo!.id}>
                  {modulo!.name}
                </CustomSelect.Option>
              ))}
            </CustomSelect>
            {/* Ao contrário do ciclo, aqui o id fixo é a resposta certa: módulo
                é contêiner durável, sprint não é. */}
            <p className="text-11 text-tertiary">{t("automations.module_hint")}</p>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="flex flex-col gap-3">
      {acoes.map((acao, indice) => (
        <div key={`${acao.type}-${indice}`} className="rounded-sm border border-subtle bg-surface-2 p-3">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-13 font-medium text-primary">{rotuloDoTipo(acao.type)}</span>
            <button
              type="button"
              onClick={() => remover(indice)}
              className="hover:text-danger text-tertiary"
              aria-label={t("common.remove")}
            >
              <Trash2 className="size-3.5" />
            </button>
          </div>
          {corpo(acao, indice)}
        </div>
      ))}

      <CustomSelect
        value=""
        label={
          <span className="flex items-center gap-1 text-13">
            <Plus className="size-3.5" />
            {t("automations.action.add_action")}
          </span>
        }
        onChange={(valor: TAutomationActionType) => acrescentar(valor)}
        customButton={
          <Button variant="secondary" size="sm" className="w-fit">
            <Plus className="size-3.5" />
            {t("automations.action.add_action")}
          </Button>
        }
      >
        {Object.values(AUTOMATION_ACTION)
          .filter((tipo) => trigger !== AUTOMATION_TRIGGER.SCHEDULED || !ACOES_DE_CRIACAO.has(tipo))
          .map((tipo) => (
            <CustomSelect.Option key={tipo} value={tipo}>
              {rotuloDoTipo(tipo)}
            </CustomSelect.Option>
          ))}
      </CustomSelect>
    </div>
  );
});

/**
 * As variáveis disponíveis, ditas na tela.
 *
 * Escondê-las obrigaria a pessoa a saber de cor o que existe — e o custo de não
 * saber é um comentário automático com `{{orçamento}}` literal no meio.
 */
const AjudaDeVariaveis = observer(function AjudaDeVariaveis() {
  const { t } = useTranslation();
  return (
    <p className="text-11 text-tertiary">
      {t("automations.variables_hint")} {VARIAVEIS_DA_AUTOMACAO.map((nome) => `{{${nome}}}`).join(" · ")}
    </p>
  );
});

/** A lista de subtarefas — um campo por linha, como um checklist se escreve. */
const ListaDeSubtarefas = observer(function ListaDeSubtarefas(props: {
  nomes: string[];
  onChange: (nomes: string[]) => void;
}) {
  const { nomes, onChange } = props;
  const { t } = useTranslation();

  const trocar = (indice: number, valor: string) => onChange(nomes.map((n, i) => (i === indice ? valor : n)));

  return (
    <div className="flex flex-col gap-1.5">
      {nomes.map((nome, indice) => (
        // A posição é a identidade aqui: o campo é controlado pelo pai e não
        // guarda estado próprio, então reordenar não embaralha nada.
        // eslint-disable-next-line react/no-array-index-key
        <div key={indice} className="flex items-center gap-1.5">
          <span className="text-11 text-tertiary">{indice + 1}.</span>
          <Input
            value={nome}
            onChange={(evento) => trocar(indice, evento.target.value)}
            placeholder={t("automations.subtask_placeholder")}
            className="flex-1"
          />
          <button
            type="button"
            onClick={() => onChange(nomes.filter((_, i) => i !== indice))}
            className="hover:text-danger text-tertiary"
            aria-label={t("common.remove")}
          >
            <Trash2 className="size-3.5" />
          </button>
        </div>
      ))}
      <Button variant="secondary" size="sm" className="w-fit" onClick={() => onChange([...nomes, ""])}>
        <Plus className="size-3.5" />
        {t("automations.add_subtask")}
      </Button>
    </div>
  );
});

/** As duas opções que valem para qualquer criação. */
const OpcoesDaCriacao = observer(function OpcoesDaCriacao(props: {
  indice: number;
  config: TAutomationAction["config"];
  atualizarConfig: (indice: number, mudanca: Record<string, unknown>) => void;
}) {
  const { indice, config, atualizarConfig } = props;
  const { t } = useTranslation();

  return (
    <div className="flex flex-wrap items-center gap-4">
      <label className="flex items-center gap-2 text-12 text-secondary">
        <input
          type="checkbox"
          checked={Boolean(config.herdar_responsaveis)}
          onChange={(evento) => atualizarConfig(indice, { herdar_responsaveis: evento.target.checked })}
        />
        {t("automations.inherit_assignees")}
      </label>
      <label className="flex items-center gap-2 text-12 text-secondary">
        {t("automations.due_in_days")}
        <Input
          type="number"
          value={config.due_in_days === undefined ? "" : String(config.due_in_days)}
          onChange={(evento) =>
            atualizarConfig(indice, {
              due_in_days: evento.target.value === "" ? undefined : Number(evento.target.value),
            })
          }
          className="w-20"
          placeholder="—"
        />
      </label>
    </div>
  );
});

/**
 * O campo de valor muda com o tipo da propriedade — é a mesma regra do
 * formulário de propriedades: oferecer caixa de texto para uma seleção
 * produziria valor que o backend recusa.
 */
const ValorDaPropriedade = observer(function ValorDaPropriedade(props: {
  propriedade: TIssueProperty | undefined;
  valor: unknown;
  onChange: (valor: unknown) => void;
}) {
  const { propriedade, valor, onChange } = props;
  const { t } = useTranslation();

  if (!propriedade) return null;

  if (propriedade.property_type === "select" || propriedade.property_type === "multi_select") {
    const opcoes = propriedade.options ?? [];
    const atual = typeof valor === "string" ? valor : "";
    return (
      <CustomSelect
        value={atual}
        label={opcoes.find((opcao) => opcao.id === atual)?.name ?? t("automations.pick_value")}
        onChange={(escolha: string) => onChange(escolha)}
        input
        maxHeight="lg"
      >
        {opcoes.map((opcao) => (
          <CustomSelect.Option key={opcao.id} value={opcao.id}>
            {opcao.name}
          </CustomSelect.Option>
        ))}
      </CustomSelect>
    );
  }

  const tipoDoCampo = propriedade.property_type === "date" ? "date" : "text";
  return (
    <Input
      type={tipoDoCampo}
      value={typeof valor === "string" || typeof valor === "number" ? String(valor) : ""}
      onChange={(evento) => onChange(evento.target.value)}
      placeholder={t("automations.pick_value")}
      className="w-48"
    />
  );
});
