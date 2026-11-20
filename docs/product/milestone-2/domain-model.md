# Milestone 2 — Domain model

The business concepts that [milestone 2](README.md) adds or changes, their relations and the rules they must always respect. The concepts of [milestone 1](../milestone-1/domain-model.md) (rooms, games, placements…) do not change. This is a **conceptual** model: it names what the product manipulates, not how it is stored.

## Class diagram

```mermaid
classDiagram
    direction LR

    class User {
        display name
        role: user | super admin
        email confirmed
    }
    class Sanction {
        kind: temporary ban | permanent ban
        reason
        ends at
        lifted at
    }
    class Template {
        name
        visibility: private | public
        made public at
        forks allowed
        moderation: none | hidden
        official
        featured at
    }
    class Tag {
        word
    }
    class Tile {
        text
        order
    }
    class Image {
        status: visible | hidden | deleted
        fingerprint
        uploaded at
    }
    class BannedFingerprint {
        fingerprint
    }
    class Like
    class Favorite
    class Report {
        target: template | image | nickname | game
        reason
        text
        status: open | dismissed | actioned
    }
    class ModerationAction {
        action
        target
        reason, if any
        at
    }

    User "1" --> "0..*" Template : owns
    Template "0..*" --> "0..1" Template : forked from
    Template "1" *-- "0..5" Tag : tagged with
    Template "1" *-- "0..32" Tile : has
    Tile "0..*" --> "0..1" Image : shows
    User "0..1" --> "0..*" Image : uploaded
    Image "0..1" --> "0..1" BannedFingerprint : banned as
    User "1" --> "0..*" Like : gives
    Like "0..*" --> "1" Template : on
    User "1" --> "0..*" Favorite : keeps
    Favorite "0..*" --> "1" Template : of
    Report "0..*" --> "0..1" User : sent by
    User "1" --> "0..*" Sanction : receives
    ModerationAction "0..*" --> "1" User : taken by super admin
    ModerationAction "0..1" --> "0..*" Report : closes
```

## Concepts

| Concept               | Meaning                                                                                                                                                                                                                                                                                                                                                                                                    |
| --------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **User**              | An account. Gains a **role** (user or super admin, granted outside the app) and uses its **confirmed email** to publish.                                                                                                                                                                                                                                                                                   |
| **Sanction**          | A ban of an account by a super admin: **temporary** (with an end date) or **permanent**, with a reason. It can be lifted.                                                                                                                                                                                                                                                                                  |
| **Template**          | Gains a **visibility** (private or public), the date it was made public, whether **forks are allowed**, a **moderation** state, and the template it was **forked from**, if any. An **official** template is owned by the site's account « TierList » and edited by the super admins; a draft is a private official template, and a published official template can be **featured** in the TierList picks. |
| **Tag**               | A word or short expression chosen by the owner, used to find the template. Compared without case or accents.                                                                                                                                                                                                                                                                                               |
| **Image**             | The uploaded file of a tile (already stored compressed). Gains a moderation **status** and a **fingerprint** of the file.                                                                                                                                                                                                                                                                                  |
| **BannedFingerprint** | The fingerprint of a deleted image: the same file is refused at upload.                                                                                                                                                                                                                                                                                                                                    |
| **Like**              | A user's like of a public template. The number of likes is the template's **popularity**.                                                                                                                                                                                                                                                                                                                  |
| **Favorite**          | A public template a user keeps to find it again.                                                                                                                                                                                                                                                                                                                                                           |
| **Report**            | A report sent by anyone about a template, an image, a nickname or a game, with a reason. Sent by an account, or anonymously by a guest or a visitor (rate limited).                                                                                                                                                                                                                                        |
| **ModerationAction**  | One entry of the **moderation log**: which super admin did what, on what, when and why. It may close reports. The editorial actions on official templates (create, edit, publish, unpublish, feature, unfeature) have no reason.                                                                                                                                                                           |

The **marketplace** is not a concept of its own: it is the list of the templates that are **listed** (invariant 2), searched and sorted.

The site's account « TierList » is a **User** of its own: a system account that owns the official templates. Nobody can sign in to it and it cannot be banned. The diagram shows the player limits; an official template has up to 256 tiles and 20 tags.

## Invariants

Rules the model always respects, whatever the screen or the action:

1. Only a **super admin** can take a moderation action; the role is never granted by the app.
2. A template is **listed** in the marketplace if and only if it is **public**, **not hidden** by moderation, **not deleted**, and its owner is **not banned**.
3. A template can be made public only by its **owner**, whose email is **confirmed**, and only if it is not hidden by moderation. An official template is published by a **super admin** instead, only if it has tiles and is not hidden; only a published official template that is not hidden can be featured.
4. A template has **at most 5 tags** (20 for an official template) of **30 characters at most**, without duplicates (ignoring case and accents).
5. A user has **at most one like** and **at most one favorite** per template, and never likes their own template.
6. Likes and favorites are **shown** only while their template is listed; they are kept otherwise.
7. A template can be forked only while it is **listed** and its owner **allows forks**. A fork starts **private**, owned by the person who forked it, and keeps the template it was forked from **forever**, even if that template becomes private, hidden or deleted.
8. A game is played on a **snapshot** (milestone 1): making a template private, hiding it or deleting it never changes a game already started.
9. A **hidden** or **deleted** image is never served: an "image removed" visual replaces it everywhere. A deleted image's file is gone for good.
10. An image whose fingerprint is **banned** cannot be uploaded.
11. A **banned** account cannot sign in while its ban is active; a super admin, and the site's account, can never be banned.
12. A content has **at most one open report** per reporter (an account, or a guest's or visitor's browser).
13. Every moderation action, and every editorial action on an official template, is written to the **log**, and log entries are never edited or deleted.
14. An official template is edited by **one super admin at a time**.
