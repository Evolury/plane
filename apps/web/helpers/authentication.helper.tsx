/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { ReactNode } from "react";
import Link from "next/link";
// plane imports
import { SUPPORT_EMAIL } from "@plane/constants";
import { translate } from "@plane/i18n";

export enum EPageTypes {
  PUBLIC = "PUBLIC",
  NON_AUTHENTICATED = "NON_AUTHENTICATED",
  SET_PASSWORD = "SET_PASSWORD",
  ONBOARDING = "ONBOARDING",
  AUTHENTICATED = "AUTHENTICATED",
}

export enum EAuthModes {
  SIGN_IN = "SIGN_IN",
  SIGN_UP = "SIGN_UP",
}

export enum EAuthSteps {
  EMAIL = "EMAIL",
  PASSWORD = "PASSWORD",
  UNIQUE_CODE = "UNIQUE_CODE",
}

export enum EErrorAlertType {
  BANNER_ALERT = "BANNER_ALERT",
  INLINE_FIRST_NAME = "INLINE_FIRST_NAME",
  INLINE_EMAIL = "INLINE_EMAIL",
  INLINE_PASSWORD = "INLINE_PASSWORD",
  INLINE_EMAIL_CODE = "INLINE_EMAIL_CODE",
}

export enum EAuthenticationErrorCodes {
  // Global
  INSTANCE_NOT_CONFIGURED = "5000",
  INVALID_EMAIL = "5005",
  EMAIL_REQUIRED = "5010",
  SIGNUP_DISABLED = "5015",
  MAGIC_LINK_LOGIN_DISABLED = "5016",
  BOT_USER_LOGIN_FORBIDDEN = "5017",
  PASSWORD_LOGIN_DISABLED = "5018",
  USER_ACCOUNT_DEACTIVATED = "5019",
  // Password strength
  INVALID_PASSWORD = "5020",
  PASSWORD_TOO_WEAK = "5021",
  SMTP_NOT_CONFIGURED = "5025",
  // Sign Up
  USER_ALREADY_EXIST = "5030",
  AUTHENTICATION_FAILED_SIGN_UP = "5035",
  REQUIRED_EMAIL_PASSWORD_SIGN_UP = "5040",
  INVALID_EMAIL_SIGN_UP = "5045",
  INVALID_EMAIL_MAGIC_SIGN_UP = "5050",
  MAGIC_SIGN_UP_EMAIL_CODE_REQUIRED = "5055",
  // Sign In
  USER_DOES_NOT_EXIST = "5060",
  AUTHENTICATION_FAILED_SIGN_IN = "5065",
  REQUIRED_EMAIL_PASSWORD_SIGN_IN = "5070",
  INVALID_EMAIL_SIGN_IN = "5075",
  INVALID_EMAIL_MAGIC_SIGN_IN = "5080",
  MAGIC_SIGN_IN_EMAIL_CODE_REQUIRED = "5085",
  // Both Sign in and Sign up for magic
  INVALID_MAGIC_CODE_SIGN_IN = "5090",
  INVALID_MAGIC_CODE_SIGN_UP = "5092",
  EXPIRED_MAGIC_CODE_SIGN_IN = "5095",
  EXPIRED_MAGIC_CODE_SIGN_UP = "5097",
  EMAIL_CODE_ATTEMPT_EXHAUSTED_SIGN_IN = "5100",
  EMAIL_CODE_ATTEMPT_EXHAUSTED_SIGN_UP = "5102",
  // Oauth
  OAUTH_NOT_CONFIGURED = "5104",
  GOOGLE_NOT_CONFIGURED = "5105",
  GITHUB_NOT_CONFIGURED = "5110",
  GITLAB_NOT_CONFIGURED = "5111",
  GOOGLE_OAUTH_PROVIDER_ERROR = "5115",
  GITHUB_OAUTH_PROVIDER_ERROR = "5120",
  GITLAB_OAUTH_PROVIDER_ERROR = "5121",
  // Reset Password
  INVALID_PASSWORD_TOKEN = "5125",
  EXPIRED_PASSWORD_TOKEN = "5130",
  // Change password
  INCORRECT_OLD_PASSWORD = "5135",
  MISSING_PASSWORD = "5138",
  INVALID_NEW_PASSWORD = "5140",
  // set password
  PASSWORD_ALREADY_SET = "5145",
  // Admin
  ADMIN_ALREADY_EXIST = "5150",
  REQUIRED_ADMIN_EMAIL_PASSWORD_FIRST_NAME = "5155",
  INVALID_ADMIN_EMAIL = "5160",
  INVALID_ADMIN_PASSWORD = "5165",
  REQUIRED_ADMIN_EMAIL_PASSWORD = "5170",
  ADMIN_AUTHENTICATION_FAILED = "5175",
  ADMIN_USER_ALREADY_EXIST = "5180",
  ADMIN_USER_DOES_NOT_EXIST = "5185",
  ADMIN_USER_DEACTIVATED = "5190",
  // Rate limit
  RATE_LIMIT_EXCEEDED = "5900",
}

export type TAuthErrorInfo = {
  type: EErrorAlertType;
  code: EAuthenticationErrorCodes;
  title: string;
  message: ReactNode;
};

// TODO: move all error messages to translation files
const errorCodeMessages: {
  [key in EAuthenticationErrorCodes]: { title: string; message: (email?: string) => ReactNode };
} = {
  // global
  [EAuthenticationErrorCodes.INSTANCE_NOT_CONFIGURED]: {
    title: translate("auth_error.instance_not_configured"),
    message: () => translate("auth_error.instance_not_configured_please_contact_your_administ"),
  },
  [EAuthenticationErrorCodes.INVALID_EMAIL]: {
    title: translate("auth_error.invalid_email"),
    message: () => translate("auth_error.invalid_email_please_try_again"),
  },
  [EAuthenticationErrorCodes.EMAIL_REQUIRED]: {
    title: translate("auth_error.email_required"),
    message: () => translate("auth_error.email_required_please_try_again"),
  },
  [EAuthenticationErrorCodes.SIGNUP_DISABLED]: {
    title: translate("auth_error.sign_up_disabled"),
    message: () => translate("auth_error.sign_up_disabled_please_contact_your_administrator"),
  },
  [EAuthenticationErrorCodes.MAGIC_LINK_LOGIN_DISABLED]: {
    title: translate("auth_error.magic_link_login_disabled"),
    message: () => translate("auth_error.magic_link_login_disabled_please_contact_your_admini"),
  },
  [EAuthenticationErrorCodes.PASSWORD_LOGIN_DISABLED]: {
    title: translate("auth_error.password_login_disabled"),
    message: () => translate("auth_error.password_login_disabled_please_contact_your_administ"),
  },
  [EAuthenticationErrorCodes.USER_ACCOUNT_DEACTIVATED]: {
    title: translate("auth_error.user_account_deactivated"),
    message: () => `User account deactivated. Please contact ${SUPPORT_EMAIL ? SUPPORT_EMAIL : "administrator"}.`,
  },
  [EAuthenticationErrorCodes.BOT_USER_LOGIN_FORBIDDEN]: {
    title: translate("auth_error.sign_in_not_allowed"),
    message: () => translate("auth_error.this_account_cannot_be_used_to_sign_in_please_use_a"),
  },
  [EAuthenticationErrorCodes.INVALID_PASSWORD]: {
    title: translate("auth_error.invalid_password"),
    message: () => translate("auth_error.invalid_password_please_try_again"),
  },
  [EAuthenticationErrorCodes.PASSWORD_TOO_WEAK]: {
    title: translate("auth_error.password_too_weak"),
    message: () => translate("auth_error.please_use_a_stronger_password"),
  },
  [EAuthenticationErrorCodes.SMTP_NOT_CONFIGURED]: {
    title: translate("auth_error.smtp_not_configured"),
    message: () => translate("auth_error.smtp_not_configured_please_contact_your_administrato"),
  },

  // sign up
  [EAuthenticationErrorCodes.USER_ALREADY_EXIST]: {
    title: translate("auth_error.user_already_exists"),
    message: (email = undefined) => (
      <div>
        Your account is already registered.&nbsp;
        <Link
          className="font-medium underline underline-offset-4 transition-all hover:font-bold"
          href={`/sign-in${email ? `?email=${encodeURIComponent(email)}` : ``}`}
        >
          {translate("ui.sign_in_2")}
        </Link>
        &nbsp;now.
      </div>
    ),
  },
  [EAuthenticationErrorCodes.REQUIRED_EMAIL_PASSWORD_SIGN_UP]: {
    title: translate("auth_error.email_and_password_required"),
    message: () => translate("auth_error.email_and_password_required_please_try_again"),
  },
  [EAuthenticationErrorCodes.AUTHENTICATION_FAILED_SIGN_UP]: {
    title: translate("auth_error.authentication_failed"),
    message: () => translate("auth_error.authentication_failed_please_try_again"),
  },
  [EAuthenticationErrorCodes.INVALID_EMAIL_SIGN_UP]: {
    title: translate("auth_error.invalid_email"),
    message: () => translate("auth_error.invalid_email_please_try_again"),
  },
  [EAuthenticationErrorCodes.MAGIC_SIGN_UP_EMAIL_CODE_REQUIRED]: {
    title: translate("auth_error.email_and_code_required"),
    message: () => translate("auth_error.email_and_code_required_please_try_again"),
  },
  [EAuthenticationErrorCodes.INVALID_EMAIL_MAGIC_SIGN_UP]: {
    title: translate("auth_error.invalid_email"),
    message: () => translate("auth_error.invalid_email_please_try_again"),
  },

  [EAuthenticationErrorCodes.USER_DOES_NOT_EXIST]: {
    title: translate("auth_error.user_does_not_exist"),
    message: (email = undefined) => (
      <div>
        No account found.&nbsp;
        <Link
          className="font-medium underline underline-offset-4 transition-all hover:font-bold"
          href={`/${email ? `?email=${encodeURIComponent(email)}` : ``}`}
        >
          {translate("ui.create_one")}
        </Link>
        &nbsp;to get started.
      </div>
    ),
  },
  [EAuthenticationErrorCodes.REQUIRED_EMAIL_PASSWORD_SIGN_IN]: {
    title: translate("auth_error.email_and_password_required"),
    message: () => translate("auth_error.email_and_password_required_please_try_again"),
  },
  [EAuthenticationErrorCodes.AUTHENTICATION_FAILED_SIGN_IN]: {
    title: translate("auth_error.authentication_failed"),
    message: () => translate("auth_error.authentication_failed_please_try_again"),
  },
  [EAuthenticationErrorCodes.INVALID_EMAIL_SIGN_IN]: {
    title: translate("auth_error.invalid_email"),
    message: () => translate("auth_error.invalid_email_please_try_again"),
  },
  [EAuthenticationErrorCodes.MAGIC_SIGN_IN_EMAIL_CODE_REQUIRED]: {
    title: translate("auth_error.email_and_code_required"),
    message: () => translate("auth_error.email_and_code_required_please_try_again"),
  },
  [EAuthenticationErrorCodes.INVALID_EMAIL_MAGIC_SIGN_IN]: {
    title: translate("auth_error.invalid_email"),
    message: () => translate("auth_error.invalid_email_please_try_again"),
  },

  // Both Sign in and Sign up
  [EAuthenticationErrorCodes.INVALID_MAGIC_CODE_SIGN_IN]: {
    title: translate("auth_error.authentication_failed"),
    message: () => translate("auth_error.invalid_magic_code_please_try_again"),
  },
  [EAuthenticationErrorCodes.INVALID_MAGIC_CODE_SIGN_UP]: {
    title: translate("auth_error.authentication_failed"),
    message: () => translate("auth_error.invalid_magic_code_please_try_again"),
  },
  [EAuthenticationErrorCodes.EXPIRED_MAGIC_CODE_SIGN_IN]: {
    title: translate("auth_error.expired_magic_code"),
    message: () => translate("auth_error.expired_magic_code_please_try_again"),
  },
  [EAuthenticationErrorCodes.EXPIRED_MAGIC_CODE_SIGN_UP]: {
    title: translate("auth_error.expired_magic_code"),
    message: () => translate("auth_error.expired_magic_code_please_try_again"),
  },
  [EAuthenticationErrorCodes.EMAIL_CODE_ATTEMPT_EXHAUSTED_SIGN_IN]: {
    title: translate("auth_error.expired_magic_code"),
    message: () => translate("auth_error.expired_magic_code_please_try_again"),
  },
  [EAuthenticationErrorCodes.EMAIL_CODE_ATTEMPT_EXHAUSTED_SIGN_UP]: {
    title: translate("auth_error.expired_magic_code"),
    message: () => translate("auth_error.expired_magic_code_please_try_again"),
  },

  // Oauth
  [EAuthenticationErrorCodes.OAUTH_NOT_CONFIGURED]: {
    title: translate("auth_error.oauth_not_configured"),
    message: () => translate("auth_error.oauth_not_configured_please_contact_your_administrat"),
  },
  [EAuthenticationErrorCodes.GOOGLE_NOT_CONFIGURED]: {
    title: translate("auth_error.google_not_configured"),
    message: () => translate("auth_error.google_not_configured_please_contact_your_administra"),
  },
  [EAuthenticationErrorCodes.GITHUB_NOT_CONFIGURED]: {
    title: translate("auth_error.github_not_configured"),
    message: () => translate("auth_error.github_not_configured_please_contact_your_administra"),
  },
  [EAuthenticationErrorCodes.GITLAB_NOT_CONFIGURED]: {
    title: translate("auth_error.gitlab_not_configured"),
    message: () => translate("auth_error.gitlab_not_configured_please_contact_your_administra"),
  },
  [EAuthenticationErrorCodes.GOOGLE_OAUTH_PROVIDER_ERROR]: {
    title: translate("auth_error.google_oauth_provider_error"),
    message: () => translate("auth_error.google_oauth_provider_error_please_try_again"),
  },
  [EAuthenticationErrorCodes.GITHUB_OAUTH_PROVIDER_ERROR]: {
    title: translate("auth_error.github_oauth_provider_error"),
    message: () => translate("auth_error.github_oauth_provider_error_please_try_again"),
  },
  [EAuthenticationErrorCodes.GITLAB_OAUTH_PROVIDER_ERROR]: {
    title: translate("auth_error.gitlab_oauth_provider_error"),
    message: () => translate("auth_error.gitlab_oauth_provider_error_please_try_again"),
  },

  // Reset Password
  [EAuthenticationErrorCodes.INVALID_PASSWORD_TOKEN]: {
    title: translate("auth_error.invalid_password_token"),
    message: () => translate("auth_error.invalid_password_token_2"),
  },
  [EAuthenticationErrorCodes.EXPIRED_PASSWORD_TOKEN]: {
    title: translate("auth_error.expired_password_token"),
    message: () => translate("auth_error.expired_password_token_please_try_again"),
  },

  // Change password
  [EAuthenticationErrorCodes.MISSING_PASSWORD]: {
    title: translate("auth_error.password_required"),
    message: () => translate("auth_error.password_required_please_try_again"),
  },
  [EAuthenticationErrorCodes.INCORRECT_OLD_PASSWORD]: {
    title: translate("auth_error.incorrect_old_password"),
    message: () => translate("auth_error.incorrect_old_password_please_try_again"),
  },
  [EAuthenticationErrorCodes.INVALID_NEW_PASSWORD]: {
    title: translate("auth_error.invalid_new_password"),
    message: () => translate("auth_error.invalid_new_password_please_try_again"),
  },

  // set password
  [EAuthenticationErrorCodes.PASSWORD_ALREADY_SET]: {
    title: translate("auth_error.password_already_set"),
    message: () => translate("auth_error.password_already_set_please_try_again"),
  },

  // admin
  [EAuthenticationErrorCodes.ADMIN_ALREADY_EXIST]: {
    title: translate("auth_error.admin_already_exists"),
    message: () => translate("auth_error.admin_already_exists_please_try_again"),
  },
  [EAuthenticationErrorCodes.REQUIRED_ADMIN_EMAIL_PASSWORD_FIRST_NAME]: {
    title: translate("auth_error.email_password_and_first_name_required"),
    message: () => translate("auth_error.email_password_and_first_name_required_please_try_ag"),
  },
  [EAuthenticationErrorCodes.INVALID_ADMIN_EMAIL]: {
    title: translate("auth_error.invalid_admin_email"),
    message: () => translate("auth_error.invalid_admin_email_please_try_again"),
  },
  [EAuthenticationErrorCodes.INVALID_ADMIN_PASSWORD]: {
    title: translate("auth_error.invalid_admin_password"),
    message: () => translate("auth_error.invalid_admin_password_please_try_again"),
  },
  [EAuthenticationErrorCodes.REQUIRED_ADMIN_EMAIL_PASSWORD]: {
    title: translate("auth_error.email_and_password_required"),
    message: () => translate("auth_error.email_and_password_required_please_try_again"),
  },
  [EAuthenticationErrorCodes.ADMIN_AUTHENTICATION_FAILED]: {
    title: translate("auth_error.authentication_failed"),
    message: () => translate("auth_error.authentication_failed_please_try_again"),
  },
  [EAuthenticationErrorCodes.ADMIN_USER_ALREADY_EXIST]: {
    title: translate("auth_error.admin_user_already_exists"),
    message: () => (
      <div>
        Admin user already exists.&nbsp;
        <Link className="font-medium underline underline-offset-4 transition-all hover:font-bold" href={`/admin`}>
          {translate("ui.sign_in_2")}
        </Link>
        &nbsp;now.
      </div>
    ),
  },
  [EAuthenticationErrorCodes.ADMIN_USER_DOES_NOT_EXIST]: {
    title: translate("auth_error.admin_user_does_not_exist"),
    message: () => (
      <div>
        Admin user does not exist.&nbsp;
        <Link className="font-medium underline underline-offset-4 transition-all hover:font-bold" href={`/admin`}>
          {translate("ui.sign_in_2")}
        </Link>
        &nbsp;now.
      </div>
    ),
  },
  [EAuthenticationErrorCodes.ADMIN_USER_DEACTIVATED]: {
    title: translate("auth_error.admin_user_deactivated"),
    message: () => <div>{translate("ui.account_deactivated")}</div>,
  },
  [EAuthenticationErrorCodes.RATE_LIMIT_EXCEEDED]: {
    title: "",
    message: () => translate("auth_error.rate_limit_exceeded_please_try_again_later"),
  },
};

export const authErrorHandler = (errorCode: EAuthenticationErrorCodes, email?: string): TAuthErrorInfo | undefined => {
  const bannerAlertErrorCodes = [
    EAuthenticationErrorCodes.INSTANCE_NOT_CONFIGURED,
    EAuthenticationErrorCodes.INVALID_EMAIL,
    EAuthenticationErrorCodes.EMAIL_REQUIRED,
    EAuthenticationErrorCodes.SIGNUP_DISABLED,
    EAuthenticationErrorCodes.MAGIC_LINK_LOGIN_DISABLED,
    EAuthenticationErrorCodes.PASSWORD_LOGIN_DISABLED,
    EAuthenticationErrorCodes.BOT_USER_LOGIN_FORBIDDEN,
    EAuthenticationErrorCodes.USER_ACCOUNT_DEACTIVATED,
    EAuthenticationErrorCodes.INVALID_PASSWORD,
    EAuthenticationErrorCodes.SMTP_NOT_CONFIGURED,
    EAuthenticationErrorCodes.USER_ALREADY_EXIST,
    EAuthenticationErrorCodes.AUTHENTICATION_FAILED_SIGN_UP,
    EAuthenticationErrorCodes.REQUIRED_EMAIL_PASSWORD_SIGN_UP,
    EAuthenticationErrorCodes.INVALID_EMAIL_SIGN_UP,
    EAuthenticationErrorCodes.INVALID_EMAIL_MAGIC_SIGN_UP,
    EAuthenticationErrorCodes.MAGIC_SIGN_UP_EMAIL_CODE_REQUIRED,
    EAuthenticationErrorCodes.USER_DOES_NOT_EXIST,
    EAuthenticationErrorCodes.AUTHENTICATION_FAILED_SIGN_IN,
    EAuthenticationErrorCodes.REQUIRED_EMAIL_PASSWORD_SIGN_IN,
    EAuthenticationErrorCodes.INVALID_EMAIL_SIGN_IN,
    EAuthenticationErrorCodes.INVALID_EMAIL_MAGIC_SIGN_IN,
    EAuthenticationErrorCodes.MAGIC_SIGN_IN_EMAIL_CODE_REQUIRED,
    EAuthenticationErrorCodes.INVALID_MAGIC_CODE_SIGN_IN,
    EAuthenticationErrorCodes.INVALID_MAGIC_CODE_SIGN_UP,
    EAuthenticationErrorCodes.EXPIRED_MAGIC_CODE_SIGN_IN,
    EAuthenticationErrorCodes.EXPIRED_MAGIC_CODE_SIGN_UP,
    EAuthenticationErrorCodes.EMAIL_CODE_ATTEMPT_EXHAUSTED_SIGN_IN,
    EAuthenticationErrorCodes.EMAIL_CODE_ATTEMPT_EXHAUSTED_SIGN_UP,
    EAuthenticationErrorCodes.OAUTH_NOT_CONFIGURED,
    EAuthenticationErrorCodes.GOOGLE_NOT_CONFIGURED,
    EAuthenticationErrorCodes.GITHUB_NOT_CONFIGURED,
    EAuthenticationErrorCodes.GITLAB_NOT_CONFIGURED,
    EAuthenticationErrorCodes.GOOGLE_OAUTH_PROVIDER_ERROR,
    EAuthenticationErrorCodes.GITHUB_OAUTH_PROVIDER_ERROR,
    EAuthenticationErrorCodes.GITLAB_OAUTH_PROVIDER_ERROR,
    EAuthenticationErrorCodes.INVALID_PASSWORD_TOKEN,
    EAuthenticationErrorCodes.EXPIRED_PASSWORD_TOKEN,
    EAuthenticationErrorCodes.INCORRECT_OLD_PASSWORD,
    EAuthenticationErrorCodes.MISSING_PASSWORD,
    EAuthenticationErrorCodes.INVALID_NEW_PASSWORD,
    EAuthenticationErrorCodes.PASSWORD_ALREADY_SET,
    EAuthenticationErrorCodes.ADMIN_ALREADY_EXIST,
    EAuthenticationErrorCodes.REQUIRED_ADMIN_EMAIL_PASSWORD_FIRST_NAME,
    EAuthenticationErrorCodes.INVALID_ADMIN_EMAIL,
    EAuthenticationErrorCodes.INVALID_ADMIN_PASSWORD,
    EAuthenticationErrorCodes.REQUIRED_ADMIN_EMAIL_PASSWORD,
    EAuthenticationErrorCodes.ADMIN_AUTHENTICATION_FAILED,
    EAuthenticationErrorCodes.ADMIN_USER_ALREADY_EXIST,
    EAuthenticationErrorCodes.ADMIN_USER_DOES_NOT_EXIST,
    EAuthenticationErrorCodes.ADMIN_USER_DEACTIVATED,
    EAuthenticationErrorCodes.RATE_LIMIT_EXCEEDED,
    EAuthenticationErrorCodes.PASSWORD_TOO_WEAK,
  ];

  if (bannerAlertErrorCodes.includes(errorCode))
    return {
      type: EErrorAlertType.BANNER_ALERT,
      code: errorCode,
      title: errorCodeMessages[errorCode]?.title || "Error",
      message: errorCodeMessages[errorCode]?.message(email) || translate("something_went_wrong_please_try_again"),
    };

  return undefined;
};

export const passwordErrors = [
  EAuthenticationErrorCodes.PASSWORD_TOO_WEAK,
  EAuthenticationErrorCodes.INVALID_NEW_PASSWORD,
];
