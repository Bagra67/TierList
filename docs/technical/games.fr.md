# Parties

[English](games.md) | Français

Comment une partie se joue dans une salle : son démarrage, ses tours et, plus tard, ses placements, son cooldown et sa clôture. **Construit dans #91** pour le démarrage ; les placements (#92), l'enchaînement des tours et les timers (#93), l'écran de jeu (#94), la reconnexion (#95), le cooldown (#96) et la clôture (#98) suivent.

## 1. Vue fonctionnelle

Le room admin lance une partie depuis le lobby (US-3.1). La partie est figée sur la version courante du template, l'ordre des items est fixé, et le premier item est montré à tous.

| Action            | Endpoint                  | Résultat                                                                                                                             |
| ----------------- | ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| Lancer une partie | `POST /rooms/{code}/game` | La salle en `playing`, avec sa partie : tour 1 sur N, l'item en cours (texte et/ou image) et la fin de son timer quand il y en a un. |

### Règles

- **Qui** : le room admin seulement (`403` `room_admin_required`) ; un lecteur sans place reçoit `404` `room_not_found`, comme pour toutes les routes des salles.
- **Une partie à la fois** (invariant 3) : une salle déjà `playing` répond `409` `game_in_progress`. Un index unique partiel sur `games(room_id)` (`status <> 'closed'`) est le dernier filet.
- **Quelqu'un doit placer les items** (US-3.1, US-3.5) : les participants qui placent sont les participants qui ont une place, moins le room admin quand il ne joue pas (`admin_plays` désactivé) ; il garde alors seulement les commandes. Sans aucun, `409` `no_placing_participant` (le room admin seul, qui ne joue pas). Être connecté n'est pas exigé : un participant absent reçoit des votes absents, comme à n'importe quel tour (#93).
- **Template** : le template de la salle doit encore exister et avoir des tuiles. Un template purgé répond `409` `template_not_found`, un template sans tuile `409` `template_has_no_tiles`.
- **Version figée** (invariant 4) : `take_snapshot` ([guide des templates](templates.fr.md#24-instantanés-versions-de-template)) copie les tiers et les tuiles ; modifier le template ensuite ne change jamais la partie.
- **Ordre des items** (invariant 5) : les tuiles de la version figée dans l'ordre du template, ou mélangées quand `item_order` vaut `random`. Un tour par tuile, numéroté à partir de 1.
- **Premier tour** : démarré tout de suite ; avec `auto_advance = timer`, sa fin (`ends_at`) vaut maintenant + `timer_seconds`.
- **Réglages gardés avec la partie** : `item_order` et `admin_plays`, pour qu'ils restent connus une fois la salle fermée (les résultats excluent le room admin qui n'a pas joué).

### Messages

| Situation                                        | HTTP            | Code de l'API                                                | Traduction (FR / EN)                                                                                                                                                                            |
| ------------------------------------------------ | --------------- | ------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Une partie est déjà en cours                     | 409             | `game_in_progress`                                           | `Une partie est déjà en cours dans cette salle.` / `A game is already in progress in this room.`                                                                                                |
| Personne ne placerait les items                  | 409             | `no_placing_participant`                                     | `Il faut au moins un participant qui place les items : invitez un joueur ou jouez vous-même.` / `A game needs at least one participant who places the items: invite a player or play yourself.` |
| Template purgé, ou sans tuile                    | 409             | `template_not_found`, `template_has_no_tiles`                | Traductions existantes ([guide des templates](templates.fr.md))                                                                                                                                 |
| Pas le room admin / sans place / pas authentifié | 403 / 404 / 401 | `room_admin_required`, `room_not_found`, `not_authenticated` | Traductions existantes ([guide des salles](rooms.fr.md#messages))                                                                                                                               |

## 2. Conception technique

### 2.1 Modèle de données

```
rooms ──< games (room_id SET NULL) ──< rounds >── snapshot_tiles
             └──> template_snapshots
```

| Table    | Colonnes                                                                                                                                                                    | Remarques                                                                                                                                                                                                                              |
| -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `games`  | `id`, `room_id` → `rooms` (nullable), `snapshot_id` → `template_snapshots`, `status`, `item_order`, `admin_plays`, `current_round_number`, `started_at`, `closed_at`, dates | `ON DELETE SET NULL` vers `rooms` : une partie **survit** à sa salle (invariant 11). `status` : `in_round`, `cooldown`, `closed` (colonne texte avec un `CHECK`, comme la salle). Index unique partiel `uq_games_room_id_in_progress`. |
| `rounds` | `id`, `game_id` → `games`, `number`, `snapshot_tile_id` → `snapshot_tiles`, `started_at`, `ends_at`, `ended_at`                                                             | `ON DELETE CASCADE` vers `games`. Uniques `(game_id, number)` et `(game_id, snapshot_tile_id)` : un tour par tuile. Un tour désigne une tuile de la **version figée**, jamais une tuile du template.                                   |

Tous les tours sont créés au démarrage ; seul le tour 1 a un `started_at`. `ends_at` est la fin du timer (heure du serveur, UTC), `ended_at` la fin réelle (#93).

### 2.2 Démarrage

`GameService.start` (`app/services/games.py`) tourne dans **une seule transaction** :

1. Verrouille la salle et vérifie le room admin (`RoomService.get_for_admin_change`), puis le statut, le template et les participants qui placent.
2. `TemplateService.take_snapshot` verrouille le template et fait seulement un flush.
3. Ordonne les tuiles de la version figée (`shuffle_items`, `random.SystemRandom`, pour `random`), crée la partie et ses tours, démarre le tour 1.
4. Passe la salle en `playing`, incrémente `rooms.version`, fait le commit.
5. **Après le commit**, publie `game.started` (`{round_number, round_count, ends_at}`) à la salle ([guide du temps réel](realtime.fr.md)).

La fin du timer est **enregistrée mais pas encore appliquée** : terminer le tour à l'échéance, et reprogrammer les échéances au démarrage du serveur, arrivent avec #93 ([guide du temps réel](realtime.fr.md#28-timers-côté-serveur)).

### 2.3 Ce que renvoie la salle

`RoomResponse.game` est la partie en cours, `null` hors partie :

```json
{
  "round_number": 1,
  "round_count": 12,
  "current_item": {
    "id": "…",
    "text": "Paprika",
    "image_url": "https://…/x.webp"
  },
  "ends_at": null
}
```

L'item en cours est montré à tous les participants : ce n'est pas un secret. Les placements des autres ne sont jamais envoyés (plateau privé, #92). Les routes des salles reçoivent le stockage des images (`get_image_storage`) pour construire l'adresse publique de l'image, comme les routes des templates.

## 3. Dans le code

### Backend (`backend/app/`)

| Couche      | Fichier                                                                                 | Contenu                                                                                                                                                                                                                                                                                                                                                   |
| ----------- | --------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Route       | `api/routes/rooms.py`                                                                   | `start_game` (`POST /rooms/{code}/game`, `201`) ; `current_game_response` (`api/presenters/rooms.py`) construit `RoomResponse.game`.                                                                                                                                                                                                                      |
| Dépendances | `api/dependencies.py`                                                                   | `get_game_service`.                                                                                                                                                                                                                                                                                                                                       |
| Service     | `services/games.py`                                                                     | `GameService.start`, `placing_participants`, `shuffle_items` (remplacé dans les tests). Reçoit `RoomService` et `TemplateService` de `get_game_service`, sur la même session.                                                                                                                                                                             |
| Modèles     | `models/game.py`, `models/round.py`, `models/room.py`, `models/enums.py`, `db/types.py` | `Game`, `current_round` ; `Round` ; `Room.current_game` (relation en lecture seule filtrée sur `status <> 'closed'`) ; `GameStatus`, `RoomStatus`, `ItemOrder` et `AutoAdvance` (`models/enums.py`), partagés par la salle, la partie, les schémas et les services ; `text_enum` (`db/types.py`), la colonne texte avec un `CHECK` utilisée par les deux. |
| Repository  | `repositories/rooms.py`                                                                 | `get_room_by_code` charge aussi la partie en cours, ses tours et leur tuile.                                                                                                                                                                                                                                                                              |
| Schémas     | `schemas/rooms.py`, `schemas/room_events.py`                                            | `CurrentGameResponse`, `CurrentItemResponse` ; `GameStartedEvent`.                                                                                                                                                                                                                                                                                        |
| Erreurs     | `exceptions/games.py`, `constants/error_codes.py`, `constants/messages.py`              | `GameInProgressError`, `NoPlacingParticipantError` ; `GAME_IN_PROGRESS`, `NO_PLACING_PARTICIPANT`.                                                                                                                                                                                                                                                        |
| Migration   | `migrations/versions/5f588806f8ee_create_games_and_rounds.py`                           | Crée `games` et `rounds`.                                                                                                                                                                                                                                                                                                                                 |

### Frontend (`frontend/src/`)

| Couche      | Fichier                          | Contenu                                                                                                                                                   |
| ----------- | -------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| API         | `api/rooms.ts`                   | `useStartGame` (`POST /rooms/{code}/game`) ; la salle renvoyée remplace celle du cache.                                                                   |
| Composants  | `components/StartGameButton.tsx` | « Lancer la partie », pour le room admin hors partie ; erreurs traduites.                                                                                 |
|             | `components/RoomLobby.tsx`       | Pendant une partie : « Partie en cours », « Item n sur N » et l'item en cours (texte, image avec son `alt`). Provisoire : l'écran de jeu arrive avec #94. |
| Temps réel  | `api/roomChannel.ts`             | `game.started` fait relire la salle (comportement par défaut).                                                                                            |
| Traductions | `i18n/locales/fr.ts`, `en.ts`    | `rooms.lobby.start.*`, `rooms.lobby.currentItem`, `rooms.lobby.currentItemImage`, `errors.api.{game_in_progress, no_placing_participant}`.                |

### Tests

`backend/tests/integration/test_game_start.py` ; `frontend/src/components/StartGameButton.test.tsx` et la partie en cours dans `pages/RoomPage.test.tsx`. Tous sont décrits dans le [guide des tests](testing.fr.md).

## 4. Limites connues

- Le tour ne se termine jamais encore : pas de placements (#92), ni de « suivant », de timer ou de « tout le monde a placé » (#93).
- Le sort des placements d'un participant retiré est décidé avec les placements (#92).
- Fermer une salle pendant une partie (#89) devra d'abord clôturer la partie (#98).
- « Une partie est en cours » vit à deux endroits : `rooms.status = playing` et une ligne `games` qui n'est pas `closed`. Le démarrage écrit les deux dans une seule transaction, sous le verrou de la salle ; la clôture (#98) devra repasser la salle en `open` dans la même transaction que la partie.
