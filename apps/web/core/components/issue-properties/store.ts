/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: leitura em bloco dos valores de propriedade (ADR 0011, P3).
//
// Um hook por PROJETO, não por tarefa. Os layouts carregam centenas de tarefas
// por página, e um pedido por cartão seria o N+1 que o ADR proibiu — o SWR
// compartilha a mesma resposta entre todos os cartões da página.
//
// A chave inclui os ids da página: mudou a página, muda a chave, e o SWR
// busca de novo sem que ninguém precise invalidar nada à mão.

import { useEffect, useMemo } from "react";
import useSWR, { mutate as mutarGlobal } from "swr";
import type { TIssueProperty, TPropertyValue } from "@plane/types";
import { IssuePropertyService } from "@/services/issue-property.service";
import { guardarPropriedades } from "./cache";

const servico = new IssuePropertyService();

export const chaveDasDefinicoes = (workspaceSlug: string, projectId: string) =>
  `ISSUE_PROPERTY_DEFINITIONS_${workspaceSlug}_${projectId}`;

/** As definições ativas do projeto — compartilhadas por toda a página. */
export const usePropriedadesDoProjeto = (workspaceSlug: string, projectId: string) => {
  const { data } = useSWR(
    workspaceSlug && projectId ? chaveDasDefinicoes(workspaceSlug, projectId) : null,
    () => servico.list(workspaceSlug, projectId),
    { revalidateOnFocus: false }
  );
  // A identidade importa: quem consome monta configs de filtro em `useMemo`,
  // e uma lista nova a cada render faria os configs nascerem de novo a cada
  // render — e o registro deles no MobX é o que dispara o próximo render.
  const ativas = useMemo(() => (data?.properties ?? []).filter((p: TIssueProperty) => p.is_active), [data]);

  // Alimenta a ponte para o MobX: quem desenha as colunas do quadro é uma
  // função pura, sem acesso a hooks.
  useEffect(() => {
    if (projectId) guardarPropriedades(projectId, ativas);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId, data]);

  return ativas;
};

/** Os valores de um conjunto de tarefas — uma chamada para a página inteira. */
export const useValoresDasTarefas = (
  workspaceSlug: string,
  projectId: string,
  issueIds: string[]
): Record<string, Record<string, TPropertyValue>> => {
  // A ordem não pode entrar na chave: a mesma página em outra ordenação é a
  // mesma pergunta, e ordenar aqui evita buscar tudo de novo por nada.
  // A cópia antes do `sort` é de propósito: não muda a lista de quem chamou.
  // (`no-array-sort` está desligada no .oxlintrc.json — a correção que ela
  // sugere, `toSorted()`, não existe no alvo de compilação deste repositório.)
  const chave = [...issueIds].sort().join(",");
  const { data } = useSWR(
    workspaceSlug && projectId && chave ? `ISSUE_PROPERTY_VALUES_BULK_${projectId}_${chave}` : null,
    () => servico.valuesForIssues(workspaceSlug, projectId, issueIds),
    { revalidateOnFocus: false }
  );
  return data?.values ?? {};
};

/**
 * Os valores das propriedades marcadas para o cartão, do PROJETO inteiro.
 *
 * Uma chamada por projeto, e não uma por cartão — o cartão não conhece a
 * página em que está, e um pedido por cartão seria exatamente o N+1 que o
 * ADR 0011 proibiu. O SWR compartilha a resposta entre todos eles.
 *
 * O tamanho é limitado por construção: só entram tarefas que têm valor numa
 * propriedade marcada como "mostrar no cartão", e essa marca é opt-in. Se um
 * dia isso crescer demais, a variante por página já existe acima.
 */
export const useValoresDeCartao = (
  workspaceSlug: string,
  projectId: string,
  habilitado: boolean
): Record<string, Record<string, TPropertyValue>> => {
  const { data } = useSWR(
    workspaceSlug && projectId && habilitado ? `ISSUE_PROPERTY_CARD_VALUES_${projectId}` : null,
    () => servico.cardValues(workspaceSlug, projectId),
    { revalidateOnFocus: false }
  );
  return data?.values ?? {};
};

/**
 * Manda o cartão buscar de novo os valores deste projeto.
 *
 * Evolury: o valor da propriedade aparece no cartão só depois de recarregar a
 * página, e o motivo é que o cartão lê de uma chave PRÓPRIA
 * (`ISSUE_PROPERTY_CARD_VALUES_<projeto>`), do projeto inteiro, enquanto o
 * painel da tarefa revalida a chave DELE. São perguntas diferentes ao mesmo
 * dado, e salvar respondia só uma.
 *
 * Vale para os dois jeitos de o cartão ficar desatualizado: preencher o valor
 * numa tarefa, e ligar ou desligar "mostrar no cartão" na definição — porque o
 * endereço do cartão devolve apenas as propriedades marcadas, então mudar a
 * marca muda a resposta inteira.
 *
 * `revalidateOnFocus` continua desligado de propósito: a resposta é do projeto
 * inteiro, e voltar para a aba não é motivo para buscá-la de novo. Quem sabe
 * que ela mudou é quem acabou de gravar — e é daí que a revalidação sai.
 */
export const revalidarValoresDoProjeto = (projectId: string) => {
  if (!projectId) return;
  void mutarGlobal(`ISSUE_PROPERTY_CARD_VALUES_${projectId}`);
  // A leitura por página tem a lista de tarefas na chave, então não dá para
  // montá-la aqui: revalida por prefixo.
  void mutarGlobal(
    (chave) => typeof chave === "string" && chave.startsWith(`ISSUE_PROPERTY_VALUES_BULK_${projectId}_`)
  );
};
