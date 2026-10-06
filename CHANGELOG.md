# Changelog

English | [Français](CHANGELOG.fr.md)

All notable changes to this project are documented in this file.
Versions follow [Semantic Versioning](https://semver.org/): see [docs/technical/releasing.md](docs/technical/releasing.md).

## [0.4.0] - 2026-10-04

### Features

- backend: reject access tokens issued before a logout or password reset (#56)
- frontend: show a not found page for unknown URLs (#61)
- frontend: catch rendering errors with an error boundary (#62)

### Bug fixes

- backend: handle concurrent first Google sign-ins (#54)
- backend: delete expired refresh tokens at sign-in (#55)
- frontend: redirect signed-in users away from sign-in pages (#60)

### Refactoring

- backend: name database constraints deterministically (#52)
- frontend: share the API error check (#58)
- frontend: share the auth page layout and error message (#59)

### Documentation

- todo: plan end-to-end tests with the tier list editor (#64)

### Tests

- backend: check that migrations match the models (#51)

### Chores

- remove the hello world demo (#57)
- frontend: lint accessibility with eslint-plugin-jsx-a11y-x (#63)
- frontend: detect unused exports, files and dependencies with knip (#65)

## [0.3.0] - 2026-10-03

### Features

- frontend: adopt tailwind css and shadcn/ui as the ui library (#41)
- frontend: add a dark mode (light / dark / system) (#42)
- backend: send transactional emails over smtp (#45)
- verify the email address with a link sent by email (#46)
- reset a forgotten password with a link sent by email (#48)

### Bug fixes

- backend: tolerate clock skew when verifying google id tokens (#39)

### Documentation

- add a french changelog kept up to date by the release script (#38)
- todo: remove the completed setup, checks and release sections (#40)
- todo: plan the design system once the tier list editor exists (#44)

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
