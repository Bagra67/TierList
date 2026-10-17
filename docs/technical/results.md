# Results

English | [Français](results.fr.md)

How the results of a closed game are computed: distribution of the votes, absent votes, median ranking. Decided in spike #76; the computation is a pure function, served by the results API (#99, §2.6) and shown by the results page (#100, §2.7). What the results show to the user: [user stories](../product/milestone-1/user-stories.md) US-5.2.

**In short**: for each item, the placements of all the players are turned into **fine scores** (tier + position in the tier), and the item keeps the **median score**. Then the median tier list of all the items is built: each item goes into the tier of its median score, and inside a tier the items are sorted by median score.

## 1. Functional overview

The results of a game (US-5.2) show:

- **each participant's ranking**: their final placements as they are, without any computation;
- the **overall view**: for each item, how many players put it in each tier, and how many were absent;
- the **median ranking**: a tier list where each item has one tier and one place.

A checkbox **"Include absent votes"** recomputes the overall view and the median ranking. It is checked by default, as on the [results screen](../product/milestone-1/screens.md).

### Rules

- The results use the **final placements** of a closed game: the round placement, moved during the cooldown if the player changed their mind ([domain model](../product/milestone-1/domain-model.md)).
- A ranking is **ordered**: inside a tier, the position of each item matters.
- Only **players** count. The room admin who does not play is not in the results.
- Tiers are those of the template snapshot of the game, from top (best) to bottom; there is at least one.

## 2. Technical design

Notation: the tiers are numbered from top to bottom, `t = 0, 1, …` (`0` is the best tier). A smaller score is a better one.

### 2.1 Votes counted

For an item, each player counts **at most once**:

| Player's situation for the item                       | Box checked            | Box unchecked |
| ----------------------------------------------------- | ---------------------- | ------------- |
| Placed it during the round                            | Vote (final placement) | Vote          |
| Absent in the round, caught it up during the cooldown | Vote (final placement) | Ignored       |
| Absent in the round, never placed it                  | Counted in "Absent"    | Ignored       |

- **Checked**: every player who ranked the item counts, catch-ups included; those who never placed it make the "Absent" row of the overall view, without effect on the median (they have no tier).
- **Unchecked**: only the votes made during the round count, the "hot take" of the game; absent players are removed, even if they caught the item up, and the "Absent" row is empty.

### 2.2 Fine score of a vote

A tier alone is too coarse: two items in the same tier would always tie. The **fine score** adds the position in the tier:

```
score = t + (k + 1/2) / n
```

- `t`: index of the tier where the player put the item;
- `k`: rank of the item in that tier for this player (`0` = first); only the order of the positions counts;
- `n`: number of items the player put in that tier.

The score is always strictly between `t` and `t + 1`, so sorting by score also sorts by tier. Dividing by `n` makes players comparable even when their tiers do not hold the same number of items. Example: the 2nd item out of 4 in tier A (`t = 1`) scores `1 + 1.5 / 4 = 1.375`.

A score is computed on the **player's whole ranking**, whatever the checkbox: unchecking it removes votes, it does not change the rankings. Scores are exact fractions (`fractions.Fraction`), so that ties are exact.

### 2.3 Median score and median tier

- The scores of the votes counted are sorted in increasing order; the **median score** is the one at index `⌊N / 2⌋` (indices from 0, `N` = number of votes).
- With an **odd** number of votes, it is the middle vote. With an **even** number, it is the **worse of the two middle votes**: a strict majority of the players put the item at this level or better (convention of majority judgment). Example: votes A, A, B, B → B.
- The **median tier** is the integer part of the median score. It is always a tier where at least one player put the item.
- The **mean score** (average of the scores) is also computed: it breaks ties (§2.4) and is ready for the mean ranking planned later ([game rules](../product/game-rules.md)).

### 2.4 Median ranking

1. Each item goes into its median tier.
2. Inside a tier, items are sorted by **median score**, then by **mean score**, then by **template order** (always distinct, so the order is total and stable).
3. An item **without any vote counted** (every player absent and never caught up, or box unchecked and nobody voted during the round) has no median tier: it is listed apart as **unranked**, in template order.
4. A tier may stay empty.

### 2.5 Inputs and outputs

`compute_results(tier_count, tile_ids, players, include_absent_votes)` in `app/services/results.py`:

| Input                  | Content                                                                                                                                                           |
| ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `tier_count`           | Number of tiers of the snapshot.                                                                                                                                  |
| `tile_ids`             | The tiles of the snapshot, in template order (last tie-break, order of the unranked items).                                                                       |
| `players`              | One `PlayerRanking` per player: `final_placements` (tile → `FinalPlacement(tier_index, position)`) and `absent_tile_ids` (absent in the round, caught up or not). |
| `include_absent_votes` | The checkbox.                                                                                                                                                     |

The output, `GameResults`, holds for each item an `ItemResults` (`votes_per_tier`, `absent_count`, `median_score`, `mean_score`, `median_tier_index`, the last three `None` when unranked), the `median_ranking` (one tuple of tiles per tier, top to bottom) and the `unranked_tile_ids`.

The function is pure (no database): the results API (§2.6) loads the snapshot and the placements, excludes the admin who does not play, and turns the output into its response schema. At most 10 players and 32 items: the computation is instant, the API can recompute it at each request, toggle included.

### 2.6 Results API

Built in #99.

- **Link**: each closed game has a `games.public_token`, drawn by `_close_game` (`generate_public_results_token`, `secrets.token_urlsafe`, 128 bits); the games closed before #99 got one in the migration (`gen_random_uuid`, 122 bits). A closed game always has one (`ck_games_closed_has_public_token`). The token is kept in clear: the lobby shows it again, and it only gives read access to the results.
- **Who reads**: `GET /results/{public_token}` needs **no account**: the link is the only protection, impossible to guess. After the closing, nothing links a guest to the game any more (no seat, no `user_id`), so the link is the only identity left. Only the seats of the room get it, through `RoomResponse.past_games` ([rooms guide](rooms.md)); the history of the accounts (#103) will give it too. An unknown link, or a game not closed, answers `404` `results_not_found`; a link longer than the column (32 characters) is refused at once with `422`.
- **Checkbox**: `include_absent_votes` (`true` by default, like the checkbox); the computation is redone at each request.
- **Reading**: `GameResultsService` (`app/services/game_results.py`) reads the game with `get_closed_game_by_token` (tiers, tiles and their images, placements, frozen players, one query per table: the count does not grow with the items). For each frozen player, the `FINAL` placements give the `FinalPlacement`s and the absent `ROUND` placements the `absent_tile_ids`. The room admin who does not play has no placement, hence no frozen player: they are left out.
- **Response** `GameResultsResponse`:

  | Field                        | Content                                                                                                                                                                                                            |
  | ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
  | `template_name`, `closed_at` | Name of the frozen template, closing time.                                                                                                                                                                         |
  | `include_absent_votes`       | The checkbox used.                                                                                                                                                                                                 |
  | `tiers`                      | `{id, name, color}`, top to bottom.                                                                                                                                                                                |
  | `items`                      | `{id, text, image_url}`, in template order.                                                                                                                                                                        |
  | `median_ranking`             | `[{tier_id, item_ids}]`, one per tier, top to bottom.                                                                                                                                                              |
  | `unranked_item_ids`          | Items without any vote counted, in template order.                                                                                                                                                                 |
  | `distribution`               | `[{item_id, votes_per_tier, absent_count, median_tier_id}]`, in template order; `votes_per_tier` follows `tiers`; `absent_count` is `0` without the absent votes; `median_tier_id` is `null` for an unranked item. |
  | `players`                    | `[{display_name, tiers: [{tier_id, item_ids}], unplaced_item_ids}]`: each player's final ranking (it does not depend on the checkbox) and the items they never placed.                                             |

  The fine scores (fractions) are not sent.

### 2.7 Results page

Built in #100.

- **Route**: `/results/:token` (`ROUTES.RESULTS`, `resultsPath`), outside `RequireAuth`: the link is enough, with or without an account.
- **Reaching it**: the lobby lists the closed games of the room (`PastGames`, from `RoomResponse.past_games`), newest first, each with "See the results". The game closing does not open the page by itself: everyone opens it when they want, and the room stays ready for the next game. The link carries the room and whether the reader is its admin in its navigation state (`ResultsLinkState`), so the page offers "Back to the room", and "Play again" to the room admin (`ResultsRoomActions`, the same start as the lobby, then the room opens; the server checks the role); a visitor arriving by the public link has no such state, hence neither.
- **Checkbox** "Include absent votes", checked by default: it is part of the query key (`useGameResults(token, includeAbsentVotes)`), so toggling reads the results once, then each variant stays in cache (`staleTime: Infinity`: a closed game no longer changes). A `4xx` is not retried (`retryUnlessClientError`). The title, the date, the box and the tabs come from either variant already read (`anyVariant`); the statistics shown always match the box: while the other variant is read, or after a failure, the panel shows the loading state or the error instead (`aria-busy`), and checking back shows the cached variant at once.
- **Views**, in ARIA tabs (`ResultsTabs`: a single tab in the tab order, the arrows, Home and End move between tabs and activate them; the panel is focusable, since most views have no interactive element):
  - **Median**: `ResultsTierList`, read-only, with the "Unranked" row under the tiers; each row is a group named by its tier;
  - **Overall**: `ResultsDistributionTable`, a real `<table>` (caption for screen readers, a row header per item), one column per tier and the "Absent" column when the absent votes are included; the table scrolls on its own on a small screen, not the page;
  - **Per player**: a player `<select>`, their `ResultsTierList` and the "Never placed" row.
- **States**: loading, and the translated error (`results_not_found` for an unknown link).
- **Public link** (#101, US-5.3): the page shows its own address, `<origin>/results/<token>`, with "Copy the link" (`CopyLinkField`, shared with the room invitation: the copy is announced, and a message asks to copy by hand when the clipboard refuses). Any visitor opening it sees the same views, read-only: the page offers no room action (no "Play again" for a visitor; only "Back to the room", and "Play again" for the room admin, when opened from its lobby). Without a session, the navigation tries to restore one, then the page shows without any sign-in redirect.
- **Lifetime**: the link never expires and cannot be revoked. It keeps working after the room is closed (the game survives its room, `games.room_id` set to `NULL`) and after a player deletes their account (the frozen player stays, without account).
- **Items without text**: their image is named by their number in the template order ("Image of item 3", `ResultItem.imageLabel`), so two images never share a name in the table or the lists.

### 2.8 Known limitations

- The open mode (later) has live statistics; whether to recompute them fully or incrementally is still open ([roadmap](../product/roadmap.md#technical-questions)). This function covers room games.
- Comparing round and final placements ("changes of mind") is a later statistic; it is not computed here.

## 3. Worked examples

The tests of `tests/test_results.py` recompute each example ([testing guide](testing.md)). Tiers are S, A, B (`t = 0, 1, 2`) unless stated otherwise.

### Example 1: base case

| Player | S                 | A               | B      |
| ------ | ----------------- | --------------- | ------ |
| Alice  | Paprika, Barbecue | Nature          |        |
| Bob    | Barbecue          | Paprika, Nature |        |
| Chloé  | Paprika           | Barbecue        | Nature |

| Item     | Fine scores (Alice, Bob, Chloé) | Sorted        | Median | Mean  | Votes S / A / B | Median tier |
| -------- | ------------------------------- | ------------- | ------ | ----- | --------------- | ----------- |
| Paprika  | 1/4, 5/4, 1/2                   | 1/4, 1/2, 5/4 | 1/2    | 2/3   | 2 / 1 / 0       | S           |
| Barbecue | 3/4, 1/2, 3/2                   | 1/2, 3/4, 3/2 | 3/4    | 11/12 | 2 / 1 / 0       | S           |
| Nature   | 3/2, 7/4, 5/2                   | 3/2, 7/4, 5/2 | 7/4    | 23/12 | 0 / 2 / 1       | A           |

Median ranking: **S** Paprika, Barbecue (1/2 < 3/4) · **A** Nature · **B** empty.

### Example 2: even number of votes

Four players put Paprika alone in its tier: two in A, two in B. Scores 3/2, 3/2, 5/2, 5/2; index `⌊4 / 2⌋ = 2` → **5/2**, tier **B** (the worse of the two middle votes).

### Example 3: absent votes and the checkbox

| Player | S        | A       | B        | Absent in the round                  |
| ------ | -------- | ------- | -------- | ------------------------------------ |
| Alice  | Barbecue | Paprika |          |                                      |
| Dan    | Paprika  |         | Barbecue | Barbecue (caught up in the cooldown) |
| Eve    |          | Paprika |          | Barbecue (never placed)              |

| Barbecue          | Votes counted      | Votes S / A / B | Absent | Median | Median tier |
| ----------------- | ------------------ | --------------- | ------ | ------ | ----------- |
| **Box checked**   | Alice 1/2, Dan 5/2 | 1 / 0 / 1       | 1      | 5/2    | B           |
| **Box unchecked** | Alice 1/2          | 1 / 0 / 0       | 0      | 1/2    | S           |

Paprika is in A both times (scores 3/2, 1/2, 3/2 → median 3/2, mean 7/6, votes 1 / 2 / 0). Median ranking: checked **A** Paprika · **B** Barbecue; unchecked **S** Barbecue · **A** Paprika.

### Example 4: item nobody placed

Alice (Paprika in S) and Bob (Paprika in A) both missed Vinaigre and never placed it. Vinaigre has no vote: **unranked**, with 2 absent votes when the box is checked, 0 when it is unchecked. Paprika is in A (scores 1/2 and 3/2, the worse of the two).

### Example 5: tie-breaks

Tiers S, A (`t = 0, 1`).

| Player | S       | A       |
| ------ | ------- | ------- |
| Alice  |         | X, Y, Z |
| Bob    |         | Y, X, Z |
| Chloé  | Y, X, Z |         |

X: scores 7/6, 3/2, 1/2 → median **7/6**, mean **19/18**. Y: scores 3/2, 7/6, 1/6 → median **7/6**, mean **17/18**. Same median score: the mean decides, **Y before X**, although X comes first in the template.

If Alice ranks S: X, Y and Bob S: Y, X, both items have median 3/4 and mean 1/2: the **template order** decides, X before Y.

## 4. In the code

| Part     | File                                                                                                                                             | Content                                                                                                   |
| -------- | ------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------- |
| Backend  | `backend/app/services/results.py`                                                                                                                | `compute_results` and its data classes (`FinalPlacement`, `PlayerRanking`, `ItemResults`, `GameResults`). |
| Tests    | `backend/tests/test_results.py`                                                                                                                  | The examples of §3 ([testing guide](testing.md)).                                                         |
| Backend  | `backend/app/services/game_results.py`, `app/repositories/games.py`                                                                              | `GameResultsService`, `get_closed_game_by_token`.                                                         |
| Backend  | `backend/app/api/routes/results.py`, `presenters/results.py`, `schemas/results.py`                                                               | `GET /results/{public_token}` and its response.                                                           |
| Tests    | `backend/tests/integration/test_game_results.py`, `test_game_queries.py`                                                                         | The API against a real PostgreSQL ([testing guide](testing.md)).                                          |
| Frontend | `frontend/src/pages/ResultsPage.tsx`, `api/results.ts`                                                                                           | The page, `useGameResults`.                                                                               |
| Frontend | `components/ResultsTabs.tsx`, `resultsViews.ts`, `ResultsTierList.tsx`, `ResultsDistributionTable.tsx`, `ResultsPlayerView.tsx`, `PastGames.tsx` | The views, and the past games of the lobby.                                                               |
| Frontend | `i18n/locales/fr.ts`, `en.ts`                                                                                                                    | `results.*`, `rooms.lobby.pastGames.*`, `errors.api.results_not_found`.                                   |
| Tests    | `frontend/src/pages/ResultsPage.test.tsx`, `RoomPage.test.tsx`                                                                                   | The page and the past games ([testing guide](testing.md)).                                                |
