# Documentação

Índice da documentação técnica do repositório. Os documentos de governança vivem
na raiz: [UPSTREAM.md](../UPSTREAM.md) (relação com o Plane CE),
[VERSIONING.md](../VERSIONING.md) (versão e release),
[CONTRIBUTING.md](../CONTRIBUTING.md) (fluxo de trabalho) e
[CHANGELOG.md](../CHANGELOG.md).

## Infraestrutura e operação

| Documento                      | O que responde                                                                    |
| ------------------------------ | --------------------------------------------------------------------------------- |
| [telemetria.md](telemetria.md) | O que a instância não envia para terceiros, e como religar contra coletor próprio |
| [linting.md](linting.md)       | Como o lint funciona no monorepo (OxLint/oxfmt)                                   |

## Customizações e funcionalidades Evolury

Tudo o que a Evolury constrói por cima da base herdada é documentado em
[evolury/](evolury/README.md):

- [evolury/decisoes/](evolury/decisoes/) — decisões de arquitetura (ADRs), numeradas e imutáveis
- [evolury/funcionalidades/](evolury/funcionalidades/) — uma pasta por funcionalidade própria, da especificação ao backlog

| Funcionalidade                                                                | Status                                                                                                                 |
| ----------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| [minhas-tarefas](evolury/funcionalidades/minhas-tarefas/especificacao.md)     | Entregue na v1.1.0 — F0–F6 concluídas; matriz de compatibilidade executada                                             |
| [terminologia-tarefa](evolury/funcionalidades/terminologia-tarefa/backlog.md) | Entregue na v1.2.0 — ADR 0003                                                                                          |
| [concluir-tarefa](evolury/funcionalidades/concluir-tarefa/backlog.md)         | Entregue nas v1.3.0–v1.7.0 — botão, ciclo de vida da etapa pessoal e etapa de conclusão do projeto (ADR 0009)          |
| [tarefa-recorrente](evolury/funcionalidades/tarefa-recorrente/manual.md)      | Entregue na v1.7.0, redesenhada na v1.8.0 — recorrência na tarefa (ADR 0010); F5 e o responsável padrão aguardam corte |
