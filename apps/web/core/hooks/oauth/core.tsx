/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// plane imports
import { useSearchParams } from "next/navigation";
import { useTheme } from "next-themes";
import { API_BASE_URL } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import type { TOAuthConfigs, TOAuthOption } from "@plane/types";
// assets
import giteaLogo from "@/app/assets/logos/gitea-logo.svg?url";
import GithubLightLogo from "@/app/assets/logos/github-black.png?url";
import GithubDarkLogo from "@/app/assets/logos/github-dark.svg?url";
import gitlabLogo from "@/app/assets/logos/gitlab-logo.svg?url";
import googleLogo from "@/app/assets/logos/google-logo.svg?url";
// hooks
import { useInstance } from "@/hooks/store/use-instance";

export const useCoreOAuthConfig = (oauthActionText: string): TOAuthConfigs => {
  //router
  const searchParams = useSearchParams();
  // query params
  const next_path = searchParams.get("next_path");
  // theme
  const { resolvedTheme } = useTheme();
  // plane hooks
  const { t } = useTranslation();
  // store hooks
  const { config } = useInstance();
  // derived values
  const isOAuthEnabled =
    (config &&
      (config?.is_google_enabled ||
        config?.is_github_enabled ||
        config?.is_gitlab_enabled ||
        config?.is_gitea_enabled)) ||
    false;
  // Evolury: rótulos e textos alternativos dos provedores OAuth vindos do i18n
  const oAuthOptions: TOAuthOption[] = [
    {
      id: "google",
      text: t("auth.common.oauth.continue_with_provider", { action: oauthActionText, provider: "Google" }),
      icon: (
        <img
          src={googleLogo}
          height={18}
          width={18}
          alt={t("aria_labels.auth_forms.provider_logo", { provider: "Google" })}
        />
      ),
      onClick: () => {
        window.location.assign(`${API_BASE_URL}/auth/google/${next_path ? `?next_path=${next_path}` : ``}`);
      },
      enabled: config?.is_google_enabled,
    },
    {
      id: "github",
      text: t("auth.common.oauth.continue_with_provider", { action: oauthActionText, provider: "GitHub" }),
      icon: (
        <img
          src={resolvedTheme === "dark" ? GithubDarkLogo : GithubLightLogo}
          height={18}
          width={18}
          alt={t("aria_labels.auth_forms.provider_logo", { provider: "GitHub" })}
        />
      ),
      onClick: () => {
        window.location.assign(`${API_BASE_URL}/auth/github/${next_path ? `?next_path=${next_path}` : ``}`);
      },
      enabled: config?.is_github_enabled,
    },
    {
      id: "gitlab",
      text: t("auth.common.oauth.continue_with_provider", { action: oauthActionText, provider: "GitLab" }),
      icon: (
        <img
          src={gitlabLogo}
          height={18}
          width={18}
          alt={t("aria_labels.auth_forms.provider_logo", { provider: "GitLab" })}
        />
      ),
      onClick: () => {
        window.location.assign(`${API_BASE_URL}/auth/gitlab/${next_path ? `?next_path=${next_path}` : ``}`);
      },
      enabled: config?.is_gitlab_enabled,
    },
    {
      id: "gitea",
      text: t("auth.common.oauth.continue_with_provider", { action: oauthActionText, provider: "Gitea" }),
      icon: (
        <img
          src={giteaLogo}
          height={18}
          width={18}
          alt={t("aria_labels.auth_forms.provider_logo", { provider: "Gitea" })}
        />
      ),
      onClick: () => {
        window.location.assign(`${API_BASE_URL}/auth/gitea/${next_path ? `?next_path=${next_path}` : ``}`);
      },
      enabled: config?.is_gitea_enabled,
    },
  ];

  return {
    isOAuthEnabled,
    oAuthOptions,
  };
};
