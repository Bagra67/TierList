# Changelog

English | [Français](CHANGELOG.fr.md)

All notable changes to this project are documented in this file.
Versions follow [Semantic Versioning](https://semver.org/): see [docs/releasing.md](docs/releasing.md).

## [0.2.0] - 2026-10-03

### Features

- auth: add account registration and email/password sign-in (#26)
- auth: let users delete their account (#27)
- auth: sign in with google (#29)
- api: return a stable error code with every error response (#31)
- frontend: translate the interface into english (i18n fr / en) (#32)

### Refactoring

- group constants, settings and exceptions (#30)

### Build & CI

- release: skip pnpm git checks when bumping the version (#35)

### Documentation

- agents: explain why automatic head branch deletion is disabled (#25)
- agents: allow merging a stack of prs with gh stack merge (#34)

## [0.1.0] - 2026-10-02

### Features

- backend: configure application logging (#5)
- frontend: fetch server data with TanStack Query and openapi-fetch (#10)
- backend: return every API error in a single JSON format (#12)
- backend: add a /health liveness probe independent of the database (#13)
- dev: start the database from the dev scripts (#14)

### Build & CI

- set up GitHub Actions, type checking, tests and Dependabot (#4)
- add a per-test report to the CI run summary (#7)
- generate frontend API types from the backend OpenAPI schema (#8)
- run the CI on every pull request, including stacked ones (#11)
- scan for secrets with gitleaks before each commit and on CI (#17)
- check commit messages with commitlint (#18)
- version releases with SemVer computed from conventional commits (#22)
- release: run git-cliff from the repository root (#23)

### Documentation

- agents: define merge strategy, English git messages and bilingual docs (#3)
- add testing guide (#6)
- agents: delete work branches once merged into develop (#9)
- add an architecture overview and close the starter roadmap (#19)
- list the Secrets job among the required CI checks (#20)
- remove the completed starter roadmap (#21)

### Chores

- initialise le monorepo TierList (backend FastAPI + frontend React)
- initialise le starter (Hello World, PostgreSQL, outillage) (#1)
- add an .editorconfig shared by every editor (#15)
- vscode: add debug configurations for FastAPI and Vitest (#16)
