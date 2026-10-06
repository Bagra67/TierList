# Milestone 1 — User stories

English | [Français](user-stories.fr.md)

What each actor can do in [milestone 1](README.md), grouped by epic. Each story has an ID, a priority and acceptance criteria written as _Given / When / Then_. Vocabulary: [product.md](../product.md#glossary). Screens: [screens.md](screens.md).

**Priority**: **Must** = required for the milestone to be playable; **Should** = expected in the milestone, can slip to the next one if needed.

## Actors

| Actor          | Who                                                                                                |
| -------------- | -------------------------------------------------------------------------------------------------- |
| **User**       | A signed-in account (accounts already exist: [authentication](../../technical/authentication.md)). |
| **Room admin** | The user who created the room.                                                                     |
| **Player**     | A room participant with an account.                                                                |
| **Guest**      | A room participant without an account.                                                             |
| **Visitor**    | Anyone with a public results link, signed in or not.                                               |

"Participant" means player or guest.

## E1 — Templates

### US-1.1 Create a template — Must

As a **user**, I want to create a tier list template, so that I can play it later in a room.

- _Given_ I am signed in, _when_ I create a template with a name, _then_ it is created **private**, owned by me, with the **default tiers S, A, B, C, D, E** and no tiles.
- _Given_ the name is empty, _when_ I save, _then_ the template is not created and the field shows an error.

### US-1.2 Add text and image tiles — Must

As a **template owner**, I want to add tiles with a text and/or an image, so that players have items to rank.

- _Given_ my template, _when_ I add a tile with a text, an image, or both, _then_ the tile is added at the end of the tile list.
- _Given_ I upload an image, _when_ it is accepted, _then_ the server **compresses** it before storing it, and the tile shows the stored version.
- _Given_ a file that is not a supported image, or too large, _when_ I upload it, _then_ it is refused with a message.
- _Given_ my template already has **32 tiles**, _when_ I try to add one, _then_ it is refused with a message stating the limit.
- _Given_ a tile with neither text nor image, _when_ I save, _then_ it is refused.

### US-1.3 Edit, reorder and delete tiles — Must

As a **template owner**, I want to edit, reorder and delete tiles, so that the template matches what I want to rank.

- _Given_ a tile, _when_ I change its text or image, _then_ the change is saved.
- _Given_ several tiles, _when_ I move one, _then_ the new **template order** is saved (used when a room plays items in template order).
- _Given_ a tile, _when_ I delete it, _then_ it disappears from the template.

### US-1.4 Configure tiers — Must

As a **template owner**, I want to add, remove, rename, recolor and reorder tiers, so that the tier list fits its subject.

- _Given_ my template, _when_ I add a tier, _then_ it appears at the bottom with a default name and color.
- _Given_ a tier, _when_ I rename it, change its color or move it, _then_ the change is saved.
- _Given_ my template has **one tier left**, _when_ I try to remove it, _then_ it is refused: a tier list needs at least one tier.

### US-1.5 List my templates — Must

As a **user**, I want to see my templates, so that I can edit them or start a room.

- _Given_ I am signed in, _when_ I open my templates, _then_ I see each one with its name, number of tiles and last change date.
- _Given_ I have no template, _when_ I open the page, _then_ an empty state invites me to create one.

### US-1.6 Delete a template — Should

As a **template owner**, I want to delete a template, so that my list stays tidy.

- _Given_ my template, _when_ I delete it after confirming, _then_ it disappears from my templates.
- _Given_ games were already played with it, _when_ I delete it, _then_ those games and their results **stay available**: they are frozen on the version they were played with.
- _Given_ a room uses it, _when_ I delete it, _then_ a game in progress can finish, but no new game can be started with it.

### US-1.7 Edit a template that was already played — Must

As a **template owner**, I want to keep editing a template after playing it, so that I can improve it.

- _Given_ a template already played, _when_ I edit it, _then_ the past games are **not** changed, and the next game uses the new version.

## E2 — Room

### US-2.1 Create a room — Must

As a **user**, I want to create a room from one of my templates, so that I can play with friends.

- _Given_ one of my templates with at least one tile, _when_ I create a room, _then_ I am its **room admin**, and the room gets a **link** and a short **code**.
- _Given_ a template without tiles, _when_ I try to create a room, _then_ it is refused.

### US-2.2 Configure the room — Must

As a **room admin**, I want to choose the room settings, so that the game fits my group.

- _Given_ my room before a game starts, _when_ I set the **item order** (template or random), the **automatic move** (none, timer per item with its duration, or when everyone has placed), the **cooldown duration**, **whether I play** and whether **late arrivals** are allowed during a game, _then_ the next game uses these settings.
- _Given_ a game in progress, _when_ I open the settings, _then_ they cannot be changed until the game is closed, **except late arrivals** (US-2.10).

### US-2.3 Invite players — Must

As a **room admin**, I want to share the room link or code, so that my friends can join.

- _Given_ my room, _when_ I copy the link or read the code, _then_ anyone with them can join (US-2.4, US-2.5).
- Both work for everyone; in practice the **link** suits a message (guests open it and join), the **code** suits people already in the app or a code read aloud (stream, same room).

### US-2.4 Join with an account — Must

As a **user**, I want to join a room with its link or code, so that I can play.

- _Given_ I am signed in, _when_ I open the room link, _then_ I enter the room **directly with my account** as a **player**, shown with my display name: no nickname, no extra step.
- _Given_ I am signed in, _when_ I type the code in the app's "Join a room" field, _then_ the result is the same.
- _Given_ I am not signed in, _when_ I open the link, _then_ I can sign in (and come back to the room right after) or join as a guest (US-2.5).
- _Given_ a wrong code or a closed room, _when_ I try to join, _then_ a message says the room cannot be found or is closed.
- _Given_ I am already in the room, _when_ I open the link again, _then_ I get my seat back instead of a second one.

### US-2.5 Join as a guest — Must

As a **guest**, I want to join a room without an account, so that I can play right away.

- _Given_ a valid link or code and no account, _when_ I enter a **nickname**, _then_ I enter the room as a **guest** and receive my **personal link**.
- _Given_ an empty nickname, or one already used in the room, _when_ I join, _then_ it is refused with a message.

### US-2.6 Room size limit — Must

As the **application**, I want to cap rooms at the free plan size, so that the plans can be enforced later.

- _Given_ a room with **10 participants**, _when_ someone else tries to join, _then_ it is refused with a message stating the limit.
- _Given_ the room admin does not play, _then_ they still count in the 10 (to be confirmed at implementation).

### US-2.7 Close the room — Must

As a **room admin**, I want to close my room, so that nobody can join or play any more.

- _Given_ my room with no game in progress, _when_ I close it, _then_ the room is **not kept**: it disappears with its link and code, and guest personal links stop working. Its **games are kept**: they stay in the history of participants with an account, and their public results links **keep working**.
- _Given_ a game in progress, _when_ I close the room, _then_ I am asked to confirm, the game is closed first (US-5.1), then the room.

### US-2.8 Automatic closing — Should

As the **application**, I want to close rooms left inactive, so that abandoned rooms do not stay open forever.

- _Given_ a room without activity for the inactivity delay (application setting), _then_ it is closed as in US-2.7.

### US-2.9 Play again — Must

As a **room admin**, I want to start a new game in the same room, so that my group can replay without a new link.

- _Given_ a closed game in my room, _when_ I start a new game, _then_ the participants still in the room take part, with the same link and code, on the **current** version of the template.

### US-2.10 Lock arrivals during a game — Must

As a **room admin**, I want to allow or block new arrivals during a game, so that nobody joins at a bad moment.

- _Given_ a game in progress, _when_ I lock arrivals, _then_ nobody new can join until I unlock them; participants already in the room can **still come back** to their seat (US-4.4).
- _Given_ arrivals are locked, _when_ someone new tries to join, _then_ a message says a game is in progress and the room is locked.
- _Given_ I change it during the game, _then_ the change is kept as the room setting for the next games.

## E3 — Game

### US-3.1 Start the game — Must

As a **room admin**, I want to start the game, so that the first round begins.

- _Given_ my room with at least one participant who places items (me included if I play), _when_ I start the game, _then_ the game is frozen on the current template version, the item order is set (template order or shuffled), and the first item is shown to everyone.

### US-3.2 See the current item — Must

As a **participant**, I want to see the item to rank, so that I can place it.

- _Given_ a round in progress, _then_ I see the current item (text and/or image), its number out of the total, my own tier list and, if a timer is set, the time left.

### US-3.3 Place the item — Must

As a **participant**, I want to drop the current item into a tier at the position I want, so that my ranking reflects my opinion.

- _Given_ the current item, _when_ I drop it into a tier, before, between or after the items already there, _then_ it is saved at that **tier and position**.
- _Given_ I already placed it, _when_ I move it during the same round, _then_ the new place replaces the old one.
- _Given_ items from **past rounds**, _then_ I cannot move them until the final cooldown.
- _Given_ a **private board**, _then_ I never see the other participants' rankings during the game; I only see who has placed the current item.

### US-3.4 Move to the next item — Must

As a **room admin**, I want to move to the next item, so that the game goes on at the right pace.

- _Given_ a round, _when_ I click "next", _then_ the round ends and the next item is shown, **whatever the automatic setting** and even if some participants have not placed it.
- _Given_ the "timer" setting, _when_ the time is up, _then_ the round ends automatically.
- _Given_ the "everyone done" setting, _when_ every connected participant has placed the item, _then_ the round ends automatically.
- _Given_ a participant has not placed the item when the round ends, _then_ they get an **absent vote** for it (US-4.3).
- _Given_ the last item, _when_ its round ends, _then_ the final cooldown starts (US-4.1).

### US-3.5 Play or only host — Must

As a **room admin**, I want to play or only host, depending on the settings.

- _Given_ "the room admin plays", _then_ I place items like any participant, and also have the controls.
- _Given_ "the room admin does not play", _then_ I only have the controls and see the current item, without a tier list; I am not counted in "everyone done" nor in the results.

## E4 — Final cooldown and absences

### US-4.1 Final cooldown — Must

As a **participant**, I want a last timed moment to move all my tiles, so that I can fix my ranking with the whole list in view.

- _Given_ the cooldown has started, _then_ I see a countdown and an interface "under pressure", and I can move **any** of my tiles.
- _Given_ the cooldown, _when_ the time is up or the room admin ends it, _then_ my ranking is final and the game is closed (US-5.1).

### US-4.2 Keep both placements — Must

As the **application**, I want to keep each round placement and each final placement, so that changes of mind can be measured.

- _Given_ an item placed during its round, then moved during the cooldown, _then_ both placements are kept.
- _Given_ an item not moved during the cooldown, _then_ its final placement is its round placement.

### US-4.3 Absent vote — Must

As the **application**, I want to record an absent vote when a participant misses an item, so that statistics can be computed with or without absences.

- _Given_ a participant disconnected or not yet arrived during a round, _when_ the round ends, _then_ an **absent vote** is recorded for them on that item.

### US-4.4 Reconnect to my seat — Must

As a **participant**, I want to get my seat back after a disconnection, so that I keep my ranking.

- _Given_ I was disconnected, _when_ I come back (signed in; as a guest, automatically from the same browser, or with my guest personal link from any device), _then_ I find my ranking and the current round.

### US-4.5 Join during a game — Must

As a **user** or **guest**, I want to join a game already started, so that I can play the rest of it.

- _Given_ a game in progress, late arrivals allowed (US-2.10) and a free seat, _when_ I join, _then_ I take part from the current round, and the past rounds count as **absent votes** for me.

### US-4.6 Catch up missed items — Must

As a **participant** with absent votes, I want to place the missed items during the cooldown, so that my ranking is complete.

- _Given_ items with an absent vote, _when_ the cooldown starts, _then_ they are shown apart, and I can place them in my tier list.
- _Given_ I place such an item, _then_ it gets a final placement and **keeps its absent vote** for the round (no round placement).

## E5 — Results

### US-5.1 Close and save the game — Must

As the **application**, I want to close the game at the end of the cooldown and save it for everyone, so that results are kept.

- _Given_ the cooldown is over, _then_ the game is **closed**, its rankings can no longer change, and it is saved in the history of every participant **with an account**.

### US-5.2 See the results — Must

As a **participant**, I want to see the results of the game, so that we can compare our rankings.

- _Given_ a closed game, _then_ I can see:
  - **each participant's ranking**;
  - the **overall view**: for each item, how many participants put it in each tier (and how many were absent);
  - the **median ranking**.
- _Given_ the results, _when_ I switch "with / without absent votes", _then_ the statistics are recomputed accordingly.

### US-5.3 Share the results — Must

As a **participant**, I want a public link to the results, so that I can share them.

- _Given_ a closed game, _when_ I copy its public link, _then_ any **visitor** opening it sees the results (US-5.2), read-only, without an account.
- _Given_ the room is closed later, _then_ the public link **keeps working**.

### US-5.4 Guest return — Must

As a **guest**, I want the app to remember me, so that I can get back to my seat and results without an account.

- _Given_ I joined as a guest, _when_ I come back to the room **from the same browser**, _then_ I get my seat back automatically: the browser remembers me (a cookie), as long as its data is not cleared. The app **never** uses the IP address to recognize anyone.

- _Given_ I joined as a guest, _then_ I receive a personal link, valid for a duration set by the application (**30 days max**).
- _Given_ the link has expired or the room is closed, _when_ I open it, _then_ a message says it is no longer valid; the public results link still works.
- _Given_ another device or cleared browser data, _then_ my personal link is the way back.
- _Given_ I lose it, _then_ it cannot be recovered, and my guest game cannot be attached to an account created later.

### US-5.5 History — Should

As a **user**, I want to see the games I took part in, so that I can see their results again.

- _Given_ I am signed in, _when_ I open my history, _then_ I see my closed games (template name, date, number of participants) and can open their results.
- _Given_ no game yet, _then_ an empty state is shown.
