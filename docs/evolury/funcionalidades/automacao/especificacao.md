# Automações personalizadas — especificação

Decisão: [ADR 0012](../../decisoes/0012-automacoes-personalizadas.md).
Comportamento de tela: [manual.md](manual.md).
Estado da implementação: [backlog.md](backlog.md).

## O problema

O menu de Automações entrega duas caixas fixas — arquivar e fechar tarefas
paradas. Não há como o time descrever o próprio processo. O recurso existe para
fechar essa lacuna, e ele é o principal argumento comercial do produto: é o que
separa um gerenciador de tarefas de uma ferramenta de processo.

## O modelo

Uma regra é **evento, condição, ação** (padrão ECA), guardada em `Automation`:

| Campo            | O que é                                                               |
| ---------------- | --------------------------------------------------------------------- |
| `trigger_type`   | `work_item_created`, `field_changed`, `comment_added`, `scheduled`    |
| `trigger_config` | forma depende do gatilho; validada no serializer                      |
| `condition`      | **a mesma árvore JSON que o quadro manda em `filters`**; nulo = todas |
| `actions`        | lista ordenada de `{type, config}`; o registro `ACOES` é a allowlist  |

E `AutomationRun` guarda cada execução — inclusive a que parou na condição.

## O fluxo

```
alguém edita uma tarefa
        │
        ▼
issue_activity  (124 chamadores, 24 arquivos, uma tarefa Celery)
        │  grava as linhas de IssueActivity
        ▼
despacho.despachar_atividades          ← o único enxerto
        │  desiste barato: teto de profundidade, tipo de evento,
        │  EXISTS de regra viva, mudanças traduzíveis
        ▼
avaliar_automacoes  (fila)
        │
        ├── gatilhos.automacao_casa    → o QUANDO
        ├── condicao.casa              → o SE  (filtro do produto, 1 tarefa)
        └── acoes.executar             → o ENTÃO (IssueCreateSerializer)
                    │
                    ▼
              AutomationRun            → o registro que responde
                                         "por que não rodou?"
```

## Vocabulário: id, nunca rótulo

O histórico grava nomes (para gente ler); a regra casa por id (para não quebrar
com rename). `gatilhos.CAMPO_DO_HISTORICO` faz a tradução num lugar só, e
`CAMPOS_POR_ID` diz quais campos comparam `*_identifier` em vez de `*_value`.

Propriedade personalizada usa a chave `property_<uuid>`, a mesma do filtro.

## Travas

| Trava                         | Cobre                                              | Onde                            |
| ----------------------------- | -------------------------------------------------- | ------------------------------- |
| Regra não responde a si mesma | laço de um elo                                     | `gatilhos.automacao_casa`       |
| Teto de profundidade 3        | ciclo entre regras distintas                       | `gatilhos.TETO_DE_PROFUNDIDADE` |
| Teto de 200 execuções/hora    | edição em massa, ciclo que escapou das duas acima  | `automation_task`               |
| Ação sem efeito é descartada  | atividade falsa, webhook falso, ciclo que converge | cada ação                       |

## Fronteiras declaradas

- **Sem linguagem de expressão.** As _smart values_ do Jira são uma linguagem
  com depurador próprio.
- **Sem se/senão dentro da regra.** Duas regras.
- **Sem espera.** O gatilho agendado (F2) cobre o caso.
- **Sem requisição web de saída.** O produto já tem webhook; um POST arbitrário
  numa caixa de texto é SSRF.
- **Sem ramificação em tarefas relacionadas.** Subtarefa entra só na criação (F3).
