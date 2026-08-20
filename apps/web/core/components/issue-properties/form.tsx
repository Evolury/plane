/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: formulário de uma propriedade personalizada (ADR 0011, P1).
//
// O tipo é escolhido no nascimento e não muda depois — converter texto em
// número não tem resposta certa para o que já foi escrito, e a resposta que a
// interface escolhesse seria perda silenciosa. A única exceção é seleção única
// → múltipla, que não perde nada: cada valor vira uma lista de um.

import { useEffect, useRef, useState } from "react";
import { observer } from "mobx-react";
import { Plus, X } from "lucide-react";
// Evolury: ícone da propriedade (ADR 0011)
import { cn } from "@plane/utils";
import { CHAVES_DE_ICONE, ICONES_DE_PROPRIEDADE, chaveDoIcone } from "./icones";
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import type { TIssueProperty, TIssuePropertyOption, TPropertyCurrency, TPropertyType } from "@plane/types";
import { EModalWidth, Input, ModalCore } from "@plane/ui";
// services
import { IssuePropertyService } from "@/services/issue-property.service";
import { revalidarValoresDoProjeto } from "./store";

const servico = new IssuePropertyService();

const TIPOS: TPropertyType[] = ["text", "number", "date", "select", "multi_select", "currency"];
const MOEDAS: TPropertyCurrency[] = ["BRL", "USD", "EUR"];
const TIPOS_DE_SELECAO = new Set<TPropertyType>(["select", "multi_select"]);

type TProps = {
  workspaceSlug: string;
  projectId: string;
  propriedade?: TIssueProperty;
  isOpen: boolean;
  onClose: () => void;
  onSaved: () => void;
};

// Evolury: `chaveLocal` existe só para o React. A opção nova ainda não tem id
// do banco, e usar o índice como chave faz o React reaproveitar o campo errado
// quando alguém remove uma opção do meio — quem estava digitando vê o texto
// pular de linha.
type TOpcaoEmEdicao = Pick<TIssuePropertyOption, "name" | "color"> & { id?: string; chaveLocal?: string };

const padrao = (): Partial<TIssueProperty> => ({
  name: "",
  property_type: "text",
  is_required: false,
  show_on_card: false,
  // Ligado, ao contrário de `show_on_card`: agrupar é o uso natural de uma
  // seleção, e a caixa existe para desligar ruído, não para ligar o óbvio.
  show_in_grouping: true,
  currency: "BRL",
  decimal_places: 2,
  icon: "",
});

export const IssuePropertyForm = observer(function IssuePropertyForm(props: TProps) {
  const { workspaceSlug, projectId, propriedade, isOpen, onClose, onSaved } = props;
  const { t } = useTranslation();
  // Evolury: o foco vai por ref e não por `autoFocus`. O atributo rouba o foco
  // antes de o leitor de tela anunciar o diálogo, e quem navega por teclado
  // perde o contexto de onde está.
  const campoDoNome = useRef<HTMLInputElement>(null);
  const [dados, setDados] = useState<Partial<TIssueProperty>>(padrao());
  const [opcoes, setOpcoes] = useState<TOpcaoEmEdicao[]>([]);
  const [salvando, setSalvando] = useState(false);

  useEffect(() => {
    if (isOpen) campoDoNome.current?.focus();
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;
    setDados(propriedade ? { ...propriedade } : padrao());
    setOpcoes(propriedade?.options?.map((o) => ({ id: o.id, name: o.name, color: o.color })) ?? []);
  }, [isOpen, propriedade]);

  const rotulo = (chave: string) => t(`issue_properties.${chave}`);
  const mudar = (campos: Partial<TIssueProperty>) => setDados((atual) => ({ ...atual, ...campos }));

  const ehSelecao = TIPOS_DE_SELECAO.has(dados.property_type ?? "text");
  // Depois de criada, o seletor de tipo só oferece o que a API aceita: nada,
  // ou o único caminho que não perde dado.
  const tiposDisponiveis = !propriedade
    ? TIPOS
    : propriedade.property_type === "select"
      ? (["select", "multi_select"] as TPropertyType[])
      : [propriedade.property_type];

  const salvar = async () => {
    setSalvando(true);
    try {
      const corpo = { ...dados, options: ehSelecao ? opcoes : undefined };
      if (propriedade) await servico.update(workspaceSlug, projectId, propriedade.id, corpo);
      else await servico.create(workspaceSlug, projectId, corpo);
      revalidarValoresDoProjeto(projectId);
      setToast({
        type: TOAST_TYPE.SUCCESS,
        title: t("toast.success"),
        message: rotulo(propriedade ? "toast.updated" : "toast.created"),
      });
      onSaved();
      onClose();
    } catch (erro) {
      const mensagem =
        (erro as Record<string, string[]>)?.name?.[0] ??
        (erro as Record<string, string[]>)?.currency?.[0] ??
        (erro as Record<string, string>)?.error ??
        t("common.something_went_wrong");
      setToast({ type: TOAST_TYPE.ERROR, title: t("toast.error"), message: String(mensagem) });
    } finally {
      setSalvando(false);
    }
  };

  return (
    <ModalCore isOpen={isOpen} handleClose={onClose} width={EModalWidth.XXL}>
      <div className="flex max-h-[80vh] flex-col gap-4 overflow-y-auto p-5">
        <h3 className="text-16 font-medium">{rotulo(propriedade ? "settings.edit" : "settings.new")}</h3>

        <label className="flex flex-col gap-1 text-13">
          <span className="text-secondary">{rotulo("form.name")}</span>
          <Input value={dados.name ?? ""} onChange={(e) => mudar({ name: e.target.value })} ref={campoDoNome} />
        </label>

        <label className="flex flex-col gap-1 text-13">
          <span className="text-secondary">{rotulo("form.type")}</span>
          <select
            value={dados.property_type}
            onChange={(e) => mudar({ property_type: e.target.value as TPropertyType })}
            className="rounded-md border border-subtle bg-surface-1 px-2 py-1.5"
          >
            {tiposDisponiveis.map((tipo) => (
              <option key={tipo} value={tipo}>
                {rotulo(`type.${tipo}`)}
              </option>
            ))}
          </select>
          {!!propriedade && <span className="text-11 text-tertiary">{rotulo("form.type_locked")}</span>}
        </label>

        {/* Evolury: o ícone do campo (ADR 0011). Grade em vez de lista suspensa
            porque a escolha é visual — quem procura um ícone reconhece o
            desenho, não lembra o nome dele. */}
        <div className="flex flex-col gap-1 text-13">
          <span className="text-secondary">{rotulo("form.icon")}</span>
          <div className="flex flex-wrap gap-1">
            {CHAVES_DE_ICONE.map((chave) => {
              const Icone = ICONES_DE_PROPRIEDADE[chave];
              const escolhido =
                chaveDoIcone({
                  icon: dados.icon ?? "",
                  property_type: dados.property_type as TPropertyType,
                }) === chave;
              return (
                <button
                  key={chave}
                  type="button"
                  aria-label={chave}
                  aria-pressed={escolhido}
                  onClick={() => mudar({ icon: chave })}
                  className={cn(
                    "grid size-7 place-items-center rounded-md border transition-colors",
                    escolhido
                      ? "border-accent-subtle-1 bg-accent-subtle text-accent-primary"
                      : "border-subtle text-tertiary hover:bg-surface-2"
                  )}
                >
                  <Icone className="size-3.5" />
                </button>
              );
            })}
          </div>
          {/* Voltar ao padrão é uma escolha também, e precisa ter caminho de volta. */}
          {!!dados.icon && (
            <button
              type="button"
              onClick={() => mudar({ icon: "" })}
              className="self-start text-11 text-tertiary underline underline-offset-2 hover:text-secondary"
            >
              {rotulo("form.icon_default")}
            </button>
          )}
        </div>

        {dados.property_type === "currency" && (
          <div className="flex gap-3">
            <label className="flex flex-1 flex-col gap-1 text-13">
              <span className="text-secondary">{rotulo("form.currency")}</span>
              <select
                value={dados.currency ?? "BRL"}
                onChange={(e) => mudar({ currency: e.target.value as TPropertyCurrency })}
                className="rounded-md border border-subtle bg-surface-1 px-2 py-1.5"
              >
                {MOEDAS.map((moeda) => (
                  <option key={moeda} value={moeda}>
                    {moeda}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex flex-1 flex-col gap-1 text-13">
              <span className="text-secondary">{rotulo("form.decimal_places")}</span>
              <Input
                type="number"
                min={0}
                max={4}
                value={String(dados.decimal_places ?? 2)}
                onChange={(e) => mudar({ decimal_places: Math.min(4, Math.max(0, Number(e.target.value))) })}
              />
            </label>
          </div>
        )}

        {ehSelecao && (
          <div className="flex flex-col gap-2 text-13">
            <span className="text-secondary">{rotulo("form.options")}</span>
            {opcoes.map((opcao, indice) => (
              <div key={opcao.id ?? opcao.chaveLocal} className="flex items-center gap-2">
                <input
                  type="color"
                  value={opcao.color || "#6b7280"}
                  onChange={(e) =>
                    setOpcoes((atual) => atual.map((o, i) => (i === indice ? { ...o, color: e.target.value } : o)))
                  }
                  className="size-7 shrink-0 rounded-sm border border-subtle bg-surface-1"
                />
                <Input
                  value={opcao.name}
                  onChange={(e) =>
                    setOpcoes((atual) => atual.map((o, i) => (i === indice ? { ...o, name: e.target.value } : o)))
                  }
                  className="flex-1"
                />
                <button
                  type="button"
                  onClick={() => setOpcoes((atual) => atual.filter((_, i) => i !== indice))}
                  className="grid size-7 shrink-0 place-items-center rounded-sm text-tertiary hover:bg-layer-1 hover:text-primary"
                >
                  <X className="size-3.5" />
                </button>
              </div>
            ))}
            <button
              type="button"
              onClick={() =>
                setOpcoes((atual) => [...atual, { name: "", color: "#6b7280", chaveLocal: crypto.randomUUID() }])
              }
              className="flex w-fit items-center gap-1 rounded-sm px-1.5 py-1 text-12 text-tertiary hover:bg-layer-1 hover:text-primary"
            >
              <Plus className="size-3.5" />
              {rotulo("form.add_option")}
            </button>
          </div>
        )}

        {/* O rótulo TEM texto e está associado pelo `htmlFor`; a regra não o
            enxerga porque ele vem da tradução em tempo de execução. Silenciada
            com o motivo, e não por incômodo. */}
        {/* oxlint-disable-next-line label-has-associated-control */}
        <label htmlFor="propriedade-obrigatoria" className="flex items-start gap-2 text-13">
          <input
            id="propriedade-obrigatoria"
            type="checkbox"
            className="mt-1"
            checked={!!dados.is_required}
            onChange={(e) => mudar({ is_required: e.target.checked })}
          />
          <span>
            <span className="text-secondary">{rotulo("form.required")}</span>
            <span className="block text-11 text-tertiary">{rotulo("form.required_hint")}</span>
          </span>
        </label>

        <label className="flex items-center gap-2 text-13">
          <input
            type="checkbox"
            checked={!!dados.show_on_card}
            onChange={(e) => mudar({ show_on_card: e.target.checked })}
          />
          <span className="text-secondary">{rotulo("form.show_on_card")}</span>
        </label>

        {/* Só seleção única vira coluna: os outros tipos produziriam uma coluna
            por valor distinto, que é ruído e não organização (ADR 0011). Por
            isso a caixa some, em vez de aparecer desabilitada — controle que
            não faz nada em lugar nenhum não devia ocupar a tela. */}
        {dados.property_type === "select" && (
          // oxlint-disable-next-line label-has-associated-control
          <label htmlFor="propriedade-no-agrupamento" className="flex items-start gap-2 text-13">
            <input
              id="propriedade-no-agrupamento"
              type="checkbox"
              className="mt-1"
              checked={dados.show_in_grouping !== false}
              onChange={(e) => mudar({ show_in_grouping: e.target.checked })}
            />
            <span>
              <span className="text-secondary">{rotulo("form.show_in_grouping")}</span>
              <span className="block text-11 text-tertiary">{rotulo("form.show_in_grouping_hint")}</span>
            </span>
          </label>
        )}

        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose} disabled={salvando}>
            {t("common.cancel")}
          </Button>
          <Button variant="primary" onClick={salvar} loading={salvando} disabled={!dados.name?.trim()}>
            {t(propriedade ? "common.update" : "common.create")}
          </Button>
        </div>
      </div>
    </ModalCore>
  );
});
