/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// types
import type { WeekMonthDataType, ChartDataType, TGanttViews } from "@plane/types";
import { EStartOfTheWeek } from "@plane/types";
import { getMonthName, getWeekDayName } from "@plane/utils";

// constants
export const generateWeeks = (startOfWeek: EStartOfTheWeek = EStartOfTheWeek.SUNDAY): WeekMonthDataType[] => [
  ...weeks.slice(startOfWeek),
  ...weeks.slice(0, startOfWeek),
];

export const charCapitalize = (word: string) => `${word.charAt(0).toUpperCase()}${word.substring(1)}`;

// Evolury: os nomes de dia, mês e trimestre vinham cravados em inglês no
// cronograma. Passam a sair do locale ativo, pelos mesmos ajudantes que o
// calendário usa — assim não existe uma segunda lista de meses para manter.
//
// `shortTitle` de `weeks` continua em inglês DE PROPÓSITO: o gráfico compara
// esse valor com "sat"/"sun" para sombrear o fim de semana. É identificador,
// não texto de tela — a mesma distinção que vale no resto do produto.
const CHAVES_DE_DIA = ["sun", "mon", "tue", "wed", "thurs", "fri", "sat"];

export const weeks: WeekMonthDataType[] = CHAVES_DE_DIA.map((chave, dia) => ({
  key: dia,
  shortTitle: chave,
  title: getWeekDayName(dia),
  abbreviation: charCapitalize(getWeekDayName(dia, true)),
}));

export const months: WeekMonthDataType[] = Array.from({ length: 12 }, (_, mes) => ({
  key: mes,
  shortTitle: getMonthName(mes, true),
  title: getMonthName(mes),
  abbreviation: charCapitalize(getMonthName(mes, true)),
}));

export const quarters: WeekMonthDataType[] = [0, 3, 6, 9].map((primeiroMes, indice) => ({
  key: indice,
  shortTitle: `T${indice + 1}`,
  title: `${charCapitalize(getMonthName(primeiroMes, true))} - ${charCapitalize(getMonthName(primeiroMes + 2, true))}`,
  abbreviation: `T${indice + 1}`,
}));

export const bindZero = (value: number) => (value > 9 ? `${value}` : `0${value}`);

export const timePreview = (date: Date) => {
  let hours = date.getHours();
  const amPm = hours >= 12 ? "PM" : "AM";
  hours = hours % 12;
  hours = hours ? hours : 12;

  let minutes: number | string = date.getMinutes();
  minutes = bindZero(minutes);

  return `${bindZero(hours)}:${minutes} ${amPm}`;
};

export const datePreview = (date: Date, includeTime: boolean = false) => {
  const day = date.getDate();
  let month: number | WeekMonthDataType = date.getMonth();
  month = months[month];
  const year = date.getFullYear();

  return `${charCapitalize(month?.shortTitle)} ${day}, ${year}${includeTime ? `, ${timePreview(date)}` : ``}`;
};

// context data
export const VIEWS_LIST: ChartDataType[] = [
  {
    key: "week",
    i18n_title: "common.week",
    data: {
      startDate: new Date(),
      currentDate: new Date(),
      endDate: new Date(),
      approxFilterRange: 4, // it will preview week dates with weekends highlighted with 1 week limitations ex: title (Wed 1, Thu 2, Fri 3)
      dayWidth: 60,
    },
  },
  {
    key: "month",
    i18n_title: "common.month",
    data: {
      startDate: new Date(),
      currentDate: new Date(),
      endDate: new Date(),
      approxFilterRange: 6, // it will preview monthly all dates with weekends highlighted with no limitations ex: title (1, 2, 3)
      dayWidth: 20,
    },
  },
  {
    key: "quarter",
    i18n_title: "common.quarter",
    data: {
      startDate: new Date(),
      currentDate: new Date(),
      endDate: new Date(),
      approxFilterRange: 24, // it will preview week starting dates all months data and there is 3 months limitation for preview ex: title (2, 9, 16, 23, 30)
      dayWidth: 5,
    },
  },
];

export const currentViewDataWithView = (view: TGanttViews = "month") =>
  VIEWS_LIST.find((_viewData) => _viewData.key === view);
