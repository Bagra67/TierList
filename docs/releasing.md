# Releasing

English | [Français](releasing.fr.md)

Every merge of `develop` into `main` is a **release** with a version number `X.Y.Z` ([Semantic Versioning](https://semver.org/)), a `vX.Y.Z` tag and a GitHub Release. The version is **computed from the commit messages** of `develop` (Conventional Commits, checked by commitlint), not chosen by hand.

## Version rules

| Squash commit on `develop`                                  | Effect on the version               | Example                                  |
| ----------------------------------------------------------- | ----------------------------------- | ---------------------------------------- |
| `!` after the type, or a `BREAKING CHANGE:` footer          | **X** + 1 (while in 0.x: **Y** + 1) | `feat(api)!: rename /hello to /greeting` |
| `feat`                                                      | **Y** + 1                           | `feat(backend): add tier lists`          |
| `fix`, `perf`                                               | **Z** + 1                           | `fix(frontend): keep the items order`    |
| `docs`, `chore`, `ci`, `build`, `test`, `refactor`, `style` | none                                | listed in the CHANGELOG all the same     |

The highest change since the last release wins: one `feat` and three `fix` give a **Y** release.

- **One version for the whole repository**, written in `backend/pyproject.toml`, `frontend/package.json` and `app.version` (`backend/app/main.py`, also in `openapi.json`). The test `test_versions_are_in_sync` checks that they are equal.
- **0.x phase**: as long as the version is 0.x, the API is not stable and a breaking change only bumps **Y**. Moving to **1.0.0** is a deliberate decision (first version for real users): `./scripts/prepare-release.sh --version 1.0.0`.
- **Breaking changes must be visible**: the PR's squash subject carries `!` (`feat(api)!: …`) and its body explains the migration in a `BREAKING CHANGE: …` footer. Reviewers check it before merging.
- **Tags `vX.Y.Z` only exist on `main`**, created by the `Release` workflow, never by hand and never on `develop`.
- **The CHANGELOG is generated** (`CHANGELOG.md`, by [git-cliff](https://git-cliff.org) with `cliff.toml`) and reviewed in the preparation PR. A line may be fixed by hand; published sections are never regenerated.
- **The French CHANGELOG** (`CHANGELOG.fr.md`) gets the same section, with French headings (`cliff.fr.tera`). Its lines come from the English commit subjects: translate them when reviewing the preparation PR. The GitHub Release notes come from `CHANGELOG.md` only.
- **No direct commit or hotfix on `main`**: a fix goes through `develop`, then a **Z** release.

## Making a release

1. **Prepare** on a new branch from an up-to-date `develop`:

   ```bash
   git switch develop && git pull
   ./scripts/prepare-release.sh --dry-run          # shows the computed version
   git switch -c chore/release-vX.Y.Z
   ./scripts/prepare-release.sh                    # or --version X.Y.Z to force it
   ```

   The script updates the three version fields, regenerates `openapi.json` and `schema.d.ts`, and adds the new section at the top of `CHANGELOG.md` and `CHANGELOG.fr.md`. It refuses to run when there is nothing to release (no `feat`, `fix`, `perf` or breaking change since the last tag), when the branch does not start from `origin/develop`, or when `CHANGELOG.fr.md` is missing.

   Review `CHANGELOG.md`, translate the new lines of `CHANGELOG.fr.md`, then commit `chore(release): prepare vX.Y.Z`, open a PR to `develop` and squash-merge it.

2. **Publish**: open a PR from `develop` to `main` titled `chore(release): vX.Y.Z` and merge it with a **merge commit** (AGENTS.md §40).

3. **Automatic**: when the CI passes on `main`, the `Release` workflow (`.github/workflows/release.yml`) checks that the versions are equal, that the tag does not exist yet and that `CHANGELOG.md` has the section, then creates the `vX.Y.Z` tag on the merge commit and the GitHub Release with that section as notes. If a check fails, the workflow fails with the reason and nothing is published.

## How the version is computed

Tags are on the merge commits of `main`, which `develop` does not contain. The script therefore takes the highest `vX.Y.Z` tag of the repository and analyses the commits of `vX.Y.Z..HEAD`: this range excludes everything already released.
