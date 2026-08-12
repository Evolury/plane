# ADR 0003 — "Tarefa" como termo pt-BR para work item

- **Status:** Aceito (12/08/2026)
- **Contexto:** funcionalidade [terminologia-tarefa](../funcionalidades/terminologia-tarefa/backlog.md)

## Contexto

O Plane chama a unidade de trabalho de **work item** ("item de trabalho" no
pt-BR). Para o produto Evolury, o termo adequado é **tarefa** — mais curto,
natural em português e convergente com a página "Minhas tarefas" (que passa a
listar, literalmente, tarefas).

A pergunta estrutural era: isso é tradução ou arquitetura? A varredura
(12/08/2026) respondeu:

- **581 ocorrências** de "item(ns) de trabalho" nos 19 arquivos do locale
  pt-BR (`packages/i18n`), compartilhado por web, space e admin.
- **142 linhas de inglês hardcoded** fora do i18n em **71 arquivos** do web
  (feed de atividade, ciclo ativo, estimativas, gráficos) — débito do
  upstream: essas telas já exibem "work item" em inglês hoje.
- Nenhuma ocorrência visível em e-mails; exportações CSV e mensagens da API
  pública são contrato técnico em inglês.

## Decisão

1. **Camada de tradução, não de estrutura.** Mudam apenas os **valores**
   pt-BR. Chaves de i18n (`work_item_*`), código (`issue`), banco, API,
   webhooks, rotas e exportações permanecem intactos. Zero migração.
2. **Escopo de idioma: somente pt-BR.** Os demais 18 locales mantêm o termo
   nativo deles para work item.
3. **Sobras hardcoded entram na mesma entrega**: as 142 linhas em inglês
   viram chaves de i18n — o `en` mantém "work item"; o pt-BR recebe
   "tarefa". Melhoria colateral para todos os idiomas.
4. **Gênero gramatical é revisão, não regex.** "Item" (masculino) → "tarefa"
   (feminino) flexiona artigos, pronomes e particípios ("novo item criado" →
   "nova tarefa criada"; "ao item" → "à tarefa"; "nenhum item encontrado" →
   "nenhuma tarefa encontrada"). Cada string é revisada individualmente.

## Glossário canônico

| Conceito (en)             | pt-BR anterior               | pt-BR canônico       |
| ------------------------- | ---------------------------- | -------------------- |
| work item                 | item de trabalho             | tarefa               |
| work items                | itens de trabalho            | tarefas              |
| sub-work item             | sub-item de trabalho         | subtarefa            |
| work item type(s)         | tipo(s) de item de trabalho  | tipo(s) de tarefa    |
| recurring work item       | item de trabalho recorrente  | tarefa recorrente    |
| draft work item           | rascunho de item de trabalho | rascunho de tarefa   |
| Epic                      | Épico                        | Épico (inalterado)   |
| My tasks (funcionalidade) | Minhas tarefas               | Minhas tarefas       |
| to-do list (bloco editor) | Lista de tarefas             | Lista de tarefas (¹) |

(¹) O bloco de checklist do editor coexiste sem conflito prático; manter.

## Consequências

- A UI pt-BR inteira (web, space, admin) fala "tarefa"; textos de outros
  idiomas não mudam.
- Novas strings pt-BR devem seguir o glossário acima (vale para o fluxo da
  skill `translate`).
- O nome do conceito no código continua `issue`/`work item` — comentários e
  documentos técnicos podem usar os dois, mas texto de usuário só "tarefa".
- As telas hoje em inglês passam a ser traduzíveis (chaves novas), reduzindo
  o débito herdado do upstream.
