# Milestone 2 — Public templates

English | [Français](README.fr.md)

The design of the second milestone of TierList: **templates that everyone can see and play**, and the **moderation** that public content needs first. It details, for this milestone only, what [roadmap.md](../roadmap.md#milestone-2--public-templates) lists, using the vocabulary of [product.md](../product.md#glossary), the rules of [game-rules.md](../game-rules.md#8-templates-and-marketplace) and the roles of [permissions.md](../permissions.md).

**Status: designed.** The stories are tracked in the [GitHub milestone](https://github.com/Bagra67/TierList/milestone/3).

This is **business design**, not technical documentation: no tables, endpoints or storage details. Those are written in `docs/technical/` once implemented.

## Pages

| Page                            | Content                                                                            |
| ------------------------------- | ---------------------------------------------------------------------------------- |
| [User stories](user-stories.md) | What each actor can do, with acceptance criteria, grouped by epic.                 |
| [Domain model](domain-model.md) | The new business concepts, their relations and their invariants (class diagram).   |
| [Lifecycles](lifecycles.md)     | The states of a template, an image, a report and an account (state diagrams).      |
| [Screens](screens.md)           | Wireframes of the new screens on the visual identity, with the stories they cover. |

The same screens, as editable mockups, are on the [design canvas "TierList — Écrans"](https://claude.ai/artifact/EYMsS8K3Yj5fAjXGgj9t5d) (claude.ai, private to its owner, shared on request), page "Jalon 2". They are drafts: the stories are the reference.

## Scope

### Included

- **Moderation foundation**, before anything is public:
  - a **super admin** role, granted outside the app and checked server-side;
  - **reports** on a template, an image, a nickname or a game, open to everyone, with a super admin **queue**; it is also the notice mechanism for illegal content;
  - **hide**, unhide or **delete** an image or a template; **banned fingerprints** so that a deleted image cannot be uploaded again;
  - a **review of the recent uploads**;
  - a **user page** for super admins and **account sanctions**: temporary and permanent ban;
  - a **moderation log** of every decision.
- **Public templates**: the owner makes a template public or private again; only an account with a **confirmed email** can publish.
- **Marketplace**: browsing **without an account** (read only), search by **keywords** and **tags**, sort by **popularity** or **newest**, a page per public template, **likes**, **favorites**, **forks** allowed by the owner and crediting their whole lineage.
- **Rooms on someone else's template**: any user can start a room with a public template.
- **Pagination** of the marketplace and of _My templates_.

### Not included

Planned for later milestones ([roadmap.md](../roadmap.md)): open mode and the home page featuring (milestone 3), blind mode (milestone 4), template sharing with contributors, profiles and friends, notifications by email, removing a purchased plan, automatic NSFW detection, the super admin view of deleted templates, special ranks.

## Decided

Product decisions taken when designing this milestone (2026-10-31):

- **Order**: public content comes before blind mode, so that the marketplace and the open mode bring new players.
- **Whole marketplace** of [game-rules.md §8](../game-rules.md#8-templates-and-marketplace): search, sort, likes, favorites and forks.
- **Moderation after publication**: a template is public as soon as its owner publishes it, if the account email is confirmed. Reports and the review of uploads are the safety net.
- **Visitors** without an account can browse the marketplace and open a public template; liking, adding to favorites, forking and starting a room need an account.
- **Account sanctions** (temporary and permanent ban) are part of this milestone.
- **Wording** (validated on the mockups): the marketplace is called _modèles publics_ / _public templates_ in the interface, and a fork _copier dans mes modèles_ / _copy to my templates_ ([i18n guide](../../technical/i18n.md#vocabulary)). The header gets a _Modèles publics_ link for everyone, and a _Modération_ link with the number of open reports for super admins only.

## Assumptions

Points not decided yet, taken as the simplest option for this milestone. Each one can be revisited before its story is implemented.

- **Popularity** is the number of likes.
- **Tags** are free words chosen by the owner, **5 at most** per template, compared without case or accents.
- **Forks are not allowed** until the owner allows them. A fork is a new **private** template of the person who forks it; it keeps its lineage even if an ancestor becomes private or is deleted (the ancestor is then shown without a link).
- **Likes and favorites** of a template that becomes private or is hidden are kept but not shown; they come back if it is public again.
- **Report reasons**: illegal content, sexual content, violence or hate, harassment, spam, other (with a text). Anyone can report, guests and visitors included, with a rate limit.
- A template **hidden by moderation** leaves the marketplace, its owner sees why, and cannot make it public again until a super admin unhides it. Games in progress finish, as for a template made private ([game-rules.md §8](../game-rules.md#8-templates-and-marketplace)).
- A **banned account** is signed out everywhere and cannot sign in until the end of the ban; its public templates leave the marketplace for the duration of the ban.
- The person affected by a decision sees it **in the app**, with its reason (no email: notifications come later).
- The **privacy policy** is updated with the stories that change what other users see (public templates, owner name on the marketplace) and with the reports and the moderation log (new personal data).
