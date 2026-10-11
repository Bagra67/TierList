# Salles

[English](rooms.md) | Français

Comment les salles sont créées, lues et configurées par l'API : modèle de données, code et lien, réglages, endpoints, le lobby, et où cela se trouve dans le code. **Construit dans #83** (API) et **#84** (écrans, §3). Ce qu'est une salle pour l'utilisateur : [user stories](../product/milestone-1/user-stories.fr.md) US-2.1 et US-2.2, [cycles de vie](../product/milestone-1/lifecycles.fr.md).

## 1. Vue fonctionnelle

Une salle est le lieu où un groupe joue, rejoint par son **code** ou son **lien**. Elle est créée à partir d'un des templates de l'utilisateur, qui en devient le **room admin**. Ses **réglages** s'appliquent à la partie suivante.

| Action                | Endpoint                       | Résultat                                                                                                                |
| --------------------- | ------------------------------ | ----------------------------------------------------------------------------------------------------------------------- |
| Créer une salle       | `POST /rooms`                  | Une salle ouverte sur un de mes templates qui a au moins une tuile ; j'en suis le room admin et le premier participant. |
| Ouvrir une salle      | `GET /rooms/{code}`            | La salle, ses réglages et ses participants, pour un participant.                                                        |
| Modifier les réglages | `PATCH /rooms/{code}/settings` | Les nouveaux réglages (room admin seulement) ; pendant une partie, seulement les arrivées.                              |

### Règles

- **Template** : un des miens, non supprimé, avec **au moins une tuile** (US-2.1). Sinon `404` `template_not_found` ou `409` `template_has_no_tiles`. Plusieurs salles peuvent utiliser le même template.
- **Code** : 6 caractères parmi `ABCDEFGHJKLMNPQRSTUVWXYZ23456789` (sans `0`, `O`, `1`, `I`, qu'on confond en lisant ou en dictant), aléatoire (`secrets`), unique. Il est lu sans tenir compte de la casse : `k7p2qx` ouvre `K7P2QX`.
- **Lien** : `FRONTEND_BASE_URL` + `/r/` + le code, par ex. `http://localhost:5173/r/K7P2QX`. La page elle-même arrive avec #84.
- **Room admin** : le créateur. Il a aussitôt une ligne **participant** : il compte dans la limite de participants même s'il ne joue pas (US-2.6).
- **Visibilité** : une salle n'est visible que de ses **participants**. Les autres reçoivent `404` `room_not_found`, exactement comme pour un code inconnu : l'API ne révèle jamais qu'une salle existe. Rejoindre une salle arrive avec #86.
- **Réglages** (US-2.2), avec leurs valeurs par défaut :

  | Réglage                 | Valeurs                            | Défaut                          |
  | ----------------------- | ---------------------------------- | ------------------------------- |
  | `item_order`            | `template`, `random`               | `template`                      |
  | `auto_advance`          | `none`, `timer`, `everyone_placed` | `none` (manuel seulement)       |
  | `timer_seconds`         | 5 à 300 s                          | `ROOM_DEFAULT_TIMER_SECONDS`    |
  | `cooldown_seconds`      | 10 à 600 s                         | `ROOM_DEFAULT_COOLDOWN_SECONDS` |
  | `admin_plays`           | `true`, `false`                    | `true`                          |
  | `late_arrivals_allowed` | `true`, `false`                    | `true`                          |

  `timer_seconds` est gardé même quand `auto_advance` n'est pas `timer` : la durée choisie revient si le timer est remis.

- **Seul le room admin** modifie les réglages (`403` `room_admin_required` pour un autre participant ; [permissions](../product/permissions.fr.md)).
- **Pendant une partie** (statut `playing`), les réglages sont bloqués, **sauf les arrivées** (US-2.10) : tout autre champ répond `409` `room_settings_locked`.
- **Modification vide** : un `PATCH` sans aucun champ (ou avec seulement des valeurs `null`) ne change rien.
- **Suppressions** : la purge d'un template supprimé garde la salle, sans template (`template: null`) ; aucune nouvelle partie ne peut alors y démarrer. La suppression du compte du room admin supprime ses salles et leurs participants.

### Messages

L'API renvoie un **code** d'erreur ; le frontend le traduit (`errors.api.*` et `errors.field.*` dans `frontend/src/i18n/locales/`).

| Situation                                                  | HTTP | Code API                                                                                | Traduction (FR / EN)                                                                                                    |
| ---------------------------------------------------------- | ---- | --------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| Template inconnu, supprimé ou d'un autre utilisateur       | 404  | `template_not_found`                                                                    | `Ce template est introuvable.` / `This template could not be found.`                                                    |
| Template sans tuile                                        | 409  | `template_has_no_tiles`                                                                 | `Ajoutez au moins une tuile à ce template pour jouer avec.` / `Add at least one tile to this template to play with it.` |
| Salle inconnue, ou l'utilisateur n'y a pas de place        | 404  | `room_not_found`                                                                        | `Cette salle est introuvable ou a été fermée.` / `This room could not be found or has been closed.`                     |
| Réglages modifiés par un participant qui n'est pas l'admin | 403  | `room_admin_required`                                                                   | `Seul le room admin peut faire cela.` / `Only the room admin can do this.`                                              |
| Réglage autre que les arrivées pendant une partie          | 409  | `room_settings_locked`                                                                  | `Pendant une partie, seules les arrivées peuvent être modifiées.` / `During a game, only late arrivals can be changed.` |
| Durée hors bornes                                          | 422  | `validation_error`, champ `greater_than_equal` / `less_than_equal` (params `ge` / `le`) | `Au moins {{ge}}.` / `At least {{ge}}.`, `Au plus {{le}}.` / `At most {{le}}.`                                          |
| Valeur de réglage inconnue                                 | 422  | `validation_error`                                                                      | `Certains champs sont invalides.` / `Some fields are invalid.`                                                          |
| Access token absent ou invalide                            | 401  | `not_authenticated`                                                                     | Géré par le client API : rafraîchissement de la session, sinon retour à `/login`                                        |

## 2. Conception technique

### 2.1 Options considérées

| Sujet            | Options                                                                 | Choix et raison                                                                                                                                                                                                                        |
| ---------------- | ----------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Réglages         | Table `room_settings` séparée (1-1) ; **colonnes de `rooms`**           | **Colonnes** : le modèle de domaine en fait une composition 1-1 de la salle ; des colonnes évitent une jointure et une ligne orpheline. L'API les regroupe quand même dans un objet `settings`.                                        |
| Verrou de partie | Attendre les parties (#91) ; **`status` open / playing dès maintenant** | **Statut dès maintenant** : la règle « bloqué pendant une partie » est construite et testée avec les réglages ; le démarrage (#91) ne fait que poser `playing`. « Fermée » n'est pas un statut : une salle fermée est supprimée (#89). |
| Code             | Séquentiel ; UUID ; **code court aléatoire**                            | **Code court aléatoire** : tapé ou dicté par les joueurs, impossible à deviner à partir d'autres codes. Une contrainte d'unicité et un nouveau tirage en cas de collision le gardent unique.                                           |
| Place de l'admin | Rôle seulement dans `rooms.admin_id` ; **ligne participant aussi**      | **Ligne participant** : l'admin compte dans la limite de participants même s'il ne joue pas (US-2.6), et sa place lui donne accès comme à tout participant.                                                                            |
| Adressage        | Par UUID ; **par code**                                                 | **Par code** : le [guide du temps réel](realtime.fr.md) adresse le canal de la salle et son instantané REST par code (`/rooms/{code}`).                                                                                                |

### 2.2 Modèle de données

```
users ──< rooms ──< participants >── users
            │
            └──> templates (SET NULL)
```

| Table          | Colonnes                                                                                                                                                                                                           | Remarques                                                                                                                                                                                                                                   |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `rooms`        | `id`, `code` (6, unique), `admin_id` → `users`, `template_id` → `templates` (nullable), `status`, `item_order`, `auto_advance`, `timer_seconds`, `cooldown_seconds`, `admin_plays`, `late_arrivals_allowed`, dates | `ON DELETE CASCADE` vers `users`, `ON DELETE SET NULL` vers `templates` ; index sur `admin_id` et `template_id`. `status`, `item_order`, `auto_advance` : colonnes texte avec une contrainte `CHECK` (`ck_rooms_*`), comme `images.status`. |
| `participants` | `id`, `room_id` → `rooms`, `user_id` → `users`, dates                                                                                                                                                              | `ON DELETE CASCADE` vers les deux. Unique `(room_id, user_id)` : une place par utilisateur et par salle (invariant 10) ; sert aussi d'index sur `room_id`. Index sur `user_id`.                                                             |

Les issues voisines ajoutent leurs propres colonnes : `connected` et la version de la salle pour le temps réel (#85), les champs des invités (#87, `user_id` devient nullable), et #89 gardera les participants des parties passées à la fermeture d'une salle.

### 2.3 Génération du code

`generate_room_code()` (`app/services/rooms.py`) tire `ROOM_CODE_LENGTH` caractères de `ROOM_CODE_ALPHABET` avec `secrets.choice`. `RoomService.create` insère la salle dans un **savepoint** (`session.begin_nested()`) : quand l'insertion viole la contrainte d'unicité `uq_rooms_code`, seul le savepoint est annulé et un nouveau code est tiré, jusqu'à `ROOM_CODE_MAX_ATTEMPTS` (5) fois. Avec 32^6 (environ un milliard) de codes, une seule collision est déjà rare ; atteindre la limite est journalisé comme une erreur et répond `500`. Toute autre erreur d'intégrité remonte telle quelle.

### 2.4 Réglages

| Variable                        | Rôle                                                        | Défaut |
| ------------------------------- | ----------------------------------------------------------- | ------ |
| `ROOM_DEFAULT_TIMER_SECONDS`    | Timer par item d'une nouvelle salle, en secondes (5 à 300)  | `30`   |
| `ROOM_DEFAULT_COOLDOWN_SECONDS` | Cooldown final d'une nouvelle salle, en secondes (10 à 600) | `60`   |

Les bornes sont des constantes (`app/constants/rooms.py`) : l'API valide les durées avec elles et les renvoie en params `ge` / `le`, que le frontend affiche sans les recopier. Les valeurs par défaut sont validées avec les mêmes bornes au démarrage de l'application.

### 2.5 Endpoints

Chaque route exige l'access token Bearer (`401` sinon).

| Méthode et chemin              | Corps                                                                                                   | Succès               | Erreurs                           |
| ------------------------------ | ------------------------------------------------------------------------------------------------------- | -------------------- | --------------------------------- |
| `POST /rooms`                  | `{template_id}`                                                                                         | `201` `RoomResponse` | `401`, `404`, `409`, `422`        |
| `GET /rooms/{code}`            | —                                                                                                       | `200` `RoomResponse` | `401`, `404`                      |
| `PATCH /rooms/{code}/settings` | `{item_order?, auto_advance?, timer_seconds?, cooldown_seconds?, admin_plays?, late_arrivals_allowed?}` | `200` `RoomResponse` | `401`, `403`, `404`, `409`, `422` |

- `RoomResponse` vaut `{code, link, status, template: {id, name} | null, settings: {item_order, auto_advance, timer_seconds, cooldown_seconds, admin_plays, late_arrivals_allowed}, participants: [{id, display_name, is_admin}], is_admin}`. `participants` sont dans l'ordre d'arrivée, le room admin d'abord ; `is_admin` indique si l'utilisateur qui fait la requête est le room admin.
- `PATCH /rooms/{code}/settings` verrouille la ligne de la salle (`SELECT … FOR UPDATE`) jusqu'à son commit, comme le [guide du temps réel](realtime.fr.md) le demande pour toute modification d'une salle.

### 2.6 Limites connues

- Seul le room admin a une place : rejoindre avec un compte (#86) ou en invité (#87) arrive plus tard, ainsi que la limite de participants (#88).
- Pas encore de mises à jour en direct : le canal de la salle et la présence arrivent avec #85 ; d'ici là, le lobby est relu quand l'onglet reprend le focus.
- Pas encore de partie : le démarrage (#91) pose `playing` et fige le template (`take_snapshot`, [guide des templates](templates.fr.md) §2.4).
- La fermeture d'une salle (#89) et sa fermeture automatique en cas d'inactivité (#90) arrivent plus tard.

## 3. Dans le code

### Backend (`backend/app/`)

| Couche        | Fichier                                                                   | Contenu                                                                                                                                                                                                                               |
| ------------- | ------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Routes        | `api/routes/rooms.py`                                                     | Les routes `/rooms` ; traduisent les exceptions métier en `404` `template_not_found` / `room_not_found`, `409` `template_has_no_tiles` / `room_settings_locked`, `403` `room_admin_required` ; `_room_response` construit la réponse. |
| Dépendances   | `api/dependencies.py`                                                     | `get_room_service`.                                                                                                                                                                                                                   |
| Schémas       | `schemas/rooms.py`                                                        | `CreateRoomRequest`, `UpdateRoomSettingsRequest` (`TimerSeconds`, `CooldownSeconds` avec leurs bornes), `RoomSettingsResponse`, `RoomTemplateResponse`, `ParticipantResponse`, `RoomResponse`.                                        |
| Service       | `services/rooms.py`                                                       | `generate_room_code` ; `RoomService` : `create` (nouveau tirage en cas de collision, `_insert_unless_code_taken`), `get`, `update_settings` (verrouillé), `link`. Porte les transactions (`commit`).                                  |
| Repository    | `repositories/rooms.py`                                                   | `add_room`, `get_room_by_code` (avec le template et les participants, verrouillé avec `for_update`).                                                                                                                                  |
| Modèles       | `models/room.py`, `models/participant.py`                                 | `Room` avec `RoomStatus`, `ItemOrder`, `AutoAdvance` ; `Participant`.                                                                                                                                                                 |
| Exceptions    | `exceptions/rooms.py`                                                     | `RoomNotFoundError`, `RoomAdminRequiredError`, `RoomSettingsLockedError` ; `TemplateHasNoTilesError` vient de `exceptions/templates.py`.                                                                                              |
| Constantes    | `constants/rooms.py`, `constants/error_codes.py`, `constants/messages.py` | Longueur et alphabet du code, `ROOM_CODE_MAX_ATTEMPTS`, `FRONTEND_ROOM`, bornes des durées ; les codes `ROOM_NOT_FOUND`, `ROOM_ADMIN_REQUIRED`, `ROOM_SETTINGS_LOCKED` et leurs messages pour les développeurs.                       |
| Configuration | `core/config.py`                                                          | `ROOM_DEFAULT_TIMER_SECONDS`, `ROOM_DEFAULT_COOLDOWN_SECONDS`.                                                                                                                                                                        |
| Migration     | `migrations/versions/fedf7b56dfa2_create_rooms_and_participants.py`       | Crée les deux tables.                                                                                                                                                                                                                 |

### Frontend (`frontend/src/`)

Construit dans #84.

| Couche      | Fichier                                     | Contenu                                                                                                                                                                                                                                                                                                                                                                                                                        |
| ----------- | ------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| API         | `api/rooms.ts`                              | `useCreateRoom` (`POST /rooms`), `useRoom` (`GET /rooms/{code}`), `useUpdateRoomSettings` (`PATCH /rooms/{code}/settings`). La salle renvoyée par une création ou une modification remplace celle du cache (`roomQueryKey(code)`) : le lobby l'affiche sans nouvelle requête.                                                                                                                                                  |
| Constantes  | `constants/rooms.ts`, `constants/routes.ts` | `ROOMS_QUERY_KEY`, `roomQueryKey` ; `ROUTES.ROOM` (`/r/:code`, le format du lien partagé, `FRONTEND_ROOM` côté backend) et `roomPath(code)`. Les bornes des durées ne sont pas recopiées : le formulaire affiche les params `ge` / `le` de la `422`.                                                                                                                                                                           |
| Bouton      | `components/CreateRoomButton.tsx`           | « Créer une salle », sur chaque ligne de _Mes templates_ et à côté du titre de l'éditeur de template. Crée la salle avec les réglages par défaut, puis ouvre son lobby ; affiche l'erreur traduite (`template_has_no_tiles`, `template_not_found`).                                                                                                                                                                            |
| Page        | `pages/RoomPage.tsx`                        | `/r/:code`, réservée aux comptes connectés (`RequireAuth`) : titre, nom du template (ou un avertissement s'il a été purgé), mention « Partie en cours », `RoomInvite`, participants (le room admin signalé), résumé des réglages et, pour le room admin, `RoomSettingsDialog`. États de chargement et d'erreur (`room_not_found` pour un code inconnu ou un utilisateur sans place).                                           |
| Composants  | `components/RoomInvite.tsx`                 | Le code en grand et le lien dans un champ en lecture seule ; « Copier le lien » utilise `navigator.clipboard` et annonce « Lien copié » dans une zone `aria-live`, ou demande de copier à la main si le presse-papiers refuse.                                                                                                                                                                                                 |
|             | `components/RoomSettingsSummary.tsx`        | Les cinq réglages en clair, pour tous les participants.                                                                                                                                                                                                                                                                                                                                                                        |
|             | `components/RoomSettingsDialog.tsx`         | `<dialog>` natif ouvert par « Modifier » : boutons radio (ordre des items, item suivant), champs numériques (timer, cooldown), cases à cocher (l'admin joue, arrivées). La durée du timer n'est active et envoyée qu'avec le timer. Pendant une partie, tous les champs sauf les arrivées sont désactivés et seules les arrivées sont envoyées. Le formulaire est remonté à chaque ouverture : il repart des réglages actuels. |
| Traductions | `i18n/locales/fr.ts`, `en.ts`               | `rooms.create.*`, `rooms.lobby.*`, `rooms.settings.*` (avec `rooms.settings.summary.*`), `errors.api.{room_not_found, room_admin_required, room_settings_locked}` et `errors.field.{greater_than_equal, less_than_equal}`.                                                                                                                                                                                                     |

Pas de mise à jour en direct avant #85 : le lobby s'appuie sur le rafraîchissement par défaut de TanStack Query (quand l'onglet reprend le focus). Rejoindre depuis le lien sans avoir de place relève de #86.

### Tests

`backend/tests/integration/test_rooms.py` (endpoints, sur un vrai PostgreSQL) et `backend/tests/test_room_codes.py` (générateur de code) ; `frontend/src/pages/RoomPage.test.tsx`, `components/RoomSettingsDialog.test.tsx`, et la création d'une salle dans `TemplatesPage.test.tsx` / `TemplateEditorPage.test.tsx`. Tous sont décrits dans le [guide des tests](testing.fr.md).
