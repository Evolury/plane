/**
 * Copyright (c) 2026-present Evolury
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { imagemEhSegura, literalDeHostBloqueado, REDES_BLOQUEADAS } from "@/lib/url-security";

describe("imagemEhSegura — o que o servidor recusa buscar", () => {
  it("recusa os alvos que motivaram o guarda", () => {
    // Cada linha é um pedido que o servidor faria, hoje, se alguém colasse
    // isto como imagem numa página.
    const alvos = [
      "http://169.254.169.254/latest/meta-data/iam/security-credentials/", // metadados da nuvem
      "http://metadata.google.internal/computeMetadata/v1/", // idem, no GCP
      "http://plane-db:5432/", // nome de serviço do Docker: rótulo único
      "http://plane-minio:9000/uploads/", // idem
      "http://localhost:8000/api/", // a própria API, por dentro
      "http://127.0.0.1:6379/", // Redis
      "http://10.0.0.5/interno.png", // rede privada
      "http://192.168.1.1/admin", // roteador
      "http://172.16.0.9/", // privada /12
      "http://[::1]:8000/", // loopback IPv6
      "http://[fd00::1]/", // único-local IPv6
      "file:///etc/passwd", // esquema de disco
      "/etc/passwd", // caminho absoluto: viraria fs.readFile
      "../../etc/passwd", // caminho relativo
      "gopher://exemplo.com/", // esquema exótico
      "http://exemplo.com@10.0.0.5/", // credencial disfarçando o host real
    ];
    for (const alvo of alvos) {
      expect(imagemEhSegura(alvo), alvo).toBe(false);
    }
  });

  it("recusa endereço disfarçado de número", () => {
    // A forma clássica de passar por uma comparação de texto ingênua.
    for (const alvo of ["http://0x7f.1/", "http://2130706433/", "http://0177.0.0.1/", "http://0/"]) {
      expect(imagemEhSegura(alvo), alvo).toBe(false);
    }
  });

  it("recusa caractere de controle contrabandeado no meio da URL", () => {
    expect(imagemEhSegura("http://exemplo.com\n/x.png")).toBe(false);
    expect(imagemEhSegura(" http://exemplo.com/x.png")).toBe(false);
    expect(imagemEhSegura("http://exemplo.com\t/x.png")).toBe(false);
  });

  it("recusa entrada vazia e o que não é texto", () => {
    expect(imagemEhSegura("")).toBe(false);
    expect(imagemEhSegura(undefined as unknown as string)).toBe(false);
    expect(imagemEhSegura(null as unknown as string)).toBe(false);
  });

  it("aceita o que o produto realmente usa", () => {
    // Se estes falharem, o guarda quebrou o PDF de quem não fez nada de errado.
    const legitimos = [
      "data:image/jpeg;base64,/9j/4AAQSkZJRg==", // o que `processImages` devolve
      "data:image/png;base64,iVBORw0KGgo=",
      "https://plane.evolury.app.br/uploads/a.png",
      "https://exemplo-s3.amazonaws.com/bucket/chave.png?assinatura=x",
      "http://cdn.exemplo.com/a.png",
    ];
    for (const url of legitimos) {
      expect(imagemEhSegura(url), url).toBe(true);
    }
  });

  it("não confunde nome público com nome interno pelo prefixo", () => {
    // "localhost.exemplo.com" é um domínio público legítimo; "api.local" não é.
    expect(imagemEhSegura("https://localhost.exemplo.com/a.png")).toBe(true);
    expect(imagemEhSegura("https://api.local/a.png")).toBe(false);
    expect(imagemEhSegura("https://servico.internal/a.png")).toBe(false);
  });

  it("não deixa o ponto final escapar do teste de rótulo único", () => {
    // "plane-db." é o mesmo host que "plane-db" para o resolvedor.
    expect(imagemEhSegura("http://plane-db./")).toBe(false);
    expect(imagemEhSegura("http://localhost./")).toBe(false);
  });
});

describe("literalDeHostBloqueado", () => {
  it("deixa passar endereço público literal", () => {
    // Não é o vetor: buscar 8.8.8.8 não alcança nada de dentro.
    expect(literalDeHostBloqueado("8.8.8.8")).toBe(false);
    expect(literalDeHostBloqueado("1.2.3.4")).toBe(false);
  });

  it("bloqueia as faixas internas", () => {
    for (const ip of ["127.0.0.1", "10.255.255.255", "172.31.0.1", "192.168.0.1", "169.254.169.254", "100.64.0.1"]) {
      expect(literalDeHostBloqueado(ip), ip).toBe(true);
    }
  });

  it("julga IPv6 pela forma canônica, e não pelo texto recebido", () => {
    // `::1` se escreve de muitas maneiras. Comparar prefixo contra uma delas
    // deixa as outras passarem — foi o que um commit posterior do upstream
    // corrigiu no guarda deles, e o que este teste tranca aqui.
    //
    // A armadilha específica: chamada por `imagemEhSegura`, esta função recebe
    // um host que o `new URL` já canonicalizou, então ela PARECERIA correta sem
    // normalizar nada. É exportada; estes casos são a chamada direta.
    const disfarces = [
      "0:0:0:0:0:0:0:1", // loopback expandido
      "0000:0000:0000:0000:0000:0000:0000:0001", // idem, com zeros à esquerda
      "0:0:0:0:0:ffff:127.0.0.1", // IPv4 mapeado, forma longa
      "0:0:0:0:0:ffff:7f00:1", // idem, em hexadecimal
      "0:0:0:0:0:ffff:a9fe:a9fe", // metadados da nuvem por dentro do IPv6
      "fe80:0:0:0:0:0:0:1", // link-local expandido
      "0064:ff9b:0000:0000:0000:0000:7f00:0001", // NAT64 com zeros à esquerda
    ];
    for (const host of disfarces) {
      expect(literalDeHostBloqueado(host), host).toBe(true);
    }
  });

  it("recusa o que tem dois-pontos e não se lê como IPv6", () => {
    // Sem forma canônica não há o que julgar — e o que não se julga, recusa-se.
    expect(literalDeHostBloqueado("::zz::1")).toBe(true);
    expect(literalDeHostBloqueado("1:2:3")).toBe(true);
  });

  it("deixa passar IPv6 público", () => {
    // `2001:db8::` não é Teredo (que é `2001:0000::/32`): não pode ser
    // confundido com ele pelo prefixo "2001:".
    expect(literalDeHostBloqueado("2606:4700::6810:85e5")).toBe(false);
    expect(literalDeHostBloqueado("2001:db8::1")).toBe(false);
  });

  it("não bloqueia vizinho de faixa que está de fora", () => {
    // 172.32.0.1 fica FORA de 172.16.0.0/12, e 11.0.0.1 fora de 10.0.0.0/8.
    // Sem isto, uma máscara errada passaria despercebida: bloquear demais
    // também é defeito.
    expect(literalDeHostBloqueado("172.32.0.1")).toBe(false);
    expect(literalDeHostBloqueado("11.0.0.1")).toBe(false);
    expect(literalDeHostBloqueado("192.169.0.1")).toBe(false);
  });
});

describe("a lista daqui e a do Python", () => {
  it("não divergiram", () => {
    // O comentário no topo dos dois arquivos promete que as listas andam
    // juntas. Promessa em comentário não se sustenta sozinha — este teste é o
    // que a sustenta. Se alguém acrescentar uma faixa de um lado só, quebra
    // aqui, e não em produção, meses depois, com uma das duas defesas furada.
    const guardaPython = readFileSync(path.resolve(__dirname, "../../../api/plane/utils/ip_address.py"), "utf-8");
    const bloco = guardaPython.split("_BLOCKED_NETWORKS")[1]?.split("]")[0] ?? "";
    const doPython = [...bloco.matchAll(/"([^"]+\/\d+)"/g)].map((m) => m[1]);

    expect(doPython.length).toBeGreaterThan(0); // o arquivo mudou de forma
    expect([...REDES_BLOQUEADAS]).toEqual(doPython);
  });
});
