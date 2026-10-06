# Roadmap

English | [Français](roadmap.fr.md)

In which order the [product](product.md) is built, and the technical questions to settle along the way. Today the repository contains the foundations: accounts and sign-in ([authentication.md](authentication.md)), translations ([i18n.md](i18n.md)) and emails ([emails.md](emails.md)).

Milestones are not version numbers: releases keep following [releasing.md](releasing.md). A feature gets its technical documentation (in [architecture.md](architecture.md) or its own page) once it is **implemented**, not before.

## Milestone 1 — MVP

The first playable version: a live room with friends.

- **Templates**: text and image tiles (uploaded images), **configurable tiers** (add, remove, settings).
- **Private room**: joined with a link or a code, guests allowed, **rounds run by the room admin**.
- **Private board** (no holograms).
- **Final cooldown**: players can move all their tiles again.
- **Results**: per player, overall, and the **median ranking**.

## Milestone 2 — Blind mode

Right after the MVP, and soon: blind templates, hidden tiles, admin view with the answers, reveal after each round or at the end, guessing with points (three answer modes, free text judged collectively). See [game-rules.md](game-rules.md#4-blind-mode).

## Next (order to decide)

- Public board with **holograms**.
- **Open mode** (asynchronous), then featuring on the home page.
- **Marketplace**: public templates, search, likes, favorites, forks.
- **Template sharing**: contributors and read-only.
- **Solo** mode.
- **Sound and video** tiles.
- **Animated reveal** of the results.
- **Image export** of the results.
- More **statistics** (see [game-rules.md](game-rules.md#6-statistics)).
- **Friends**, then profile statistics, badges and fun facts.
- **Moderation**: reports, admin panel, sanctions, founder views.
- **Special rank** requests.
- **Plans** and room size limits, then **payment**.
- **Notifications** (emails and in-app).
- **Chat and reactions** in rooms.
- **Public rooms**.
- **Blind open mode**.

## Much later

- **Mobile** version.
- A **Discord bot** joining the voice channel to play blind-mode sounds for everyone.
- Hidden-tile looks chosen from **presets** (blind mode).
- **Automatic criteria** for special rank requests.

## Technical questions

To settle when the related feature is designed; the decision then goes into the technical documentation.

| Topic                     | Question                                                                                                                                                                                                                 |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Real time**             | How rooms push rounds, placements and holograms to every player (e.g. WebSockets), and how it scales. The main performance risk, and the reason public rooms are postponed.                                              |
| **Hologram threshold**    | An application setting that can be raised without a rebuild: where it lives (environment, database…).                                                                                                                    |
| **Statistics**            | Live open-mode results: full recomputation or incremental update, whichever uses the fewest resources. Median ranking of ordered rankings: from the global rank (mean or median of positions)?                           |
| **Images**                | Server-side compression before storage: format (e.g. WebP), maximum size and quality; where files are stored.                                                                                                            |
| **Sound without spoiler** | A YouTube player shows the title and thumbnail, which spoils a blind test. YouTube's API rules seem to forbid separating audio from video (hidden player): to check; fallback, a small visible player or uploaded files. |
| **Template versions**     | How a game stays frozen on the template version it was played on.                                                                                                                                                        |
| **Guest links**           | Token for the guest personal link: validity (30 days max), revoked when the room closes.                                                                                                                                 |
| **Room closing**          | Inactivity delay before a room closes automatically.                                                                                                                                                                     |
| **Blind mode scoring**    | Speed bonus formula, number of attempts per item.                                                                                                                                                                        |
| **Payment**               | Payment provider; on mobile, app stores take a 15 to 30% fee.                                                                                                                                                            |
