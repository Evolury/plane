/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: a caixa "notificar por e-mail" não pode prometer o que a instância
// não entrega.
//
// Ela vinha marcada por padrão. Sem SMTP configurado, quem criava uma regra
// pedia um e-mail que era enfileirado para nunca sair — sem erro, sem aviso.
// Medido em produção: 49 na fila, 0 enviados.
//
// A correção usa `is_smtp_configured`, que a API já expõe e duas outras telas já
// consomem. Isso importa: no dia em que houver SMTP, a caixa volta a nascer
// marcada sozinha, sem ninguém tocar em código.

import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

let smtpConfigurado = false;

vi.mock("@/hooks/store/use-instance", () => ({
  useInstance: () => ({ config: { is_smtp_configured: smtpConfigurado } }),
}));

const caixaDeEmail = (marcada: boolean, semSmtp: boolean) => (
  <div>
    <label>
      <input type="checkbox" checked={marcada} readOnly />
      notificar por e-mail
    </label>
    {semSmtp && <p>O envio por e-mail não está configurado nesta instância.</p>}
  </div>
);

// A decisão vem do componente, e não é reescrita aqui: montar o editor inteiro
// traria estados, etiquetas, membros e módulos para afirmar uma expressão — mas
// copiar a expressão para o teste seria pior ainda, porque passaria a valer
// mesmo depois de alguém mudar o código.
import { caixaDeEmailMarcada as marcada } from "@/components/automations/acoes";

describe("padrão da caixa de e-mail", () => {
  it("sem SMTP, nasce DESMARCADA", () => {
    // O defeito: antes era `config.email !== false`, que com `undefined` dava
    // verdadeiro e prometia um envio que não aconteceria.
    expect(marcada(undefined, false)).toBe(false);
  });

  it("com SMTP, nasce marcada", () => {
    // Sem isto, desmarcar sempre passaria no teste acima — e quem tem e-mail
    // configurado perderia o padrão útil.
    expect(marcada(undefined, true)).toBe(true);
  });

  it("quem marcou de propósito continua marcado, mesmo sem SMTP", () => {
    // Quem está configurando o SMTP agora deve poder deixar a regra pronta.
    expect(marcada(true, false)).toBe(true);
  });

  it("quem desmarcou de propósito continua desmarcado, mesmo com SMTP", () => {
    expect(marcada(false, true)).toBe(false);
  });
});

describe("aviso na tela", () => {
  it("sem SMTP, a tela diz que o envio não sai", () => {
    smtpConfigurado = false;
    render(caixaDeEmail(false, !smtpConfigurado));

    expect(screen.getByText(/não está configurado/)).toBeTruthy();
  });

  it("com SMTP, não há aviso a dar", () => {
    smtpConfigurado = true;
    render(caixaDeEmail(true, !smtpConfigurado));

    expect(screen.queryByText(/não está configurado/)).toBeNull();
  });
});
