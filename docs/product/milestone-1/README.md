# Milestone 1 — MVP

English | [Français](README.fr.md)

The design of the first playable version of TierList: **a live private room with friends**. It details, for this milestone only, what [roadmap.md](../roadmap.md#milestone-1--mvp) lists, using the vocabulary of [product.md](../product.md#glossary) and the rules of [game-rules.md](../game-rules.md).

This is **business design**, not technical documentation: no tables, endpoints or real-time protocol. Those are written in `docs/technical/` once implemented.

## Pages

| Page                            | Content                                                                              |
| ------------------------------- | ------------------------------------------------------------------------------------ |
| [User stories](user-stories.md) | What each actor can do, with acceptance criteria, grouped by epic.                   |
| [Domain model](domain-model.md) | The business concepts, their relations and their invariants (class diagram).         |
| [Lifecycles](lifecycles.md)     | The states of a room, a game, a round and a participant (state diagrams).            |
| [Game flow](game-flow.md)       | Who does what, in which order, from the template to the results (sequence diagrams). |
| [Screens](screens.md)           | Low-fidelity wireframes of each screen, with the stories they cover.                 |

## Scope

### Included

- **Templates**: private, text and image tiles (uploaded images, compressed by the server), **default tiers S, A, B, C, D, E**, which can be added, removed, renamed, recolored and reordered.
- **Private room**: created from one of your templates, joined with a **link** or a **code**, with an account or as a **guest**.
- **Room settings**: item order (template or random), automatic move to the next item (timer or everyone done; manual is always possible), final cooldown duration, whether the room admin plays.
- **Game**: rounds run by the room admin, **private board**, ordered rankings.
- **Final cooldown**: move all your tiles again; both placements are kept.
- **Absent players**: absent votes, reconnection to your seat, catching up missed items during the cooldown.
- **Persisting room**: start a new game in the same room; closed by the room admin or after inactivity.
- **Results**: per player, overall (distribution per item), **median ranking**, with or without absent votes.
- **Links**: public results link; guest personal link (30 days max, dead once the room is closed).
- **History** of games for accounts.
- **Free plan limits**: **10 players** per room, **32 tiles** per template.

### Not included

Planned for later milestones ([roadmap.md](../roadmap.md)): public board and holograms, open mode, solo, blind mode, marketplace and public templates, template sharing, sound and video tiles, animated reveal, image export, profile pictures, friends, moderation, plans and payment, chat and reactions, mobile.

## Assumptions

Points not decided yet, taken as the simplest option for this milestone. Each one can be revisited.

- **Results are visible once the game is closed** (the "before or after closing" setting comes later).
- **Nobody has a profile picture** in this milestone: participants are shown by their display name (account) or nickname (guest).
- **Durations** (timer per item, cooldown, inactivity before closing, guest link validity) are room settings or application settings whose default values are chosen at implementation.
- **How statistics are computed** (median of ordered rankings, effect of absent votes) is decided at implementation (see [roadmap.md](../roadmap.md#technical-questions)).
