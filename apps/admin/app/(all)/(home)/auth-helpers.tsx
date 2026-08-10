/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import Link from "next/link";
// plane packages
import type { TAdminAuthErrorInfo } from "@plane/constants";
import { SUPPORT_EMAIL, EAdminAuthErrorCodes } from "@plane/constants";
import { translate } from "@plane/i18n";

export enum EErrorAlertType {
  BANNER_ALERT = "BANNER_ALERT",
  INLINE_FIRST_NAME = "INLINE_FIRST_NAME",
  INLINE_EMAIL = "INLINE_EMAIL",
  INLINE_PASSWORD = "INLINE_PASSWORD",
  INLINE_EMAIL_CODE = "INLINE_EMAIL_CODE",
}

const errorCodeMessages: {
  [key in EAdminAuthErrorCodes]: { title: string; message: (email?: string) => React.ReactNode };
} = {
  // admin
  [EAdminAuthErrorCodes.ADMIN_ALREADY_EXIST]: {
    title: `Admin already exists`,
    message: () => translate("auth_error.admin_already_exists_please_try_again"),
  },
  [EAdminAuthErrorCodes.REQUIRED_ADMIN_EMAIL_PASSWORD_FIRST_NAME]: {
    title: translate("auth_error.email_password_and_first_name_required"),
    message: () => translate("auth_error.email_password_and_first_name_required_please_try_ag"),
  },
  [EAdminAuthErrorCodes.INVALID_ADMIN_EMAIL]: {
    title: translate("auth_error.invalid_admin_email"),
    message: () => translate("auth_error.invalid_admin_email_please_try_again"),
  },
  [EAdminAuthErrorCodes.INVALID_ADMIN_PASSWORD]: {
    title: translate("auth_error.invalid_admin_password"),
    message: () => translate("auth_error.invalid_admin_password_please_try_again"),
  },
  [EAdminAuthErrorCodes.REQUIRED_ADMIN_EMAIL_PASSWORD]: {
    title: translate("auth_error.email_and_password_required"),
    message: () => translate("auth_error.email_and_password_required_please_try_again"),
  },
  [EAdminAuthErrorCodes.ADMIN_AUTHENTICATION_FAILED]: {
    title: translate("auth_error.authentication_failed"),
    message: () => translate("auth_error.authentication_failed_please_try_again"),
  },
  [EAdminAuthErrorCodes.ADMIN_USER_ALREADY_EXIST]: {
    title: `Admin user already exists`,
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
  [EAdminAuthErrorCodes.ADMIN_USER_DOES_NOT_EXIST]: {
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
  [EAdminAuthErrorCodes.ADMIN_USER_DEACTIVATED]: {
    title: `User account deactivated`,
    message: () => `User account deactivated. Please contact ${SUPPORT_EMAIL ? SUPPORT_EMAIL : "administrator"}.`,
  },
};

export const authErrorHandler = (errorCode: EAdminAuthErrorCodes, email?: string): TAdminAuthErrorInfo | undefined => {
  const bannerAlertErrorCodes = [
    EAdminAuthErrorCodes.ADMIN_ALREADY_EXIST,
    EAdminAuthErrorCodes.REQUIRED_ADMIN_EMAIL_PASSWORD_FIRST_NAME,
    EAdminAuthErrorCodes.INVALID_ADMIN_EMAIL,
    EAdminAuthErrorCodes.INVALID_ADMIN_PASSWORD,
    EAdminAuthErrorCodes.REQUIRED_ADMIN_EMAIL_PASSWORD,
    EAdminAuthErrorCodes.ADMIN_AUTHENTICATION_FAILED,
    EAdminAuthErrorCodes.ADMIN_USER_ALREADY_EXIST,
    EAdminAuthErrorCodes.ADMIN_USER_DOES_NOT_EXIST,
    EAdminAuthErrorCodes.ADMIN_USER_DEACTIVATED,
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
