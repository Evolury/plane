# Como contribuir

Este guia cobre o fluxo de trabalho do repositório, o setup local e as
convenções de tradução. Para o esquema de versão e o processo de release, ver
[VERSIONING.md](VERSIONING.md); para a relação com o Plane CE, [UPSTREAM.md](UPSTREAM.md).

## Fluxo de trabalho

**Branch.** Toda branch sai de `main` e segue `<tipo>/<descrição-curta>`, em
minúsculas e com hífens. Tipos: `feat`, `fix`, `chore`, `refactor`, `docs`,
`perf`, `i18n`. Nunca trabalhe direto na `main`, e nunca use os nomes do
upstream (`preview`, `master`, `canary`).

**Commits.** Conventional commits, com assunto em português e no imperativo:
`feat(web): ocultar faturamento das configurações`. O corpo importa mais que o
assunto — explique _por que_ a mudança existe, não o que o diff já mostra. Se a
mudança tem número (tamanho de imagem, tempo de query, contagem de strings),
inclua a medição.

**PR.** Base sempre `main`, seguindo o [template](.github/pull_request_template.md).
Os checks que rodam: lint e build (api e web apps), tipos, sync de i18n,
migrações quando o modelo mudar, copyright e CodeQL.

Os de i18n são três, e cada um pega o que os outros não veem:

| Check            | O que pega                                                                                                                               |
| ---------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| `check:sync`     | chave que existe num idioma e falta no outro                                                                                             |
| `check:chaves`   | chave que o código pede e não existe em lugar nenhum — na tela ela aparece como o próprio identificador                                  |
| `check:literais` | **texto em inglês no código que já tem tradução pronta** — o defeito mais comum, e o único que nenhuma comparação entre arquivos enxerga |

Para deixar um texto em inglês de propósito — nome próprio, formato de papel,
termo técnico —, acrescente-o à lista comentada em
`packages/i18n/scripts/literais-traduziveis.ts`. A lista é curta por regra:
exceção sem justificativa é onde o problema se esconde.

**Merge.** Squash, um commit por PR. As mensagens dos commits da branch viram o
corpo da mensagem final.

**Correção vinda do upstream.** Não faça merge de branch do Plane: cherry-pick
com `-x` e registre o CVE/GHSA no PR. O passo a passo está em
[UPSTREAM.md](UPSTREAM.md).

## Abrindo uma issue

Antes de abrir, procure nas [issues](https://github.com/Evolury/plane/issues) —
pode já existir registro ou contorno.

Para bug, o essencial é conseguirmos reproduzir: descreva o passo a passo, o que
era esperado e o que aconteceu, com versão da instância (visível no god-mode),
navegador e, quando houver, o erro do console ou o trecho de log. Sem
reprodução, a investigação empaca.

Títulos seguem o formato:

- Bug: `🐛 Bug: [descrição curta]`
- Funcionalidade: `🚀 Feature: [descrição curta]`
- Melhoria: `🛠️ Improvement: [descrição curta]`
- Documentação: `📘 Docs: [descrição curta]`

Vulnerabilidade **não** vira issue: ver [SECURITY.md](SECURITY.md).

## Projects setup and Architecture

### Requirements

- Docker Engine installed and running
- Node.js version 20+ [LTS version](https://nodejs.org/en/about/previous-releases)
- Python version 3.8+
- Postgres version v14
- Redis version v6.2.7
- **Memory**: Minimum **12 GB RAM** recommended
  > ⚠️ Running the project on a system with only 8 GB RAM may lead to setup failures or memory crashes (especially during Docker container build/start or dependency install). Use cloud environments like GitHub Codespaces or upgrade local RAM if possible.

### Setup the project

The project is a monorepo, with backend api and frontend in a single repo.

The backend is a django project which is kept inside apps/api

1. Clone the repo

```bash
git clone git@github.com:Evolury/plane.git [folder-name]
cd [folder-name]
chmod +x setup.sh
```

2. Run setup.sh

```bash
./setup.sh
```

3. Start the containers

```bash
docker compose -f docker-compose-local.yml up
```

4. Start web apps:

```bash
pnpm dev
```

5. Open your browser to http://localhost:3001/god-mode/ and register yourself as instance admin
6. Open up your browser to http://localhost:3000 then log in using the same credentials from the previous step

That’s it! You’re all set to begin coding. Remember to refresh your browser if changes don’t auto-reload. Happy contributing! 🎉

## Coding guidelines

- Funcionalidade nova e correção de bug vêm acompanhadas de teste.
- Lint com [OxLint](https://oxc.rs/docs/guide/usage/linter) (`.oxlintrc.json`) e
  formatação com [oxfmt](https://oxc.rs/docs/guide/usage/formatter)
  (`.oxfmtrc.json`), ambos na raiz. `pnpm check` roda formato, lint e tipos;
  `pnpm fix` corrige o que é automático.
- Texto visível ao usuário nunca é escrito direto no componente: vai para o
  i18n, seguindo o guia de tradução abaixo.
- **Constante carrega chave, nunca texto.** Um campo `label`/`title`/`name` em
  inglês ao lado de um `i18n_*` é a forma mais comum de o inglês vazar para a
  tela: o texto existe, a tradução existe, e algum consumidor lê o campo
  errado — sem erro de compilação e sem alarme em teste. Guarde só o
  `i18n_*` ([ADR 0008](docs/evolury/decisoes/0008-i18n-nos-pacotes-compartilhados.md)).
- **Identidade é `key`, nunca o rótulo.** Comparar com o texto
  (`item.name === "Intake"`) faz a tela quebrar em silêncio no dia em que
  alguém a traduzir.
- Ao alterar arquivo herdado do upstream, marque a divergência com um comentário
  começando por `Evolury:` explicando o motivo. É o que torna a mudança
  reconhecível anos depois, quando ninguém lembra do contexto.
- Cabeçalho de copyright: os arquivos herdados mantêm o da Plane Software Inc.
  Ver [UPSTREAM.md](UPSTREAM.md).

## Contributing to language support

This guide is designed to help contributors understand how to add or update translations in the application.

### Understanding translation structure

#### File organization

Translations are organized by language in the locales directory. Each language has its own folder containing JSON files for translations. Here's how it looks:

```
packages/i18n/src/locales/
    ├── en/
    │   ├── core.json       # Critical translations
    │   └── translations.json
    ├── fr/
    │   └── translations.json
    └── [language]/
        └── translations.json
```

#### Nested structure

To keep translations organized, we use a nested structure for keys. This makes it easier to manage and locate specific translations. For example:

```json
{
  "issue": {
    "label": "Work item",
    "title": {
      "label": "Work item title"
    }
  }
}
```

### Translation formatting guide

We use [IntlMessageFormat](https://formatjs.github.io/docs/intl-messageformat/) to handle dynamic content, such as variables and pluralization. Here's how to format your translations:

#### Examples

- **Simple variables**

  ```json
  {
    "greeting": "Hello, {name}!"
  }
  ```

- **Pluralization**
  ```json
  {
    "items": "{count, plural, one {Work item} other {Work items}}"
  }
  ```

### Contributing guidelines

#### Updating existing translations

1. Locate the key in `locales/<language>/translations.json`.

2. Update the value while ensuring the key structure remains intact.
3. Preserve any existing ICU formats (e.g., variables, pluralization).

#### Adding new translation keys

1. When introducing a new key, ensure it is added to **all** language files, even if translations are not immediately available. Use English as a placeholder if needed.

2. Keep the nesting structure consistent across all languages.

3. If the new key requires dynamic content (e.g., variables or pluralization), ensure the ICU format is applied uniformly across all languages.

### Adding new languages

Adding a new language involves several steps to ensure it integrates seamlessly with the project. Follow these instructions carefully:

1.  **Update type definitions**
    Add the new language to the TLanguage type in the language definitions file:

```ts
// packages/i18n/src/types/language.ts
export type TLanguage = "en" | "fr" | "your-lang";
```

1.  **Add language configuration**
    Include the new language in the list of supported languages:

```ts
// packages/i18n/src/constants/language.ts
export const SUPPORTED_LANGUAGES: ILanguageOption[] = [
  { label: "English", value: "en" },
  { label: "Your Language", value: "your-lang" },
];
```

2.  **Create translation files**
    1. Create a new folder for your language under locales (e.g., `locales/your-lang/`).

    2. Add a `translations.json` file inside the folder.

    3. Copy the structure from an existing translation file and translate all keys.

3.  **Update import logic**
    Modify the language import logic to include your new language:

```ts
      private importLanguageFile(language: TLanguage): Promise<any> {
      switch (language) {
          case "your-lang":
          return import("../locales/your-lang/translations.json");
          // ...
      }
      }
```

### Quality checklist

Before submitting your contribution, please ensure the following:

- All translation keys exist in every language file.
- Nested structures match across all language files.
- ICU message formats are correctly implemented.
- All languages load without errors in the application.
- Dynamic values and pluralization work as expected.
- There are no missing or untranslated keys.

#### Pro tips

- When in doubt, refer to the English translations for context.
- Verify pluralization works with different numbers.
- Ensure dynamic values (e.g., `{name}`) are correctly interpolated.
- Double-check that nested key access paths are accurate.

Happy translating! 🌍✨

## Dúvidas e sugestões

Abra uma [issue](https://github.com/Evolury/plane/issues) ou escreva para
[contato@evolury.com.br](mailto:contato@evolury.com.br).
