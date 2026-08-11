---
name: branch-name
description: Use when starting a new branch or renaming an existing one — produces a branch name in the format `<type>/<short-description>`, always cut from `main`.
user_invocable: true
---

# Branch Naming

Create branch names that follow the convention `<type>/<short-description>`. Branches são sempre cortadas de `main` (ver VERSIONING.md).

## Format

```
<type>/<short-description>
```

- All lowercase, hyphen-separated
- Short description is 2–5 words in kebab-case, focused on the _what_, not the _how_

## Workflow

1. **Determine the type** based on the work being done:
   - `feat` — new functionality
   - `fix` — bug fix
   - `chore` — tooling, deps, config, non-user-facing housekeeping
   - `refactor` — restructuring without behavior change
   - `docs` — documentation only
   - `perf` — performance improvement

2. **Write the short description**:
   - 2–5 words in kebab-case
   - Describe the outcome, not the implementation (`add-app-tile-visibility`, not `update-tile-component`)
   - Skip filler words (`the`, `a`, `for`)

3. **Assemble and create the branch**:

```
   git switch -c <type>/<short-description> main
```

4. **Return the branch name** to the user.

## Examples

```
fix/relative-config-urls
feat/app-tile-visibility
chore/bump-eslint
refactor/extract-auth-middleware
docs/pr-template-update
perf/cache-workspace-lookup
i18n/traduzir-empty-states
```

## Common Mistakes

- Using underscores or camelCase instead of hyphens
- Writing a long, narrative description — keep it scannable
- Cutting the branch from anything other than `main`
- Using a type that won't match the eventual PR type (pick the type you'd use in the PR title)
