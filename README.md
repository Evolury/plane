# Evolury — gestão de projetos

Plataforma de gestão de projetos operada pela Evolury: work items, ciclos,
módulos, visões, páginas e analytics, com interface e padrões brasileiros
(pt-BR como idioma da instância, fuso de Brasília, formatos de data e hora
locais).

O produto deriva do [Plane Community Edition](https://github.com/makeplane/plane)
v1.4.1, sob AGPL-3.0. Desde a versão 1.0.0 ele segue desenvolvimento e
versionamento próprios — ver [UPSTREAM.md](UPSTREAM.md) e
[VERSIONING.md](VERSIONING.md).

## Estrutura

Monorepo pnpm + turbo:

| Caminho      | O que é                                                  |
| ------------ | -------------------------------------------------------- |
| `apps/api`   | Backend Django (REST, Celery, migrations)                |
| `apps/web`   | Aplicação principal (React Router)                       |
| `apps/admin` | God-mode: configuração da instância                      |
| `apps/space` | Publicação de views públicas                             |
| `apps/live`  | Servidor WebSocket de colaboração nas páginas            |
| `packages/*` | UI, editor, i18n, tipos, utils e demais pacotes internos |

## Rodando localmente

Pré-requisitos: Docker Engine, Node.js 20+, pnpm, e pelo menos 12 GB de RAM
disponíveis.

```bash
git clone git@github.com:Evolury/plane.git
cd plane
chmod +x setup.sh && ./setup.sh          # gera os .env a partir do .env.example
docker compose -f docker-compose-local.yml up
pnpm dev
```

Depois: `http://localhost:3001/god-mode/` para registrar o admin da instância e
`http://localhost:3000` para entrar com as mesmas credenciais.

Comandos de rotina (detalhes em [AGENTS.md](AGENTS.md)):

```bash
pnpm check        # formato, lint e tipos
pnpm fix          # corrige formato e lint
pnpm build
```

Testes do backend rodam em stack isolada:

```bash
docker compose -f docker-compose-test.yml up --build --abort-on-container-exit --exit-code-from api-tests
```

## Documentação interna

- [UPSTREAM.md](UPSTREAM.md) — relação com o Plane CE e como acompanhar correções de segurança
- [VERSIONING.md](VERSIONING.md) — esquema de versão e processo de release
- [CONTRIBUTING.md](CONTRIBUTING.md) — fluxo de trabalho, setup e guia de tradução
- [CHANGELOG.md](CHANGELOG.md) — o que mudou em cada versão
- [docs/telemetria.md](docs/telemetria.md) — o que a instância não envia, e por quê
- [docs/linting.md](docs/linting.md) — como o lint funciona no monorepo
- [SECURITY.md](SECURITY.md) — como reportar vulnerabilidades

## Segurança

Vulnerabilidades devem ser reportadas para
[contato@evolury.com.br](mailto:contato@evolury.com.br), nunca em issue pública.
Ver [SECURITY.md](SECURITY.md).

## Licença e código-fonte

[GNU AGPL-3.0-only](LICENSE.txt), herdada do Plane CE. Duas consequências
práticas que valem lembrar:

- Os cabeçalhos de copyright da Plane Software Inc. permanecem nos arquivos
  herdados. Arquivos novos ganham a nossa linha ao lado, sem substituir a deles.
- A seção 13 da AGPL dá a quem usa a instância pela rede o direito de receber o
  código-fonte da versão modificada em execução. Se este repositório não for
  público, é preciso oferecer esse acesso por outro meio visível aos usuários.
