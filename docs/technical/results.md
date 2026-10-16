# Results

English | [Français](results.fr.md)

How the results of a closed game are computed: distribution of the votes, absent votes, median ranking. Decided in spike #76; the computation exists as a pure function (§4), and the results API (#99) and page (#100) will use it. What the results show to the user: [user stories](../product/milestone-1/user-stories.md) US-5.2.

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

The function is pure (no database): the results API (#99) loads the snapshot and the placements, excludes the admin who does not play, and turns the output into its response schema. At most 10 players and 32 items: the computation is instant, the API can recompute it at each request, toggle included.

### 2.6 Known limitations

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

| Part    | File                              | Content                                                                                                   |
| ------- | --------------------------------- | --------------------------------------------------------------------------------------------------------- |
| Backend | `backend/app/services/results.py` | `compute_results` and its data classes (`FinalPlacement`, `PlayerRanking`, `ItemResults`, `GameResults`). |
| Tests   | `backend/tests/test_results.py`   | The examples of §3 ([testing guide](testing.md)).                                                         |

The API (#99) and the results page with the checkbox (#100) come next.
