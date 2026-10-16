# Product

English | [Français](product.fr.md)

What TierList is, who it is for, and the vocabulary used everywhere else. The detailed rules are in [game-rules.md](game-rules.md), who can do what in [permissions.md](permissions.md), and the delivery order in [roadmap.md](roadmap.md).

This page describes the **target product**. Most of it is not built yet: [roadmap.md](roadmap.md) says what comes first.

## Vision

TierList is a **community tier list** application. Instead of ranking things alone, people join a **room** and rank the same items **at the same time**: the room admin shows an item, everyone places it in their own tier list, then the results are compared (per player, overall, median ranking, fun statistics) and replayed as an animated reveal, like the end of a Gartic Phone game.

Around this live game:

- an **open mode**, where a tier list stays open for a while and everyone fills it in on their own;
- a **solo mode**, to make a tier list alone;
- a **blind mode**, where players rank items without knowing what they are (a sound, a tasting…) and try to guess them;
- a free **marketplace** of public templates.

## Glossary

| Term               | Meaning                                                                                                                                                       |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Template**       | A reusable tier list set: its tiles and its tiers. Created beforehand, private or public. Either **classic** or **blind**.                                    |
| **Tile**           | One item to rank: text, image, sound or video. A blind tile also has a hint, an answer name and an answer image.                                              |
| **Tier**           | A row of the tier list (S, A, B…). A template starts with default tiers that can be added, removed and configured.                                            |
| **Ranking**        | A player's tier list: every tile in a tier, **ordered within the tier**.                                                                                      |
| **Room**           | A lobby where players meet to play live. Joined with a link or a code. It persists between games until it is closed; then only its games are kept.            |
| **Room admin**     | The person who prepares the room, picks the template, runs the game and configures it. May play or not.                                                       |
| **Player**         | Someone taking part in a game, with an account or as a guest.                                                                                                 |
| **Guest**          | A player without an account: fewer personalization options, access to their results through a temporary link only.                                            |
| **Game**           | One play of a template in a room, from the first round to the closing. Saved for every player once closed, frozen with the template version it was played on. |
| **Round**          | One item shown by the room admin, placed by every player at the same time.                                                                                    |
| **Final cooldown** | A configurable timed phase at the end of a game where players can move all their tiles again.                                                                 |
| **Board**          | What a player sees during a game. **Private**: only their own. **Public**: everyone's placements shown as semi-transparent **holograms**.                     |
| **Absent vote**    | Recorded for an item a player missed (disconnected, joined late), so statistics can be computed with or without absences.                                     |
| **Open mode**      | A tier list open to everyone for a set duration, without a room: each person fills it in alone and submits it. Started by the template owner.                 |
| **Solo**           | A tier list made alone.                                                                                                                                       |
| **Blind mode**     | Items are hidden behind a number while being ranked, then revealed. Players can guess them to score points.                                                   |
| **Marketplace**    | The free catalog of public templates: search by tags and keywords, sort by popularity or newest, like, favorite, fork.                                        |
| **Fork**           | A copy of a template that someone else can modify, when the owner allows it. It always credits its whole lineage.                                             |
| **Super admin**    | An application founder: sees everything and moderates.                                                                                                        |
| **Special rank**   | A rank granted on request to creators (YouTuber, streamer…), whose open-mode tier lists are featured first.                                                   |
| **Plan**           | The maximum room size: free (10 players), level 2 (32 players), special (unlimited). Bought once for life; everything is free for now.                        |

## Game modes

| Mode                | Played                                     | Real time                          | Account required           | Details                                  |
| ------------------- | ------------------------------------------ | ---------------------------------- | -------------------------- | ---------------------------------------- |
| **Room**            | Together, round by round, led by the admin | Yes (holograms on a public board)  | No, guests allowed         | [Room game](game-rules.md#1-room-game)   |
| **Open mode**       | Each person alone, during a set duration   | No (results update on each submit) | Yes (prevents mass voting) | [Open mode](game-rules.md#2-open-mode)   |
| **Solo**            | Alone                                      | No                                 | Yes (saved in the history) | [Solo](game-rules.md#3-solo)             |
| **Blind** (variant) | In a room, from a blind template           | Yes                                | As for a room              | [Blind mode](game-rules.md#4-blind-mode) |

## Platforms

The web application comes first. A **mobile** version (touch drag and drop, small screens) is planned much later.
