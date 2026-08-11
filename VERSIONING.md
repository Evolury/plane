# Versionamento e release

## Esquema

[Semver](https://semver.org/lang/pt-BR/) próprio, começando em `1.0.0`. O número
não guarda relação com a versão do Plane CE: a base herdada é fato de histórico,
registrado em [UPSTREAM.md](UPSTREAM.md), não parte da identidade da versão.

| Incremento          | Quando                                                                                                                                 |
| ------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| **major** (`2.0.0`) | Quebra de compatibilidade que exige ação de quem opera: migração manual, mudança de contrato de API pública, remoção de funcionalidade |
| **minor** (`1.1.0`) | Funcionalidade nova, mudança de comportamento visível ao usuário, atualização relevante de dependência                                 |
| **patch** (`1.0.1`) | Correção de bug, ajuste de tradução, melhoria interna sem efeito visível                                                               |

Correção de segurança sobe **patch**, salvo quando vier junto de mudança que
exija ação de quem opera.

## Onde a versão vive

| Lugar                                              | Como                                                                                   |
| -------------------------------------------------- | -------------------------------------------------------------------------------------- |
| `package.json` (20 arquivos: raiz, apps e pacotes) | Todos no mesmo número, sempre                                                          |
| Tag git                                            | `v1.0.0`                                                                               |
| Imagem docker                                      | `1.0.0` (mesma string, sem o `v`)                                                      |
| `APP_VERSION`                                      | Opcional no ambiente; quando definida, ganha do `package.json` na exibição do god-mode |

As tags `v0.x`–`v1.4.1` presentes no repositório são do upstream, anteriores ao
corte. Não reutilize esses números.

## Processo de release

```bash
git switch -c release/v1.1.0 main
# bump nos 20 package.json e entrada nova no CHANGELOG.md
git commit -m "chore(release): versão 1.1.0"
git push -u origin release/v1.1.0
```

Abra o PR para `main`. O workflow `check-version` roda **apenas** em PR cuja
branch comece com `release/` e falha se a versão não tiver mudado em relação à
`main` — por isso o nome da branch importa.

Depois do merge:

```bash
git switch main && git pull
git tag v1.1.0 && git push origin v1.1.0
```

O `CHANGELOG.md` é escrito no PR de release, a partir dos commits que entraram
desde a tag anterior:

```bash
git log --format='%s' v1.0.0..main
```

Como todo commit segue conventional commits, o agrupamento sai direto do prefixo
(`feat`, `fix`, `i18n`, `build`, `chore`).

## Fluxo de branches

- `main` — única linha de desenvolvimento; protegida, só recebe merge via PR.
- `<tipo>/<descrição-curta>` — trabalho do dia a dia, saindo de `main`
  (`feat/`, `fix/`, `chore/`, `refactor/`, `docs/`, `perf/`, `i18n/`).
- `release/vX.Y.Z` — só o bump de versão e o changelog.

Merge de PR é **squash**: um commit por PR em `main`. As mensagens dos commits
de trabalho viram o corpo da mensagem final, então vale escrevê-las com cuidado.

`preview`, `master` e `canary` são nomes do upstream. Não use nenhum deles.
