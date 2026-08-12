# ADR 0006 — Só os fusos horários do Brasil

- **Status:** Aceito (12/08/2026)
- **Relacionado:** [ADR 0004](0004-idioma-unico-pt-br.md) (idioma único),
  [ADR 0005](0005-semana-comeca-no-domingo.md) (início da semana)

## Contexto

O produto atende só o Brasil, e o seletor de fuso do Plane listava 111
localidades do mundo — das quais apenas duas brasileiras. A proposta inicial
era remover o seletor e fixar um fuso único.

**A premissa de fuso único não se sustenta: o Brasil tem quatro offsets.**

| Offset | Onde                                                     | Zona IANA de referência |
| ------ | -------------------------------------------------------- | ----------------------- |
| UTC−2  | Fernando de Noronha                                      | `America/Noronha`       |
| UTC−3  | Brasília e a maior parte do país                         | `America/Sao_Paulo`     |
| UTC−4  | AM (leste), MT, MS, RO, RR                               | `America/Manaus`        |
| UTC−5  | AC e sudoeste do AM                                      | `America/Rio_Branco`    |

Fixar um fuso único deslocaria em uma ou duas horas o horário de quem está em
Manaus, Cuiabá, Campo Grande, Porto Velho, Boa Vista ou Rio Branco — Manaus
sozinha é a 7ª maior cidade do país. Perto da meia-noite, isso joga um prazo
para o dia errado. E falharia em silêncio, sem tela para corrigir.

Agrava: o padrão do upstream era **UTC**, três horas à frente de Brasília —
errado para todo usuário do produto. Em produção, dois dos três usuários
estavam assim.

## Decisão

Manter o fuso configurável, com **uma opção por offset** — quatro no total —
e `America/Sao_Paulo` como padrão. Isso entrega o que se queria (o fim das
400+ zonas do mundo poluindo a tela) sem quebrar quem está fora de Brasília.

| Offset | Opção exibida                        | Zona IANA            |
| ------ | ------------------------------------ | -------------------- |
| UTC−2  | Fernando de Noronha                  | `America/Noronha`    |
| UTC−3  | Brasília, São Paulo, Rio de Janeiro  | `America/Sao_Paulo`  |
| UTC−4  | Manaus                               | `America/Manaus`     |
| UTC−5  | Rio Branco                           | `America/Rio_Branco` |

As outras 12 zonas IANA brasileiras foram dispensadas: elas só diferem das
que ficaram em regras de horário de verão **anteriores a 2019**, quando o país
o aboliu. Para datas de hoje em diante são equivalentes, e a base do produto
começa em 2026 — a migração `0131` remapeia cada uma para a zona que ficou no
mesmo offset, então ninguém muda de hora. Cada opção leva a cidade principal
do offset; o UTC−3, que concentra a maioria das capitais, cita as principais.

A restrição vale em três camadas: o endpoint `/api/timezones/` passa a
devolver só as 16 zonas (o seletor de Preferências e o do Power-K consomem
essa mesma lista), as `choices` do campo passam a ser validadas pelo DRF
(barrando um cliente antigo que tente gravar outra zona) e a migração `0130`
normaliza quem estava fora da lista, preservando quem já estava numa zona
brasileira. A normalização vem antes do `AlterField` de propósito: com
`choices` restritas, um perfil em "UTC" falharia na validação no primeiro
PATCH e o usuário não teria como consertar.

O Brasil aboliu o horário de verão em 2019, então os offsets são estáveis e
não há complexidade adicional de DST.

## Alternativa considerada

**Fixar `America/Sao_Paulo` e remover o seletor**, como foi feito com idioma e
início da semana. Rejeitada: aqueles dois são preferência de exibição com
convenção nacional única; fuso é um fato geográfico que varia dentro do país.
O custo de manter uma lista de 16 itens é próximo de zero, e o custo de errar
é silencioso.

## Consequências

- A opção "UTC" avulsa saiu do seletor no front — não é fuso do Brasil.
- Os fallbacks de interface que apontavam para `Asia/Kolkata` (herança do
  upstream) passaram a `America/Sao_Paulo`.
- Fusos de workspace, projeto e ciclo continuam com a lista completa do pytz:
  são outro fluxo e não foram tocados aqui.
