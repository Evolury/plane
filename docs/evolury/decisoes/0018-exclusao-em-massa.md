# ADR 0018 — Excluir em massa é a mesma exclusão, e dá para desfazer

- **Status:** Aceito (20/08/2026)
- **Relacionado:** [ADR 0009](0009-botao-concluir-tarefa.md) (concluir, e a barra da seleção), [ADR 0013](0013-atualizacao-em-tempo-real.md) (aviso de mudança)

## Contexto

A seleção múltipla já existia inteira: caixas nos layouts de lista, planilha e
cronograma, faixa por `shift+clique`, seleção por grupo. O que não existia era o
que fazer com ela — no Plane, as operações em massa são da edição paga, e o
lugar da barra era ocupado por uma faixa de propaganda. O ADR 0009 pôs ali o
primeiro botão, "Concluir".

Faltava excluir. E, ao olhar, o produto tinha as peças e nenhuma porta:

| Peça                                                       | Situação                                                        |
| ---------------------------------------------------------- | --------------------------------------------------------------- |
| `DELETE …/bulk-delete-issues/`                             | existia                                                         |
| `bulkDeleteIssues` no cliente, `removeBulkIssues` no store | existiam                                                        |
| Modal de confirmação                                       | existia                                                         |
| Quem abria o modal                                         | **ninguém** — a única referência no repositório era o `onClose` |

Pior: o endpoint **não fazia o que a exclusão de uma tarefa faz**. Medido, lendo
os dois caminhos:

|                                           | Uma tarefa                      | Em massa (antes) |
| ----------------------------------------- | ------------------------------- | ---------------- |
| Permissão                                 | administrador **ou quem criou** | só administrador |
| Cascata (subtarefas, comentários, anexos) | sim                             | **não**          |
| Histórico                                 | sim                             | **não**          |
| Notificação e tempo real                  | sim                             | **não**          |

A diferença nasce de uma sutileza: `issue.delete()` numa INSTÂNCIA dispara a
cascata; `issues.delete()` num QUERYSET só escreve `deleted_at`. Pelo caminho em
massa, a subtarefa continuava viva apontando para um pai que não existe mais.

## A decisão

**1. A quantidade não muda a regra.** Excluir dez é excluir uma, dez vezes:
mesma cascata, mesmo histórico, mesmo aviso de tempo real, mesma permissão —
administrador do projeto ou quem criou a tarefa.

**2. Recusa inteira, nunca parcial.** Se alguma tarefa da seleção não for de
quem pediu, o pedido todo é recusado. Excluir 8 de 10 sem dizer quais ficaram é
pior que não excluir nada. A barra ajuda antes disso: só oferece o que a pessoa
pode excluir, e o modal diz quantas ficaram de fora.

**3. Teto de 500 por pedido.** Não é limite de banco — é limite de
arrependimento. Seleção maior que isso é quase sempre um "selecionar tudo" que
ninguém leu.

**4. A cascata é por conjunto de linhas, e as relações são descobertas.** Uma
consulta por relação, não uma por tarefa: com 300 selecionadas, o caminho do
upstream faria milhares de idas ao banco dentro da requisição. E a lista de
relações é lida do modelo — das 33 relações reversas de `Issue`, **seis são
deste fork**, e a próxima entraria sem que ninguém lembrasse de atualizar uma
lista escrita à mão.

**5. O instante é a identidade do lote.** Todas as linhas de uma exclusão
recebem exatamente o mesmo `deleted_at`. É isso — e só isso — que torna o
desfazer possível **sem coluna nova**: restaurar é limpar `deleted_at` onde ele
vale aquele instante.

**6. Desfazer faz parte da entrega.** A exclusão aqui sempre foi suave: o
expurgo definitivo só passa 60 dias depois (`HARD_DELETE_AFTER_DAYS`). O dado
estava lá o tempo todo; faltava a porta. O aviso de sucesso traz "Desfazer" e
fica na tela mais tempo que um aviso comum — uma saída que some antes de ser
vista não é uma saída.

**7. `SET_NULL` fica como está** — e aqui divergimos do upstream de propósito. A
cascata dele anula os campos que apontam para a tarefa (`IssueSequence.issue`,
`AutomationRun.issue`, …). Anular é perda que nenhum desfazer traz de volta:
coisa de exclusão definitiva, não de exclusão reversível. Quem aponta para uma
tarefa excluída não a enxerga de qualquer forma.

**8. Não notifica por item.** A exclusão de uma tarefa avisa quem a acompanha, e
faz sentido: é um evento. Duzentas de uma vez são uma limpeza, e duzentos avisos
para a mesma pessoa transformariam a caixa de entrada em lixo. O histórico
registra tudo, e é lá que se procura o que aconteceu.

## O que a pesquisa mudou no desenho

A [documentação do Plane Cloud](https://docs.plane.so/core-concepts/issues/bulk-ops)
descreve a barra com atualização de propriedades, cópia (até 1000), inscrição,
arquivamento e exclusão — esta última com o aviso de que "não pode ser
desfeita", e nada mais.

A orientação da [NN/g](https://www.nngroup.com/articles/confirmation-dialog/) é
que diálogo de confirmação se justifica no que é grave e irreversível, mas que
**desfazer é melhor que perguntar** quando existe como voltar atrás; que o texto
precisa dizer o número e a consequência, e não "tem certeza?"; e que confirmação
digitada se reserva ao raro e severo, porque usada sempre vira reflexo.

Daí o desenho: confirmação **com o número e o que vai junto**, botão com verbo
(`Excluir 12 tarefas`), saída segura no `Cancelar` — e, depois, o desfazer. Sem
confirmação digitada: com o desfazer na mão, ela só cobraria atrito sem comprar
segurança.

## Consequências

- **Custo de sincronia com o upstream**: o endpoint reescrito, uma rota nova, e
  a declaração de `removeBulkIssues` que morava repetida em nove interfaces do
  front passou a morar na interface base. Nenhuma migração.
- **A API v1 pública não ganha o desfazer.** Integração que exclua continua
  excluindo pelo caminho de uma tarefa por vez.
- **Só onde a exclusão faz sentido**: a barra não aparece em arquivados nem em
  rascunhos, e o endpoint não os alcança.
- **Fora de escopo**: copiar, inscrever e editar propriedades em massa. Arquivar
  em massa continua sem gatilho na interface, como estava.
- **O worker precisa conhecer a tarefa nova.** Um worker antigo em pé descarta a
  mensagem com "unregistered task", e o efeito é silencioso: a exclusão
  acontece, o histórico não. Foi visto no `planedev` com um worker de 15 horas —
  o deploy reinicia os processos, então não alcança produção, mas é o tipo de
  coisa que só aparece quando se mede.
