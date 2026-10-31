# Changelog

English | [Français](CHANGELOG.fr.md)

All notable changes to this project are documented in this file.
Versions follow [Semantic Versioning](https://semver.org/): see [docs/technical/releasing.md](docs/technical/releasing.md).

## [1.0.1] - 2026-10-31

### Bug fixes

- frontend: give the test waits a timeout a busy machine can meet (#257)

### Build & CI

- speed up the ci, backend first (#249)
- backend: run the tests in parallel with pytest-xdist (#253)

### Documentation

- add the continuous integration guide (#258)

### Tests

- frontend: run the vitest files without isolation (#255)

### Chores

- backend: move to python 3.15, the python of the new pods (#260)

## [1.0.0] - 2026-10-30

### Features

- frontend: visual identity color tokens (#213)
- frontend: logo, favicon and display font (#214)
- new default tier colors (#215)
- frontend: tier board redesign (#216)
- frontend: home presentation and clearer states (#218)
- frontend: loading skeletons, cooldown stage and panel variants (#221)
- frontend: lucide icons (#222)
- frontend: drag preview on the boards (#227)
- frontend: three-column round layout (#228)
- frontend: cooldown side panel and move here (#229)
- votes of an item in the results (#230)
- frontend: results reveal (#231)
- frontend: terms of use, legal notice and content reports (#237)
- frontend: public home page (#239)
- frontend: shake the final cooldown in its last seconds (#244)
- frontend: add many image tiles at once (#245)

### Bug fixes

- i18n: replace franglais with plain french and english (#220)

### Refactoring

- frontend: ui consistency (#217)
- frontend: one page width for the app (#238)

### Documentation

- mark milestone 1 as done (#234)
- mark node 26 as lts (#243)

### Chores

- deps: bump astral-sh/setup-uv from 10.3.0 to 10.3.2 (#225)
- deps: bump the frontend-minor-patch group with 17 updates (#223)
- deps: bump pillow from 12.3.0 to 13.0.0 (#211)
- unblock the httpx2 and seaweedfs updates (#233)
- deps: bump the backend-minor-patch group with 6 updates (#226)
- deps: bump chrislusf/seaweedfs from 4.48 to 4.50 (#224)

## [0.6.1] - 2026-10-21

### Bug fixes

- deploy: refuse requests that reach the pod without the tunnel (#207)

## [0.6.0] - 2026-10-21

### Features

- rooms: cap rooms at 10 participants and lock arrivals during a game (#156)
- games: start a game with its snapshot and rounds (#164)
- games: place the current item with tier and position (#170)
- games: move rounds on with next, a timer or everyone placed (#171)
- frontend: game screen with the private board and the host controls (#172)
- games: play the final cooldown and end it with a timer or the admin (#175)
- frontend: cooldown screen with the final board, missed items and end now (#176)
- games: save the closed game with its frozen players (#177)
- rooms: close a room (#179)
- rooms: close inactive rooms automatically (#180)
- results: results api for a closed game (#182)
- frontend: results page with the absent votes toggle (#183)
- results: public results link (#184)
- games: play again in the same room (#186)
- history: history of the closed games of an account (#187)
- settings: settings panel in the navbar (#190)
- deploy: deploy to minestrator pods behind a cloudflare tunnel (#193)
- deploy: restart the pod through the minestrator panel api (#195)
- deploy: tell the minestrator panel when the pod is ready (#197)
- legal: privacy policy page (#203)

### Bug fixes

- games: address the audit of the game stack (#178)
- auth: hide private links once the session has ended (#189)
- images: upload tile images with the public-read acl (#199)

### Refactoring

- frontend: share the dialog shell and split the test tools (#169)
- backend: place shared types and helpers by responsibility (#166)
- api: build responses in presenters and share dependency aliases (#167)

### Documentation

- decide the hosting and the continuous deployment (#157)
- use tierlist-staging.ladwein.dev as the staging domain (#194)
- runbook of the staging setup and steps for production (#198)

### Tests

- games: cover coming back to one's seat and joining during a game (#174)

## [0.5.0] - 2026-10-16

### Features

- backend: add template crud api with default tiers (#107)
- frontend: add the my templates page with creation and deletion (#117)
- configure the tiers of a template (#118)
- edit the text tiles of a template (#119)
- decide and compute the game results (median ranking, absent votes) (#132)
- images: upload and compress tile images to s3 storage (#134)
- templates: attach images to tiles with an upload limit and cleanup (#135)
- frontend: upload and show tile images in the template editor (#137)
- templates: freeze a template snapshot when a game starts (#140)
- rooms: create rooms and configure their settings (#142)
- frontend: create a room and show its lobby (#143)
- rooms: join a room with an account (#144)
- rooms: join a room as a guest (#145)
- rooms: follow a room live with a websocket channel and presence (#147)
- rooms: remove or ban a participant from the room (#149)

### Bug fixes

- ci: stop label events from cancelling the docs check (#116)

### Refactoring

- backend: split user models and adopt model mixins (#115)

### Build & CI

- check bilingual docs and the testing guide stay in sync (#68)
- note that the release workflow is read from develop (#108)

### Documentation

- describe the product, game rules, permissions and roadmap (#69)
- split docs into product and technical folders (#70)
- product: design milestone 1 (stories, domain, lifecycles, flow, wireframes) (#73)
- decide the real-time transport for rooms (#122)
- decide the tile image upload, compression and storage (#129)
- point the game start to #91 instead of #90 (#141)

### Chores

- deps: bump sqlalchemy from 2.1.2 to 2.1.3 in /backend (#110)
- deps: bump the frontend-minor-patch group in /frontend with 7 updates (#111)
- deps-dev: bump @types/node from 24.19.0 to 26.6.4 in /frontend (#112)
- switch the node runtime to node 26 (#113)
- frontend: serve the vite dev server on 127.0.0.1 (#121)
- open the dev links in the browser when dev.sh starts (#131)
- deps: bump astral-sh/setup-uv from 10.2.0 to 10.3.0 (#150)
- deps: bump the backend-minor-patch group in /backend with 3 updates (#151)
- deps: bump the frontend-minor-patch group in /frontend with 12 updates (#152)

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
