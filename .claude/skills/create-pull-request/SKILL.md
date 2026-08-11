---
name: create-pull-request
description: Use when creating a pull request for the current branch — gathers branch context, generates a PR description in pt-BR following the repo's pull_request_template.md, and creates the PR against `main`.
user_invocable: true
---

# Create PR

Create a pull request using the repo's PR template, with a fully filled-out description based on the actual diff. Título e corpo em português, como o resto do repositório.

## Workflow

1. **Determine the base branch**: Default to `main` unless the user specifies otherwise. Nunca use `preview`/`master` — são branches do upstream (ver UPSTREAM.md).

2. **Gather context** (in parallel):
   - `git status -s` — check for uncommitted changes
   - `git diff <base>...HEAD --stat` — files changed
   - `git log <base>...HEAD --oneline` — all commits on the branch
   - `git diff <base>...HEAD --no-color` — full diff for understanding changes (if very large, focus on the most important files first)
   - `git rev-parse --abbrev-ref --symbolic-full-name @{u}` — check if branch tracks a remote
   - Read `.github/pull_request_template.md` from the repo root

3. **Draft the PR** using the template from step 2:

   **Title**: `<type>: <resumo conciso>` (under 70 chars, em português)
   - Type reflects the change: `fix`, `feat`, `chore`, `refactor`, `docs`, `perf`, `i18n`

   **Body**: Fill in every section from the PR template based on the actual diff:
   - **Description** — Clear, concise summary of what the PR does and why. Focus on the "what" and "why", not line-by-line changes. Mention important implementation decisions.
   - **Type of Change** — Check the appropriate box(es): Bug fix, Feature, Improvement, Code refactoring, Performance improvements, Documentation update.
   - **Screenshots and Media** — Leave a placeholder: `<!-- Add screenshots here -->`
   - **Test Scenarios** — Suggest concrete scenarios grounded in the actual changes (e.g., "Navigate to project settings and verify the new toggle works"), not generic ones.
   - **References** — Link related issues the user mentions. Em cherry-pick vindo do upstream, cite o commit de origem e o CVE/GHSA.

   Append a Claude Code session line at the bottom of the body.

4. **Push and create** (in parallel where possible):
   - Push branch with `-u` if no upstream is set
   - Create PR via `gh pr create` using a HEREDOC for the body

5. **Return the PR URL** to the user.

## Example Title

```
fix: permitir URLs relativas em configuration_url
```

## Guidelines

- Keep the description concise but informative
- Use bullet points when listing multiple changes
- Focus on user-facing impact, not implementation details
- Don't fabricate test scenarios that aren't relevant to the actual changes

## Common Mistakes

- Summarizing only the latest commit instead of all commits on the branch
- Forgetting to check for an upstream before pushing
- Abrir o PR contra `preview`/`master` em vez de `main`
- Wrapping the PR body in a code fence when passing it to `gh pr create`
