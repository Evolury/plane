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
- [evolury/backlog-tecnico.md](evolury/backlog-tecnico.md) — dívida que atravessa funcionalidades, com o número medido de cada item

| Funcionalidade                                                                           | Status                                                                                                                                                                                                              |
| ---------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [minhas-tarefas](evolury/funcionalidades/minhas-tarefas/especificacao.md)                | Entregue na v1.1.0 — F0–F6; etapa pela janela da tarefa na v1.2.0 (F7); movimentação diária pelo vencimento na v1.26.0 (F8, ADR 0014). Backlog sem item aberto                                                      |
| [terminologia-tarefa](evolury/funcionalidades/terminologia-tarefa/backlog.md)            | Entregue na v1.2.0 — ADR 0003                                                                                                                                                                                       |
| [concluir-tarefa](evolury/funcionalidades/concluir-tarefa/backlog.md)                    | Entregue nas v1.3.0–v1.7.0 — botão, ciclo de vida da etapa pessoal e etapa de conclusão do projeto (ADR 0009)                                                                                                       |
| [tarefa-recorrente](evolury/funcionalidades/tarefa-recorrente/manual.md)                 | Entregue na v1.7.0, redesenhada na v1.8.0 — recorrência na tarefa (ADR 0010); F5 e o responsável padrão saíram na v1.9.0                                                                                            |
| [propriedade-personalizada](evolury/funcionalidades/propriedade-personalizada/manual.md) | Entregue na v1.13.0 — campos próprios por projeto, com filtro, agrupamento e ordenação (ADR 0011). Na v1.29.0, virou eixo do quadro: subagrupamento, agrupar como opt-in da definição e arrastar para mudar o valor |
| [automacao](evolury/funcionalidades/automacao/manual.md)                                 | Entregue na v1.18.0 — regras quando / se / então, com as três fases do backlog concluídas (ADR 0012)                                                                                                                |
| [atualização em tempo real](evolury/decisoes/0013-atualizacao-em-tempo-real.md)          | Entregue nas v1.21.0–v1.25.0 — a tela acompanha o que muda fora dela (ADR 0013). Sem pasta própria: é capacidade que atravessa funcionalidades, e não uma delas                                                     |
| [paginas-pessoais](evolury/funcionalidades/paginas-pessoais/especificacao.md)            | F1–F3 concluídas — página fora de projeto com abas em Minhas tarefas, compartilhamento por pessoa e movimentação nos dois sentidos (ADR 0015). Backlog sem item aberto                                              |
| [um-responsavel](evolury/funcionalidades/um-responsavel/especificacao.md)                | Concluída, sai na próxima release — uma tarefa tem um responsável, garantido por índice no banco (ADR 0016). Backlog sem item aberto                                                                                |
| [faturamento](evolury/funcionalidades/faturamento/especificacao.md)                      | Planejada — assinatura por espaço de trabalho, três planos e travas por plano, com pagamento pelo Asaas (ADR 0021). Especificação, arquitetura e backlog aprovados em 21/08/2026; implementação em E1               |
