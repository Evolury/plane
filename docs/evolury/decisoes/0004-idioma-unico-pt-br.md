# ADR 0004 — pt-BR como idioma único e fixo

- **Status:** Aceito (12/08/2026)
- **Relacionado:** [ADR 0003](0003-terminologia-tarefa-pt-br.md) (terminologia)

## Contexto

O produto atende o Brasil e é escrito em português. O Plane herdado traz 19
idiomas, um seletor no perfil e outro no Power-K.

A medição feita antes da decisão mostrou o custo real disso:

| Fato                                                      | Valor                    |
| --------------------------------------------------------- | ------------------------ |
| Idiomas mantidos                                          | 19                       |
| Arquivos de tradução                                      | 532 (28 namespaces × 19) |
| Tamanho em disco                                          | 7,8 MB                   |
| **Strings idênticas ao inglês nos 17 idiomas não usados** | **~23% de cada um**      |
| Strings idênticas ao inglês no pt-BR                      | 2% (nomes próprios)      |

Ou seja: o upstream nunca completou nenhum dos outros idiomas — cerca de uma
em cada quatro strings aparece em inglês. Manter isso não entrega valor a
ninguém e cobra pedágio em cada PR, porque a paridade de chaves é obrigatória
no CI (`i18n-sync-check`): uma chave nova exige tradução para 18 idiomas.

## Decisão

1. **pt-BR é o único idioma, sem opção de troca.** `SUPPORTED_LANGUAGES` passa
   a ter uma entrada, o que também reduz o `supportedLngs` do i18next — outros
   valores são recusados no runtime. O tipo `TLanguage` vira `"pt-BR"`, para o
   compilador recusar antes.
2. **Os dois seletores saem da interface** (Preferências do perfil e Power-K).
   Fuso horário e início da semana continuam configuráveis.
3. **As três fontes de idioma passam a concordar:** o `localStorage` é
   normalizado no boot (quem trocou de idioma antes não fica preso ao valor
   antigo), o perfil não sincroniza mais idioma para a UI, e o campo
   `Profile.language` vira somente leitura na API — sem seletor, um PATCH
   direto ainda conseguiria gravar um valor que nenhuma tela corrigiria. A
   migração `0128` normaliza os perfis existentes.
4. **Os 17 idiomas não usados saem do repositório** — 476 arquivos, 7 MB, e
   outros tantos _chunks_ a menos no build.
5. **O locale `en` fica**, sem ser selecionável. Ele é a fonte das chaves para
   as duas ferramentas do pacote: `generate-types.ts` deriva dele a união de
   chaves do TypeScript e `sync-check.ts` o usa como referência. Com ele no
   lugar, o CI segue funcionando e ganha um propósito melhor: garantir que o
   **pt-BR** não esqueceu nenhuma chave.

## Consequências

- Chave nova exige dois valores (en e pt-BR) em vez de 19 traduções.
- O `i18n-sync-check` continua no CI, agora como guarda de completude do pt-BR.
- Textos fora do pacote de i18n **não** são cobertos por esta decisão: os
  e-mails são templates Django em inglês (`apps/api/templates/emails/`) e
  seguem como estão até uma tarefa própria.
- Reversível: os arquivos removidos continuam no histórico do git, e voltar um
  idioma é reverter o commit e reinserir a entrada em `SUPPORTED_LANGUAGES`.
