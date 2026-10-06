# Milestone 1 — Game flow

English | [Français](game-flow.fr.md)

Who does what, and in which order, in [milestone 1](README.md): from creating a template to sharing the results. The diagrams show **business exchanges** between the actors and the application, not technical calls. States: [lifecycles.md](lifecycles.md). Stories: [user-stories.md](user-stories.md).

Actors: **Admin** (room admin, here also the template owner), **Player** (participant with an account), **Guest** (participant without an account), **Visitor** (anyone with the public link), **App** (TierList).

## 1. Prepare a template

```mermaid
sequenceDiagram
    actor Admin
    participant App
    Admin->>App: Create a template "Chips" (US-1.1)
    App-->>Admin: Private template, tiers S A B C D E, no tile
    loop For each item (32 max)
        Admin->>App: Add a tile: text and/or image (US-1.2)
        App->>App: Compress the image
        App-->>Admin: Tile added at the end
    end
    Admin->>App: Rename, recolor, reorder tiers (US-1.4)
    Admin->>App: Reorder tiles (US-1.3)
```

## 2. Create a room and gather the players

```mermaid
sequenceDiagram
    actor Admin
    actor Player
    actor Guest
    participant App
    Admin->>App: Create a room from "Chips" (US-2.1)
    App-->>Admin: Room open: link + code
    Admin->>App: Settings: random order, timer 30 s, cooldown 60 s, I play (US-2.2)
    Admin-->>Player: Shares the link (outside the app)
    Admin-->>Guest: Shares the code (outside the app)
    Player->>App: Open the link, signed in (US-2.4)
    App-->>Player: Seat in the room, shown with display name
    Guest->>App: Type the code and a nickname (US-2.5)
    App-->>Guest: Seat in the room + guest personal link
    App-->>Admin: Lobby updated: 3 participants out of 10
```

## 3. Play the rounds

```mermaid
sequenceDiagram
    actor Admin
    actor Player
    actor Guest
    participant App
    Admin->>App: Start the game (US-3.1)
    App->>App: Freeze the template, shuffle the items
    loop For each item
        App-->>Admin: Item n out of N (+ timer)
        App-->>Player: Item n out of N (+ timer)
        App-->>Guest: Item n out of N (+ timer)
        Player->>App: Drop the item in tier A, position 2 (US-3.3)
        App-->>Admin: Player has placed (not where)
        Guest->>App: Drop the item in tier S, position 1
        App-->>Admin: Guest has placed
        alt Room admin clicks next
            Admin->>App: Next (US-3.4)
        else Timer is up
            App->>App: End the round
        else Everyone connected has placed
            App->>App: End the round
        end
        App->>App: Absent vote for whoever has not placed (US-4.3)
    end
    App-->>Admin: Final cooldown starts
```

## 4. Disconnection, late arrival and catching up

```mermaid
sequenceDiagram
    actor Guest
    actor Late as Late player
    participant App
    Note over Guest,App: Round 3 in progress
    Guest--xApp: Connection lost
    App->>App: Round 3 ends: absent vote for Guest
    Guest->>App: Open the guest personal link (US-4.4)
    App-->>Guest: Same seat, same ranking, round 4
    Late->>App: Join during round 5 (US-4.5)
    App-->>Late: Seat, rounds 1 to 4 count as absent
    Note over Guest,App: Final cooldown
    App-->>Guest: Missed item 3 shown apart (US-4.6)
    Guest->>App: Place item 3 in tier B
    App-->>Late: Missed items 1 to 4 shown apart
    Late->>App: Place them
```

## 5. Cooldown, closing and results

```mermaid
sequenceDiagram
    actor Admin
    actor Player
    actor Visitor
    participant App
    App-->>Player: Cooldown: countdown, every tile movable (US-4.1)
    Player->>App: Move item 7 from C to A
    App->>App: Keep the round placement (C) and the final one (A) (US-4.2)
    alt Time is up
        App->>App: End the cooldown
    else Room admin ends it
        Admin->>App: End the cooldown
    end
    App->>App: Close and save the game (US-5.1)
    App-->>Admin: Results + public link, room back to open
    App-->>Player: Results: each ranking, overall view, median (US-5.2)
    Player-->>Visitor: Shares the public link (outside the app)
    Visitor->>App: Open the public link (US-5.3)
    App-->>Visitor: Results, read-only
    Admin->>App: Start a new game in the same room (US-2.9)
```
