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

| Funcionalidade                                                                           | Status                                                                                                                                                          |
| ---------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [minhas-tarefas](evolury/funcionalidades/minhas-tarefas/especificacao.md)                | Entregue na v1.1.0 — F0–F6; etapa pela janela da tarefa na v1.2.0 (F7); movimentação diária pelo vencimento na v1.26.0 (F8, ADR 0014). Backlog sem item aberto  |
| [terminologia-tarefa](evolury/funcionalidades/terminologia-tarefa/backlog.md)            | Entregue na v1.2.0 — ADR 0003                                                                                                                                   |
| [concluir-tarefa](evolury/funcionalidades/concluir-tarefa/backlog.md)                    | Entregue nas v1.3.0–v1.7.0 — botão, ciclo de vida da etapa pessoal e etapa de conclusão do projeto (ADR 0009)                                                   |
| [tarefa-recorrente](evolury/funcionalidades/tarefa-recorrente/manual.md)                 | Entregue na v1.7.0, redesenhada na v1.8.0 — recorrência na tarefa (ADR 0010); F5 e o responsável padrão saíram na v1.9.0                                        |
| [propriedade-personalizada](evolury/funcionalidades/propriedade-personalizada/manual.md) | Entregue na v1.13.0 — campos próprios por projeto, com filtro, agrupamento e ordenação (ADR 0011)                                                               |
| [automacao](evolury/funcionalidades/automacao/manual.md)                                 | Entregue na v1.18.0 — regras quando / se / então, com as três fases do backlog concluídas (ADR 0012)                                                            |
| [atualização em tempo real](evolury/decisoes/0013-atualizacao-em-tempo-real.md)          | Entregue nas v1.21.0–v1.25.0 — a tela acompanha o que muda fora dela (ADR 0013). Sem pasta própria: é capacidade que atravessa funcionalidades, e não uma delas |
| [paginas-pessoais](evolury/funcionalidades/paginas-pessoais/especificacao.md)            | Em desenvolvimento — página criada fora de projeto, com abas em Minhas tarefas (F1, ADR 0015). F2 (compartilhar) e F3 (mover) em aberto                         |
