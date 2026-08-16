# Desenvolvimento e validação local

Como subir o ambiente para validar uma mudança visualmente, e as três armadilhas
que já custaram retrabalho. Escrito depois da terceira vez.

## As duas stacks

| Stack           | Para quê                          | Como                                                                       |
| --------------- | --------------------------------- | -------------------------------------------------------------------------- |
| **`planetest`** | pytest da API                     | `pnpm test:api` (ou `bin/testes-api.sh`), que **para a stack ao terminar** |
| **`planedev`**  | banco e API para validação visual | `docker compose -p planedev up -d`                                         |

Os dois arquivos declaram `name:` próprio desde 14/08/2026, então não é mais
preciso lembrar do `-p`. **Compose novo neste repositório nasce com `name:`** —
sem ele o Compose deriva o nome do diretório, que é `plane`, o mesmo da
produção que roda nesta máquina. Ver [ADR de infraestrutura no histórico do PR
#88](https://github.com/Evolury/plane/pull/88).

## O front

```bash
pnpm turbo run dev --filter=web... --concurrency=15
```

O `--concurrency=15` não é enfeite: são 11 tarefas persistentes, e o padrão de
10 faz o comando abortar antes de começar.

**Espere o `200`, e não o processo.** O servidor aceita conexão antes de os
pacotes compartilhados terminarem de construir; validar nesse intervalo dá
"Failed to load url … Does the file exist?" e parece defeito do código.

```bash
until [ "$(curl -s -o /dev/null -w '%{http_code}' --max-time 3 http://localhost:3000/)" = "200" ]; do sleep 5; done
```

## A armadilha que custou três vezes

**Nunca rode `build` de um pacote compartilhado com o dev server no ar.**

```bash
pnpm --filter=@plane/types run build     # ❌ com o dev rodando
```

O motivo está nos próprios scripts do pacote:

| Script  | Comando                     | O que faz com o `dist`    |
| ------- | --------------------------- | ------------------------- |
| `dev`   | `tsdown --watch --no-clean` | reconstrói **sem apagar** |
| `build` | `tsdown`                    | **apaga e reconstrói**    |

O `turbo run dev` já sobe o watcher de cada pacote. O `build` manual apaga o
`dist` que o Vite está segurando, e a tela vira um overlay vermelho que não tem
nada a ver com a mudança em análise.

**Salvar o arquivo basta.** Conferido em 14/08/2026: editar
`packages/types/src/…` reconstruiu o `dist` sozinho, sem nenhum comando.

Se o dev **não** estiver no ar, `build` é seguro e às vezes necessário — por
exemplo antes de rodar `check:types` num terminal limpo.

## O driver de navegador

`playwright-core` não está instalado neste repositório. O caminho provado:

```bash
NODE_PATH=/home/tassio/Projetos/evolury/painel-central/node_modules/.pnpm/playwright-core@1.60.0/node_modules \
  node driver.js
```

com `executablePath: "/home/tassio/.local/bin/google-chrome"` e `headless: true`.

## A API do `planedev` pode ficar velha

O container monta o código e o Django recarrega sozinho — mas o autoreloader
**perde mudanças** quando muitos arquivos mudam de uma vez, ou quando um
`git switch` reescreve a árvore no instante em que ele reinicia. O sintoma é um
500 com `'X' object has no attribute 'y'`: rota nova, módulo velho.

O sintoma nem sempre é 500. Em 16/08/2026 ele apareceu como **filtro que não
filtra**: a requisição saía correta, a resposta voltava com a contagem inteira,
e o mesmo filtro rodado num `manage.py shell` — processo novo, código novo —
devolvia o resultado certo. Divergência entre o shell e o servidor é assinatura
de módulo velho.

Antes de investigar um 500 estranho na stack de desenvolvimento:

```bash
docker compose -p planedev restart api
```

Isso **não** acontece em produção: lá a API roda de imagem construída, sem
`bind mount` e sem autoreloader.

## Abrir o dev de outro computador

Três coisas precisam estar certas, e as três já estão no repositório ou no
`.env` local:

| O quê                       | Onde             | Por quê                                                                                                                                                                                            |
| --------------------------- | ---------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `--host 0.0.0.0`            | linha de comando | o padrão do `vite.config.ts` é só `localhost`                                                                                                                                                      |
| `allowedHosts: [".ts.net"]` | `vite.config.ts` | o Vite 6 confere o `Host` contra DNS rebinding e **só aceita `localhost` e IPs** — pelo nome do tailnet ele devolve **403 da própria aplicação**, o que parece problema de rede e não é            |
| `proxy` de `/api` e `/auth` | `vite.config.ts` | com `VITE_API_BASE_URL` vazio, cada chamada segue o host pelo qual a página foi aberta; sem isso a URL da API fica fixa num endereço e quem abre por outro carrega a tela sem falar com o servidor |

Com isso, `localhost`, IP da rede e nome do tailnet funcionam **ao mesmo tempo**,
e o CORS deixa de existir no caminho: mesma origem, como em produção.

Falta um detalhe que **não** dá para resolver no `vite.config.ts`: o
redirecionamento pós-login é montado pelo servidor, a partir de `APP_BASE_URL`.
Ele é um endereço só. Aponte-o para o endereço que você usa de fora (em
`apps/api/.env`), senão o login termina num host que a máquina remota não
alcança.

Pela rede local ainda é preciso liberar a porta no firewalld — a interface da
LAN fica na zona `FedoraWorkstation`, que não abre TCP alto; a `tailscale0` está
na zona `trusted`, e por isso o tailnet funciona sem nada.

## Corrigido: o seletor de filtros e o `StrictMode`

Até 15/08/2026, clicar no funil não abria nada com `pnpm dev`, e o console
registrava `Filters toggle error - filter instance not available`. O contorno
era desligar o `StrictMode` — e está aqui porque a **causa** vale para qualquer
recurso com ciclo de vida parecido.

O `WorkItemFiltersHOC` criava a instância de filtro num `useMemo` e a apagava no
`cleanup` do `useEffect`. O `StrictMode` monta, desmonta e remonta o **mesmo
fiber**: o `cleanup` apagava a instância, e o `useMemo` — que já rodou naquele
fiber — não a recriava. Sobrava uma referência órfã.

A correção é a regra geral: **`useMemo` não é dono de ciclo de vida.** Quem cria
e destrói é o efeito, e quem renderiza lê o estado vivo em vez de uma referência
memorizada. Hoje o efeito recria ao (re)montar e o componente lê a instância do
store a cada renderização.

Não precisa mais mexer no `entry.client.tsx` para validar filtro.

## Higiene: o que cada ação suja

Medido nesta máquina em 15/08/2026, e por isso a limpeza de duas delas está
**dentro do próprio comando** — quem depende de lembrar, esquece.

| Ação                             | O que fica                              | Quanto                           | Limpeza                                   |
| -------------------------------- | --------------------------------------- | -------------------------------- | ----------------------------------------- |
| `pytest`                         | a stack de teste fica de pé             | 0,27 GB e **171% de CPU** ocioso | **automática** em `pnpm test:api`         |
| `docker compose build` do deploy | imagens antigas viram órfãs             | 3,85 GB                          | **automática** em `infra/plane/deploy.sh` |
| `docker compose build` do deploy | cache do BuildKit                       | 15 GB                            | **manual, por marco** — ver abaixo        |
| `pnpm turbo run build`           | `.turbo`, `apps/web/build`, `dist`      | ~400 MB                          | `rm -rf .turbo apps/web/build`            |
| validação visual                 | tarefas, propriedades e opções de teste | —                                | apagar o que criou                        |
| trocar de branch / encerrar      | processos `turbo`/`vite` órfãos         | —                                | `pkill -f "react-router/dev/bin.js dev"`  |

**O cache de build é a exceção deliberada.** Ele existe para o próximo build ser
rápido; limpá-lo a cada deploy troca 15 GB de disco por minutos em toda
publicação. O gatilho é pressão de disco ou um marco — depois de uma release,
por exemplo:

```bash
docker builder prune -af
```

## O gancho de pré-commit cobra erro, não aviso

`lint-staged` roda `oxfmt` e `oxlint --fix` nos arquivos preparados. **Erro
barra o commit; aviso não.**

Foi assim a partir de 16/08/2026, e a razão é prática: com `--deny-warnings`,
qualquer commit que tocasse um arquivo herdado era barrado por avisos que já
estavam lá. O resultado real não era código mais limpo — era `--no-verify` em
todo commit, e um gancho que não protegia nada.

Quem cobra aviso é a CI, com **orçamento por pacote**
(`oxlint --max-warnings=N`). É lá que a dívida herdada pode encolher aos poucos:
baixando o número quando um arquivo é limpo, em vez de exigir tudo de uma vez.

## Chave de tradução que não existe

O `sync-check` compara os idiomas **entre si**: ele pega chave que falta num e
sobra no outro. Ele **não** pega a que não existe em lugar nenhum — essa aparece
na tela como o próprio identificador (`common.save`), sem quebrar nada, sem
alarme em teste e sem erro de compilação.

Aconteceu aqui, e só foi visto olhando a tela. Por isso existe:

```bash
pnpm dlx tsx packages/i18n/scripts/chaves-usadas.ts
```

Ele varre as chamadas `t("a.b.c")` do código e confere contra o pt-BR, que é o
idioma do produto (ADR 0004). Roda na CI junto com o `sync-check`. Chave montada
em tempo de execução é ignorada de propósito: adivinhar o valor daria falso
positivo, e verificação que dá falso positivo é verificação que se aprende a
ignorar.

Na primeira execução ele achou duas chaves inexistentes em código herdado.

## Depois de validar

Apague o que você criou no `planedev`. Ele é ambiente compartilhado entre
sessões, e dado de teste esquecido vira ruído na validação seguinte.
