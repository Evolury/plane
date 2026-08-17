/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

// Evolury: o que o servidor aceita buscar ao montar um PDF (revisão do upstream, 16/08/2026).
//
// Por que existe: o `src` de uma imagem vem do CONTEÚDO da página, e o
// `@react-pdf/renderer` busca qualquer URL que receba — inclusive um nome de
// serviço da rede interna do Docker (`http://plane-db:5432`) ou o endereço de
// metadados da nuvem (169.254.169.254) — ou lê um caminho do disco com
// `fs.readFile`. Quem consegue escrever numa página consegue fazer o servidor
// buscar o que quiser. Isso é SSRF, e estava aberto.
//
// **A fonte da verdade é o guarda Python**, em `apps/api/plane/utils/ip_address.py`.
// A lista abaixo é o espelho dele, e as duas não podem divergir: se uma bloquear
// uma faixa que a outra busca, o produto tem duas respostas para a mesma
// pergunta e a defesa vale pela mais fraca. Há teste comparando as duas listas.
//
// Falha fechada: o que não for positivamente liberado é recusado.
//
// O que este guarda NÃO cobre, dito na cara: um nome público que RESOLVE para
// um endereço interno (`interno.exemplo.com` → 10.0.0.5). Julgar isso exigiria
// resolver o DNS aqui e torcer para a busca seguinte resolver igual — a janela
// entre as duas resoluções é o próprio furo. A defesa contra isso é de rede
// (egresso do contêiner), não deste arquivo. O que se fecha aqui é o vetor
// direto: literal de endereço, nome de serviço do Docker, caminho de disco e
// esquema exótico.

/** Só estes esquemas. `file:`, `gopher:` e afins nunca são imagem legítima. */
const ESQUEMAS_PERMITIDOS = new Set(["http:", "https:", "data:"]);

/** Nomes que só existem dentro da rede — nunca uma imagem de página. */
const SUFIXOS_BLOQUEADOS = [".local", ".localhost", ".internal", ".home.arpa", ".lan"];
const NOMES_BLOQUEADOS = new Set(["localhost", "metadata", "metadata.google.internal"]);

/**
 * Espelho de `_BLOCKED_NETWORKS` do guarda Python. Mantenha na mesma ordem e
 * com os mesmos comentários — é o que torna a divergência visível numa revisão.
 */
export const REDES_BLOQUEADAS = [
  "0.0.0.0/8", // "this host on this network" (RFC 1122)
  "100.64.0.0/10", // NAT de operadora (RFC 6598)
  "169.254.0.0/16", // link-local, inclui os metadados da nuvem
  "255.255.255.255/32", // broadcast limitado
  "::ffff:0:0/96", // IPv4 mapeado em IPv6
  "64:ff9b::/96", // NAT64 (RFC 6052)
  "64:ff9b:1::/48", // NAT64 local (RFC 8215)
  "2002::/16", // 6to4
  "2001::/32", // Teredo
  "fec0::/10", // site-local IPv6, obsoleto
] as const;

/** As faixas privadas e especiais que o `ipaddress` do Python já classifica. */
const FAIXAS_IPV4_PRIVADAS: [number, number, number][] = [
  [10, 0, 8], // 10.0.0.0/8 privada
  [127, 0, 8], // 127.0.0.0/8 loopback
  [172, 16, 12], // 172.16.0.0/12 privada
  [192, 168, 16], // 192.168.0.0/16 privada
  [169, 254, 16], // 169.254.0.0/16 link-local
  [100, 64, 10], // 100.64.0.0/10 NAT de operadora
  [0, 0, 8], // 0.0.0.0/8
  [224, 0, 4], // 224.0.0.0/4 multicast
  [240, 0, 4], // 240.0.0.0/4 reservada
];

const dentroDaFaixa = (octetos: number[], base: [number, number, number]): boolean => {
  const [b0, b1, prefixo] = base;
  const valor = (octetos[0] << 24) | (octetos[1] << 16) | (octetos[2] << 8) | octetos[3];
  const raiz = (b0 << 24) | (b1 << 16);
  const mascara = prefixo === 0 ? 0 : (-1 << (32 - prefixo)) >>> 0;
  return (valor & mascara) >>> 0 === (raiz & mascara) >>> 0;
};

/** Um IPv4 em notação decimal com pontos, ou `null` se não for isso. */
const octetosDeIPv4 = (host: string): number[] | null => {
  const partes = host.split(".");
  if (partes.length !== 4) return null;
  const octetos = partes.map((p) => (/^\d{1,3}$/.test(p) ? Number(p) : Number.NaN));
  return octetos.every((o) => Number.isInteger(o) && o >= 0 && o <= 255) ? octetos : null;
};

/**
 * A forma canônica de um literal IPv6, ou `null` se não for um.
 *
 * Existe porque `::1` se escreve de muitas maneiras — `0:0:0:0:0:0:0:1`,
 * `0000:...:0001`, `::ffff:127.0.0.1` — e comparar prefixo de texto contra uma
 * delas deixa as outras passarem. Quem canonicaliza é o interpretador de URL da
 * plataforma, e não uma expansão escrita à mão aqui: a que existe está testada
 * pelo mundo inteiro, a que eu escrevesse estaria testada por mim.
 */
const canonicalizarIPv6 = (host: string): string | null => {
  try {
    // `hostname` volta entre colchetes e já comprimido: [::1], [::ffff:7f00:1].
    return new URL(`http://[${host}]/`).hostname.replace(/^\[|\]$/g, "");
  } catch {
    return null;
  }
};

/**
 * O host é um literal de endereço que não devemos buscar?
 *
 * Números em hexadecimal (`0x7f.1`), octal ou decimal curto nunca são nome de
 * máquina real e são a forma clássica de contornar comparação ingênua — todos
 * são recusados sem tentar interpretar.
 *
 * Vale chamar esta função com texto cru: ela normaliza o IPv6 por conta
 * própria. Isso não é zelo à toa — `imagemEhSegura` a chama com um host que o
 * `new URL` já canonicalizou, e sem a normalização daqui a função pareceria
 * correta ali e estaria errada em qualquer outra chamada. Ela é exportada.
 */
export const literalDeHostBloqueado = (host: string): boolean => {
  const limpo = host.replace(/^\[|\]$/g, "").toLowerCase();

  const octetos = octetosDeIPv4(limpo);
  if (octetos) return FAIXAS_IPV4_PRIVADAS.some((faixa) => dentroDaFaixa(octetos, faixa));

  // Qualquer coisa só com dígitos, hexadecimal ou pontos e sem letra de nome:
  // é endereço disfarçado, não host.
  if (/^(0x[0-9a-f]+|\d+)(\.(0x[0-9a-f]+|\d+))*$/.test(limpo)) return true;

  if (limpo.includes(":")) {
    const canonico = canonicalizarIPv6(limpo);
    // Tem dois-pontos e não é IPv6 que se leia: não há o que julgar, recusa.
    if (canonico === null) return true;
    if (canonico === "::" || canonico === "::1") return true;
    if (/^(fe[89a-f]|fc|fd)/.test(canonico)) return true; // link-local, site-local, único-local
    // As formas de transição: todas embutem IPv4 e alcançam a rede de dentro.
    if (/^(::ffff:|::|2002:|2001:0?:|64:ff9b)/.test(canonico)) return true;
    return false;
  }

  return false;
};

const nomeEhPermitido = (host: string): boolean => {
  const limpo = host.toLowerCase().replace(/\.$/, ""); // "api." burla o teste do ponto
  if (!limpo) return false;
  if (NOMES_BLOQUEADOS.has(limpo)) return false;
  if (SUFIXOS_BLOQUEADOS.some((s) => limpo.endsWith(s))) return false;
  // Sem ponto = rótulo único = nome de serviço da rede interna do Docker.
  return limpo.includes(".");
};

/**
 * Esta `src` pode ser buscada pelo servidor ao montar um PDF?
 *
 * Falha fechada: qualquer coisa que não seja positivamente liberada é `false`,
 * e o renderizador desenha um espaço reservado no lugar.
 */
export const imagemEhSegura = (src: string): boolean => {
  if (typeof src !== "string" || !src) return false;

  // Caracteres de controle, espaço e tabulação são removidos por interpretadores
  // de URL e historicamente serviram para contrabandear um esquema
  // (`java\nscript:`). Escritos como escapes de propósito: um byte de controle
  // literal aqui seria invisível na revisão.
  // oxlint-disable-next-line no-control-regex -- é exatamente isto que se recusa
  if (/[\u0000-\u0020\u007f]/.test(src)) return false;

  let url: URL;
  try {
    url = new URL(src);
  } catch {
    // Caminho relativo ou de disco cai aqui. O `@react-pdf/image` os entregaria
    // ao `fs.readFile`, então são recusados.
    return false;
  }

  if (!ESQUEMAS_PERMITIDOS.has(url.protocol)) return false;

  // `data:` carrega o conteúdo embutido — não há host a julgar.
  if (url.protocol === "data:") return true;

  // Credencial embutida em URL de imagem nunca é legítima e confunde a leitura
  // do host.
  if (url.username || url.password) return false;

  if (!url.hostname) return false;
  if (literalDeHostBloqueado(url.hostname)) return false;
  return nomeEhPermitido(url.hostname);
};
