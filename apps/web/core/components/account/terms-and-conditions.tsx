/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import React from "react";
import Link from "next/link";
import { EAuthModes } from "@plane/constants";
import { useTranslation } from "@plane/i18n";

interface TermsAndConditionsProps {
  authType?: EAuthModes;
}

// Constants for better maintainability
// QooWork: apontavam para os documentos legais do Plane — a tela de entrada
// dizia à pessoa que ela concorda com os termos de OUTRA empresa. As páginas
// precisam existir no domínio antes da produção real (ADR 0020).
const LEGAL_LINKS = {
  termsOfService: "https://qoowork.com.br/termos",
  privacyPolicy: "https://qoowork.com.br/privacidade",
} as const;

// QooWork: a chave, e não o texto. Este objeto era montado com `translate()` no
// corpo do módulo — avaliado antes de o i18n carregar —, e o que congelava era a
// própria chave: a tela de entrada dizia "ui.by_signing_in, você entende e
// concorda…". A tradução acontece na renderização, com o `t` do componente.
const CHAVES = {
  [EAuthModes.SIGN_UP]: "ui.by_creating_an_account",
  [EAuthModes.SIGN_IN]: "ui.by_signing_in",
} as const;

// Reusable link component to reduce duplication
function LegalLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link href={href} className="text-secondary" target="_blank" rel="noopener noreferrer">
      <span className="text-13 font-medium underline hover:cursor-pointer">{children}</span>
    </Link>
  );
}

export function TermsAndConditions({ authType = EAuthModes.SIGN_IN }: TermsAndConditionsProps) {
  const { t } = useTranslation();
  return (
    <div className="flex items-center justify-center">
      {/* Evolury: frase montada por fragmentos traduzidos, já que os links ficam no meio dela */}
      <p className="text-center text-13 whitespace-pre-line text-tertiary">
        {`${t(CHAVES[authType])}${t("ui.terms_agreement")}`}
        <LegalLink href={LEGAL_LINKS.termsOfService}>{t("ui.terms_of_service")}</LegalLink> {t("ui.and")}{" "}
        <LegalLink href={LEGAL_LINKS.privacyPolicy}>{t("ui.privacy_policy")}</LegalLink>.
      </p>
    </div>
  );
}
