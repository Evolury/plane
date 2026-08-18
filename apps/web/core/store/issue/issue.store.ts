/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { set, update } from "lodash-es";
import { action, makeObservable, observable, runInAction } from "mobx";
import { computedFn } from "mobx-utils";
// types
import type { TIssue } from "@plane/types";
// helpers
import { getCurrentDateTimeInISO } from "@plane/utils";
import { rootStore } from "@/lib/store-context";
// services
import { IssueService } from "@/services/issue";

export type IIssueStore = {
  // observables
  issuesMap: Record<string, TIssue>; // Record defines issue_id as key and TIssue as value
  issuesIdentifierMap: Record<string, string>; // Record defines issue_identifier as key and issue_id as value
  // actions
  getIssues(workspaceSlug: string, projectId: string, issueIds: string[]): Promise<TIssue[]>;
  addIssue(issues: TIssue[]): void;
  addIssueIdentifier(issueIdentifier: string, issueId: string): void;
  updateIssue(issueId: string, issue: Partial<TIssue>): void;
  removeIssue(issueId: string): void;
  // Evolury: eco das escritas desta aba (ADR 0013, fase 2)
  registrarEscritaLocal(issueId: string): void;
  consumirEscritaLocal(issueId: string): boolean;
  // helper methods
  getIssueById(issueId: string): undefined | TIssue;
  getIssueIdByIdentifier(issueIdentifier: string): undefined | string;
  getIssuesByIds(issueIds: string[], type: "archived" | "un-archived"): TIssue[]; // Record defines issue_id as key and TIssue as value
};

/**
 * Por quanto tempo uma escrita desta aba continua explicando um aviso, em ms.
 *
 * Generoso porque o custo de errar para mais é uma rebusca perdida, e o de
 * errar para menos é o cartão não atualizar — o defeito que tudo isto corrige.
 */
const VALIDADE_DA_ESCRITA_LOCAL = 15_000;

export class IssueStore implements IIssueStore {
  // observables
  issuesMap: { [issue_id: string]: TIssue } = {};
  issuesIdentifierMap: { [issue_identifier: string]: string } = {};
  /**
   * Evolury: o que ESTA aba acabou de escrever (ADR 0013, fase 2).
   *
   * Serve para reconhecer o próprio eco sem perguntar ao servidor quem fez a
   * mudança. A fase 1 comparava o ator do aviso com o usuário da sessão, e isso
   * confundia "fui eu nesta aba" com "fui eu na outra aba" — duas abas da mesma
   * pessoa não se enxergavam.
   *
   * Fica FORA do `makeObservable` de propósito: nada na tela depende disto, e
   * torná-lo observável só criaria reações a cada escrita.
   */
  private escritasLocais = new Map<string, number>();
  // service
  issueService;

  constructor() {
    makeObservable(this, {
      // observable
      issuesMap: observable,
      issuesIdentifierMap: observable,
      // actions
      addIssue: action,
      addIssueIdentifier: action,
      updateIssue: action,
      removeIssue: action,
    });
    this.issueService = new IssueService();
  }

  // Evolury: ADR 0013, fase 2 — ver `escritasLocais`.
  /** Anota que esta aba mandou uma mudança para esta tarefa. */
  registrarEscritaLocal = (issueId: string) => {
    this.escritasLocais.set(issueId, Date.now() + VALIDADE_DA_ESCRITA_LOCAL);
  };

  /**
   * Responde se o aviso desta tarefa se explica por uma escrita desta aba — e,
   * respondendo que sim, **gasta** a anotação.
   *
   * Gastar é o que faz a mesma pessoa editando a mesma tarefa em duas abas
   * continuar funcionando: o primeiro aviso é o eco desta aba e some, e um
   * segundo aviso, que só pode ter vindo de outro lugar, passa.
   */
  consumirEscritaLocal = (issueId: string) => {
    const validade = this.escritasLocais.get(issueId);
    if (validade === undefined) return false;
    this.escritasLocais.delete(issueId);
    // Anotação vencida não explica nada: se o aviso demorou mais do que a
    // validade, ele quase certamente não é o eco desta escrita.
    return validade > Date.now();
  };

  // actions
  /**
   * @description This method will add issues to the issuesMap
   * @param {TIssue[]} issues
   * @returns {void}
   */
  addIssue = (issues: TIssue[]) => {
    if (issues && issues.length <= 0) return;
    runInAction(() => {
      issues.forEach((issue) => {
        // add issue identifier to the issuesIdentifierMap
        const projectIdentifier = rootStore.projectRoot.project.getProjectIdentifierById(issue?.project_id);
        const workItemSequenceId = issue?.sequence_id;
        const issueIdentifier = `${projectIdentifier}-${workItemSequenceId}`;
        set(this.issuesIdentifierMap, issueIdentifier, issue.id);

        if (!this.issuesMap[issue.id]) set(this.issuesMap, issue.id, issue);
        else update(this.issuesMap, issue.id, (prevIssue) => ({ ...prevIssue, ...issue }));
      });
    });
  };

  /**
   * @description This method will add issue_identifier to the issuesIdentifierMap
   * @param issueIdentifier
   * @param issueId
   * @returns {void}
   */
  addIssueIdentifier = (issueIdentifier: string, issueId: string) => {
    if (!issueIdentifier || !issueId) return;
    runInAction(() => {
      set(this.issuesIdentifierMap, issueIdentifier, issueId);
    });
  };

  getIssues = async (workspaceSlug: string, projectId: string, issueIds: string[]) => {
    const issues = await this.issueService.retrieveIssues(workspaceSlug, projectId, issueIds);

    runInAction(() => {
      issues.forEach((issue) => {
        if (!this.issuesMap[issue.id]) set(this.issuesMap, issue.id, issue);
      });
    });

    return issues;
  };

  /**
   * @description This method will update the issue in the issuesMap
   * @param {string} issueId
   * @param {Partial<TIssue>} issue
   * @returns {void}
   */
  updateIssue = (issueId: string, issue: Partial<TIssue>) => {
    if (!issue || !issueId || !this.issuesMap[issueId]) return;
    runInAction(() => {
      set(this.issuesMap, [issueId, "updated_at"], getCurrentDateTimeInISO());
      Object.keys(issue).forEach((key) => {
        set(this.issuesMap, [issueId, key], issue[key as keyof TIssue]);
      });
    });
  };

  /**
   * @description This method will remove the issue from the issuesMap
   * @param {string} issueId
   * @returns {void}
   */
  removeIssue = (issueId: string) => {
    if (!issueId || !this.issuesMap[issueId]) return;
    runInAction(() => {
      delete this.issuesMap[issueId];
    });
  };

  // helper methods
  /**
   * @description This method will return the issue from the issuesMap
   * @param {string} issueId
   * @returns {TIssue | undefined}
   */
  getIssueById = computedFn((issueId: string) => {
    if (!issueId || !this.issuesMap[issueId]) return undefined;
    return this.issuesMap[issueId];
  });

  /**
   * @description This method will return the issue_id from the issuesIdentifierMap
   * @param {string} issueIdentifier
   * @returns {string | undefined}
   */
  getIssueIdByIdentifier = computedFn((issueIdentifier: string) => {
    if (!issueIdentifier || !this.issuesIdentifierMap[issueIdentifier]) return undefined;
    return this.issuesIdentifierMap[issueIdentifier];
  });

  /**
   * @description This method will return the issues from the issuesMap
   * @param {string[]} issueIds
   * @param {boolean} archivedIssues
   * @returns {Record<string, TIssue> | undefined}
   */
  getIssuesByIds = computedFn((issueIds: string[], type: "archived" | "un-archived") => {
    if (!issueIds || issueIds.length <= 0) return [];
    const filteredIssues: TIssue[] = [];
    Object.values(issueIds).forEach((issueId) => {
      // if type is archived then check archived_at is not null
      // if type is un-archived then check archived_at is null
      const issue = this.issuesMap[issueId];
      if (issue && ((type === "archived" && issue.archived_at) || (type === "un-archived" && !issue?.archived_at))) {
        filteredIssues.push(issue);
      }
    });
    return filteredIssues;
  });
}
