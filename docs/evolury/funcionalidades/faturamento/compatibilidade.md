# Faturamento — matriz de compatibilidade

- **Decisão:** [ADR 0021](../../decisoes/0021-faturamento-por-assinatura.md)

Checklist executado antes de considerar a funcionalidade entregue. `[ ]` é item
a verificar; `[!]` é ponto que já se sabe que precisa de trabalho.

## O que a trava atravessa

O faturamento é a primeira coisa neste fork que diz **não** a uma escrita por
motivo que não é permissão nem regra de negócio. Todo caminho de escrita passa a
ter um estado a mais para respeitar.

| Recurso                                                                                                                                    | Interação                                                                                                                                             | Situação |
| ------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------- | -------- |
| Exclusão em massa e desfazer ([ADR 0018](../../decisoes/0018-exclusao-em-massa.md))                                                        | Escrita: recusada em `restrita` e `bloqueada`                                                                                                         | `[ ]`    |
| Preenchimento em massa ([ADR 0019](../../decisoes/0019-preenchimento-em-massa.md))                                                         | Idem, incluindo o endpoint de propriedade                                                                                                             | `[ ]`    |
| Propriedades personalizadas ([ADR 0011](../../decisoes/0011-propriedades-personalizadas.md))                                               | Teto por plano (5 ou 30). Quem cai de plano acima do teto **não perde** propriedade: para de criar                                                    | `[!]`    |
| Automações ([ADR 0012](../../decisoes/0012-automacoes-personalizadas.md))                                                                  | Teto de regras ativas (2 ou sem teto) — trava nova. E: regra **não executa** em `restrita`/`bloqueada`, e não há reprocessamento retroativo ao voltar | `[!]`    |
| Tarefas recorrentes ([ADR 0010](../../decisoes/0010-tarefas-recorrentes.md))                                                               | A geração é escrita por rotina: **não gera** enquanto restrito, e ao voltar retoma da data corrente, sem preencher o buraco                           | `[!]`    |
| Etapas por vencimento ([ADR 0014](../../decisoes/0014-etapas-por-vencimento.md))                                                           | A varredura escreve, mas escreve estado **derivado**: continua rodando, para que o que se lê continue coerente                                        | `[!]`    |
| Páginas pessoais ([ADR 0015](../../decisoes/0015-paginas-pessoais.md))                                                                     | Edição passa pelo servidor de tempo real — ver abaixo                                                                                                 | `[!]`    |
| Tempo real ([ADR 0013](../../decisoes/0013-atualizacao-em-tempo-real.md))                                                                  | Ler continua; a difusão de mudança dos outros continua                                                                                                | `[ ]`    |
| Recebidos (intake)                                                                                                                         | Criação vinda de fora do espaço também é escrita: recusada em `restrita`                                                                              | `[!]`    |
| Anexos e capas ([ADR 0017](../../decisoes/0017-capa-e-identidade-visual.md), [ADR 0020](../../decisoes/0020-qoowork-nome-e-identidade.md)) | Upload é escrita: recusado                                                                                                                            | `[ ]`    |
| Exportação                                                                                                                                 | **Funciona em todos os estados**, até a remoção. É o que torna o bloqueio defensável                                                                  | `[!]`    |
| Analytics                                                                                                                                  | Recurso de plano: 402 no servidor, escondido na tela                                                                                                  | `[ ]`    |
| Webhooks de saída e API pública                                                                                                            | Recurso de plano. Token existente **para de funcionar** ao cair para o Essencial — o plano é conferido no disparo, não só na criação                  | `[!]`    |
| Convite de membro                                                                                                                          | Nunca bloqueado por assento; bloqueado por estado restrito                                                                                            | `[ ]`    |
| Convite de convidado                                                                                                                       | Bloqueado ao estourar a cota, dizendo qual plano a aumenta                                                                                            | `[ ]`    |

## O buraco do servidor de tempo real

Página é editada pelo `apps/live`, que salva chamando de volta a API
([database.ts:72](../../../../apps/live/src/extensions/database.ts#L72),
`storeDocument` → `updateDescriptionBinary`). O middleware **pega** essa
chamada, então o dado não escapa da trava — mas o que o usuário vê é
"Unable to save the page. Please try again." depois de ter digitado.

O live já sabe distinguir `page_locked` e `page_archived` e avisar direito. O
espaço restrito precisa do mesmo tratamento: um código próprio, uma mensagem que
diz o motivo, e o editor entrando em modo de leitura **antes** de aceitar
digitação — não depois de perdê-la.

`[!]` Item obrigatório da E5. Sem ele, "somente leitura" vira perda de trabalho.

## Dois relógios que não são o mesmo

| Relógio                                                                         | O que apaga                   | Prazo   |
| ------------------------------------------------------------------------------- | ----------------------------- | ------- |
| `HARD_DELETE_AFTER_DAYS` ([ADR 0018](../../decisoes/0018-exclusao-em-massa.md)) | Item excluído pelo usuário    | 60 dias |
| `remover_dados_em` (ADR 0021)                                                   | Espaço com contrato encerrado | 90 dias |

`[ ]` Verificar que a purga diária das 00:00 UTC e a régua das 00:30 não
disputam o mesmo espaço: a régua encerra, a purga não conhece assinatura.

## God-mode e instância

`[ ]` A trava é do espaço, **nunca** da instância: administrador de instância
continua entrando em tudo, inclusive num espaço bloqueado — é assim que o
financeiro conserta o que quebrar.

`[ ]` `InstanceWorkSpaceEndpoint` passa a juntar assinatura. Verificar que
continua em uma consulta, sem N+1.

## Desempenho

`[ ]` A leitura de direito entra em caminho quente (criar tarefa, convidar,
carregar espaço). Cache em Redis com invalidação no webhook e na troca de plano;
medir o custo acrescentado numa criação de tarefa antes e depois.

`[ ]` O middleware resolve o par slug → status a cada requisição. Mesma
medição, no percentil 95.

## Pendências desta matriz

1. `[!]` Confirmar no sandbox se checkout recorrente aceita PIX — a documentação
   diz que não, e a v1 assume que não.
2. `[!]` Decidir se automação e recorrência **acumulam** o que não rodou durante
   a restrição. A proposta é não acumular, e é decisão de produto, não detalhe.
3. `[!]` Espaços que já existem hoje precisam de classificação um a um antes de
   a régua ser ligada — senão o primeiro dia de faturamento restringe cliente
   pagante.
