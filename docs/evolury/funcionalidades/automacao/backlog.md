# Automações personalizadas — backlog de implementação

Decisão: [ADR 0012](../../decisoes/0012-automacoes-personalizadas.md).
Manual: [manual.md](manual.md).
Plano aprovado em 16/08/2026, com as três respostas do dono do produto:
gatilho agendado **no v1**, ação de criar tarefa **completa**, notificar
**no produto e por e-mail**.

As três fases juntas são o v1 aprovado. Cada uma é publicável sozinha.

## F1 — O motor e a reação

- [x] F1.1 Modelos `Automation` e `AutomationRun`, com índice de despacho
      (projeto + gatilho + ativa) e de histórico (regra + data)
- [x] F1.2 Migração `0143_evolury_automacoes`
- [x] F1.3 `condicao.py` — o "se" como o filtro do produto aplicado a uma tarefa
      só, reusando `FiltroComPropriedades`
- [x] F1.4 `gatilhos.py` — tradução do vocabulário do histórico para o do filtro,
      casamento por **id**, teto de profundidade, autoguarda da regra
- [x] F1.5 `acoes.py` — registro de ações; as seis de campo, todas pelo
      `IssueCreateSerializer`
- [x] F1.6 `ator.py` — usuário-robô por workspace
- [x] F1.7 `despacho.py` — o enxerto único dentro de `issue_activity`, com
      descarte barato
- [x] F1.8 Correção da lacuna das propriedades personalizadas: a gravação de
      valor não passava por `issue_activity` e usava o **nome** como campo
- [x] F1.9 `automation_task.py` — avaliação, execução, registro, teto por hora
- [x] F1.10 `validacao.py` + serializer — regra malformada recusada com frase
- [x] F1.11 API: CRUD, `/runs`, `/simulate`
- [x] F1.12 Declaração em `CELERY_IMPORTS`
- [x] F1.13 Lista na tela de Automações, com a regra **dita em português**
- [x] F1.14 Editor em rota própria: QUANDO / SE / ENTÃO, frase viva, simulação
- [x] F1.15 Painel de execuções
- [x] F1.16 Testes de contrato (32), com defeitos reintroduzidos para provar que
      não são vazios
- [x] F1.17 Verificação visual ponta a ponta no `planedev`

## F2 — O relógio e a voz

- [ ] F2.1 Gatilho agendado: `trigger_config` com frequência, dias e horário no
      fuso do produto (ADR 0006); `next_run_at` e tarefa no Celery beat a cada
      15 min, mesma cadência das recorrentes
- [ ] F2.2 Execução em lote: uma linha de `AutomationRun` resume a rodada, com
      as tarefas alcançadas em `actions_result`
- [ ] F2.3 Ação **comentar**, com a lista fechada de variáveis
      (`{{tarefa}}`, `{{responsável}}`, `{{quem_disparou}}`, `{{estado}}`,
      `{{vencimento}}`) — sem funções, sem aninhamento
- [ ] F2.4 Ação **notificar**: `Notification` no sino + fila de e-mail existente
- [ ] F2.5 Ação **arquivar**
- [ ] F2.6 Ação **incluir no ciclo ativo / módulo**
- [ ] F2.7 Editor do gatilho agendado, e simulação que mostra a próxima rodada

## F3 — Criação e ergonomia

- [ ] F3.1 Ação **criar tarefa** e **criar subtarefas**, com as travas de laço e
      a checagem estática "criada + criar tarefa no mesmo projeto"
- [ ] F3.2 Aviso na tela quando a regra for _agendada + criar tarefa_, apontando
      para Tarefas recorrentes (ADR 0010), que faz esse trabalho melhor
- [ ] F3.3 Catálogo de receitas prontas no estado vazio (as constantes já estão
      escritas em `packages/constants/src/automacao.ts`, sem tela ainda)
- [ ] F3.4 Poda de `AutomationRun` antigo em `cleanup_task.py`, como os logs de
      API

## Dívidas conhecidas

- [ ] O detalhe de `set_assignees` e `set_labels` no registro mostra contagem
      ("1 → 2 responsável(is)"), e não nomes. Legível, mas menos útil que o de
      estado, que já mostra nomes.
- [ ] `RECEITAS_DE_AUTOMACAO` existe em constantes e ainda não é consumido por
      tela nenhuma (F3.3). Está declarado como `as const` e não afeta o bundle
      de quem não usa, mas é código sem chamador até a F3.
