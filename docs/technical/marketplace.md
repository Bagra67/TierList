# Marketplace

How the marketplace lists, searches, sorts and pages the public templates. **Decided in spike #274, not built yet**: the tags come with #272, the likes with #276, the marketplace with #277 and the pagination of _My templates_ with #105. Each of those issues fills §3 and turns this page into the description of the code once it is built.

## 1. Functional overview

### What is needed

- The marketplace shows the **listed** templates, page after page, with a _See more_ button (US-3.1, [screens](../product/milestone-2/screens.md)). A template is listed if and only if it is **public**, **not hidden** by the moderation, **not deleted**, and its owner is **not banned** (invariant 2 of the [domain model](../product/milestone-2/domain-model.md#invariants)). A temporary ban ends on its own, so the rule depends on the current time.
- **Keywords** search the name and the tags, ignoring case and accents (US-3.2). A keyword matches the **start of a word**: `poke` finds _Pokémon_, `kemon` does not. Several keywords must **all** match (AND); `|` separates alternatives (OR): `mario film | zelda` finds the templates matching both `mario` and `film`, or `zelda`.
- A **tag** filter keeps the templates with that tag; it combines with the keywords.
- Two sorts: **popularity** (number of likes, the default) and **newest** (date the template was first made public).
- **Tags**: 5 at most per template, 30 characters at most each, duplicates ignoring case and accents merged (US-2.2, invariant 4).
- **Volumes**: a few hundred to a few thousand public templates expected in the first year. 24 templates per page.
- No new service: everything runs in the PostgreSQL the app already uses (PostgreSQL 17 in production, 18 locally and on CI).

### Not available yet

- No **relevance** sort: a search keeps the chosen sort (popularity or newest).
- No **fuzzy** search: a typo (`pokmeon`) finds nothing (§2.10).

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

Examples: `Pokémon` → `pokemon`, `Œuvres d'Art` → `oeuvres d art`, `Spider-Man 2` → `spider man 2`, `café_crème` → `cafe creme`. Non-Latin scripts (`日本`) give an empty string, hence cannot be searched (§2.10).

### 2.4 Tags

A table `template_tags`, owned by the template (composition: no shared tag catalogue, the tags are free words):

| Column             | Content                                                                                 |
| ------------------ | --------------------------------------------------------------------------------------- |
| `template_id`      | Foreign key to `templates.id`, `ON DELETE CASCADE`.                                     |
| `label`            | The tag as typed by the owner (trimmed), shown everywhere; 30 characters at most.       |
| `normalized_label` | `normalize_search_text(label)`: duplicates and the tag filter compare this column only. |

- Primary key `(template_id, normalized_label)`: a duplicate is refused by the database too. Adding a tag whose normalized form already exists keeps the first label (merge, US-2.2).
- A tag whose normalized form is empty (only punctuation or a non-Latin script) is refused.
- At most 5 tags: checked by the service, on the template row locked with `SELECT … FOR UPDATE` like every template change.
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
- A cursor that cannot be decoded, or was made for another sort, answers `400` with a new `ErrorCode` `invalid_cursor` (translated under `errors.api.*` in the PR that adds it). The keywords and the tag are sent again with each page, not stored in the cursor.
- The query fetches 25 rows for a page of 24 (`MARKETPLACE_PAGE_SIZE = 24` in `app/constants/`): the 25th only tells that a next page exists.
- _My templates_ (#105) uses the same envelope and cursor on `GET /templates`, with its own order `updated_at DESC, id DESC`; `next_cursor` is added next to `items` in `TemplateListResponse`, which does not break the current clients.

### 2.8 Indexes and measures

Indexes, each one created by the migration of the PR that needs it:

| Table            | Index                                                                                                                             | Serves                    |
| ---------------- | --------------------------------------------------------------------------------------------------------------------------------- | ------------------------- |
| `templates`      | GIN on `to_tsvector('simple', search_text)`, partial `WHERE visibility = 'public' AND moderation = 'none' AND deleted_at IS NULL` | Keywords                  |
| `templates`      | B-tree `(first_made_public_at DESC, id DESC)`, same partial condition                                                             | `newest` sort and cursor  |
| `template_tags`  | Primary key `(template_id, normalized_label)`, B-tree on `normalized_label`                                                       | Duplicates, tag filter    |
| `template_likes` | Primary key `(template_id, user_id)`, B-tree on `user_id`                                                                         | Like count, a user's like |
| `account_bans`   | B-tree on `user_id` (exists)                                                                                                      | Listing rule              |

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

Proposed for #277 (the PR fixes the final names):

`GET /marketplace/templates?q=&tag=&sort=popular|newest&cursor=`, open to visitors, answers `{"items": [...], "next_cursor": …}`. Each item carries what a card shows (US-3.1): id, name, owner's display name, tags (labels), number of tiles, number of likes, preview image of the first tile (or the "image removed" visual, [images guide](images.md#29-moderation)).

### 2.10 Known limitations

- **Likes moving between pages**: with the `popular` sort, a like given while someone pages can move a template across the cursor, so it is shown twice or skipped. The frontend drops a template already shown (same `id`) when it appends a page; a skipped one comes back on the next search.
- **No relevance, no typo tolerance**: the next step would be `pg_trgm` (similarity), which needs the extension in production.
- **Latin scripts only**: words in other scripts are removed by the normalization, hence not searchable.
- `search_text` must be rewritten by every code path that changes a name or the tags; a test per path guards it (#272).

## 3. In the code

Nothing yet. What each issue adds:

| Issue | Adds                                                                                                                                                   |
| ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| #272  | `normalize_search_text`, table `template_tags`, column `templates.search_text` and its GIN index, rewrite of `search_text` on rename and tag changes.  |
| #276  | Table `template_likes` and its indexes; the privacy policy (likes are personal data).                                                                  |
| #277  | `listed_templates_condition`, query builder of §2.5, cursor of §2.7, `invalid_cursor`, `MARKETPLACE_PAGE_SIZE`, index of the `newest` sort, the route. |
| #105  | Cursor on `GET /templates` (`next_cursor` in `TemplateListResponse`).                                                                                  |
