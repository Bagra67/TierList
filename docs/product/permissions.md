# Permissions

English | [Français](permissions.fr.md)

Who can do what in TierList: on templates, in rooms, and in moderation. Vocabulary: [product.md](product.md#glossary). Game rules: [game-rules.md](game-rules.md). These permissions are not implemented yet, see [roadmap.md](roadmap.md). As for authentication, they are checked by the **backend**: hiding a button in the interface is never the security boundary.

## Roles

| Role               | Who                                                          |
| ------------------ | ------------------------------------------------------------ |
| **Template owner** | The creator of a template (or of a fork).                    |
| **Contributor**    | Someone a template was shared with, **with edit rights**.    |
| **Read-only**      | Someone a template was shared with, **without edit rights**. |
| **User**           | Any signed-in account.                                       |
| **Room admin**     | The user who created a room.                                 |
| **Player**         | A room member, signed in or guest.                           |
| **Guest**          | A player without an account.                                 |
| **Super admin**    | An application founder.                                      |

## Templates

| Action                                 | Owner | Contributor | Read-only | Other user                      |
| -------------------------------------- | :---: | :---------: | :-------: | ------------------------------- |
| Edit the template                      |  Yes  |     Yes     |    No     | No                              |
| Share it (as contributor or read-only) |  Yes  |     Yes     |    No     | No                              |
| Start a room with it                   |  Yes  |     Yes     |    Yes    | Only if the template is public  |
| Start an open mode with it             |  Yes  |     No      |    No     | No                              |
| Make it public or private              |  Yes  |     No      |    No     | No                              |
| Allow forks                            |  Yes  |     No      |    No     | No                              |
| Fork it                                |   —   |      —      |     —     | If public and forks are allowed |
| Delete it                              |  Yes  |     No      |    No     | No                              |
| Like it, add it to favorites           |   —   |      —      |     —     | If public                       |
| Report it                              |   —   |      —      |     —     | Yes                             |

A **private** template can only be used to start a room by its owner and by the people it was shared with.

## Rooms and games

| Action                                                                  |         Room admin          | Player (account) | Guest                            |
| ----------------------------------------------------------------------- | :-------------------------: | :--------------: | -------------------------------- |
| Configure the room, start a game, move to the next item, close the room |             Yes             |        No        | No                               |
| See the answers in blind mode                                           |             Yes             |        No        | No                               |
| Have the final say on a free-text guess                                 |             Yes             | Gives an opinion | Gives an opinion                 |
| Place items                                                             |    If configured to play    |       Yes        | Yes                              |
| Score guessing points (blind mode)                                      | No (votes flagged as admin) |       Yes        | Yes                              |
| Choose a nickname and profile picture                                   |             Yes             |       Yes        | Limited                          |
| Keep the game in the history                                            |             Yes             |       Yes        | No: temporary personal link only |
| Invite a friend directly                                                |             Yes             |        —         | —                                |
| Export an image of the results                                          |             Yes             |       Yes        | Yes                              |

Anyone with the **public results link** can see a closed game (see [game-rules.md](game-rules.md#links)).

The room size is limited by the **room admin's plan** (see [game-rules.md](game-rules.md#7-plans-and-limits)).

## Special rank

- Granted **on request** to creators (YouTuber, streamer…) by super admins.
- The request **must include proof**: Twitch, YouTube, Discord links…
- Later: **automatic criteria** to accept or refuse requests.
- Effect: the owner's open modes are **featured first** on the home page.

## Moderation

- Any user can **report** content.
- Every report is reviewed **by hand**, in an **admin panel** showing the number of reports and their details.
- **Super admins see everything** (founder views) and can moderate **everything**: templates, media, nicknames, games…
- Sanctions: **hide**, **delete**, **temporary ban**, **permanent ban**, **remove a purchased plan**.
