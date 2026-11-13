---
name: dependabot-review
description: Review Dependabot PRs and write, in French, a summary of each changelog, the risks for TierList (breaking changes, code that uses the package), the CI state and a recommendation. Takes PR numbers, or reviews every open Dependabot PR when none is given. Read-only; use whenever the user asks about a Dependabot PR or a dependency update.
---

# Dependabot review

Read-only: never merge, approve, comment on, rebase or push to a Dependabot PR unless the user
asks for it afterwards. Never invent a changelog entry or a usage: say when something could not be
verified.

## 1. Pick the PRs

- Arguments given (e.g. `443 440`): review those PRs.
- No argument: every open Dependabot PR.

```bash
gh pr list --state open --author "app/dependabot" --json number,title,headRefName,mergeStateStatus
```

## 2. For each PR, gather the facts

1. **What moves**: package(s), old and new versions, ecosystem (`uv` backend, `npm` frontend,
   `github-actions`, `docker-compose`), and the update type (patch, minor, major; a `0.x` minor
   counts as major). Grouped PRs (`*-minor-patch`) bump several packages: list each one.

   ```bash
   gh pr view <N> --json title,body,files,mergeStateStatus,statusCheckRollup
   gh pr diff <N> --name-only
   ```

2. **Changelog**: the release notes are in the PR body (`Release notes`, `Changelog`). When the
   body is truncated or missing for a version in between, read the upstream releases
   (`gh api repos/<owner>/<repo>/releases`, or the `CHANGELOG` linked in the body). Cover every
   version between the old and the new one, not only the last.

3. **Use in TierList**: find where the package is used, so the risk is judged on the real code.

   - npm: `frontend/package.json` (dependency or devDependency), then `import ... from '<pkg>'`
     under `frontend/src/`, `frontend/e2e/` and the config files (`vite.config.ts`,
     `playwright.config.ts`, `eslint.config.js`...).
   - uv: `backend/pyproject.toml`, then `import <module>` / `from <module>` under `backend/`.
   - GitHub Actions: the `uses:` lines under `.github/workflows/`.
   - Docker Compose: the service in `compose.yaml` and what depends on it (backend storage
     settings, tests, the services in `.github/workflows/ci.yml`).

   For each breaking change or deprecation in the changelog, check whether TierList uses the
   affected API or option, and name the files.

4. **CI state**: from `statusCheckRollup` and `mergeStateStatus`. When a check fails or the PR is
   `BLOCKED`, find out why:

   ```bash
   gh run list --branch <headRefName> --limit 5 --json databaseId,name,conclusion
   gh run view <run-id> --log-failed
   ```

   Tell a failure caused by the update (test, type or build error) apart from an unrelated one
   (flaky e2e, cancelled run, missing review, branch behind `develop`).

## 3. Report, in French

One section per PR, in this format:

```markdown
## #<N> — <paquet> <ancienne> → <nouvelle> (<patch | mineure | majeure>, <backend | frontend | CI | Docker>)

**Notes de version**

- <les changements qui comptent, en quelques puces ; les corrections de sécurité en premier>

**Risques pour TierList** : <faible | moyen | élevé>

- <chaque changement cassant ou dépréciation, et si TierList est concerné, avec les fichiers>
- <« Aucun usage direct » quand le paquet n'est qu'une dépendance d'outillage>

**CI** : <verte | en échec : cause | bloquée : cause>

**Recommandation** : <fusionner | fusionner après <vérification> | attendre | fermer>, <pourquoi>
```

End with a short table of every PR reviewed (`PR`, `paquet`, `risque`, `CI`, `recommandation`).

Write in French, without franglais where a French word exists (see the vocabulary table in
`docs/technical/i18n.md`); package names, APIs and error messages stay as they are.
