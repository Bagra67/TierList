# Game rules

English | [Français](game-rules.fr.md)

The business rules of TierList: how each mode is played, what can be configured, and what is saved. Vocabulary: [product.md](product.md#glossary). Who may do each action: [permissions.md](permissions.md). Most of these rules are not implemented yet, see [roadmap.md](roadmap.md).

## 1. Room game

### Joining a room

- A room is joined with a **link** or with a **code** typed in the app.
- Players can have an account or be **guests**. A guest has fewer personalization options (e.g. no profile picture).
- A room **persists between games**: same lobby, same code, a new game can be started on the same template.
- A room is closed by its **admin**, or **automatically** after some time of inactivity.
- The maximum number of players depends on the room admin's [plan](#7-plans-and-limits).

### Running a game

- One **round** = the room admin **shows an item**, and **every player places it at the same time**.
- Item order: the **template order** or **random**, chosen by the room admin.
- Moving to the next item:
  - the room admin can **always** move on **by hand**;
  - optionally, automatically: after a **timer** per item, or **as soon as everyone has placed** the item.
- A ranking is **ordered**: inside a tier, the position of each tile matters.
- The room admin **plays or not**, as configured.
- Optional **chat and reactions** (emojis): wanted, low priority.

### Board visibility

| Board       | What players see                                                                                                     |
| ----------- | -------------------------------------------------------------------------------------------------------------------- |
| **Private** | Only their own ranking. Results and statistics are revealed afterwards.                                              |
| **Public**  | A semi-transparent **hologram** of every other player's tile, **moving live** while they drag it (hesitations show). |

Holograms are **turned off above a number of players**. This threshold is an **application setting**, not a room setting, and it can be changed **without a rebuild**.

### Final cooldown

- After the last item, a **configurable cooldown** lets every player **move all their tiles again**, with a "under pressure" interface (timer, atmosphere).
- **Both placements are kept**: the one made during the round ("hot take") and the final one. Statistics use the final placement and can compare both.

### Absent players

- A player who misses an item (disconnected, joined late) gets an **absent vote** for it.
- During the final cooldown, they **can place the items they missed**.
- Statistics can be computed **with or without** absent votes.

### Closing and saving

- At the end, the game is **closed** and **saved for every player**.
- A saved game is **frozen** with the version of the template it was played on: editing the template later does not change it.

### Room settings

Private rooms are **highly configurable**. Settings named so far:

- board visibility (private / public);
- item order (template / random);
- automatic move to the next item (none / timer / everyone done);
- final cooldown duration;
- whether the room admin plays;
- when results are visible (before or after closing);
- animated reveal pace (led by the room admin or automatic);
- guest link validity (30 days max);
- blind mode settings, see [section 4](#4-blind-mode).

**Public rooms** (anyone can join) are possible but postponed: they raise performance concerns if the app grows, see [roadmap.md](roadmap.md#technical-questions).

## 2. Open mode

- **No room**: each person fills in the tier list **on their own**.
- Open for a **set duration**, then closed.
- **An account is required** to take part (prevents mass voting).
- A participant can **change their ranking** after submitting it, while it is open.
- Results and statistics are **updated live** on each submission or change.
- **No holograms**, no real time.
- Only the **template owner** can start an open mode.
- **Featured on the home page**, by number of likes, or first when the owner has a [special rank](permissions.md#special-rank).
- Blind open mode: possible, but **not at first**.

## 3. Solo

- A tier list made **alone**, from a template.
- **Saved in the history**, **shareable** and **exportable** like a game.

## 4. Blind mode

Players rank items **without knowing what they are**, then the items are revealed. Example: a sound blind test, or a tasting where the room admin hands out each item in real life while the matching tile is shown. The app only handles the ranking: nothing physical.

### Templates

- A template is either **classic** or **blind**.
- A classic template is played **only in classic** mode. A blind template can be played **blind or classic**.
- A blind tile has, besides its content: a **hint**, an **answer name** and an **answer image** (shown at the reveal).

### During the game

- A hidden tile is shown as a **number**. Later: other looks, chosen from **presets**.
- **Sounds**: each player can play the sound **on their own device** (players in the same room organize themselves).
- The room admin has a **different view showing the answers**.
- The room admin **can play**, but their votes are **flagged as admin**: they count in the tier list, **not in the guessing score**.
- **Reveal**: **after each round** or **at the end**, configurable.

### Guessing

- Players try to **guess** each item and score points.
- The answer mode is **chosen by the template creator**:
  - pick among **all the template's items**;
  - pick among a **list defined by the creator** (choices, decoys);
  - **free text**, judged like in K-Culture: players give a **collective opinion** (accept or not), and the **room admin has the final say**.
- **1 point per correct answer** plus a **speed bonus**. The bonus formula and the number of attempts per item are decided at implementation.
- The score is **shown during the game**, with a **recap at the end**.

## 5. Results and sharing

- Results are shown **per player**, **overall**, and as an **animated reveal** (each item revealed one after another, with who placed it where), like the end of a Gartic Phone game.
- Results are visible **before or after closing**, as configured.
- Each game has a **dedicated results page**, **shareable**: **anyone with the link** can see the game.
- **Image export** of a finished tier list: each participant **chooses what to export** (their ranking, the median ranking, statistics…).

### Links

| Link                    | Purpose                                         | Validity                                                              |
| ----------------------- | ----------------------------------------------- | --------------------------------------------------------------------- |
| **Guest personal link** | Lets a guest get back to their seat and results | Configurable, **30 days max**; stops working once the room is closed. |
| **Public results link** | Lets anyone see the game                        | Stays valid.                                                          |

A lost guest link cannot be recovered, and a guest game **cannot be attached** to an account created later. An **account** is required to keep the **history for life**.

## 6. Statistics

Decided:

- **Median** and **mean** ranking of each item. Since rankings are ordered within tiers, a **global rank** per item gives a finer median and mean than the tier alone.
- Statistics **with or without absent votes**.
- **Changes of mind**: the round placement compared with the final one.
- Available **at the end of the game**, and **during it** where it makes sense.

Ideas, to confirm when the feature is designed:

- Most **consensual** item (low spread) and most **divisive** item (high spread, e.g. as many S as D).
- Vote distribution per item (S → D histogram).
- Agreement between players: the most "mainstream" player (closest to the mean), the "rebel" (furthest), the two players with the closest and the most opposite tastes.
- Each player's "hot take": their item furthest from the consensus.
- Across games on the same template: how an item or a player evolves.
- During the game: decision time per item, **hesitations** (moves before dropping a tile).
- Profile fun facts, e.g. "this player is 30% more extreme than their friends".

## 7. Plans and limits

| Plan        | Room size  |
| ----------- | ---------- |
| **Free**    | 10 players |
| **Level 2** | 32 players |
| **Special** | Unlimited  |

- The **room admin** pays, **once**: the plan belongs to their account **for life** (no subscription). Moderation can remove a purchased plan.
- **Everything is free for now**: plans exist from the start so that payment can be added later.
- Free plan limits on templates:
  - **32 tiles** max per template;
  - tile images are **uploaded** and **compressed by the server** before being stored;
  - **no video**;
  - sound **only through a YouTube link**, ideally without the image (see [roadmap.md](roadmap.md#technical-questions)).
- Paid plans unlock nothing else **for now** (video, uploaded sound or video, more tiles: decided later).

## 8. Templates and marketplace

- Tiles can be **text**, **image**, **sound** or **video**. Sound and video can be **uploaded files** or **embedded links** (YouTube…), within the [plan limits](#7-plans-and-limits).
- **Default tiers** (S, A, B…) that can be **added**, **removed** and **configured**.
- Templates are **private** or **public**. Public templates appear in the **marketplace**: search by **tags** and **keywords**, sort by **popularity**, **newest**, etc.
- A template can be **liked** and added to **favorites**.
- A template can be **forked** when its owner allows it. A fork **always credits its whole lineage** (fork of a fork… up to the original).
- When a public template is made private again or deleted, games **in progress** elsewhere can **finish**, but **no new game** can be started with it, even in a persisting room.

## 9. Social

- **Simple profile** at first. Later: player statistics, badges, fun facts.
- **Friends**: added by **request and acceptance**. A friend can be **invited directly** to a room, and their templates and badges can be seen.
- **Profile and history visibility**: **chosen by each user**.

## 10. Notifications

Emails must be useful, never spam.

| Kind                                 | Events                                                                                                                                                                  |
| ------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Always sent** (account)            | Email confirmation, forgotten password (already built), moderation sanction, plan purchase.                                                                             |
| **Can be turned off** by the user    | A template was shared with you, your open mode ended (results ready), an open mode you took part in was closed, your rank request was handled, your report was handled. |
| **Never by email** (in the app only) | Likes, forks, friend requests.                                                                                                                                          |
