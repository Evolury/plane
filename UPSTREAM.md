# Relação com o Plane CE

Este produto deriva do [Plane Community Edition](https://github.com/makeplane/plane).
Em 11/08/2026 ele deixou de ser um fork que acompanha o upstream e passou a
produto independente: desenvolvimento, roadmap e versionamento próprios.

## A base herdada

|                              |                                                                                     |
| ---------------------------- | ----------------------------------------------------------------------------------- |
| Versão do upstream           | Plane CE `v1.4.1`                                                                   |
| Ponto de corte               | `31853ab2b`, que é a tag `v1.4.1-rc2`                                               |
| Patches próprios até o corte | 30 commits (i18n pt-BR, marca, fuso e formatos brasileiros, imagens docker enxutas) |
| Primeira versão independente | `v1.0.0`                                                                            |

**O corte saiu do candidato, e o candidato virou a release sem uma linha a
mais.** `git diff 31853ab2b v1.4.1` é vazio: os quatro commits que separam um do
outro são todos merges de release, e um dos pais do `release: v1.4.1` é
exatamente o nosso ponto de corte. O Plane desenvolve em `preview`, marca um
`rc`, e ao aprovar mescla em `master` e tagueia — o `rc2` **é** a `v1.4.1`, com
outro nome.

Isso importa para quem for comparar diffs: procurar `31853ab2b` na `master`
deles não encontra nada, porque o commit vive na `preview` e só chega à `master`
pelo merge da release.

O histórico anterior ao corte continua no repositório: `git log v1.4.1` mostra
toda a linha do upstream, e `git log v1.4.1..main` mostra o que é nosso.

## O que "independente" significa aqui

**Não rebaseamos mais sobre o upstream.** Não há sincronização periódica, não
adotamos releases novas do Plane, e a numeração de versão não acompanha a deles.
O `main` é a única linha de desenvolvimento.

**O upstream continua sendo fonte de patches de segurança.** Esta é a
contrapartida da independência, e ignorá-la é o risco real do arranjo: o Plane
CE corrige com frequência falhas que também existem no nosso código, e ninguém
mais vai aplicá-las por nós.

O remote existe só para leitura:

```bash
git remote add upstream https://github.com/makeplane/plane.git   # se ainda não existir
git remote set-url --push upstream DISABLED                      # evita push acidental
git fetch upstream --tags
```

## Acompanhando correções de segurança

Sem cadência fixa não funciona. O mínimo é uma revisão mensal, mais uma checagem
sempre que o upstream publicar release:

```bash
git fetch upstream --tags
git log --oneline v1.4.1..upstream/master              # o que entrou desde o nosso corte
git log --oneline v1.4.1..upstream/master --grep -iE 'secur|CVE|GHSA|vuln|XSS|IDOR|authz'
```

Vale também acompanhar os
[security advisories](https://github.com/makeplane/plane/security/advisories) do
repositório de origem.

## Aplicando um patch do upstream

Cherry-pick pontual, nunca merge de branch inteira:

```bash
git switch -c fix/<descrição-curta> main
git cherry-pick -x <sha>          # -x registra o commit de origem na mensagem
# resolver conflitos: o arquivo daqui pode ter divergido (i18n, marca, defaults)
pnpm check
git push -u origin fix/<descrição-curta>
```

Duas coisas a verificar antes de abrir o PR:

1. **O patch faz sentido no nosso código?** Correções em áreas que já alteramos
   (telemetria, defaults de idioma e fuso, marca) podem chegar sem sentido ou
   reintroduzir algo que removemos de propósito.
2. **O `-x` ficou na mensagem?** É o que permite, meses depois, saber de onde o
   patch veio e conferir se veio inteiro.

Anote no PR o CVE/GHSA correspondente quando houver — vira o registro de que a
falha foi tratada aqui.

## Licença e atribuição

O código é AGPL-3.0-only e continua sendo. Independência é de projeto, não de
licença:

- Os cabeçalhos `Copyright (c) 2023-present Plane Software, Inc. and contributors`
  permanecem nos arquivos herdados. Não troque o titular; em arquivo novo,
  acrescente a linha da Evolury ao lado.
- "Plane" é marca da Plane Software Inc. O produto derivado usa a marca Evolury e
  não pode sugerir endosso ou associação com a empresa de origem.
- A seção 13 da AGPL exige oferecer o código-fonte da versão em execução a quem
  usa a instância pela rede.
