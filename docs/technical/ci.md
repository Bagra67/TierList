# Continuous integration

English | [Français](ci.fr.md)

How the GitHub Actions workflows fit together, why the CI is built the way it is, and how to keep it fast. The jobs and their steps are listed in the [README](../../README.md#continuous-integration-github-actions); every test is described in the [testing guide](testing.md).

## 1. Workflows and how they chain

| Workflow      | Starts on                                                         | Does                                                                                                 |
| ------------- | ----------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| `ci.yml`      | every PR; a push to `develop` or `main`                           | `Changed parts`, `Backend`, `Frontend`, `Secrets`                                                    |
| `docs.yml`    | every PR (also when a label changes); a push to `develop`/`main`  | `Docs`: bilingual docs and testing guide in sync                                                     |
| `deploy.yml`  | a completed `CI` or `Release` run of `develop` or `main`; by hand | staging after a CI push to `develop`, production after `Release` ([deployment guide](deployment.md)) |
| `release.yml` | a completed CI push to `main`                                     | tags `vX.Y.Z` and publishes the GitHub Release ([releasing guide](releasing.md))                     |
| `bundle.yml`  | called by `deploy.yml`                                            | builds the archive deployed to the pods                                                              |
| `backup.yml`  | every night; by hand                                              | database backup                                                                                      |

```text
PR ──> CI + Docs (required checks) ──squash──> push develop ──> CI ──> Deploy (staging)
release PR develop ──> main ──merge commit──> push main ──> CI ──> Release ──> Deploy (production)
```

`Deploy` and `Release` start from `workflow_run`, which GitHub reads from the default branch (`develop`): a change to them applies once merged into `develop`. `Deploy` filters the completed runs on `develop` and `main`; a `Release` run counts as a run of `develop`, since a `workflow_run` runs on the default branch.

## 2. Only what a PR touches

The `Changed parts` job (a few seconds) lists the files of the PR through the GitHub API, then `Backend` and `Frontend` run only for their part:

| Files of the PR                                          | Backend | Frontend |
| -------------------------------------------------------- | :-----: | :------: |
| `backend/…`                                              |    ✓    |          |
| `backend/openapi.json` (the frontend types come from it) |    ✓    |    ✓     |
| `frontend/…`, `docs/…` (Prettier checks `docs/`)         |         |    ✓     |
| other Markdown files (README, `AGENTS.md`…)              |         |          |
| any other file (`.github/`, `compose.yaml`…)             |    ✓    |    ✓     |

- A **skipped job counts as passed** for the required checks: the rulesets need no change.
- A **push to `develop` or `main` always runs everything**: it deploys staging or creates the release.
- **When in doubt, everything runs**: an unknown file, an API error or a failed `Changed parts` job.
- A new kind of file that only one side checks needs a line in the `case` of `ci.yml`, otherwise both jobs run for it (safe, only slower).

## 3. Speed choices

Measured during the spike #246 on `ubuntu-latest` (4 vCPU), median of several runs:

| Change                                                     | Effect                                                                              |
| ---------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| Development on Python 3.13, the version of the pods        | the suite runs once instead of twice (3.11, then 3.13); `Backend` ≈ 241 s → ≈ 112 s |
| Coverage through `sys.monitoring` (`COVERAGE_CORE=sysmon`) | coverage costs almost nothing; line coverage only (no branch coverage is measured)  |
| SeaweedFS started in the background                        | its 14 s of start-up overlap the install and the checks; `Backend` ≈ 100 s          |
| `pytest -n auto` (pytest-xdist)                            | tests ≈ 64 s → ≈ 57 s; `Backend` ≈ 90 s                                             |
| Vitest files not isolated (`isolate: false`)               | Vitest 25–40 s → ≈ 10 s; `Frontend` ≈ 55 s                                          |

Kept as they are, on purpose:

- **Docs on label events**: creating a PR with labels runs `Docs` several times (≈ 10 s each). Skipping those runs would report a _skipped_, so passed, `Docs` check on a commit whose earlier run failed.
- **CI on the push after a merge**: it re-runs the tree the PR already tested, but its success gates the staging deployment and the release.
- **Parallel frontend jobs** (lint, `tsc`, knip, build): each new job pays its own setup (≈ 20 s) to save about 5 s.
- **Python 3.14**: the suite passes on it, but it is not faster than 3.13 with `sysmon`, and it depends on the Python of the pods.

## 4. Keeping it fast and reliable

- Backend tests must work in parallel: no fixed name shared between tests in the database or the S3 bucket, and no random value in a `parametrize` list (every worker must collect the same test names). See the [testing guide](testing.md#15-integration-tests-testsintegration-real-postgresql-and-s3).
- Frontend test files share their modules and jsdom: a file restores what it changes, and the global setup resets the rest. Waits use the common 3 s timeout. See the [testing guide](testing.md).
- The run summary lists the slowest tests of each job: a test that climbs there is worth a look.
