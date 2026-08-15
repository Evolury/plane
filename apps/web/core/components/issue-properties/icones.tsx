/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: o ícone da propriedade personalizada (ADR 0011).
//
// A escolha é guardada como CHAVE, e este arquivo é o único lugar que a
// traduz em desenho. Duas consequências de propósito: nome de componente
// nunca vem do banco, e trocar de biblioteca de ícones um dia é refazer este
// mapa, não migrar dado.
//
// A lista é curta e fechada, como a das moedas — o servidor recusa o que não
// está nela. Ela precisa espelhar `ICONES_DE_PROPRIEDADE` do backend; a
// diferença apareceria como ícone vazio, e por isso existe o teste que compara
// as duas.

import {
  Briefcase,
  Building,
  Calendar,
  CircleCheck,
  Clock,
  CreditCard,
  DollarSign,
  FileText,
  Flag,
  Folder,
  Hash,
  Layers,
  Link,
  List,
  Mail,
  MapPin,
  Package,
  Percent,
  Phone,
  ShoppingCart,
  Sparkles,
  Star,
  Tag,
  Target,
  Truck,
  TriangleAlert,
  Type,
  User,
  Users,
  Wrench,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { TIssueProperty, TPropertyType } from "@plane/types";

export const ICONES_DE_PROPRIEDADE: Record<string, LucideIcon> = {
  tag: Tag,
  hash: Hash,
  type: Type,
  calendar: Calendar,
  clock: Clock,
  "dollar-sign": DollarSign,
  percent: Percent,
  list: List,
  layers: Layers,
  "circle-check": CircleCheck,
  flag: Flag,
  star: Star,
  target: Target,
  "triangle-alert": TriangleAlert,
  users: Users,
  user: User,
  building: Building,
  "map-pin": MapPin,
  phone: Phone,
  mail: Mail,
  link: Link,
  "file-text": FileText,
  folder: Folder,
  package: Package,
  truck: Truck,
  "shopping-cart": ShoppingCart,
  "credit-card": CreditCard,
  briefcase: Briefcase,
  wrench: Wrench,
  sparkles: Sparkles,
};

/** A ordem em que o seletor mostra — a mesma do mapa, que agrupa por assunto. */
export const CHAVES_DE_ICONE = Object.keys(ICONES_DE_PROPRIEDADE);

/**
 * O ícone padrão de cada tipo.
 *
 * Existe para o padrão não ser o mesmo desenho em tudo: um campo de dinheiro
 * com cara de etiqueta obriga a ler o nome para saber o que é — justamente o
 * trabalho que o ícone deveria poupar.
 */
export const ICONE_PADRAO_POR_TIPO: Record<TPropertyType, string> = {
  text: "type",
  number: "hash",
  date: "calendar",
  select: "list",
  multi_select: "layers",
  currency: "dollar-sign",
};

/** A chave que a propriedade veste de fato — vazio cai no padrão do tipo. */
export const chaveDoIcone = (propriedade: Pick<TIssueProperty, "icon" | "property_type">): string =>
  propriedade.icon || ICONE_PADRAO_POR_TIPO[propriedade.property_type] || "tag";

/** O componente do ícone da propriedade, pronto para desenhar. */
export const iconeDaPropriedade = (propriedade: Pick<TIssueProperty, "icon" | "property_type">): LucideIcon =>
  ICONES_DE_PROPRIEDADE[chaveDoIcone(propriedade)] ?? Tag;
