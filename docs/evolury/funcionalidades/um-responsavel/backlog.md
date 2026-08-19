# Um responsável por tarefa — backlog

Plano aprovado em 19/08/2026. Especificação em
[especificacao.md](especificacao.md), decisões no
[ADR 0016](../../decisoes/0016-um-responsavel-por-tarefa.md).

## F1 — A garantia

- [x] F1.1 Índice único parcial em `IssueAssignee` e `DraftIssueAssignee`
- [x] F1.2 Migração `0147` com **colapso antes da trava** — sem ele quebraria em
      qualquer banco que já tivesse tarefa com dois
- [x] F1.3 `apenas_um()` nas cinco portas de escrita, e nas recorrentes e nos
      dados de exemplo — o segundo sorteava vários
- [x] F1.4 A normalização entra **antes** da validação de "é membro do projeto?",
      que reordena pelo que o banco devolve
- [x] F1.5 Testes com defeito reintroduzido, um de cada vez

## F2 — A tela

- [x] F2.1 `AssigneeDropdown` próprio, em vez de tirar `multiple` em onze pontos:
      a regra fica num lugar só
- [x] F2.2 Automação com uma pessoa, sem o modo "somar"
- [x] F2.3 Variável `{{responsável}}` no singular
- [x] F2.4 **O histórico lia o pedido e anunciava duas pessoas** quando só uma
      era gravada; passou a ler o banco

## F3 — Rótulos

- [x] F3.1 Campos de uma tarefa no singular; filtros seguem no plural, porque
      filtrar por responsável pode selecionar várias pessoas

## Descobertas do ciclo

- **A suíte roda com `--nomigrations`**: o banco de teste vem dos modelos, e as
  migrações nunca são executadas. Apareceu porque a primeira injeção de defeito
  não derrubou nada. A regra de colapso foi extraída para `excedentes()` para ter
  teste, e a migração foi verificada contra a instância real.
- **Dois testes existentes mudaram de premissa**, e não foram apagados: o que
  eles provavam deixou de ser possível. Ver o ADR.

## Fora de escopo

- **Trocar o M2M por chave estrangeira** — a garantia seria a mesma, e o custo
  seria reescrever todo caminho de leitura, quebrar a API pública e o formato do
  histórico, e conflitar com o upstream para sempre.
- **Tornar responsável obrigatório** — tarefa sem dono é como triagem funciona.
