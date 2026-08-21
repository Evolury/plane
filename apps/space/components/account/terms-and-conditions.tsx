/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useTranslation } from "@plane/i18n";

// QooWork: apontavam para os documentos legais do Plane — a tela de entrada
// dizia à pessoa que ela concorda com os termos de OUTRA empresa. As páginas
// precisam existir no domínio antes da produção real (ADR 0020).
const LEGAL_LINKS = {
  termsOfService: "https://qoowork.com.br/termos",
  privacyPolicy: "https://qoowork.com.br/privacidade",
} as const;

type Props = {
  isSignUp?: boolean;
};

export function TermsAndConditions(props: Props) {
  const { t } = useTranslation();
  const { isSignUp = false } = props;
  return (
    <span className="flex items-center justify-center py-6">
      <p className="text-center text-13 whitespace-pre-line text-secondary">
        {`${isSignUp ? t("ui.by_creating_an_account") : t("ui.by_signing_in")}${t("ui.terms_agreement")}`}
        <a href={LEGAL_LINKS.termsOfService} target="_blank" rel="noopener noreferrer">
          <span className="text-13 font-medium underline hover:cursor-pointer">{t("ui.terms_of_service")}</span>
        </a>{" "}
        {t("ui.and")}{" "}
        <a href={LEGAL_LINKS.privacyPolicy} target="_blank" rel="noopener noreferrer">
          <span className="text-13 font-medium underline hover:cursor-pointer">{t("ui.privacy_policy")}</span>
        </a>
        {"."}
      </p>
    </span>
  );
}
