# Desenvolvimento e validação local

Como subir o ambiente para validar uma mudança visualmente, e as três armadilhas
que já custaram retrabalho. Escrito depois da terceira vez.

## As duas stacks

| Stack           | Para quê                          | Como                                                                    |
| --------------- | --------------------------------- | ----------------------------------------------------------------------- |
| **`planetest`** | pytest da API                     | `docker compose -f docker-compose-test.yml run --rm api-tests pytest …` |
| **`planedev`**  | banco e API para validação visual | `docker compose -p planedev up -d`                                      |

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

Antes de investigar um 500 estranho na stack de desenvolvimento:

```bash
docker compose -p planedev restart api
```

Isso **não** acontece em produção: lá a API roda de imagem construída, sem
`bind mount` e sem autoreloader.

## O seletor de filtros não abre no dev — e não é bug seu

Clicar no funil do cabeçalho não abre nada com `pnpm dev`, e o console registra
`Filters toggle error - filter instance not available`.

A causa é o `StrictMode` em `apps/web/app/entry.client.tsx`. O
`WorkItemFiltersHOC` cria a instância de filtro num `useMemo` e a apaga no
`cleanup` do `useEffect`. O `StrictMode` monta, desmonta e remonta: o `cleanup`
apaga a instância, e o `useMemo` — que já rodou naquele fiber — não a recria.

**Só afeta desenvolvimento**: o `StrictMode` não duplica efeitos em produção.

Para validar qualquer coisa que dependa do seletor de filtros, troque

```tsx
<StrictMode>
  <HydratedRouter />
</StrictMode>
```

por `<HydratedRouter />`, valide, e **religue antes de cortar**. Confira com
`git diff apps/web/app/entry.client.tsx` — vazio é o que se espera.

## Depois de validar

Apague o que você criou no `planedev`. Ele é ambiente compartilhado entre
sessões, e dado de teste esquecido vira ruído na validação seguinte.
