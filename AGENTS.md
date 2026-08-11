# Agent Development Guide

## Política do fork

Este repositório é um produto independente derivado do Plane CE v1.4.1, não um
fork que acompanha o upstream. Consequências práticas para qualquer trabalho aqui:

- A branch principal é `main`. `preview`, `master` e `canary` são nomes do
  upstream — nunca abra PR contra eles nem trabalhe a partir deles.
- Versionamento é próprio, a partir de `1.0.0`, sem relação com a numeração do
  Plane. Ver `VERSIONING.md`.
- Commits em português, conventional commits, com o _porquê_ no corpo. Merge por
  squash.
- Não há work item ID da Plane nos títulos de PR; a convenção do upstream não se
  aplica.
- Ao alterar arquivo herdado, marque a divergência com um comentário iniciado por
  `Evolury:`. Mantenha os cabeçalhos de copyright existentes (AGPL-3.0, ver
  `UPSTREAM.md`).
- A instância não envia telemetria. Antes de mexer em qualquer coisa que fale com
  a rede a partir do backend, leia `docs/telemetria.md`.
- Correção do upstream entra por cherry-pick com `-x`, nunca por merge de branch.
- Funcionalidades próprias são documentadas em `docs/evolury/funcionalidades/`
  (especificação, arquitetura, matriz de compatibilidade e backlog) e as decisões
  estruturais em `docs/evolury/decisoes/` (ADRs). Antes de mexer em uma
  funcionalidade Evolury, leia a especificação dela; ao implementar, referencie os
  itens do backlog no PR.

## Commands

- `pnpm dev` - Start all dev servers (web:3000, admin:3001)
- `pnpm build` - Build all packages and apps
- `pnpm check` - Run all checks (format, lint, types)
- `pnpm check:lint` - OxLint across all packages
- `pnpm check:types` - TypeScript type checking
- `pnpm fix` - Auto-fix format and lint issues
- `pnpm turbo run <command> --filter=<package>` - Target specific package/app
- `pnpm --filter=@plane/ui storybook` - Start Storybook on port 6006

## Code Style

- **Imports**: Use `workspace:*` for internal packages, `catalog:` for external deps
- **TypeScript**: Strict mode enabled, all files must be typed
- **Formatting**: oxfmt, run `pnpm fix:format`
- **Linting**: OxLint with shared `.oxlintrc.json` config
- **Naming**: camelCase for variables/functions, PascalCase for components/types
- **Error Handling**: Use try-catch with proper error types, log errors appropriately
- **State Management**: MobX stores in `packages/shared-state`, reactive patterns
- **Testing**: All features require unit tests, use existing test framework per package
- **Components**: Build in `@plane/ui` with Storybook for isolated development

## Backend tests (Docker)

The Django/pytest suite for `apps/api` runs in an isolated stack defined by `docker-compose-test.yml` at the repo root.

Prereq (once): `./setup.sh` — generates `apps/api/.env` from `.env.example`.

- Full suite: `docker compose -f docker-compose-test.yml up --build --abort-on-container-exit --exit-code-from api-tests`
- Subset: `docker compose -f docker-compose-test.yml run --rm api-tests pytest -m unit`
- Teardown: `docker compose -f docker-compose-test.yml down -v`

See `apps/api/tests/RUNNING_TESTS.md` for the full walkthrough and troubleshooting; see `apps/api/tests/TESTING_GUIDE.md` for test conventions and fixtures.
