# Marketplace

How the marketplace lists, searches, sorts and pages the public templates. **Decided in spike #274**, and **built**: the tags and the search text in #272 ([templates guide](templates.md#29-tags)), the listing rule in #275 ([templates guide](templates.md#210-public-template-page)), the likes in #276, the favorites in #278, the marketplace in #277, the pages of _My templates_ in #105 ([templates guide](templates.md#26-endpoints)) and the TierList picks in #492. §3 lists where each piece lives.

## 1. Functional overview

### What is needed

- The marketplace shows the **listed** templates, page after page, with a _See more_ button (US-3.1, [screens](../product/milestone-2/screens.md)). A template is listed if and only if it is **public**, **not hidden** by the moderation, **not deleted**, and its owner is **not banned** (invariant 2 of the [domain model](../product/milestone-2/domain-model.md#invariants)). A temporary ban ends on its own, so the rule depends on the current time.
- **Keywords** search the name and the tags, ignoring case and accents (US-3.2). A keyword matches the **start of a word**: `poke` finds _Pokémon_, `kemon` does not. Several keywords must **all** match (AND); `|` separates alternatives (OR): `mario film | zelda` finds the templates matching both `mario` and `film`, or `zelda`.
- A **tag** filter keeps the templates with that tag; it combines with the keywords.
- Two sorts: **popularity** (number of likes, the default) and **newest** (date the template was first made public).
- **TierList picks**: the official templates featured by the super admins come first, above the list and on the home page (§2.12).
- **Tags**: 5 at most per template (20 for an official template), 30 characters at most each, duplicates ignoring case and accents merged (US-2.2, invariant 4).
- **Volumes**: a few hundred to a few thousand public templates expected in the first year. 24 templates per page.
- No new service: everything runs in the PostgreSQL the app already uses (PostgreSQL 17 in production, 18 locally and on CI).

### Not available yet

- No **relevance** sort: a search keeps the chosen sort (popularity or newest).
- No **fuzzy** search: a typo (`pokmeon`) finds nothing (§2.13).

## 2. Technical design

### 2.1 Options considered

| Topic            | Options                                                                                   | Choice and reason                                                                                                                                                                                                                                                                                                                                                                                                                                |
| ---------------- | ----------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Case and accents | `unaccent` extension, **normalization in Python**, ICU collation                          | **Python**: one function used for the tags (duplicates), the stored search text and the query, so the three always agree. `unaccent` is not `IMMUTABLE` (an index needs a wrapper function), and creating an extension needs the PostgreSQL contrib modules and the right to create it, both unverified on the production pod. A nondeterministic ICU collation supports `LIKE` only from PostgreSQL 18 (production runs 17), and not full text. |
| Start-of-word    | `LIKE 'kw%' OR LIKE '% kw%'`, `pg_trgm`, **PostgreSQL full text with prefix queries**     | **Full text** (`to_tsvector` / `to_tsquery`, `simple` configuration, `word:*` prefixes): built into PostgreSQL, matches the start of each word, has AND (`&`) and OR (`\|`) operators, and a GIN index serves it. `LIKE` with a leading `%` cannot use a B-tree index; `pg_trgm` is an extension and matches inside words too.                                                                                                                   |
| Pagination       | Offset (`limit`/`offset` + `has_more`, used by the moderation pages), **cursor (keyset)** | **Cursor**: an offset skips or repeats templates when one is made public between two pages, and gets slower page after page; the cursor reads the next rows from an index. #105 had already chosen it for _My templates_. The existing offset lists stay as they are.                                                                                                                                                                            |
| Popularity       | **Count the likes in the query**, a `like_count` counter on `templates`                   | **Count in the query**: one source of truth. A counter drifts when likes disappear without going through the service, e.g. when an account is deleted (cascade). Measured cost acceptable at the expected volumes (§2.8), with a threshold to switch.                                                                                                                                                                                            |

### 2.2 Listing rule

One reusable SQLAlchemy condition, `listed_templates_condition(now)`, in the templates repository:

```sql
templates.visibility = 'public'
AND templates.moderation = 'none'
AND templates.deleted_at IS NULL
AND NOT EXISTS (SELECT 1 FROM account_bans
                WHERE account_bans.user_id = templates.owner_id AND <active at now>)
```

`<active at now>` is the existing `is_active(now)` of `app/repositories/account_bans.py` (`lifted_at IS NULL AND (ends_at IS NULL OR ends_at > now)`), so a ban that ends brings the templates back without any job. The public template page (#275), the likes (#276) and the favorites (#278) reuse the same condition.

### 2.3 Text normalization

`normalize_search_text(text) -> str`, a pure function:

1. replace the ligatures `œ` → `oe`, `æ` → `ae` (Unicode does not decompose them, and French writes _oeuvre_ as often as _œuvre_);
2. decompose (`unicodedata.normalize("NFKD")`) and drop the combining marks (accents, cedilla);
3. `casefold()` (`ß` → `ss`);
4. turn every character other than `a-z` and `0-9` into a space, then collapse the spaces.

Examples: `Pokémon` → `pokemon`, `Œuvres d'Art` → `oeuvres d art`, `Spider-Man 2` → `spider man 2`, `café_crème` → `cafe creme`. Non-Latin scripts (`日本`) give an empty string, hence cannot be searched (§2.13).

### 2.4 Tags

A table `template_tags`, owned by the template (composition: no shared tag catalogue, the tags are free words):

| Column             | Content                                                                                 |
| ------------------ | --------------------------------------------------------------------------------------- |
| `template_id`      | Foreign key to `templates.id`, `ON DELETE CASCADE`.                                     |
| `label`            | The tag as typed by the owner (trimmed), shown everywhere; 30 characters at most.       |
| `normalized_label` | `normalize_search_text(label)`: duplicates and the tag filter compare this column only. |
| `position`         | The owner's order, from 0.                                                              |

- Primary key `(template_id, normalized_label)`: a duplicate is refused by the database too. Adding a tag whose normalized form already exists keeps the first label (merge, US-2.2).
- A tag whose normalized form is empty (only punctuation or a non-Latin script) is refused.
- At most 5 tags, 20 for an official template: `Template.max_tags`, checked by the service (`409` `tag_limit_reached`), the request schema refusing more than 20 (`422` `validation_error`); the service changes the tags on the template row locked with `SELECT … FOR UPDATE`, like every template change.
- Index on `normalized_label` for the tag filter (`EXISTS (… WHERE normalized_label = :tag)`).
- A fork copies the tags (US-3.7).

### 2.5 Search

- A column `templates.search_text`: `normalize_search_text` of the name followed by the normalized tags. The service rewrites it whenever the name or the tags change, in the same transaction. A stored column, because the tags live in another table (a generated column cannot read it).
- Condition: `to_tsvector('simple', search_text) @@ to_tsquery('simple', :query)`. The `simple` configuration only splits words and lowercases them: no stemming, no stop words, so `de` or `la` stay searchable.
- `:query` is **built in Python**, never typed by the user as tsquery syntax: the input is split on `|`, each part is normalized, each word becomes `word:*`, the words of a part are joined with `&`, the parts with `|`. Normalized words only contain `a-z0-9`, so no tsquery operator can come from the input; the query is still sent as a bound parameter.

| Input                 | Query built                       |
| --------------------- | --------------------------------- |
| `poké star`           | `(poke:* & star:*)`               |
| `mario film \| zelda` | `(mario:* & film:*) \| (zelda:*)` |
| `a & b ! c:*`         | `(a:* & b:* & c:*)`               |
| `Pokémon \|`          | `(pokemon:*)`                     |
| `\|` or blank         | no keyword condition              |

- Limits of the input, checked by the Pydantic query parameter (`422` otherwise): 100 characters, 8 words.

### 2.6 Sorts

| Sort                    | Order                                                 |
| ----------------------- | ----------------------------------------------------- |
| `popular` (the default) | `like_count DESC, first_made_public_at DESC, id DESC` |
| `newest`                | `first_made_public_at DESC, id DESC`                  |

- `like_count` is the number of rows of the likes table (#276) for the template, computed once per query with a grouped subquery joined to the templates (`LEFT JOIN (SELECT template_id, count(*) … GROUP BY template_id)`), `0` without likes. A correlated subquery per row is 8 times slower (§2.8).
- Every like counts, including those of a banned account: the product does not say otherwise.
- `first_made_public_at` never changes after the first publication ([templates guide](templates.md#28-visibility)), and `id` makes the order total, which the cursor needs.

### 2.7 Pagination

- Response: `{"items": [...], "next_cursor": "…" | null}`. `null` means the last page; there is no total count.
- The **cursor** is opaque to the client: base64url of a small JSON with the sort and the sort values of the last row (`like_count`, `first_made_public_at`, `id`). The backend decodes and validates it with a Pydantic model, then adds the keyset condition, e.g. `(like_count, first_made_public_at, id) < (:like_count, :first_made_public_at, :id)`.
- A cursor that cannot be decoded, or was made for another sort, answers `400` `invalid_cursor` (`invalid_cursor()`, `app/api/errors.py`): the position models (`PopularPosition`, `NewestPosition`, `TemplatePagePosition`) forbid extra fields and the marketplace ones carry their `sort`. The keywords and the tag are sent again with each page, not stored in the cursor.
- The query fetches 25 rows for a page of 24 (`MARKETPLACE_PAGE_SIZE = 24` in `app/constants/`): the 25th only tells that a next page exists.
- _My templates_ (#105) uses the same envelope and cursor on `GET /templates`, with its own order `updated_at DESC, id DESC` (a row comparison `(updated_at, id) < (…)` needs both columns in the same direction) and its own position model (`TemplatePagePosition`). Both lists read one row more than the page and split it with `split_page` (`app/core/cursor.py`).

### 2.8 Indexes and measures

Indexes, each one created by the migration of the PR that needs it:

| Table                | Index                                                                                                                             | Serves                      |
| -------------------- | --------------------------------------------------------------------------------------------------------------------------------- | --------------------------- |
| `templates`          | GIN on `to_tsvector('simple', search_text)`, partial `WHERE visibility = 'public' AND moderation = 'none' AND deleted_at IS NULL` | Keywords                    |
| `templates`          | B-tree `(first_made_public_at DESC, id DESC)`, same partial condition                                                             | `newest` sort and cursor    |
| `template_tags`      | Primary key `(template_id, normalized_label)`, B-tree on `normalized_label`                                                       | Duplicates, tag filter      |
| `template_likes`     | Primary key `(template_id, user_id)`, B-tree on `user_id`                                                                         | Like count, a user's like   |
| `template_favorites` | Primary key `(template_id, user_id)`, B-tree `(user_id, created_at, template_id)`                                                 | A user's favorites, by page |
| `account_bans`       | B-tree on `user_id` (exists)                                                                                                      | Listing rule                |

Measured during the spike on PostgreSQL 18 (local Docker), with 20,000 templates of which 7,441 listed candidates, 30,000 likes and 40 active bans:

| Query (first 25 rows)                                       | Plan                                                  | Time    |
| ----------------------------------------------------------- | ----------------------------------------------------- | ------- |
| Keyword `poke`, `newest`                                    | Bitmap scan of the GIN index, anti join on the bans   | 1.0 ms  |
| No keyword, `newest`, second page (cursor)                  | Index scan of the partial B-tree, stops after 25 rows | 0.2 ms  |
| Keywords `mar fil \| zel`, tag `anime`, `popular`           | GIN index and tag index, then sort of 57 rows         | 1.7 ms  |
| No keyword, `popular`, grouped like count                   | Count of every like, sort of every listed template    | 10.9 ms |
| No keyword, `popular`, correlated count (rejected)          | Two subqueries per listed template                    | 89 ms   |
| No keyword, `popular`, stored counter + index (for compare) | Index scan, stops after 25 rows                       | 0.2 ms  |

The `popular` sort without keyword is the only one that grows with the data: its cost follows the number of likes and of listed templates. **Threshold**: when that query goes over about 50 ms in production (roughly 30,000 listed templates or 150,000 likes, five times the measure above), switch to a `like_count` column kept by the like service and by the account deletion, with the index `(like_count DESC, first_made_public_at DESC, id DESC)` on the same partial condition.

### 2.9 API

Open to visitors (no user dependency, like the public template page):

| Method and path                                                          | Success                                 | Errors                        |
| ------------------------------------------------------------------------ | --------------------------------------- | ----------------------------- |
| `GET /marketplace/templates?q=&tag=&sort=popular\|newest&cursor=&limit=` | `200` `MarketplaceTemplateListResponse` | `400` `invalid_cursor`, `422` |
| `GET /marketplace/tags`                                                  | `200` `MarketplaceTagsResponse`         | —                             |
| `GET /marketplace/featured`                                              | `200` `FeaturedTemplatesResponse`       | —                             |

- `MarketplaceTemplateListResponse` is `{items, next_cursor}`. Each item (`MarketplaceTemplateResponse`) carries what a card shows (US-3.1):
  - `id`, `name`, `owner_name`, `featured` (§2.12), `tags` (labels), `tile_count`, `like_count`;
  - `preview_image_url` / `preview_image_removed`: the first tile's image, with `optional_image_url` and `is_image_removed`, so a removed image is never served ([images guide](images.md#29-moderation)); both are empty when the first tile has no image;
  - `tier_colors`: the colors of the tiers, top to bottom, for the preview of a template without a first image.
- `q` takes at most 100 characters (`SEARCH_QUERY_MAX_LENGTH`) and 8 words (`SEARCH_QUERY_MAX_WORDS`, counted after normalization by an `AfterValidator`); `tag` at most 30 characters, normalized like the stored tags; `limit` from 1 to 24 (the visitor home asks for 3).
- `GET /marketplace/tags` gives the 12 tags (`MARKETPLACE_POPULAR_TAG_COUNT`) used by the most listed templates, one per `normalized_label`, the alphabetically first label standing for its spellings.
- `GET /marketplace/featured` gives the TierList picks as `{items}`, the same cards (§2.12).

### 2.10 Likes

| Method and path                           | Success                    | Errors                                                                     |
| ----------------------------------------- | -------------------------- | -------------------------------------------------------------------------- |
| `GET /marketplace/templates/{id}/like`    | `200` `LikeStateResponse`  | `401`, `404`                                                               |
| `PUT /marketplace/templates/{id}/like`    | `200` `LikeStateResponse`  | `401`, `403` `email_not_verified`, `404`, `409` `cannot_like_own_template` |
| `DELETE /marketplace/templates/{id}/like` | `200` `LikeStateResponse`  | `401`, `404`                                                               |
| `GET /marketplace/likes?template_id=…`    | `200` `LikeStatesResponse` | `401`, `422` (no id or more than one page of ids)                          |

- Table `template_likes` (`models/template_like.py`): primary key `(template_id, user_id)`, index on `user_id`, `created_at`. Both foreign keys are `ON DELETE CASCADE`: deleting an account or purging a template removes its likes, so the count never needs a cleanup.
- `LikeStateResponse` is `{liked, like_count, can_like}`; `can_like` is false for the owner, so the public page knows whether to show the button without exposing the owner.
- `GET /marketplace/likes` gives the marketplace cards the same state for one page at once (#480): `template_id` repeated, at most `MARKETPLACE_PAGE_SIZE` ids; `LikeStatesResponse` lists `{template_id, liked, like_count, can_like}` for the **listed** ones, in the requested order, the others left out. Three queries whatever the number of ids (`list_listed_template_owner_ids`, `count_likes_of_templates`, `list_liked_template_ids`). The list `GET /marketplace/templates` keeps no user dependency, so an expired token never breaks it (as the public page, #275).
- The routes need an account; liking needs a **confirmed email address** too (`403` `email_not_verified`), like making a template public, so throwaway accounts cannot rank a template. They act on a **listed** template only (`get_listed_template_name_and_owner`), otherwise `404` `template_not_found`. `PUT` is idempotent (`INSERT … ON CONFLICT DO NOTHING`), `DELETE` too.
- The likes of a template that stops being listed are kept, and come back with it (invariant 6). `PublicTemplateResponse` carries `like_count`.

### 2.11 Favorites

A signed-in user keeps public templates in _My favorites_ to find them again (US-3.5, #278). Nobody else sees them, and there is no count.

| Route                                            | Answer                                  | Errors                                                                         |
| ------------------------------------------------ | --------------------------------------- | ------------------------------------------------------------------------------ |
| `GET /marketplace/templates/{id}/favorite`       | `200` `FavoriteStateResponse`           | `401`, `404`                                                                   |
| `PUT /marketplace/templates/{id}/favorite`       | `200` `FavoriteStateResponse`           | `401`, `403` `email_not_verified`, `404`, `409` `cannot_favorite_own_template` |
| `DELETE /marketplace/templates/{id}/favorite`    | `200` `FavoriteStateResponse`           | `401`, `404`                                                                   |
| `GET /marketplace/favorite-states?template_id=…` | `200` `FavoriteStatesResponse`          | `401`, `422` (no id or more than one page of ids)                              |
| `GET /marketplace/favorites?cursor=&limit=`      | `200` `MarketplaceTemplateListResponse` | `401`, `400` `invalid_cursor`                                                  |

- Table `template_favorites` (`models/template_favorite.py`, migration `c4e1a7d29b56`): primary key `(template_id, user_id)` (at most one favorite per template, invariant 5), `created_at`, and the index `(user_id, created_at, template_id)` for the list. Both foreign keys are `ON DELETE CASCADE`: deleting an account or purging a template removes its favorites.
- The rules follow the likes (§2.10): the routes act on a **listed** template only (`404` `template_not_found` otherwise), adding needs a **confirmed email address** (`403`), the owner cannot add their own template (`409`, `can_favorite` false), and `PUT` and `DELETE` are idempotent. `FavoriteStateResponse` is `{favorited, can_favorite}`.
- `GET /marketplace/favorite-states` gives the cards their state for one page at once, like `GET /marketplace/likes`: the **listed** ones in the requested order, the others left out, in two queries whatever the number of ids.
- `GET /marketplace/favorites` lists the account's favorites as marketplace cards, most recently added first. `list_favorite_templates` (`repositories/templates.py`) starts from the listing rule (§2.2) and joins the account's favorites, so a favorite whose template stops being listed is kept but not shown, and comes back with it (invariant 6). It pages by keyset on `(favorite.created_at DESC, id DESC)`, with the cursor position `FavoritesPosition` (`favorited_at`, `id`) encoded by `app/core/cursor.py`. The like counts come from the same correlated subquery as the TierList picks, the tile counts and first tiles from `_cards`, so a page always takes the same number of queries.

### 2.12 TierList picks

The super admins feature some official templates ([templates guide](templates.md#211-official-templates), #492); the players see them first.

- **Route**: `GET /marketplace/featured`, open to visitors, without cursor nor parameter. `list_featured_templates` (`repositories/templates.py`) reads the **listed** templates (§2.2) whose `featured_at` is set, most recently featured first (`featured_at DESC, id DESC`), at most 6 (`FEATURED_TEMPLATES_MAX`), with their like counts in the same query; `MarketplaceService.list_featured` adds the tile counts and first tiles like a page of the list (`_cards`).
- **Only official templates**: only `OfficialTemplateService.feature` sets `featured_at`, on a published official template; unpublishing or deleting it clears the column. Hiding or deleting it through the moderation also clears `featured_at`, in the same update (`set_template_moderation`, `mark_template_deleted`).
- **`featured`**: `MarketplaceTemplateResponse` and `PublicTemplateResponse` carry it (`featured_at IS NOT NULL`), so a pick also has its badge in the list, in a search and on its public page.
- **Order**: the most recently featured first; there is no manual ordering.
- A pick is also listed in `GET /marketplace/templates` under the usual sorts: the row does not remove it from the list.

### 2.13 Known limitations

- **Likes moving between pages**: with the `popular` sort, a like given while someone pages can move a template across the cursor, so it is shown twice or skipped. The frontend drops a template already shown (same `id`) when it appends a page; a skipped one comes back on the next search.
- **No relevance, no typo tolerance**: the next step would be `pg_trgm` (similarity), which needs the extension in production.
- **Latin scripts only**: words in other scripts are removed by the normalization, hence not searchable.
- `search_text` must be rewritten by every code path that changes a name or the tags; a test per path guards it (#272).

## 3. In the code

What each issue built:

| Issue | Adds                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| ----- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| #272  | **Built**: `normalize_search_text` (`app/core/search_text.py`), table `template_tags` (`models/template_tag.py`), column `templates.search_text` and its GIN index (migration `33bd344cd746`), `_refresh_search_text` on create, rename and tag changes (`services/templates.py`). Details in the [templates guide](templates.md#29-tags).                                                                                                                                                                                                                                                                                                                                                                                                                        |
| #275  | **Built**: `listed_templates_condition(now)`, `get_listed_template_with_owner_name` and `get_listed_template_name_and_owner` (`repositories/templates.py`), used by the public template page, the template reports, and the rooms and snapshots on someone else's public template (`get_playable_template`, #273). Details in the [templates guide](templates.md#210-public-template-page).                                                                                                                                                                                                                                                                                                                                                                       |
| #276  | **Built**: table `template_likes` (`models/template_like.py`, migration `a9b8f14a856a`), `repositories/template_likes.py`, `MarketplaceService.like` / `unlike` / `like_state`, the like routes (§2.10), `like_count` on the public page, the like button (`components/LikeButton.tsx`) and the privacy policy (`privacy.data.likes`).                                                                                                                                                                                                                                                                                                                                                                                                                            |
| #277  | **Built**: `build_search_query` (`app/core/search_query.py`), `list_marketplace_templates` and `list_popular_listed_tags` (`repositories/templates.py`), the tile counts and first tiles of a page's templates in two small queries (`count_tiles_of_templates`, `list_first_tiles_of_templates`, rather than loading every tile), `MarketplaceService.list_templates` with one cursor position per sort (`PopularPosition`, `NewestPosition`), constants in `app/constants/marketplace.py`, index `ix_templates_listed_newest` (migration `3cc4d74966c1`), the routes (§2.9), `/marketplace` in the sitemap ([search engines guide](seo.md#2-pages)). Frontend: `MarketplacePage`, `MarketplaceCard`, `PopularTemplates` on the visitor home, the nav link (§4). |
| #278  | **Built**: table `template_favorites` (`models/template_favorite.py`, migration `c4e1a7d29b56`), `repositories/template_favorites.py`, `list_favorite_templates`, `MarketplaceService.favorite` / `unfavorite` / `favorite_state` / `favorite_states` / `list_favorites`, the favorite routes (§2.11). Frontend: `FavoriteButton` and `CardFavoriteButton`, `FavoritesPage`, `useCardStates`, the shared test fixture `marketplaceCard`, the privacy policy (`privacy.data.favorites`) (§4).                                                                                                                                                                                                                                                                      |
| #480  | **Built**: `MarketplaceService.like_states` and `GET /marketplace/likes` (§2.10); frontend `useCardLikeStates` (now `useCardStates`, #278) and `CardLikeButton` on the cards, `PopularTemplates` on the signed-in home too (§4).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| #492  | **Built**: `featured_at` (migration `7b2e4c9d1a03`), `list_featured_templates` (`repositories/templates.py`), `MarketplaceService.list_featured`, `GET /marketplace/featured` and `FeaturedTemplatesResponse` (§2.12), `featured` on the cards and the public page. Frontend: `useFeaturedTemplates`, the « Sélection TierList » row of `MarketplacePage`, the picks first in `PopularTemplates`, `TemplateFeaturedBadge` (§4).                                                                                                                                                                                                                                                                                                                                   |
| #105  | **Built**: `encode_cursor` / `decode_cursor` (`app/core/cursor.py`, `InvalidCursorError`), `TemplateService.page_for_owner`, `next_cursor` in `TemplateListResponse`; frontend `useTemplates` as an infinite query ([templates guide](templates.md#26-endpoints)).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |

## 4. Frontend

- **Page** `MarketplacePage`, at `/marketplace` (`ROUTES.MARKETPLACE`), open to visitors:
  - a search form (`role="search"`, sent on submit, as the other search fields of the app), a "Trier par" select, the popular tags as toggle pills (`aria-pressed`, one at a time);
  - the filters live in the address (`?q=&tag=&sort=`, `sort` left out for the default), so a search can be shared and goes back with the browser; they are part of the query key (`['marketplace', 'list', filters]`);
  - the cards in the shared `PagedList` with "Voir plus"; a template already shown is dropped when a page is appended (`uniqueById`, §2.13);
  - empty state, or "nothing matches" with "Effacer la recherche";
  - the **« Sélection TierList »** row (`TierListPicks`), between the filters and the list, only without keywords nor tag and when there is at least one pick: a heading, a short sentence and the cards of `GET /marketplace/featured` (`useFeaturedTemplates`, key `['marketplace', 'list', 'featured']`), without the badge, since the heading already says it. The like and favorite states of the row are asked with the pages of the list (`useCardStates`).
- **Card** `MarketplaceCard`: the preview is the first tile's image, the "image removed" visual, or the template's tier colors as bars of decreasing width, like the logo; then the name (a link that covers the card), "par … · n éléments", the « Sélection TierList » badge for a pick (`TemplateFeaturedBadge`, a written label; `showFeaturedBadge={false}` in the row), the tags and the number of likes. For a signed-in reader who may like the template, the number is a like toggle (`CardLikeButton`, `aria-pressed`, named "J'aime « Chips » · 3", above the covering link); next to it, a reader who may add it to their favorites gets a bookmark toggle (`CardFavoriteButton`, named "Favori « Chips »"). The page, the home preview and _My favorites_ ask the like and favorite states once per page of cards (`useCardStates`), which fills the per-template caches shared with the public page.
- **Home**: `PopularTemplates` shows 3 templates, the picks first (most recently featured first) then the most liked ones not already shown, with "Voir tous les modèles publics": after the three steps for a visitor, below _Derniers modèles_ / _Dernières parties_ for a signed-in user (#480); hidden when there is none. The signed-in nav has a "Modèles publics" link (`MainNav`); the empty state of _Vos modèles_ offers "Ou partez d'un modèle public".
- **My favorites**: `FavoritesPage`, at `/favorites` (`ROUTES.FAVORITES`, inside `RequireAuth`), with a "Mes favoris" link in `MainNav`: the cards of `GET /marketplace/favorites` (`useFavoriteTemplates`, key `['marketplace', 'favorites']`) in `PagedList` with "Voir plus", or an empty state linking to the marketplace. Each page marks its cards as favorites in the per-template cache, so the page only asks the like states (`useCardLikeStates`). Removing a favorite drops it from the cached list at once; adding or removing one marks the list stale without refetching it, so it is read again on the next visit.
- **Public template page**: a "← Modèles publics" link (a visitor who comes from a search engine has no nav), tags linking to `/marketplace?tag=…` (`TemplateTagList linkToMarketplace`), the « Sélection TierList » badge of a pick, the like button and the favorite button ([templates guide](templates.md#210-public-template-page)).
