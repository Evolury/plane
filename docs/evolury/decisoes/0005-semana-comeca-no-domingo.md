# ADR 0005 — A semana começa sempre no domingo

- **Status:** Aceito (12/08/2026)
- **Relacionado:** [ADR 0004](0004-idioma-unico-pt-br.md) (idioma único)

## Contexto

O Plane deixa cada usuário escolher o primeiro dia da semana, em dois lugares
(Preferências do perfil e Power-K). O produto atende só o Brasil, onde
calendários convencionalmente começam no domingo — e era assim que o campo já
nascia (`Profile.start_of_the_week` tem domingo como padrão).

Uma preferência que praticamente ninguém muda, exposta em dois lugares, é
configuração sem uso: custa manutenção, ocupa espaço na tela e cria estados
divergentes entre membros da mesma equipe olhando o mesmo calendário.

## Decisão

Domingo, global e fixo. Os dois seletores saem da interface, o campo vira
somente leitura na API (sem tela, um PATCH direto ainda gravaria um valor que
nada corrigiria depois) e a migração `0129` normaliza os perfis existentes.

A coluna **continua no banco** e o `EStartOfTheWeek` continua no código: o
layout de calendário ordena os dias a partir desse valor, então voltar a
oferecer a escolha é reverter o commit — sem migração de esquema.

## Alternativa considerada

**Manter a escolha por usuário.** O argumento a favor é que, em gestão de
projetos, parte das equipes planeja em semana útil e prefere segunda-feira.
Vale registrar que esse é um gosto de equipe, não uma necessidade regional, e
que o Plane já oferece o botão de esconder fins de semana no calendário, que
resolve o mesmo problema sem mudar o início da semana.

## Consequências

- Uma preferência a menos na tela e no Power-K.
- Todos os membros veem o calendário com o mesmo recorte de semana.
- `START_OF_THE_WEEK_OPTIONS` saiu de `@plane/constants` por ficar sem uso —
  os rótulos dos dias vinham em inglês fixo ali, e o calendário nunca dependeu
  deles: ele formata os nomes com `date-fns` no locale pt-BR.
