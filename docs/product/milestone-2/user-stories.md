# Milestone 2 — User stories

English | [Français](user-stories.fr.md)

What each actor can do in [milestone 2](README.md), grouped by epic. Each story has an ID, a priority and acceptance criteria written as _Given / When / Then_. Vocabulary: [product.md](../product.md#glossary). Roles: [permissions.md](../permissions.md). Points marked as assumptions in the [README](README.md#assumptions) can still change.

**Priority**: **Must** = required before templates can be public; **Should** = expected in the milestone, can slip to the next one if needed.

**Order**: epic E1 (moderation) is delivered **before** E2 (public templates) is open to users: nothing is public without a way to report and remove it.

## Actors

| Actor              | Who                                                                                  |
| ------------------ | ------------------------------------------------------------------------------------ |
| **User**           | A signed-in account.                                                                 |
| **Template owner** | The user who created a template (or a fork).                                         |
| **Visitor**        | Anyone browsing the marketplace without being signed in.                             |
| **Participant**    | A room participant, player or guest ([milestone 1](../milestone-1/user-stories.md)). |
| **Super admin**    | An application founder, who moderates.                                               |

## E1 — Moderation

### US-1.1 Super admin role — Must

As a **super admin**, I want a role that only founders have, so that moderation is reserved to them.

- _Given_ an account, _when_ the role is granted **outside the app** (a server command), _then_ the account is a super admin. No screen and no API request can grant or remove it.
- _Given_ I am a super admin, _when_ I open the app, _then_ I can reach the **moderation area**; other users do not see it.
- _Given_ any moderation action, _when_ it is requested by an account that is not a super admin, _then_ the server refuses it, whatever the interface shows.

### US-1.2 Report content — Must

As **anyone** (user, participant or visitor), I want to report a template, an image, a nickname or a game, so that super admins can remove what breaks the rules or the law.

- _Given_ a public template, a tile image, a participant's nickname or a public results page, _when_ I report it with a **reason** (and a text for "other"), _then_ the report is recorded and I see that it was sent.
- _Given_ I already reported the same content, _when_ I report it again, _then_ no second report is created, and I am told it is already reported.
- _Given_ I send many reports in a short time, _then_ the next ones are refused for a while with a message (rate limit).
- _Given_ a report, _then_ the reported person **never learns** who reported them.

### US-1.3 Handle the reports — Must

As a **super admin**, I want a queue of the open reports, so that I handle each one by hand.

- _Given_ open reports, _when_ I open the queue, _then_ I see them **grouped by content**, with the number of reports, the reasons, the content itself and its owner, the most reported first.
- _Given_ a reported content, _when_ I **dismiss** the reports, _then_ they are closed and the content stays as it is.
- _Given_ a reported content, _when_ I **hide** or **delete** it (US-1.4, US-1.5) or **sanction** its owner (US-1.8), _then_ its open reports are closed with that decision.
- _Given_ any decision, _then_ it is written to the **moderation log** (US-1.9).

### US-1.4 Hide or delete an image — Must

As a **super admin**, I want to hide or delete a tile image, so that it is no longer shown anywhere.

- _Given_ a visible image, _when_ I **hide** it with a reason, _then_ it is no longer served: everywhere it appears (templates, games in progress, past results, public links), an "image removed" visual replaces it.
- _Given_ a hidden image, _when_ I **unhide** it, _then_ it is shown again everywhere.
- _Given_ an image, _when_ I **delete** it, _then_ its file is erased for good and the "image removed" visual stays; deleting cannot be undone.
- _Given_ a deleted image, _then_ its **fingerprint** is banned: the same file, uploaded again by anyone, is refused (US-1.6).

### US-1.5 Hide or delete a template — Must

As a **super admin**, I want to hide or delete a template, so that it leaves the marketplace.

- _Given_ a public template, _when_ I **hide** it with a reason, _then_ it leaves the marketplace and its page, no new room can start with it, and games in progress **finish**.
- _Given_ a hidden template, _then_ its owner sees it marked "hidden by moderation" with the reason, can still edit it, but **cannot make it public** again.
- _Given_ a hidden template, _when_ I **unhide** it, _then_ it goes back to the state its owner chose (public or private).
- _Given_ a template, _when_ I **delete** it, _then_ it is deleted as if its owner had deleted it; the games already played keep their frozen version.

### US-1.6 Refuse banned images — Should

As a **super admin**, I want a deleted image to stay out, so that the same file cannot come back.

- _Given_ a banned fingerprint, _when_ anyone uploads the **same file**, _then_ the upload is refused with the usual "image refused" message, without saying why.
- _Later_ (not in this milestone): catch re-encoded variants of the same image.

### US-1.7 Review the recent uploads — Should

As a **super admin**, I want to see the latest uploaded images, so that I can find a problem before anyone reports it.

- _Given_ the moderation area, _when_ I open the recent uploads, _then_ I see a **paginated grid**, newest first, with the author, the date and the number of templates and games that use each image.
- _Given_ the grid, _when_ I filter by author, date or status (visible, hidden), _then_ only the matching images are shown.
- _Given_ an image, _then_ I can open its author's page (US-1.8) and the templates that use it, and hide or delete it (US-1.4).

### US-1.8 User page and sanctions — Must

As a **super admin**, I want a page per account and sanctions, so that I can stop repeated abuse.

- _Given_ an account, _when_ I open its page, _then_ I see its details (display name, email, creation date, email confirmed), its templates, its uploaded images, the reports about its content and its moderation history.
- _Given_ the page, _when_ I **hide all its images** at once, _then_ each one is hidden as in US-1.4.
- _Given_ the page, _when_ I **ban** the account **temporarily** (with an end date) or **permanently**, with a reason, _then_ it is signed out everywhere, cannot sign in until the end of the ban, and its public templates leave the marketplace for the duration of the ban.
- _Given_ a banned account, _when_ it tries to sign in, _then_ it is refused with the reason and, for a temporary ban, its end date.
- _Given_ a ban, _when_ I **lift** it, or its end date is reached, _then_ the account can sign in again and its public templates come back.
- _Given_ I am a super admin, _then_ I cannot ban myself nor another super admin.

### US-1.9 Moderation log — Must

As a **super admin**, I want every decision recorded, so that we know who did what and why.

- _Given_ any moderation action (dismiss, hide, unhide, delete, ban, lift a ban), _then_ the log records **who**, **when**, **what** (the action and its target) and **why** (the reason).
- _Given_ the moderation area, _when_ I open the log, _then_ I see the actions, newest first, and can filter them by target or by super admin.
- _Given_ the log, _then_ nobody can edit or delete an entry.

### US-1.10 See a decision about my content — Should

As a **template owner**, I want to know when moderation acted on my content, so that I understand why it is no longer shown.

- _Given_ my template or image was hidden or deleted, _when_ I open my templates, _then_ I see which one, the decision and its reason.

## E2 — Public templates

### US-2.1 Make a template public — Must

As a **template owner**, I want to make my template public, so that everyone can find and play it.

- _Given_ my private template with at least one tile, and my email is **confirmed**, _when_ I make it public, _then_ it appears in the marketplace at once.
- _Given_ my email is **not confirmed**, _when_ I try, _then_ it is refused, with a link to send the confirmation email again.
- _Given_ my template is **hidden by moderation** or my account is banned, _when_ I try, _then_ it is refused with the reason.
- _Given_ a public template, _when_ I edit it, _then_ the marketplace shows the new version; games already started keep theirs.

### US-2.2 Add tags — Must

As a **template owner**, I want to add tags to my template, so that people find it by subject.

- _Given_ my template, _when_ I add tags, _then_ they are saved, **5 at most**, each one a short word or expression; duplicates (ignoring case and accents) are merged.
- _Given_ my template, _when_ I remove a tag, _then_ it is no longer used to find the template.

### US-2.3 Make a public template private again — Must

As a **template owner**, I want to make my public template private, or delete it, so that I decide who can use it.

- _Given_ my public template, _when_ I make it private or delete it, _then_ it leaves the marketplace, no **new game** can start with it, even in a persisting room, and games **in progress** elsewhere can **finish** ([game-rules.md §8](../game-rules.md#8-templates-and-marketplace)).
- _Given_ other users liked it or added it to their favorites, _then_ it no longer appears in their favorites; it comes back if I make it public again.

### US-2.4 Start a room with a public template — Must

As a **user**, I want to start a room with someone else's public template, so that I can play it with my friends.

- _Given_ a public template, _when_ I start a room with it, _then_ the room works as in [milestone 1](../milestone-1/user-stories.md#e2--room), and I am its room admin; the template stays its owner's and I cannot edit it.
- _Given_ the template becomes private, hidden or deleted, _then_ a game in progress finishes, but my room cannot start a new game with it.
- _Given_ I am a visitor, _when_ I try to start a room, _then_ I am asked to sign in, and come back to the template afterwards.

### US-2.5 Paginate my templates — Should

As a **user** with many templates, I want my list to load in pages, so that it stays fast.

- _Given_ more templates than one page, _when_ I reach the end of the list, _then_ the next ones are loaded.

## E3 — Marketplace

### US-3.1 Browse the marketplace — Must

As **anyone**, signed in or not, I want to browse the public templates, so that I find something to play.

- _Given_ the marketplace, _when_ I open it, _then_ I see the public templates, page after page, each with its name, its owner's display name, its tags, its number of tiles and of likes, and a preview (the image of its first tile, if any).
- _Given_ no public template matches, _then_ an empty state says so.
- _Given_ a hidden template or one of a banned account, _then_ it never appears.

### US-3.2 Search and sort — Must

As **anyone**, I want to search and sort the marketplace, so that I find a template on a subject.

- _Given_ the marketplace, _when_ I type **keywords**, _then_ I see the templates whose name or tags match, ignoring case and accents.
- _Given_ the marketplace, _when_ I choose a **tag**, _then_ only the templates with that tag are shown.
- _Given_ the results, _when_ I sort by **popularity** (likes) or **newest** (date it was made public), _then_ the order changes; popularity is the default.

### US-3.3 Open a public template — Must

As **anyone**, I want to see a public template before playing it, so that I know what is in it.

- _Given_ a public template, _when_ I open its page, _then_ I see its name, owner, tags, tiers, tiles, number of likes, and, for a fork, its lineage (US-3.7).
- _Given_ the page, _then_ I can start a room (US-2.4), like it (US-3.4), add it to my favorites (US-3.5), fork it (US-3.7) or report it (US-1.2).
- _Given_ the template is no longer public, _when_ I open its link, _then_ I see that it is not available, without saying why.

### US-3.4 Like a template — Must

As a **user**, I want to like a public template, so that good templates rise in the marketplace.

- _Given_ a public template that is not mine, _when_ I like it, _then_ its number of likes goes up by one; _when_ I like it again, _then_ my like is removed.
- _Given_ my own template, _then_ I cannot like it.
- _Given_ I am a visitor, _when_ I try, _then_ I am asked to sign in.

### US-3.5 Favorites — Should

As a **user**, I want to keep public templates in my favorites, so that I find them again.

- _Given_ a public template, _when_ I add it to my favorites, _then_ it appears in **My favorites**; _when_ I remove it, _then_ it disappears.
- _Given_ a favorite that is no longer public, _then_ it is not shown, and comes back if it is public again.

### US-3.6 Allow forks — Should

As a **template owner**, I want to choose whether my public template can be forked, so that I keep control over copies.

- _Given_ my template, _when_ I allow forks, _then_ other users can fork it while it is public; forks are **not allowed** until I choose to.
- _Given_ I stop allowing forks, _then_ no new fork can be made; existing forks stay.

### US-3.7 Fork a template — Should

As a **user**, I want to fork a public template, so that I adapt it to my taste.

- _Given_ a public template whose owner allows forks, _when_ I fork it, _then_ I get a new **private** template of mine, with a copy of its tiers, tiles and tags, which I can edit like any of my templates.
- _Given_ a fork, _then_ its page and the marketplace **credit its whole lineage**: the template it was forked from, up to the original, with their owners.
- _Given_ an ancestor that became private, hidden or deleted, _then_ the lineage still shows its name, without a link.
- _Given_ the forks are not allowed, or I am a visitor, _then_ I cannot fork (a visitor is asked to sign in).
