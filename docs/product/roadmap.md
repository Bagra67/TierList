# Roadmap

English | [Français](roadmap.fr.md)

In which order the [product](product.md) is built, and the technical questions to settle along the way. Milestone 1 (MVP) is **done**: it is in production since v1.0.0 ([deployment guide](../technical/deployment.md)). Public content comes next (milestones 2 and 3), then blind mode (milestone 4).

Milestones are not version numbers: releases keep following [releasing.md](../technical/releasing.md). A feature gets its technical documentation (in [architecture.md](../technical/architecture.md) or its own page under `docs/technical/`) once it is **implemented**, not before.

## Milestone 1 — MVP

The first playable version: a live room with friends.

**Done**: every user story is delivered ([GitHub milestone](https://github.com/Bagra67/TierList/milestone/1?closed=1)).

- **Templates**: text and image tiles (uploaded images), **configurable tiers** (add, remove, settings).
- **Private room**: joined with a link or a code, guests allowed, **rounds run by the room admin**.
- **Private board** (no holograms).
- **Final cooldown**: players can move all their tiles again.
- **Results**: per player, overall, and the **median ranking**.
- **Absent players**: absent votes, reconnection, catching up during the final cooldown.
- **Persisting room**: new games in the same room, closed by the room admin or after inactivity.
- **Links**: public results link, guest personal link.
- **Free plan limits**: 10 players per room, 32 tiles per template.

Detailed design (user stories, domain model, lifecycles, game flow, wireframes): [milestone-1/](milestone-1/README.md).

## Milestone 2 — Public templates

The next milestone: templates that everyone can see and play. Public content needs moderation first.

- **Moderation foundation**: super admin role checked server-side ([#123](https://github.com/Bagra67/TierList/issues/123)), reports with a super admin queue, which is also the notice mechanism for illegal content ([#126](https://github.com/Bagra67/TierList/issues/126)), hide or delete an image ([#124](https://github.com/Bagra67/TierList/issues/124)), review of the recent uploads ([#125](https://github.com/Bagra67/TierList/issues/125)). See [permissions.md](permissions.md#moderation).
- **Marketplace**: public templates, search by tags and keywords, sort by popularity or newest, likes, favorites, forks; a paginated list ([#105](https://github.com/Bagra67/TierList/issues/105)). See [game-rules.md](game-rules.md#8-templates-and-marketplace).
- The **privacy policy** changes with it: other users see public templates and their images.

## Milestone 3 — Open mode and home page

- **Open mode** (asynchronous): each person ranks a template alone, during a set duration, with an account. See [game-rules.md](game-rules.md#2-open-mode).
- **Featuring on the home page**, with the results and statistics of the whole crowd, updated live.
- More **statistics** ([#133](https://github.com/Bagra67/TierList/issues/133), [game-rules.md](game-rules.md#6-statistics)).

## Milestone 4 — Blind mode

Blind templates, hidden tiles, admin view with the answers, reveal after each round or at the end, guessing with points (three answer modes, free text judged collectively). See [game-rules.md](game-rules.md#4-blind-mode).

## Next (order to decide)

- Public board with **holograms**.
- **Template sharing**: contributors and read-only.
- **Solo** mode.
- **Sound and video** tiles.
- **Animated reveal** of the results, item by item, with who placed it where (the MVP already shows the tier list appearing tier by tier).
- **Image export** of the results.
- **Friends**, then profile statistics, badges and fun facts.
- **Moderation**, beyond the milestone 2 foundation: sanctions, admin panel, founder views.
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

| Topic                     | Question                                                                                                                                                                                                                                      |
| ------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Real time**             | How rooms push rounds, placements and holograms to every player (e.g. WebSockets), and how it scales. The main performance risk, and the reason public rooms are postponed. **Decided**: see the [real-time guide](../technical/realtime.md). |
| **Hologram threshold**    | An application setting that can be raised without a rebuild: where it lives (environment, database…).                                                                                                                                         |
| **Statistics**            | Live open-mode results: full recomputation or incremental update, whichever uses the fewest resources. Median ranking of ordered rankings: **decided**, see the [results guide](../technical/results.md).                                     |
| **Images**                | Server-side compression before storage: format (e.g. WebP), maximum size and quality; where files are stored. **Decided**: see the [images guide](../technical/images.md).                                                                    |
| **Sound without spoiler** | A YouTube player shows the title and thumbnail, which spoils a blind test. YouTube's API rules seem to forbid separating audio from video (hidden player): to check; fallback, a small visible player or uploaded files.                      |
| **Template versions**     | How a game stays frozen on the template version it was played on. **Decided**: see the [templates guide](../technical/templates.md#24-snapshots-template-versions).                                                                           |
| **Guest links**           | Token for the guest personal link: validity (30 days max), revoked when the room closes. **Decided**: see the [rooms guide](../technical/rooms.md#24-guests).                                                                                 |
| **Room closing**          | Inactivity delay before a room closes automatically. **Decided**: 24 hours without change and nobody connected, see the [rooms guide](../technical/rooms.md#26-closing-a-room).                                                               |
| **Blind mode scoring**    | Speed bonus formula, number of attempts per item.                                                                                                                                                                                             |
| **Payment**               | Payment provider; on mobile, app stores take a 15 to 30% fee.                                                                                                                                                                                 |
