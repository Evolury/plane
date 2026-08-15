import path from "node:path";
import * as dotenv from "dotenv";
import { reactRouter } from "@react-router/dev/vite";
import { defineConfig } from "vite";
import tsconfigPaths from "vite-tsconfig-paths";

dotenv.config({ path: path.resolve(__dirname, ".env") });

// Expose only vars starting with VITE_
const viteEnv = Object.keys(process.env)
  .filter((k) => k.startsWith("VITE_"))
  .reduce<Record<string, string>>((a, k) => {
    a[k] = process.env[k] ?? "";
    return a;
  }, {});

export default defineConfig(() => ({
  define: {
    "process.env": JSON.stringify(viteEnv),
  },
  build: {
    assetsInlineLimit: 0,
  },
  plugins: [reactRouter(), tsconfigPaths({ projects: [path.resolve(__dirname, "tsconfig.json")] })],
  resolve: {
    alias: {
      // Next.js compatibility shims used within web
      "next/link": path.resolve(__dirname, "app/compat/next/link.tsx"),
      "next/navigation": path.resolve(__dirname, "app/compat/next/navigation.ts"),
      "next/script": path.resolve(__dirname, "app/compat/next/script.tsx"),
    },
    dedupe: ["react", "react-dom", "@headlessui/react"],
  },
  server: {
    host: "127.0.0.1",
    // Evolury: o Vite 6 confere o cabeçalho `Host` para barrar DNS rebinding, e
    // só aceita `localhost` e IPs. Abrir o dev pelo nome do tailnet devolvia
    // 403 da própria aplicação — parecia rede, e era isto. O ponto inicial
    // cobre o tailnet inteiro, então trocar o nome da máquina não quebra.
    allowedHosts: [".ts.net"],
    // Evolury: a API atendida pela MESMA origem da página, como em produção.
    //
    // Sem isto, `VITE_API_BASE_URL` fixa um endereço só — e quem abre o dev por
    // outro nome (IP da rede, nome do tailnet) carrega a tela e não fala com a
    // API, porque `localhost` para o navegador remoto é a máquina dele. Com o
    // proxy, `API_BASE_URL` fica vazio e cada chamada segue o endereço pelo
    // qual a página foi aberta. De quebra, some o CORS: mesma origem.
    proxy: {
      "/api": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/auth": { target: "http://127.0.0.1:8000", changeOrigin: true },
    },
  },
  // No SSR-specific overrides needed; alias resolves to ESM build
}));
