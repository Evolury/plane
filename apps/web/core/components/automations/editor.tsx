/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: o editor de uma regra (ADR 0012).
//
// Cadeia vertical de cartões em três seções rotuladas — QUANDO, SE, ENTÃO —,
// que é o padrão catalogado de "rule builder" e o que Jira e Asana usam. O SE
// nasce fechado dizendo "todas as tarefas" e só abre quando alguém acrescenta
// condição: revelação progressiva, porque a maioria das regras úteis não tem
// condição nenhuma e uma linha de filtros vazia no meio da tela sugere que tem
// de ser preenchida.
//
// A frase-resumo fica no topo, viva enquanto se edita. É o que dá a
// legibilidade da receita do monday sem a rigidez dela.
//
// "Simular" existe porque a única outra forma de descobrir o alcance de uma
// condição é ligar a regra e olhar o estrago.

import { useCallback, useEffect, useState } from "react";
import { observer } from "mobx-react";
import { useNavigate, useSearchParams } from "react-router";
import { Play } from "lucide-react";
import { RECEITAS_DE_AUTOMACAO } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { AUTOMATION_TRIGGER } from "@plane/types";
import type {
  TAutomation,
  TAutomationAction,
  TAutomationPayload,
  TAutomationTrigger,
  TAutomationTriggerConfig,
  TWorkItemFilterExpression,
} from "@plane/types";
import { Input, ToggleSwitch } from "@plane/ui";
import { AutomationService } from "@/services/automation.service";
import { AcoesDaAutomacao } from "./acoes";
import { CondicaoDaAutomacao } from "./condicao";
import { ExecucoesDaAutomacao } from "./execucoes";
import { FraseDaAutomacao } from "./frase";
import { GatilhoDaAutomacao } from "./gatilho";
import { useRotulos } from "./rotulos";

const servico = new AutomationService();

type TProps = {
  workspaceSlug: string;
  projectId: string;
  /** A regra em edição, ou `undefined` para uma nova. */
  regra: TAutomation | undefined;
  onSaved: () => void;
};

/**
 * Uma cópia editável do que veio do catálogo de receitas.
 *
 * O catálogo é `as const`: as listas dentro dele são as MESMAS referências em
 * toda a aplicação. Sem a cópia profunda, editar o gatilho de uma regra nova
 * mudaria a receita para quem abrisse a próxima — um defeito que só apareceria
 * na segunda vez que alguém usasse a tela.
 */
const copiaEditavel = <T,>(valor: unknown): T => JSON.parse(JSON.stringify(valor)) as T;

const Secao = (props: { rotulo: string; children: React.ReactNode; acao?: React.ReactNode }) => (
  <section className="rounded-md border border-subtle bg-surface-1 p-4">
    <div className="mb-3 flex items-center justify-between">
      <h3 className="text-11 font-semibold tracking-wide text-tertiary uppercase">{props.rotulo}</h3>
      {props.acao}
    </div>
    {props.children}
  </section>
);

export const EditorDeAutomacao = observer(function EditorDeAutomacao(props: TProps) {
  const { workspaceSlug, projectId, regra, onSaved } = props;
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [parametros] = useSearchParams();
  const rotulos = useRotulos(workspaceSlug, projectId);

  // A receita vem pela URL, resolvida contra o catálogo — que continua sendo a
  // única fonte da verdade. Só vale para regra NOVA: numa regra existente ela
  // apagaria o que a pessoa escreveu.
  const receita = regra ? undefined : RECEITAS_DE_AUTOMACAO.find((item) => item.chave === parametros.get("receita"));

  const [nome, setNome] = useState(receita ? t(receita.i18n) : (regra?.name ?? ""));
  const [ativa, setAtiva] = useState(regra?.is_active ?? true);
  const [trigger, setTrigger] = useState<TAutomationTrigger>(
    (receita?.trigger_type as TAutomationTrigger) ?? regra?.trigger_type ?? AUTOMATION_TRIGGER.FIELD_CHANGED
  );
  const [triggerConfig, setTriggerConfig] = useState<TAutomationTriggerConfig>(
    receita
      ? copiaEditavel<TAutomationTriggerConfig>(receita.trigger_config)
      : (regra?.trigger_config ?? { field: "", to: [] })
  );
  const [condicao, setCondicao] = useState<TWorkItemFilterExpression>(
    (regra?.condition as TWorkItemFilterExpression) ?? {}
  );
  const [mostrarCondicao, setMostrarCondicao] = useState(
    Boolean(regra?.condition && Object.keys(regra.condition as object).length > 0)
  );
  const [acoes, setAcoes] = useState<TAutomationAction[]>(
    receita ? copiaEditavel<TAutomationAction[]>(receita.actions) : (regra?.actions ?? [])
  );
  const [incluirRecorrentes, setIncluirRecorrentes] = useState(regra?.include_recurring ?? false);
  const [salvando, setSalvando] = useState(false);
  const [simulacao, setSimulacao] = useState<number | undefined>(undefined);
  const [aba, setAba] = useState<"editar" | "execucoes">("editar");

  // A regra chega depois da primeira renderização (a lista é carregada por SWR).
  // Sem isto, abrir o editor por link direto mostraria um formulário vazio.
  useEffect(() => {
    if (!regra) return;
    setNome(regra.name);
    setAtiva(regra.is_active);
    setTrigger(regra.trigger_type);
    setTriggerConfig(regra.trigger_config ?? {});
    setCondicao((regra.condition as TWorkItemFilterExpression) ?? {});
    setMostrarCondicao(Boolean(regra.condition && Object.keys(regra.condition as object).length > 0));
    setAcoes(regra.actions ?? []);
    setIncluirRecorrentes(regra.include_recurring ?? false);
  }, [regra]);

  const simular = useCallback(async () => {
    try {
      const resposta = await servico.simulate(workspaceSlug, projectId, mostrarCondicao ? condicao : null);
      setSimulacao(resposta.total);
    } catch {
      setToast({ type: TOAST_TYPE.ERROR, title: t("toast.error"), message: t("common.something_went_wrong") });
    }
  }, [workspaceSlug, projectId, condicao, mostrarCondicao, t]);

  const salvar = async () => {
    if (!nome.trim()) {
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("toast.error"),
        message: t("automations.create_modal.title.required_error"),
      });
      return;
    }
    const carga: TAutomationPayload = {
      name: nome.trim(),
      is_active: ativa,
      trigger_type: trigger,
      trigger_config: triggerConfig,
      include_recurring: incluirRecorrentes,
      condition: mostrarCondicao && Object.keys(condicao).length > 0 ? condicao : null,
      actions: acoes,
    };

    setSalvando(true);
    try {
      if (regra) await servico.update(workspaceSlug, projectId, regra.id, carga);
      else await servico.create(workspaceSlug, projectId, carga);
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: t("toast.success"),
        message: t(regra ? "automations.toasts.update.success.message" : "automations.toasts.create.success.message"),
      });
      onSaved();
      navigate(`/${workspaceSlug}/settings/projects/${projectId}/automations/`);
    } catch (erro) {
      // O backend recusa regra malformada com uma frase; mostrá-la é o ponto
      // inteiro daquela validação — trocá-la por "algo deu errado" jogaria fora
      // a explicação.
      const detalhe = Object.values((erro as Record<string, string[]>) ?? {})
        .flat()
        .join(" ");
      setToast({
        type: TOAST_TYPE.ERROR,
        title: t("toast.error"),
        message: detalhe || t("common.something_went_wrong"),
      });
    } finally {
      setSalvando(false);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-3">
        <Input
          value={nome}
          onChange={(evento) => setNome(evento.target.value)}
          placeholder={t("automations.create_modal.title.placeholder")}
          className="flex-1"
        />
        <div className="flex items-center gap-2">
          <span className="text-13 text-secondary">{t("automations.active")}</span>
          <ToggleSwitch value={ativa} onChange={setAtiva} />
        </div>
      </div>

      <div className="rounded-md bg-surface-2 px-4 py-3">
        <FraseDaAutomacao
          regra={{
            trigger_type: trigger,
            trigger_config: triggerConfig,
            condition: mostrarCondicao ? condicao : null,
            actions: acoes,
          }}
          rotulos={rotulos}
        />
      </div>

      <div className="flex gap-4 border-b border-subtle">
        {(["editar", "execucoes"] as const).map((chave) => (
          <button
            key={chave}
            type="button"
            onClick={() => setAba(chave)}
            className={
              aba === chave
                ? "border-accent-primary border-b-2 pb-2 text-13 font-medium text-primary"
                : "pb-2 text-13 text-tertiary hover:text-secondary"
            }
          >
            {t(`automations.tab.${chave}`)}
          </button>
        ))}
      </div>

      {aba === "execucoes" ? (
        regra ? (
          <ExecucoesDaAutomacao workspaceSlug={workspaceSlug} projectId={projectId} automationId={regra.id} />
        ) : (
          <p className="py-6 text-center text-13 text-tertiary">{t("automations.runs.only_after_save")}</p>
        )
      ) : (
        <>
          <Secao rotulo={t("automations.trigger.label")}>
            <GatilhoDaAutomacao
              projectId={projectId}
              trigger={trigger}
              config={triggerConfig}
              propriedades={rotulos.propriedades}
              onChange={(novoGatilho, novaConfig) => {
                setTrigger(novoGatilho);
                setTriggerConfig(novaConfig);
              }}
            />
            {trigger === AUTOMATION_TRIGGER.WORK_ITEM_CREATED && (
              <label className="mt-3 flex items-start gap-2 text-12 text-secondary">
                <input
                  type="checkbox"
                  className="mt-0.5"
                  checked={incluirRecorrentes}
                  onChange={(evento) => setIncluirRecorrentes(evento.target.checked)}
                />
                <span>
                  {t("automations.include_recurring")}
                  <span className="block text-11 text-tertiary">{t("automations.include_recurring_hint")}</span>
                </span>
              </label>
            )}
          </Secao>

          <Secao
            rotulo={t("automations.condition.label")}
            acao={
              <div className="flex items-center gap-2">
                {simulacao !== undefined && (
                  <span className="text-12 text-tertiary">
                    {t("automations.simulate.result", { total: simulacao })}
                  </span>
                )}
                <Button variant="secondary" size="sm" onClick={() => void simular()}>
                  <Play className="size-3" />
                  {t("automations.simulate.button")}
                </Button>
              </div>
            }
          >
            {mostrarCondicao ? (
              <CondicaoDaAutomacao
                workspaceSlug={workspaceSlug}
                projectId={projectId}
                condicao={condicao}
                onChange={setCondicao}
              />
            ) : (
              <button
                type="button"
                onClick={() => setMostrarCondicao(true)}
                className="text-13 text-tertiary hover:text-accent-primary"
              >
                {t("automations.condition_empty")}
              </button>
            )}
          </Secao>

          <Secao rotulo={t("automations.action.label")}>
            <AcoesDaAutomacao
              projectId={projectId}
              acoes={acoes}
              propriedades={rotulos.propriedades}
              trigger={trigger}
              onChange={setAcoes}
            />
          </Secao>

          <div className="flex justify-end gap-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => navigate(`/${workspaceSlug}/settings/projects/${projectId}/automations/`)}
            >
              {t("common.cancel")}
            </Button>
            <Button variant="primary" size="sm" onClick={() => void salvar()} loading={salvando}>
              {t(
                regra
                  ? "automations.create_modal.submit_button.update"
                  : "automations.create_modal.submit_button.create"
              )}
            </Button>
          </div>
        </>
      )}
    </div>
  );
});
