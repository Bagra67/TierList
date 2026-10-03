# TODO

English | [Français](TODO.fr.md)

Manual steps left to do: configuration, checks in a browser, merges and decisions that cannot be done from the code. Tick an item once it is done, and remove a section once it is empty.

## 1. Before the first deployment

- [ ] Choose a hosting target, then write the production Docker images and the deployment (open decision, see [architecture](docs/architecture.md#open-decisions)).
- [ ] Production settings (`backend/.env` or the host's variables):
  - a `JWT_SECRET_KEY` different from development;
  - `AUTH_COOKIE_SECURE=true` (the default) and HTTPS;
  - a strong `POSTGRES_PASSWORD`.
- [ ] Google in production: add the HTTPS redirect URI to the OAuth client, set `GOOGLE_REDIRECT_URI` to it, and publish the consent screen (in "Testing" mode, only test users can sign in).

## 2. Decisions to take

- [ ] Features not available yet ([authentication guide](docs/authentication.md#not-available-yet)): email verification and "forgot password" (need an email service to choose), limiting repeated sign-in attempts, other identity providers.
- [ ] Design system (accent color, typography, logo), **once the tier list editor and one or two features around it exist**, to design on real screens. Until then: theme tokens only (`bg-primary`, `text-muted-foreground`…), no hard-coded color, so the design system is mostly a change of the variables in `frontend/src/index.css` ([frontend README](frontend/README.md#10-ui-components)). The tier colors (S, A, B…) are decided with the editor, as light and dark tokens.
- [ ] Moving to version 1.0.0 (`scripts/prepare-release.sh --version 1.0.0`), when the API is considered stable.
