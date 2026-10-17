# Parties

[English](games.md) | Français

Comment une partie se joue dans une salle : son démarrage, ses tours, ses placements et, plus tard, son cooldown et sa clôture. **Construit dans #91** pour le démarrage et **#92** pour les placements ; l'enchaînement des tours, les votes absents et les timers (#93), l'écran de jeu (#94), la reconnexion (#95), le cooldown avec les placements finaux (#96) et la clôture (#98) suivent.

## 1. Vue fonctionnelle

Le room admin lance une partie depuis le lobby (US-3.1). La partie est figée sur la version courante du template, l'ordre des items est fixé, et le premier item est montré à tous. Chaque participant qui place dépose l'item en cours dans un tier, à la position qu'il veut (US-3.3), sur un **plateau privé** : les autres voient seulement qui l'a placé.

| Action                 | Endpoint                                      | Résultat                                                                                                                                                                         |
| ---------------------- | --------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Lancer une partie      | `POST /rooms/{code}/game`                     | La salle en `playing`, avec sa partie : tour 1 sur N, l'item en cours (texte et/ou image) et la fin de son timer quand il y en a un.                                             |
| Placer l'item en cours | `PUT /rooms/{code}/game/placements/{tile_id}` | Corps `{tier_id, position}`. La salle, avec le plateau du lecteur à jour (`own_placements`) et qui a placé l'item en cours. Le placer à nouveau pendant le même tour le déplace. |

### Règles

- **Qui** : le room admin seulement (`403` `room_admin_required`) ; un lecteur sans place reçoit `404` `room_not_found`, comme pour toutes les routes des salles.
- **Une partie à la fois** (invariant 3) : une salle déjà `playing` répond `409` `game_in_progress`. Un index unique partiel sur `games(room_id)` (`status <> 'closed'`) est le dernier filet.
- **Quelqu'un doit placer les items** (US-3.1, US-3.5) : les participants qui placent sont les participants qui ont une place, moins le room admin quand il ne joue pas (`admin_plays` désactivé) ; il garde alors seulement les commandes. Sans aucun, `409` `no_placing_participant` (le room admin seul, qui ne joue pas). Être connecté n'est pas exigé : un participant absent reçoit des votes absents, comme à n'importe quel tour (#93).
- **Template** : le template de la salle doit encore exister et avoir des tuiles. Un template purgé répond `409` `template_not_found`, un template sans tuile `409` `template_has_no_tiles`.
- **Version figée** (invariant 4) : `take_snapshot` ([guide des templates](templates.fr.md#24-instantanés-versions-de-template)) copie les tiers et les tuiles ; modifier le template ensuite ne change jamais la partie.
- **Ordre des items** (invariant 5) : les tuiles de la version figée dans l'ordre du template, ou mélangées quand `item_order` vaut `random`. Un tour par tuile, numéroté à partir de 1.
- **Premier tour** : démarré tout de suite ; avec `auto_advance = timer`, sa fin (`ends_at`) vaut maintenant + `timer_seconds`.
- **Réglages gardés avec la partie** : `item_order` et `admin_plays`, pour qu'ils restent connus une fois la salle fermée (les résultats excluent le room admin qui n'a pas joué).
- **Qui place** (US-3.3, US-3.5) : chaque participant qui place, compte ou invité (l'invité avec le cookie de la salle) ; le room admin qui ne joue pas reçoit `403` `not_a_placing_participant`.
- **Seulement l'item en cours** (US-3.3) : la tuile doit être l'item du tour en cours, sinon `409` `item_not_current` (un item d'un tour passé ne bouge pas avant le cooldown, un item futur n'est pas encore montré). Hors d'un tour (pas de partie, ou plus tard le cooldown), `409` `round_not_in_progress`. Le tier doit être un tier de la version figée de la partie, sinon `404` `tier_not_found`.
- **Tier et position** : les positions commencent à `0` et restent **continues** dans chaque tier, par participant : placer en `k` décale les items suivants, une position au-delà de la fin met l'item en dernier, et le tier qu'il quitte se referme. L'ordre relatif des items passés ne change jamais. Placer à nouveau l'item pendant le même tour remplace son placement (invariant 6 : un placement de tour par tuile).
- **Plateau privé** : la réponse ne contient que les placements du lecteur ; ceux des autres ne sont jamais envoyés, seulement **qui** a placé l'item en cours (`placed_participant_ids`).
- **Participant retiré** : ses placements sont supprimés avec sa place ; il n'est plus dans la partie ni dans ses résultats.

### Messages

| Situation                                        | HTTP            | Code de l'API                                                | Traduction (FR / EN)                                                                                                                                                                            |
| ------------------------------------------------ | --------------- | ------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Une partie est déjà en cours                     | 409             | `game_in_progress`                                           | `Une partie est déjà en cours dans cette salle.` / `A game is already in progress in this room.`                                                                                                |
| Personne ne placerait les items                  | 409             | `no_placing_participant`                                     | `Il faut au moins un participant qui place les items : invitez un joueur ou jouez vous-même.` / `A game needs at least one participant who places the items: invite a player or play yourself.` |
| Le room admin ne joue pas                        | 403             | `not_a_placing_participant`                                  | `Vous ne jouez pas cette partie : vous avez seulement les commandes.` / `You do not play in this game: you only have the controls.`                                                             |
| La tuile n'est pas l'item en cours               | 409             | `item_not_current`                                           | `Cet item n'est plus l'item en cours : le tour est passé.` / `This item is no longer the current one: the round has moved on.`                                                                  |
| Aucun tour en cours                              | 409             | `round_not_in_progress`                                      | `Aucun tour n'est en cours : l'item ne peut plus être placé.` / `No round is in progress: the item can no longer be placed.`                                                                    |
| Tier hors de la partie                           | 404             | `tier_not_found`                                             | Traduction existante ([guide des templates](templates.fr.md))                                                                                                                                   |
| Template purgé, ou sans tuile                    | 409             | `template_not_found`, `template_has_no_tiles`                | Traductions existantes ([guide des templates](templates.fr.md))                                                                                                                                 |
| Pas le room admin / sans place / pas authentifié | 403 / 404 / 401 | `room_admin_required`, `room_not_found`, `not_authenticated` | Traductions existantes ([guide des salles](rooms.fr.md#messages))                                                                                                                               |

## 2. Conception technique

### 2.1 Modèle de données

```
rooms ──< games (room_id SET NULL) ──< rounds >── snapshot_tiles
             ├──> template_snapshots
             └──< placements >── participants (CASCADE), snapshot_tiles, snapshot_tiers
```

| Table        | Colonnes                                                                                                                                                                                     | Remarques                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| ------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `games`      | `id`, `room_id` → `rooms` (nullable), `snapshot_id` → `template_snapshots`, `status`, `item_order`, `admin_plays`, `current_round_number`, `started_at`, `closed_at`, dates                  | `ON DELETE SET NULL` vers `rooms` : une partie **survit** à sa salle (invariant 11). `status` : `in_round`, `cooldown`, `closed` (colonne texte avec un `CHECK`, comme la salle). Index unique partiel `uq_games_room_id_in_progress`.                                                                                                                                                                                                                                           |
| `rounds`     | `id`, `game_id` → `games`, `number`, `snapshot_tile_id` → `snapshot_tiles`, `started_at`, `ends_at`, `ended_at`                                                                              | `ON DELETE CASCADE` vers `games`. Uniques `(game_id, number)` et `(game_id, snapshot_tile_id)` : un tour par tuile. Un tour désigne une tuile de la **version figée**, jamais une tuile du template.                                                                                                                                                                                                                                                                             |
| `placements` | `id`, `game_id` → `games`, `participant_id` → `participants`, `snapshot_tile_id` → `snapshot_tiles`, `phase`, `snapshot_tier_id` → `snapshot_tiers` (nullable), `position` (nullable), dates | `ON DELETE CASCADE` vers `games` et `participants`. `phase` : `round` ou `final` (#96). Unique `(game_id, participant_id, snapshot_tile_id, phase)` (invariant 6). `ck_placements_tier_and_position` : un tier et une position `>= 0`, ou aucun des deux pour un vote **absent** (invariant 8, #93) ; `ck_placements_final_not_absent`. Pas de contrainte d'unicité sur la position : décaler les items suivants la violerait en cours de route, le service les garde continues. |

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

`RoomResponse.game` est la partie en cours **vue par le lecteur**, `null` hors partie :

```json
{
  "round_number": 1,
  "round_count": 12,
  "current_item": {
    "id": "…",
    "text": "Paprika",
    "image_url": "https://…/x.webp"
  },
  "ends_at": null,
  "tiers": [{ "id": "…", "name": "S", "color": "#FF7F7F" }],
  "placed_participant_ids": ["…"],
  "own_placements": [
    {
      "item": { "id": "…", "text": "Chorizo", "image_url": null },
      "tier_id": "…",
      "position": 0
    }
  ]
}
```

L'item en cours et les tiers de la version figée (de haut en bas) sont montrés à tous les participants. `placed_participant_ids` dit **qui** a placé l'item en cours, jamais où. `own_placements` contient les placements de tour du lecteur seulement, triés par tier puis position : un participant qui revient retrouve son plateau ; la liste est vide pour le room admin qui ne joue pas. La réponse est construite pour la **place** du lecteur (`room_response(room, seat, …)`) : les routes la trouvent avec `RoomService.seat_of` (compte ou cookie d'invité) ou `seat_in` (un compte dans une salle déjà lue). Les routes des salles reçoivent le stockage des images (`get_image_storage`) pour construire les adresses publiques des images (`optional_image_url`).

### 2.4 Placements

`GameService.place` (`app/services/games.py`) tourne dans **une seule transaction** :

1. Trouve la place du lecteur et **verrouille la salle** (`RoomService.seat_of(viewer, code, for_update=True)`) : deux placements dans la même salle passent l'un après l'autre.
2. Vérifie le tour en cours, que la place place les items (`placing_participants`), l'item en cours et le tier.
3. Travaille sur le plateau du lecteur pour la phase du tour : sort le placement de la tuile de son tier s'il existe, l'insère à la position (bornée à la fin du tier) et renumérote les deux tiers `0..n-1` (`_place_in_tier`).
4. **Premier placement du tour** : incrémente `rooms.version`, fait le commit, puis publie `participant.placed` (`{participant_id, round_number}`, sans tier ni position). **Un déplacement** fait le commit sans nouvelle version ni événement : les autres ne voient rien changer.

Les votes absents, créés à la fin d'un tour, arrivent avec #93 ; les placements finaux (cooldown) avec #96.

## 3. Dans le code

### Backend (`backend/app/`)

| Couche      | Fichier                                                                                                        | Contenu                                                                                                                                                                                                                                                                                                                                                                                |
| ----------- | -------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Route       | `api/routes/rooms.py`                                                                                          | `start_game` (`POST /rooms/{code}/game`, `201`), `place_item` (`PUT /rooms/{code}/game/placements/{tile_id}`, `200`, comptes et invités).                                                                                                                                                                                                                                              |
| Presenters  | `api/presenters/rooms.py`                                                                                      | `room_response(room, seat, …)`, construite pour la place du lecteur ; `current_game_response` construit `RoomResponse.game` (tiers, qui a placé, ses propres placements) ; `_item_response`.                                                                                                                                                                                           |
| Dépendances | `api/dependencies.py`                                                                                          | `get_game_service`.                                                                                                                                                                                                                                                                                                                                                                    |
| Service     | `services/games.py`                                                                                            | `GameService.start`, `place` (`_place_in_tier`, `_in_tier`, `_renumber`), `placing_participants`, `shuffle_items` (remplacé dans les tests). Reçoit `RoomService` et `TemplateService` de `get_game_service`, sur la même session.                                                                                                                                                     |
|             | `services/rooms.py`                                                                                            | `seat_of(viewer, code, for_update)` : la place du lecteur (compte ou invité), sa salle verrouillée au besoin ; `seat_in(room, user)`.                                                                                                                                                                                                                                                  |
| Modèles     | `models/game.py`, `models/round.py`, `models/placement.py`, `models/room.py`, `models/enums.py`, `db/types.py` | `Game`, `current_round`, `placements` ; `Round` ; `Placement`, `is_absent` ; `Room.current_game` (relation en lecture seule filtrée sur `status <> 'closed'`) ; `GameStatus`, `RoomStatus`, `ItemOrder`, `AutoAdvance` et `PlacementPhase` (`models/enums.py`), partagés par les modèles, les schémas et les services ; `text_enum` (`db/types.py`), la colonne texte avec un `CHECK`. |
| Repository  | `repositories/rooms.py`                                                                                        | `get_room_by_code` charge aussi la partie en cours, ses tours et leur tuile, ses tiers figés et ses placements.                                                                                                                                                                                                                                                                        |
| Schémas     | `schemas/rooms.py`, `schemas/room_events.py`                                                                   | `CurrentGameResponse`, `CurrentItemResponse`, `GameTierResponse`, `OwnPlacementResponse`, `PlaceItemRequest` ; `GameStartedEvent`, `ParticipantPlacedEvent`.                                                                                                                                                                                                                           |
| Erreurs     | `exceptions/games.py`, `constants/error_codes.py`, `constants/messages.py`                                     | `GameInProgressError`, `NoPlacingParticipantError`, `RoundNotInProgressError`, `NotAPlacingParticipantError`, `ItemNotCurrentError` ; les codes correspondants ; `TierNotFoundError` vient de `exceptions/templates.py`.                                                                                                                                                               |
| Migration   | `migrations/versions/5f588806f8ee_create_games_and_rounds.py`                                                  | Crée `games` et `rounds`.                                                                                                                                                                                                                                                                                                                                                              |
|             | `migrations/versions/e1bf9bc677cd_create_placements.py`                                                        | Crée `placements`.                                                                                                                                                                                                                                                                                                                                                                     |

### Frontend (`frontend/src/`)

| Couche      | Fichier                          | Contenu                                                                                                                                                                                                        |
| ----------- | -------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| API         | `api/rooms.ts`                   | `useStartGame` (`POST /rooms/{code}/game`) ; la salle renvoyée remplace celle du cache.                                                                                                                        |
| Composants  | `components/StartGameButton.tsx` | « Lancer la partie », pour le room admin hors partie ; erreurs traduites.                                                                                                                                      |
|             | `components/RoomLobby.tsx`       | Pendant une partie : « Partie en cours », « Item n sur N » et l'item en cours (texte, image avec son `alt`). Provisoire : l'écran de jeu arrive avec #94.                                                      |
| Temps réel  | `api/roomChannel.ts`             | `game.started` fait relire la salle (comportement par défaut) ; `participant.placed` ajoute le participant à `game.placed_participant_ids` dans le cache.                                                      |
| Traductions | `i18n/locales/fr.ts`, `en.ts`    | `rooms.lobby.start.*`, `rooms.lobby.currentItem`, `rooms.lobby.currentItemImage`, `errors.api.{game_in_progress, no_placing_participant, not_a_placing_participant, item_not_current, round_not_in_progress}`. |

### Tests

`backend/tests/integration/test_game_start.py` et `test_game_placements.py` ; `frontend/src/api/roomChannel.test.ts` (`participant.placed`) ; `frontend/src/components/StartGameButton.test.tsx` et la partie en cours dans `pages/RoomPage.test.tsx`. Tous sont décrits dans le [guide des tests](testing.fr.md).

## 4. Limites connues

- Le tour ne se termine jamais encore : pas de « suivant », de timer ni de « tout le monde a placé », et pas de vote absent (#93). Les tests passent au tour suivant en base.
- Le plateau n'est pas encore affiché : l'écran de jeu arrive avec #94 ; le lobby ne montre encore que l'item en cours.
- Les placements finaux (cooldown) ne sont pas construits : `phase = final` est prête dans la table (#96).
- Fermer une salle pendant une partie (#89) devra d'abord clôturer la partie (#98).
- « Une partie est en cours » vit à deux endroits : `rooms.status = playing` et une ligne `games` qui n'est pas `closed`. Le démarrage écrit les deux dans une seule transaction, sous le verrou de la salle ; la clôture (#98) devra repasser la salle en `open` dans la même transaction que la partie.
