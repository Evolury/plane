/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: a suíte passa a trazer o próprio ambiente.
//
// `src/env.ts` valida as variáveis no momento do import e chama
// `process.exit(1)` quando falta alguma — e `API_BASE_URL` e
// `LIVE_SERVER_SECRET_KEY` não têm padrão. Quem importa o controller num teste
// dispara isso.
//
// Isso passava despercebido porque a suíte nunca rodou fora desta máquina: aqui
// as variáveis existem no ambiente do desenvolvedor. Na primeira execução dentro
// da CI, o teste morreu com "Invalid environment variables" — o teste dependia
// da máquina, e ninguém sabia.
//
// Valores obviamente falsos, de propósito: se algum dia um deles vazar para uma
// asserção, o que se lê é que é um teste.
process.env.API_BASE_URL ??= "http://api.invalido.test";
process.env.LIVE_SERVER_SECRET_KEY ??= "chave-de-teste-nao-usar";
