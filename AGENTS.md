# AGENTS.md

## 1. Purpose

This repository is a full-stack application composed primarily of:

-   **Frontend:** React + TypeScript
-   **Backend:** Python + FastAPI
-   **Database:** PostgreSQL or another explicitly configured relational
    database

This file defines the engineering rules that AI coding agents must
follow when analyzing, modifying, testing, or reviewing the codebase.

The existing codebase, its architecture, its conventions, and its
documentation are the primary sources of truth.

When instructions conflict:

1.  Follow explicit task requirements.
2.  Follow this `AGENTS.md`.
3.  Follow documented project architecture and conventions.
4.  Prefer the smallest safe change.

Never invent business rules, APIs, dependencies, configuration, or
expected behavior.

------------------------------------------------------------------------

# 2. Agent Operating Rules

## MUST

-   Read the relevant code before modifying it.
-   Read the relevant `AGENTS.md`, README, architecture documentation,
    and task documentation before starting substantial work.
-   Search the repository for existing implementations before creating
    new ones.
-   Understand how the frontend, backend, API, and persistence layers
    interact before changing cross-layer behavior.
-   Reuse existing patterns and components when they are appropriate.
-   Keep changes focused on the requested task.
-   Preserve existing behavior unless the task explicitly requires
    changing it.
-   Inspect the final diff before considering the task complete.
-   Run the relevant tests, linters, type checkers, and build commands
    when available.
-   Report exactly what was changed and what validation was performed.
-   Explicitly report validation failures.
-   Ask for clarification when requirements are genuinely ambiguous and
    the ambiguity could affect architecture, behavior, data, security,
    or compatibility.

## SHOULD

-   Start complex tasks with a short implementation plan.
-   Identify affected files and dependencies before making changes.
-   Prefer incremental changes over large rewrites.
-   Validate assumptions against the codebase instead of relying on
    generic framework knowledge.
-   Explain important architectural decisions when they are not obvious.

## MUST NOT

-   Modify unrelated files without a concrete reason.
-   Rewrite existing architecture simply because another architecture
    would be preferred.
-   Upgrade frameworks or dependencies without explicit justification.
-   Introduce a new library when existing project capabilities are
    sufficient.
-   Claim that tests, builds, linting, or type checking passed unless
    they were actually executed.
-   Pretend an external service, API, database, command, or library
    exists when it has not been verified.
-   Remove working code merely to make an implementation "cleaner".
-   Hide errors or validation failures from the user.

------------------------------------------------------------------------

# 3. Task Workflow

For non-trivial tasks, follow this workflow.

## Step 1 --- Understand

Before coding:

-   Read the relevant files.
-   Search for similar functionality.
-   Identify the affected layers.
-   Identify existing tests.
-   Identify relevant API contracts.
-   Identify data models and database interactions.
-   Check project conventions.

## Step 2 --- Plan

Define:

-   What needs to change.
-   Which files are likely to change.
-   Which files should not change.
-   How frontend and backend changes interact.
-   What tests are required.
-   Potential compatibility or migration concerns.

For significant tasks, present the plan before implementation when
practical.

## Step 3 --- Implement

Implement the smallest complete solution.

Do not stop at partial scaffolding unless the task explicitly asks for
scaffolding.

## Step 4 --- Validate

Run the appropriate:

-   Backend tests.
-   Frontend tests.
-   Python type checking.
-   TypeScript type checking.
-   Linters.
-   Formatters.
-   Frontend build.
-   Backend startup/import checks.
-   Relevant integration or API tests.

## Step 5 --- Review

Before finishing:

-   Inspect the git diff.
-   Check for accidental modifications.
-   Check for dead code.
-   Check error handling.
-   Check security implications.
-   Check API compatibility.
-   Check frontend loading/error/empty states.
-   Check tests.

## Step 6 --- Report

The final response should contain:

1.  What changed.
2.  Important implementation details.
3.  Tests and checks executed.
4.  Results of those checks.
5.  Any remaining limitation or manual step.

------------------------------------------------------------------------

# 4. Core Clean Code Principles

## MUST

### KISS

Prefer the simplest solution that correctly solves the problem.

### YAGNI

Do not implement functionality that is not currently required.

### DRY

Avoid unnecessary duplication.

However, do not force unrelated concepts into a shared abstraction
merely to remove a few duplicated lines.

### SOLID

Apply SOLID principles pragmatically.

Do not introduce abstractions merely to satisfy a principle.

### Single Responsibility

A module, component, function, class, service, or route should have a
coherent responsibility.

### Separation of Concerns

Keep:

-   UI concerns in the frontend presentation layer.
-   API transport concerns in API/client layers.
-   Business rules in appropriate backend services/domain logic.
-   Persistence concerns in repositories/data-access layers.
-   Configuration in configuration modules/environment configuration.

### High Cohesion / Low Coupling

Prefer cohesive modules with explicit dependencies.

### Composition Over Inheritance

Prefer composition unless inheritance provides a clear and justified
benefit.

### Law of Demeter

Avoid unnecessary chains through unrelated objects.

------------------------------------------------------------------------

# 5. Scope and Minimal Change Principle

## MUST

-   Modify only what is necessary for the task.
-   Preserve unrelated functionality.
-   Reuse existing abstractions when appropriate.
-   Keep refactoring separate from feature implementation when possible.

## MUST NOT

-   Perform opportunistic refactoring.
-   Rename unrelated files or variables.
-   Reformat entire files without a reason.
-   Replace working architecture with a preferred architecture.
-   Upgrade dependencies as part of an unrelated feature.

If a broader refactor is genuinely required, explain why before doing
it.

------------------------------------------------------------------------

# 6. Naming

## MUST

Use names that describe intent and domain meaning.

Names should be:

-   Explicit.
-   Consistent.
-   Easy to search.
-   Consistent with the existing project vocabulary.

Avoid:

-   `data`
-   `result`
-   `temp`
-   `foo`
-   `bar`
-   `thing`

when a meaningful domain name is available.

Use framework conventions:

### Python

Prefer:

``` python
snake_case
```

for variables, functions, and modules.

Use:

``` python
PascalCase
```

for classes.

### TypeScript / React

Prefer:

``` typescript
camelCase
```

for variables and functions.

Use:

``` typescript
PascalCase
```

for React components and classes/types where appropriate.

------------------------------------------------------------------------

# 7. Functions and Methods

## MUST

-   Keep functions focused.
-   Keep control flow understandable.
-   Prefer early returns when they improve readability.
-   Keep parameter lists reasonably small.
-   Extract logic when a function becomes difficult to understand or
    test.

## MUST NOT

-   Create abstractions solely to reduce line count.
-   Create generic helper functions without a clear reusable
    responsibility.
-   Hide important business logic inside obscure utility functions.

------------------------------------------------------------------------

# 8. Error Handling

## MUST

-   Handle expected errors explicitly.
-   Preserve useful error context.
-   Return appropriate API error responses.
-   Log unexpected server-side failures with enough context to diagnose
    them.
-   Avoid exposing internal implementation details to API consumers.

## MUST NOT

-   Use broad exception handling unless justified.
-   Silently ignore exceptions.
-   Return raw stack traces to clients.
-   Use exceptions as normal control flow when ordinary conditions can
    be represented directly.

Python example:

``` python
try:
    result = await service.execute()
except ExpectedError as exc:
    raise HTTPException(
        status_code=400,
        detail=str(exc),
    ) from exc
```

Do not catch `Exception` merely to suppress errors.

------------------------------------------------------------------------

# 9. Python Backend --- FastAPI

## 9.1 General Rules

## MUST

-   Use Python type hints.
-   Prefer explicit types over `Any`.
-   Use Pydantic models for API input/output contracts.
-   Keep FastAPI route handlers thin.
-   Put business logic in services/domain logic.
-   Keep database access in repositories/data-access modules when that
    pattern exists.
-   Validate external input at the API boundary.
-   Use dependency injection for shared infrastructure where
    appropriate.
-   Keep configuration separate from business logic.
-   Write tests for business-critical behavior.

## MUST NOT

-   Put complex business logic directly in route handlers.
-   Put raw SQL or extensive ORM logic directly in API routes.
-   Return database entities directly when a dedicated API schema is
    appropriate.
-   Hard-code secrets, credentials, tokens, or environment-specific
    configuration.
-   Use `Any` as a shortcut to silence typing problems.
-   Add global mutable state without explicit justification.

------------------------------------------------------------------------

# 10. FastAPI Architecture

Prefer a structure similar to:

``` text
backend/
├── app/
│   ├── api/
│   │   ├── routes/
│   │   └── dependencies.py
│   ├── core/
│   │   ├── config.py
│   │   └── security.py
│   ├── models/
│   ├── schemas/
│   ├── services/
│   ├── repositories/
│   └── main.py
└── tests/
```

This is a guideline, not a requirement to reorganize an existing
project.

## Responsibilities

### `api/`

HTTP concerns:

-   Routes.
-   HTTP status codes.
-   Request dependencies.
-   Authentication/authorization integration.
-   API-level validation.

### `schemas/`

API contracts:

-   Request models.
-   Response models.
-   Serialization/deserialization contracts.

### `services/`

Business logic:

-   Business rules.
-   Orchestration.
-   Domain operations.

### `repositories/`

Persistence:

-   Database queries.
-   Persistence operations.
-   Data-access concerns.

### `models/`

Persistence/domain models when using an ORM.

------------------------------------------------------------------------

# 11. FastAPI Routes

A route should generally be small:

``` python
@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    user = await service.get_user(user_id)

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    return user
```

The route should not contain a large business workflow.

Prefer:

``` text
HTTP request
    ↓
FastAPI route
    ↓
Service
    ↓
Repository
    ↓
Database
```

------------------------------------------------------------------------

# 12. Pydantic

## MUST

Use explicit request and response schemas.

Example:

``` python
class CreateUserRequest(BaseModel):
    email: EmailStr
    name: str


class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    name: str
```

Do not expose internal database structures unnecessarily.

Keep API contracts explicit and stable.

------------------------------------------------------------------------

# 13. Database and ORM

## MUST

-   Use parameterized queries or ORM mechanisms.
-   Keep transactions explicit.
-   Understand transaction boundaries.
-   Add migrations for schema changes.
-   Consider indexes for frequently queried fields.
-   Test important persistence behavior.
-   Preserve data integrity constraints.

## MUST NOT

-   Build SQL by string concatenation with user-controlled input.
-   Modify production schema manually when migrations are the project
    standard.
-   Delete or rename database columns without considering compatibility
    and migration requirements.
-   Add indexes blindly without understanding query patterns.

If Alembic is used, database schema changes should normally be
represented through Alembic migrations.

------------------------------------------------------------------------

# 14. Transactions

## MUST

-   Keep transaction boundaries clear.
-   Ensure multi-step operations that must be atomic execute inside an
    appropriate transaction.
-   Roll back failed transactions correctly.

Be especially careful when an operation modifies several related
records.

------------------------------------------------------------------------

# 15. Async Python

## MUST

Use `async`/`await` consistently when working with asynchronous
libraries.

Do not introduce blocking operations into asynchronous request handlers
without understanding their impact.

Avoid unnecessary async code when the underlying operation is
synchronous.

Do not use async merely because FastAPI supports it.

------------------------------------------------------------------------

# 16. Dependency Injection

Use dependency injection for things such as:

-   Database sessions.
-   Services.
-   Authentication context.
-   External clients.
-   Configuration.

Avoid global service instances unless the project's architecture
explicitly uses them.

------------------------------------------------------------------------

# 17. React + TypeScript

## MUST

-   Use TypeScript.
-   Prefer explicit interfaces/types for important data structures.
-   Keep components focused.
-   Reuse existing components when appropriate.
-   Separate API communication from UI components.
-   Handle loading, error, and empty states where relevant.
-   Use stable React keys.
-   Keep business rules out of presentation components when they belong
    to the backend.
-   Preserve accessibility.
-   Keep state as local as possible.
-   Lift state only when multiple components genuinely need it.

## MUST NOT

-   Use `any` to bypass TypeScript errors.
-   Put large API calls directly into many unrelated components.
-   Duplicate API request logic.
-   Duplicate backend business rules in the frontend.
-   Store secrets in frontend code.
-   Use `useEffect` as a generic replacement for proper
    state/data-fetching architecture.

------------------------------------------------------------------------

# 18. React Component Design

Prefer components with one clear responsibility.

Example:

``` text
UserPage
├── UserList
├── UserFilters
├── UserForm
└── UserPagination
```

Avoid enormous components containing:

-   API calls.
-   Complex business logic.
-   Form logic.
-   Rendering logic.
-   Navigation.
-   Error handling.

all at once.

Extract only when the separation improves maintainability.

Do not split every small JSX fragment into a component without a reason.

------------------------------------------------------------------------

# 19. Frontend API Layer

Prefer a clear boundary:

``` text
React component
      ↓
Hook / query layer
      ↓
API client/service
      ↓
FastAPI
```

For example:

``` typescript
export async function getUser(userId: string): Promise<User> {
    const response = await apiClient.get<User>(`/users/${userId}`);
    return response.data;
}
```

Do not duplicate HTTP configuration throughout components.

Use the project's existing data-fetching solution when one exists.

If TanStack Query, Axios, Fetch wrappers, or another API abstraction
already exists, follow its established conventions instead of
introducing another one.

------------------------------------------------------------------------

# 20. Frontend State Management

## MUST

Use the smallest state scope that solves the problem.

Prefer:

1.  Local component state when possible.
2.  Shared context for genuinely shared state.
3.  Existing application state management for cross-cutting state.
4.  Server-state/data-fetching libraries for server state when already
    adopted by the project.

Do not introduce global state for convenience.

Distinguish between:

-   UI state.
-   Form state.
-   Server state.
-   Authentication state.
-   Persistent application state.

------------------------------------------------------------------------

# 21. Forms and Validation

## MUST

-   Validate user input.
-   Display useful validation messages.
-   Prevent duplicate submissions when appropriate.
-   Handle loading and failure states.
-   Keep API validation authoritative.

Frontend validation improves UX.

It must never be considered a security boundary.

The backend must validate incoming data independently.

------------------------------------------------------------------------

# 22. React Accessibility

## MUST

-   Use semantic HTML where appropriate.
-   Provide accessible labels for form controls.
-   Ensure keyboard navigation where applicable.
-   Do not rely solely on color to convey meaning.
-   Use accessible names for interactive controls.
-   Preserve focus behavior when implementing dialogs/navigation where
    appropriate.

Do not sacrifice accessibility for visual convenience.

------------------------------------------------------------------------

# 23. API Contract Between React and FastAPI

The backend API is the authoritative contract.

## MUST

-   Keep request and response formats explicit.
-   Keep HTTP status codes meaningful.
-   Handle API errors consistently.
-   Update frontend API types when backend contracts change.
-   Never write frontend API types by hand: they are generated from the
    backend OpenAPI schema. After a contract change, run
    `uv run python scripts/export_openapi.py` (backend) then
    `pnpm gen:api` (frontend), and commit `backend/openapi.json` and
    `frontend/src/api/schema.d.ts` together.
-   Add or update tests when contracts change.

For breaking changes:

1.  Identify affected consumers.
2.  Consider backward compatibility.
3.  Update frontend and backend together when appropriate.
4.  Document migration requirements.

Do not silently change an API contract.

------------------------------------------------------------------------

# 24. Authentication and Authorization

## MUST

-   Treat authentication and authorization as backend responsibilities.
-   Validate authorization server-side for every protected operation.
-   Never trust frontend visibility rules as authorization.
-   Keep secrets and credentials out of source code.
-   Follow the project's established token/session strategy.

Frontend code may hide unauthorized actions for UX.

It must never be the security boundary.

------------------------------------------------------------------------

# 25. Security

## MUST

-   Validate all external input.
-   Protect secrets.
-   Use secure authentication mechanisms.
-   Apply authorization server-side.
-   Avoid SQL injection.
-   Avoid command injection.
-   Avoid unsafe deserialization.
-   Avoid exposing sensitive information in logs.
-   Use HTTPS in production environments when applicable.
-   Follow dependency security practices.

## MUST NOT

-   Commit passwords, API keys, private keys, or tokens.
-   Log passwords or authentication tokens.
-   Disable security validation merely to make development easier
    without an explicit development-only reason.
-   Trust client-provided authorization information.

------------------------------------------------------------------------

# 26. Configuration

Use environment-based configuration for environment-specific values.

Prefer:

``` text
.env
.env.example
```

or the project's established configuration mechanism.

## MUST NOT

Commit:

-   Secrets.
-   Production credentials.
-   Private keys.
-   Personal tokens.

`.env.example` should contain placeholders and documentation, not real
credentials.

------------------------------------------------------------------------

# 27. Dependencies

## MUST

Before adding a dependency:

1.  Check whether the functionality already exists.
2.  Check whether the project already has an equivalent dependency.
3.  Evaluate maintenance and security implications.
4.  Keep the dependency narrowly justified.

Document the reason for important new dependencies.

## MUST NOT

Add dependencies merely because they are popular.

------------------------------------------------------------------------

# 28. Tests

Tests are part of the implementation, not an optional final step.

## Backend

Prefer:

-   `pytest`
-   FastAPI test clients/tools
-   Unit tests for business logic.
-   Integration tests for persistence/API behavior where appropriate.

## Frontend

Use the project's established testing stack.

Prefer testing behavior over implementation details.

## MUST

For new functionality:

-   Add appropriate tests.
-   Update existing tests affected by behavior changes.
-   Test important error cases.
-   Test important boundary conditions.

## Testing guide

`docs/testing.md` (English) and `docs/testing.fr.md` (French) describe
every test: what it does, its purpose and the expected result.

Whenever a test, a test fixture or a test tool is added, changed,
renamed or removed, BOTH files MUST be updated in the same PR, so that
the guide always matches the actual tests.

## MUST NOT

-   Delete failing tests merely to make CI pass.
-   Modify assertions without understanding the behavior change.
-   Mock everything to the point that tests no longer validate useful
    behavior.

------------------------------------------------------------------------

# 29. Test Isolation

Tests should be:

-   Deterministic.
-   Independent.
-   Repeatable.
-   Explicit about their setup.

Avoid dependence on:

-   Test execution order.
-   Developer-specific local state.
-   Production databases.
-   External services unless explicitly required by an integration test.

------------------------------------------------------------------------

# 30. Formatting and Linting

Use the project's configured tools.

For Python, common tools may include:

-   Ruff.
-   Black.
-   Pyright.
-   mypy.

For TypeScript/React, common tools may include:

-   ESLint.
-   Prettier.
-   TypeScript compiler.

Do not add these tools if the project has intentionally chosen
alternatives.

Do not reformat unrelated code.

------------------------------------------------------------------------

# 31. Comments and Documentation

## MUST

Write comments when they explain:

-   Why something is necessary.
-   A non-obvious constraint.
-   A business rule.
-   A workaround.
-   A compatibility requirement.

## MUST NOT

Use comments to explain obvious syntax.

Bad:

``` python
# Increment i
i += 1
```

Good:

``` python
# The external API rejects requests made within 500 ms of the previous request.
await asyncio.sleep(0.5)
```

Do not leave misleading comments.

Update comments when behavior changes.

## Documentation language

All human-facing documentation (READMEs, files under `docs/`, guides)
MUST exist in **English and French**:

-   `name.md` is the English version and the reference.
-   `name.fr.md` is the French version, in the same directory.
-   Each file starts with a language switcher:
    `English | [Français](name.fr.md)` in the English file and
    `[English](name.md) | Français` in the French one.
-   Relative links point to files in the same language
    (e.g. `README.fr.md` links to `backend/README.fr.md`).
-   Both versions MUST be updated in the same PR and stay equivalent in
    content.

Exceptions:

-   `AGENTS.md` stays English-only (instructions for agents).
-   `LICENSE` is already bilingual in a single file.
-   Code comments are not concerned.

------------------------------------------------------------------------

# 32. Logging and Observability

## MUST

Log information useful for diagnosing production behavior.

Useful information may include:

-   Operation name.
-   Relevant identifiers.
-   Error context.
-   External service failures.
-   Important state transitions.

## MUST NOT

Log:

-   Passwords.
-   Access tokens.
-   API keys.
-   Sensitive personal data unless explicitly required and protected.

Avoid excessive debug logging in production.

------------------------------------------------------------------------

# 33. Performance

Do not optimize prematurely.

## MUST

-   Identify actual bottlenecks before complex optimization.
-   Avoid obvious N+1 database queries.
-   Avoid unnecessary API requests.
-   Avoid unnecessary React renders when the cost is meaningful.
-   Use pagination for potentially large collections.
-   Consider database indexes for relevant access patterns.

## MUST NOT

Introduce complex caching or memoization without a demonstrated need.

Correctness and maintainability come before speculative optimization.

------------------------------------------------------------------------

# 34. API Design

## MUST

Use consistent:

-   URL conventions.
-   HTTP methods.
-   Status codes.
-   Request schemas.
-   Response schemas.
-   Error formats.

Prefer resource-oriented endpoints when consistent with the existing
API.

Avoid inconsistent one-off API patterns.

------------------------------------------------------------------------

# 35. DTOs, Domain Models, and Persistence Models

Do not automatically expose database models as API contracts.

Use explicit schemas when the application benefits from separation
between:

``` text
Database model
      ↓
Domain/service representation
      ↓
API response schema
```

The amount of separation should match the complexity of the application.

Do not create three layers of models for trivial data without a reason.

------------------------------------------------------------------------

# 36. Database Migrations

For schema changes:

## MUST

-   Create the appropriate migration.
-   Review the generated migration.
-   Consider existing production data.
-   Consider rollback implications.
-   Test migration behavior when practical.

## MUST NOT

-   Assume a migration is safe merely because it runs successfully.
-   Destructively modify production data without explicit requirements
    and safeguards.

------------------------------------------------------------------------

# 37. External Services

When integrating with an external API:

## MUST

-   Read the existing client/integration code first.
-   Reuse existing HTTP clients and configuration patterns when
    possible.
-   Handle timeouts.
-   Handle expected HTTP failures.
-   Validate external responses.
-   Avoid logging credentials.

Do not invent API endpoints or payload formats.

Verify them from project documentation, source code, or authoritative
external documentation.

------------------------------------------------------------------------

# 38. Resource Management

## Python

Ensure resources such as:

-   Database sessions.
-   Files.
-   HTTP clients.
-   Connections.

are properly managed and closed.

Prefer context managers or framework-supported lifecycle management.

## Frontend

Clean up resources such as:

-   Event listeners.
-   Timers.
-   Subscriptions.
-   Abortable requests.

when required by their lifecycle.

------------------------------------------------------------------------

# 39. Git

The agent must treat Git history and the current working tree as
important project context.

## MUST

Before substantial changes:

``` bash
git status
```

Understand whether there are pre-existing modifications.

Do not overwrite unrelated user changes.

After changes:

``` bash
git diff
git status
```

Review the final diff.

## MUST NOT

-   Reset or discard user changes without explicit permission.
-   Force-push without explicit permission.
-   Rewrite Git history unnecessarily.
-   Commit generated secrets or environment files.

When asked to create a commit, use a clear, focused commit message.

Commit messages and branch names follow **Conventional Commits**:

-   Commits: `type(scope): summary` (e.g. `feat(backend): ...`,
    `docs: ...`). Checked locally by commitlint
    (`frontend/.husky/commit-msg`): lowercase summary, body lines of
    100 characters at most.
-   Branches: `type/short-topic` (e.g. `chore/starter-setup`).

Everything git-related MUST be written in **English**: commit messages
(subject and body), branch names, pull request titles and descriptions,
including squash and merge commit messages. Existing French history is
left as is.

------------------------------------------------------------------------

# 40. Pull Requests

When the project uses pull requests:

A PR should normally contain:

-   A focused change.
-   A clear description.
-   Tests.
-   Relevant documentation updates.
-   No unrelated refactoring.

The PR description should explain:

-   What changed.
-   Why.
-   How it was tested.
-   Any known limitations.

Do not create a PR claiming successful validation if validation was not
actually performed.

## Merging

Pull requests MUST be merged with a **squash merge**: each PR becomes a
single commit on the target branch.

**Exception — release PRs (`develop` → `main`)** MUST use a regular
**merge commit** (no squash, no rebase). Squashing them would give `main`
commits that `develop` does not have, making the two branches diverge.
The merge commit message follows the same format, e.g.
`chore(release): merge develop into main (#2)`.

The squash commit message MUST:

-   Follow Conventional Commits.
-   Summarize the PR very briefly: a subject line plus, at most, a few
    short bullet points.
-   End the subject line with the PR number, e.g. `(#12)`.

Example:

``` text
chore: bootstrap the starter (Hello World, PostgreSQL, tooling) (#1)

- frontend reduced to the backend Hello World, dev.* scripts
- backend wired to PostgreSQL (Docker, SQLAlchemy, Alembic, /health/db)
```

With the GitHub CLI:

``` bash
# Feature PR -> develop (also deletes the work branch, locally and on origin)
gh pr merge <N> --squash --delete-branch --subject "<type>(<scope>): <summary> (#<N>)" --body "<short bullets>"

# Release PR develop -> main (never delete develop)
gh pr merge <N> --merge --subject "chore(release): <summary> (#<N>)" --body "<short bullets>"
```

These merge methods are also enforced by the GitHub rulesets: `develop`
only allows squash merges, `main` only allows merge commits.

## Releases and versioning

Every merge of `develop` into `main` is a release `vX.Y.Z` (Semantic
Versioning). Full process: `docs/releasing.md`.

-   The version is computed from the squash commits since the last tag:
    `!` or a `BREAKING CHANGE:` footer bumps X (Y while in 0.x),
    `feat` bumps Y, `fix`/`perf` bump Z; other types do not bump.
-   A breaking change MUST carry `!` in the squash subject (e.g.
    `feat(api)!: ...`) and a `BREAKING CHANGE:` footer explaining the
    migration.
-   Prepare a release with `scripts/prepare-release.sh` on a
    `chore/release-vX.Y.Z` branch from `develop`, squash-merge
    `chore(release): prepare vX.Y.Z`, then merge the release PR
    `chore(release): vX.Y.Z` into `main` with a merge commit.
-   Never edit version fields by hand outside that script, never create
    `vX.Y.Z` tags by hand: the `Release` workflow tags `main`.
-   Moving to 1.0.0 is a user decision (`--version 1.0.0`).

## Branch cleanup

Once a work branch has been merged into `develop`, it MUST be deleted,
both locally and on `origin`. `--delete-branch` above does both; if the
PR was merged another way, delete it manually:

``` bash
git switch develop
git pull
git branch -D <branch>            # -D: a squash merge is not seen as merged by git
git push origin --delete <branch>
git fetch --prune
```

`main` and `develop` are long-lived and MUST never be deleted.

------------------------------------------------------------------------

# 41. Backlog / TODO Tasks

When working from a TODO list, issue, or backlog item:

## MUST

-   Treat each item as an independent task unless dependencies require
    otherwise.
-   Read the issue description and acceptance criteria.
-   Inspect the existing implementation before coding.
-   Identify dependencies on other tasks.
-   Keep each change reviewable.

## SHOULD

Use this workflow:

``` text
TODO / Issue
    ↓
Understand
    ↓
Plan
    ↓
Implement
    ↓
Test
    ↓
Review diff
    ↓
Commit
    ↓
Pull Request
```

Do not automatically implement an entire backlog without clear task
boundaries.

------------------------------------------------------------------------

# 42. AI Agent Behavior

The AI agent is a coding assistant, not the owner of product decisions.

## MUST

-   Follow explicit user requirements.
-   Preserve user intent.
-   Ask when an important requirement is ambiguous.
-   Verify assumptions.
-   Explain significant trade-offs.
-   Keep the user informed about important changes.
-   Stop and report when a task cannot safely be completed.

## MUST NOT

-   Invent requirements.
-   Invent business rules.
-   Invent API behavior.
-   Invent database structure.
-   Invent credentials.
-   Assume a dependency is installed.
-   Assume tests pass.
-   Hide uncertainty.
-   Make unrelated improvements without permission.

------------------------------------------------------------------------

# 43. When Requirements Are Ambiguous

If ambiguity affects:

-   Data integrity.
-   Security.
-   API contracts.
-   User-visible behavior.
-   Business rules.
-   Architecture.
-   Compatibility.

ask the user before proceeding.

If ambiguity is minor and a safe convention exists, use the existing
project convention and document the assumption.

Never silently make a major product decision.

------------------------------------------------------------------------

# 44. Refactoring

Refactoring is allowed when it directly supports the requested task.

## MUST

-   Preserve behavior unless behavior change is explicitly requested.
-   Keep refactors focused.
-   Ensure tests cover important behavior.
-   Review the complete diff.

## MUST NOT

Turn every feature request into a large architectural rewrite.

If a separate refactor would significantly improve the project but is
not required, mention it separately rather than silently doing it.

------------------------------------------------------------------------

# 45. Backward Compatibility

Before changing:

-   API contracts.
-   Database schemas.
-   Authentication behavior.
-   Shared components.
-   Public interfaces.
-   Configuration.

consider existing consumers.

Prefer backward-compatible changes when practical.

For breaking changes, explicitly identify the impact.

------------------------------------------------------------------------

# 46. Dead Code

## MUST

Remove code that is made obsolete by the requested change when its
removal is clearly safe.

## MUST NOT

Delete apparently unused code merely because it looks unused without
checking:

-   Imports.
-   Dynamic usage.
-   API exposure.
-   Configuration.
-   Tests.
-   External consumers.

------------------------------------------------------------------------

# 47. No Speculative Architecture

Do not build infrastructure "for later".

Avoid creating:

-   Generic plugin systems.
-   Unused abstractions.
-   Unused interfaces.
-   Premature microservices.
-   Complex event systems.
-   Generic factories.
-   Generic repositories.

unless there is a concrete current requirement.

------------------------------------------------------------------------

# 48. Definition of Done

A task is considered complete only when:

-   [ ] Requirements are understood.
-   [ ] Relevant existing code was inspected.
-   [ ] The implementation follows project architecture.
-   [ ] Changes are focused.
-   [ ] Type safety is preserved.
-   [ ] Error handling is appropriate.
-   [ ] Security considerations were addressed.
-   [ ] Relevant tests were added or updated.
-   [ ] Relevant tests were executed.
-   [ ] Linting/formatting/type checks were executed when available.
-   [ ] Frontend build was executed when relevant.
-   [ ] Backend validation was executed when relevant.
-   [ ] Final Git diff was reviewed.
-   [ ] No unrelated changes were introduced.
-   [ ] Final response accurately reports what was actually validated.

------------------------------------------------------------------------

# 49. Final Agent Response Format

After completing a task, report:

## Summary

Briefly describe the implementation.

## Changes

List the important files and what changed.

## Validation

List commands/checks actually executed and their results.

Example:

``` text
pytest                         PASS
npm run lint                   PASS
npm run typecheck              PASS
npm run build                  PASS
```

If something was not executed:

``` text
npm run e2e                    NOT RUN
Reason: requires the external staging environment.
```

## Notes

Mention:

-   Important assumptions.
-   Known limitations.
-   Required manual actions.
-   Follow-up work only when relevant.

Never claim validation that was not performed.
