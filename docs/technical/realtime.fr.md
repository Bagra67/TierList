# Temps réel

[English](realtime.md) | Français

Comment les rooms envoient les tours, les placements, la présence et les timers à chaque participant : transport, format des messages, authentification du socket, reconnexion, timers côté serveur et montée en charge. Décidé dans le spike #74, **construit dans #85** (§3) pour le canal de la room et la présence ; les tours, les placements et les timers arrivent avec les issues du jeu. Pour comprendre, déboguer ou faire évoluer le canal, commencer par le [guide du WebSocket](websocket.fr.md). Ce qu'est une room pour l'utilisateur : [déroulé d'une partie](../product/milestone-1/game-flow.fr.md) et [cycles de vie](../product/milestone-1/lifecycles.fr.md).

## 1. Vue fonctionnelle

### Ce qui doit parvenir aux participants

Une room a **au plus 10 participants** (admin de la room compris) et une partie **au plus 32 tours**. Chaque participant doit voir, sans recharger la page :

| Moment                                                    | Événement envoyé à la room                                                                    |
| --------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| Quelqu'un rejoint, quitte, se connecte ou se déconnecte   | Le lobby / la liste des participants change (`3 participants sur 10`)                         |
| L'admin modifie les réglages ou verrouille les arrivées   | Les nouveaux réglages, « arrivées ouvertes / verrouillées »                                   |
| L'admin lance la partie                                   | La partie démarre avec son premier tour                                                       |
| Un tour commence                                          | `Item n sur N`, et son heure de fin quand la room utilise un timer                            |
| Un participant place ou déplace l'item courant            | **Qui** a placé, jamais **où** (les classements restent privés jusqu'aux résultats)           |
| Un tour se termine (« suivant » de l'admin, timer, tous)  | Le tour est fini ; les placements absents sont enregistrés par le serveur                     |
| Le dernier tour se termine                                | Le cooldown commence, avec son heure de fin                                                   |
| Le cooldown se termine (timer ou « Terminer » de l'admin) | La partie est close : classements définitifs (résultats avec #99), room de retour à _Ouverte_ |
| L'admin ferme la room, ou elle est inactive               | La room est fermée ; tous les participants la quittent                                        |

Timers : le **timer de tour** par item (réglage de la room), le **cooldown** (réglage de la room), le **délai d'inactivité** d'une room (réglage de l'application). Un participant **déconnecté** garde sa place et son classement, reçoit des placements absents pour les tours qui se terminent entre-temps, et n'est pas attendu par « tout le monde a fini ».

### Règles

- Le **serveur est la seule autorité** : il décide quand un tour se termine, enregistre les placements et fait tourner les timers. Un client ne fait qu'afficher.
- Un participant peut ouvrir plusieurs onglets : il est **connecté** tant que l'un d'eux l'est.
- Un participant qui revient (rechargement, coupure réseau, autre appareil) retrouve l'état courant : le tour en cours, ses propres placements, le temps restant.

### Pas encore disponible

Le démarrage d'une partie (`game.started`, #91), les placements (`participant.placed`, #92), l'enchaînement des tours (`round.started`, `cooldown.started`) et les timers des tours (§2.8, #93) sont construits ([guide des parties](games.fr.md)) ; le cooldown final, son timer et sa fin (`game.closed`, #96) aussi ; ainsi que la sauvegarde de la partie close (`game_players`, #98) ; les résultats arrivent avec #99. Les hologrammes, les rooms publiques et le chat (jalons suivants) réutiliseront le même canal.

## 2. Conception technique

### 2.1 Options étudiées

| Option                                          | Pour                                                                                                                                         | Contre                                                                                                                                 |
| ----------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| Polling (`GET` toutes les quelques secondes)    | Rien de nouveau                                                                                                                              | En retard (un tour peut durer quelques secondes), beaucoup de requêtes inutiles, pas de présence                                       |
| Server-Sent Events + commandes REST             | HTTP simple, reconnexion intégrée                                                                                                            | 6 connexions HTTP/1.1 max par domaine (plusieurs onglets), `EventSource` ne peut pas envoyer l'en-tête `Authorization`, présence floue |
| WebSocket, tout sur le socket                   | Un seul canal, le moins de requêtes                                                                                                          | Validation, codes d'erreur, autorisations et tests à reconstruire hors d'OpenAPI et des services existants                             |
| **WebSocket en push + commandes REST** (retenu) | Les commandes gardent OpenAPI, la validation Pydantic, les `ErrorCode`, les services et les tests ; le socket apporte le push et la présence | Deux canaux à coordonner (géré par la resynchronisation du §2.6)                                                                       |

**Décision** : un WebSocket par onglet, utilisé **uniquement pour pousser** les événements du serveur et savoir qui est connecté. Chaque **action** (rejoindre, placer, suivant, lancer, fermer, réglages) reste une route REST, comme le reste de l'API.

### 2.2 Transport

- Un endpoint par room : `WS /rooms/{room_code}/ws` (`WebSocket` FastAPI), atteint en `/api/rooms/{room_code}/ws` via le proxy Vite, qui aura alors besoin de `ws: true` dans `frontend/vite.config.ts`.
- **Serveur → client** : les événements du §2.3. **Client → serveur** : uniquement le message d'authentification (§2.4) et la réponse au heartbeat ; tout autre message ferme le socket.
- Une commande est un appel REST normal : la route appelle le service, le service commit, **puis** publie l'événement dans la room (§2.8). Le participant qui a envoyé la commande reçoit la réponse HTTP ; tout le monde (lui compris) reçoit l'événement.
- Aucune nouvelle dépendance : `fastapi[standard]` fournit déjà uvicorn avec `websockets`, `uvloop` et `httptools` (présents dans `backend/uv.lock`).

### 2.3 Format des messages

Chaque message est un objet JSON avec la même enveloppe :

```json
{
  "type": "round.started",
  "room_version": 12,
  "data": {
    "round_number": 3,
    "round_count": 20,
    "tile_id": "…",
    "ends_at": "2026-10-10T18:30:12Z"
  }
}
```

- `type` : en minuscules, `sujet.événement` séparés par un point (`participant.joined`, `participant.placed`, `round.started`, `round.ended`, `cooldown.started`, `game.closed`, `room.closed`…).
- `room_version` : un entier incrémenté par le serveur à chaque changement de la room, dans la même transaction. Un client qui reçoit une version différente de « précédente + 1 » sait qu'il a manqué quelque chose et se resynchronise (§2.6).
- `data` : le contenu de l'événement, jamais la position des placements d'un autre participant.
- Chaque événement est un modèle Pydantic ; leur union est une **union discriminée sur `type`**. Ces modèles sont ajoutés aux composants du schéma OpenAPI (schémas supplémentaires dans le `openapi()` personnalisé), pour que `pnpm gen:api` génère leurs types TypeScript comme ceux du REST (AGENTS.md §23 : les types de l'API ne sont jamais écrits à la main).
- Erreurs : le serveur ferme le socket avec un code de fermeture applicatif (`4000`–`4999`) et l'`ErrorCode` comme raison (par ex. `4401` + `not_authenticated`, `4403` + `room_access_denied`, `4404` + `room_not_found`). Le frontend traduit le code comme toute erreur de l'API (AGENTS.md §50). Les codes exacts sont créés avec les rooms.

### 2.4 Authentification du socket

Un navigateur ne peut pas envoyer l'en-tête `Authorization` à l'ouverture d'un WebSocket, et le cookie de refresh (`Path=/api/auth`) n'atteint jamais `/api/rooms`. D'où :

- **Compte** : le socket s'ouvre non authentifié ; le premier message du client doit être `{"type": "auth", "access_token": "…"}` dans les quelques secondes, sinon le serveur le ferme. Le serveur le vérifie avec l'existant `AuthService.authenticate_access_token`. Le token n'est **jamais mis dans l'URL**, qui finirait dans les logs du proxy et du serveur. Quand le frontend rafraîchit l'access token (refresh unique de `frontend/src/api/client.ts`), il n'a pas besoin de rouvrir le socket : le token n'est vérifié qu'à la connexion.
- **Invité** : l'invité est reconnu par un cookie `HttpOnly` limité à `/api/rooms`, que le navigateur envoie automatiquement avec la poignée de main (même origine). Le jeton, son cookie (`guest_token`, `Path=/api/rooms/<code>`) et sa durée de vie sont décrits dans le [guide des salles](rooms.fr.md#24-invités).
- **Contrôle de l'origine** : comme un cookie authentifie les invités, la poignée de main est refusée quand son en-tête `Origin` n'est pas l'origine de l'application (protection contre le détournement de WebSocket inter-sites).
- **Autorisation** : une fois authentifié, le serveur vérifie que le compte ou l'invité **a une place dans cette room** avant d'enregistrer le socket. Rien n'est envoyé avant.

### 2.5 Présence et heartbeat

- Le serveur envoie un heartbeat (`{"type": "ping"}`) à intervalle fixe ; le client répond `{"type": "pong"}`. Un socket sans réponse est fermé. L'intervalle garde aussi le socket ouvert derrière les proxys qui ferment les connexions inactives.
- Un participant devient **déconnecté** quand son dernier socket est fermé depuis plus d'un **délai de grâce**, pour qu'un rechargement de page ou une courte coupure réseau ne compte pas comme une déconnexion (et ne déclenche pas « tout le monde a fini » à sa place). Intervalle et délai de grâce sont des valeurs de `Settings` dont les valeurs par défaut sont choisies à l'implémentation.
- `connected` est stocké sur la ligne du participant et écrit seulement quand il change (connexion, fin du délai de grâce), pas à chaque heartbeat.

### 2.6 Reconnexion et resynchronisation

- Le client se reconnecte automatiquement avec un **backoff exponentiel avec jitter** (par exemple de 0,5 s jusqu'à 10 s), sauf après un code de fermeture qui signifie « ne pas réessayer » (room fermée, accès refusé).
- Après **chaque** (re)connexion, et dès qu'un trou dans `room_version` est vu, le client **recharge l'instantané de la room** avec le `GET` REST (`invalidateQueries` de TanStack Query). Le serveur ne rejoue donc jamais d'événements passés : l'instantané est la vérité, les événements ne font que le tenir à jour entre deux instantanés.

### 2.7 Frontend : événements et TanStack Query

```
REST GET /rooms/{code} ──▶ cache TanStack Query ──▶ composants
Événements WS ──▶ useRoomEvents(roomCode) ──┘ (setQueryData / invalidateQueries)
```

- L'état de la room reste une requête **TanStack Query** alimentée par l'instantané REST ; les commandes restent des mutations de la couche API (`frontend/src/api/`).
- Un hook, `useRoomEvents(roomCode)` dans `frontend/src/api/`, possède le socket : ouverture, authentification, heartbeat, reconnexion, fermeture au démontage. Les composants ne touchent jamais le socket.
- Les petits événements mettent à jour le cache directement (`queryClient.setQueryData` : quelqu'un a placé, présence) ; les plus gros invalident la requête (`invalidateQueries` : nouveau tour, résultats), ce qui recharge l'instantané.
- Les comptes à rebours sont calculés localement à partir du `ends_at` envoyé par le serveur.

### 2.8 Timers côté serveur

**Construit pour les tours dans #93** (`services/round_timers.py`, [guide des parties](games.fr.md#25-enchaînement-des-tours)) ; le timer du cooldown depuis #96 (`schedule_cooldown_end`, une échéance par partie). Un tour fini plus tôt garde sa tâche : la transition trouve le tour fini et ne fait rien, ce qui est plus simple que de l'annuler.

- Le serveur est la seule horloge. Un tour avec timer et le cooldown stockent leur **heure de fin** (`ends_at`, UTC) en base ; les événements l'envoient, les clients en déduisent le compte à rebours.
- Dans le processus, une tâche `asyncio` par partie attend l'échéance et appelle la transition du service ; une échéance plus récente de la partie (tour suivant, fin du cooldown) la remplace, une plus ancienne est ignorée ; une phase finie plus tôt laisse sa tâche, dont la transition ne fait alors rien ; une transition qui échoue est réessayée après 1, 5 puis 30 s. Au démarrage, les échéances en cours sont relues en base et reprogrammées : un redémarrage ne perd aucun timer.
- **Courses** (timer, « suivant » et « tout le monde a fini » en même temps) : chaque transition s'exécute dans une transaction qui verrouille la ligne de la room et vérifie l'état attendu (le tour est toujours en cours) ; la seconde trouve le tour déjà terminé et ne fait rien. Les transitions sont donc **idempotentes**.
- Le **délai d'inactivité** d'une room est géré par un balayage périodique qui ferme les rooms inactives depuis trop longtemps.
- SQLAlchemy est synchrone : depuis le code async (le socket, les timers), les appels à la base passent par le threadpool (`run_in_threadpool`) et ne bloquent jamais la boucle d'événements.

### 2.9 Montée en charge

**Pourquoi une room coûte peu** : au plus 10 sockets et quelques petits événements par tour. La charge, c'est le nombre de rooms simultanées × 10 sockets, plus les commandes REST qui sollicitent la base. Goulots attendus, dans l'ordre : l'accès à la base (SQLAlchemy synchrone via le threadpool, taille du pool), puis la boucle d'événements d'un processus, puis le réseau. Aucun chiffre de capacité n'est promis : il est **mesuré par un test de charge** avant les rooms publiques (outil choisi et justifié à ce moment-là, AGENTS.md §27).

Le chemin se fait par étapes ; chaque étape est franchie quand les métriques de la précédente l'exigent.

**Étape 0 : jalon 1 (ce qui est construit).** Un processus, un worker. Un `ConnectionRegistry` en mémoire (room → sockets ouverts de ce processus), des timers `asyncio`, des événements publiés dans le processus. Un redémarrage ferme tous les sockets : les clients se reconnectent et rechargent leur instantané, les timers sont reprogrammés depuis la base.

**Étape 1 : machine plus grosse (configuration seulement).** Plus de CPU et de mémoire, tailles du pool de connexions et du threadpool réglées via `Settings`, `uvloop` et `httptools` (déjà installés). À surveiller : sockets ouverts par processus, retard de la boucle d'événements, temps d'attente d'une connexion à la base, délai entre publication et livraison.

**Étape 2 : plusieurs instances ou workers.** Trois problèmes apparaissent :

| Problème                                                                  | Réponse                                                                                                                                                                                                                                                                                                                  |
| ------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Diffusion** : les sockets d'une room sont sur des instances différentes | Un **broker** : chaque instance écoute le canal `room:{id}` des rooms dont elle détient des sockets ; les services y publient. Premier choix **PostgreSQL `LISTEN/NOTIFY`** : aucun nouveau service, contenu ≤ 8 ko (les événements sont petits), une connexion d'écoute par instance.                                   |
| Les **timers** ne doivent se déclencher qu'une fois                       | Les échéances sont déjà en base : chaque instance fait un court balayage périodique `SELECT … WHERE ends_at <= now() FOR UPDATE SKIP LOCKED` (ou un verrou consultatif PostgreSQL par room) à la place des tâches en mémoire. Un double déclenchement serait de toute façon sans effet (transitions idempotentes, §2.8). |
| **Présence** entre instances                                              | `connected` est déjà en base ; un participant reste connecté tant qu'au moins un socket existe sur une instance (un compteur par participant, ou une clé Redis avec expiration à l'étape 3).                                                                                                                             |

Une alternative sans broker est le **routage collant par room** : le load balancer envoie le socket **et** les commandes REST d'une room à la même instance (hachage cohérent sur `room_code`, par ex. `hash … consistent` de Nginx ou HAProxy). Tout reste en mémoire, mais ajouter ou retirer une instance déplace des rooms (leurs clients se reconnectent et se resynchronisent).

Dans les deux cas, le load balancer doit accepter l'upgrade WebSocket, avec un délai d'inactivité plus long que l'intervalle du heartbeat, et un déploiement ferme les sockets avec le code `1012` (redémarrage du service) pour que les clients se reconnectent à une autre instance.

**Étape 3 : gros volume (rooms publiques, hologrammes).** `LISTEN/NOTIFY` est remplacé par **Redis pub/sub** (Redis Streams s'il devient nécessaire de rejouer des événements), la présence passe dans des clés Redis avec expiration, et les processus WebSocket peuvent être séparés des processus REST (même code, mis à l'échelle indépendamment). Redis est une nouvelle dépendance, justifiée à ce moment-là.

**Ce que le code respecte dès le jalon 1**, pour que les étapes 1 à 3 ne remplacent qu'un composant :

- Les services publient via un petit `RoomEventPublisher` (`publish(room_id, event)`), avec une implémentation en mémoire ; ils ne touchent jamais un socket. C'est la seule abstraction introduite à l'avance, car c'est la jointure dont l'étape 2 a besoin (AGENTS.md §47).
- La publication a lieu **après le commit**. Si le processus s'arrête entre les deux, le trou dans `room_version` et la resynchronisation du §2.6 le réparent : pas de table outbox à cette échelle.
- La base est la vérité (état, `ends_at`, `connected`, `room_version`) ; le processus ne garde en mémoire aucun état de room hormis ses sockets ouverts.
- Les timers appellent les mêmes transitions idempotentes du service que les commandes REST.
- Les routes REST restent sans état : n'importe quelle instance peut les servir.

### 2.10 Limites connues

- **Un seul worker** au jalon 1 : lancer le backend avec plusieurs workers séparerait les rooms (l'étape 2 est nécessaire avant).
- L'access token n'est vérifié qu'à l'ouverture du socket : une session révoquée pendant une partie continue de recevoir les événements de cette room jusqu'à la fermeture du socket (les commandes, en REST, sont refusées tout de suite). Acceptable puisque le socket ne transporte rien de privé au-delà de la room.
- Le délai d'inactivité (fermeture automatique d'une room, #90) reste à choisir.
- Un socket d'invité déjà ouvert le reste quand la place de l'invité expire, jusqu'à sa fermeture (comme une session révoquée).
- Le canal n'accepte que l'origine de `FRONTEND_BASE_URL` : ouvrir l'application par une autre adresse (par ex. `http://127.0.0.1:5173` au lieu de `http://localhost:5173`) fait refuser son canal.
- Ce qui se passe quand l'**admin de la room** se déconnecte (personne ne peut cliquer sur « suivant » ni fermer) est une question produit non couverte par les [cycles de vie](../product/milestone-1/lifecycles.fr.md) ; les timers font tout de même avancer la partie.

## 3. Dans le code

Construit dans #85. Ce qui existe aujourd'hui :

- **Événements** (`app/schemas/room_events.py`), une union discriminée sur `type`, tous porteurs de `room_version` :

  | `type`                  | `data`                                 | Envoyé quand                                                                                                                           | Frontend                    |
  | ----------------------- | -------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- | --------------------------- |
  | `participant.joined`    | `{participant_id}`                     | Un compte ou un invité rejoint (`POST /join`, `POST /guests`)                                                                          | Relit la room               |
  | `participant.presence`  | `{participant_id, connected}`          | Premier socket d'un participant ouvert ; dernier fermé depuis plus que le délai de grâce                                               | Met à jour la room en cache |
  | `participant.removed`   | `{participant_id}`                     | L'admin de la room retire ou bannit un participant (#148) ; envoyé après la fermeture de ses sockets, il ne le reçoit donc pas         | Met à jour la room en cache |
  | `room.settings_updated` | `{}`                                   | L'admin de la room change un réglage (une modification vide n'envoie rien)                                                             | Relit la room               |
  | `game.started`          | `{round_number, round_count, ends_at}` | L'admin de la room lance une partie (#91)                                                                                              | Relit la room               |
  | `participant.placed`    | `{participant_id, round_number}`       | Un participant place l'item en cours pour la première fois du tour (#92) ; un déplacement n'envoie rien. Jamais le tier ni la position | Met à jour la room en cache |
  | `round.started`         | `{round_number, round_count, ends_at}` | Un tour se termine (« suivant », timer, tout le monde a placé) et le suivant commence (#93) ; les votes absents sont enregistrés       | Relit la room               |
  | `cooldown.started`      | `{ends_at}`                            | Le dernier tour se termine : le cooldown final commence (#93)                                                                          | Relit la room               |
  | `game.closed`           | `{game_id}`                            | Le cooldown se termine (timer ou « Terminer maintenant ») : la partie est close et la room de nouveau ouverte (#96)                    | Relit la room               |

  Messages du canal : `{"type": "ping"}` du serveur, `{"type": "pong"}` et `{"type": "auth", "access_token": …}` du client. `RoomServerMessage` et `RoomClientMessage` sont ajoutés aux composants OpenAPI (`_openapi_with_room_messages` dans `app/main.py`).

- **Version de la room** : `rooms.version`, incrémentée par `RoomService` dans la même transaction que le changement (jonction, jonction d'un invité, retrait, réglages, présence), et par `GameService` (démarrage, premier placement d'un tour, fin d'un tour, fin du cooldown) ; renvoyée en `version` par l'API des rooms.
- **Authentification** : le premier message est toujours `auth`, dans le délai `ROOM_AUTH_TIMEOUT_SECONDS` : un compte envoie son access token, un invité envoie `null` et est reconnu par son cookie `guest_token` (`Path=/api/rooms/<code>`, [guide des salles](rooms.fr.md#24-invités)). Un compte passe d'abord, comme en REST.
- **Codes de fermeture** (`app/constants/rooms.py`), avec l'`ErrorCode` comme raison ; le client ne se reconnecte pas après `4401`, `4404`, `4410` et `4411` :

  | Code       | Raison              | Quand                                                                                |
  | ---------- | ------------------- | ------------------------------------------------------------------------------------ |
  | HTTP `403` | —                   | `Origin` n'est pas l'origine de `FRONTEND_BASE_URL` (refus avant la poignée de main) |
  | `4400`     | `invalid_message`   | Un message qui n'est pas `auth` d'abord, puis pas `pong`                             |
  | `4401`     | `not_authenticated` | Pas d'`auth` à temps, token invalide, ou ni token ni cookie d'invité                 |
  | `4404`     | `room_not_found`    | Room inconnue, ou le lecteur n'y a pas de place                                      |
  | `4408`     | `heartbeat_timeout` | Pas de `pong` dans le délai `ROOM_HEARTBEAT_TIMEOUT_SECONDS` après un ping           |
  | `4410`     | `removed_from_room` | L'admin de la room a retiré le participant (#148)                                    |
  | `4411`     | `room_banned`       | L'admin de la room a banni le participant (#148)                                     |

- **Réglages** (`app/core/config.py`, `.env.example`) :

  | Variable                          | Rôle                                                                                                                  | Défaut |
  | --------------------------------- | --------------------------------------------------------------------------------------------------------------------- | ------ |
  | `ROOM_HEARTBEAT_INTERVAL_SECONDS` | Ping après ce silence du client                                                                                       | `10`   |
  | `ROOM_HEARTBEAT_TIMEOUT_SECONDS`  | Socket fermé sans `pong` dans ce délai                                                                                | `5`    |
  | `ROOM_PRESENCE_GRACE_SECONDS`     | Un participant devient déconnecté ce délai après la fermeture de son dernier socket (un rechargement ne clignote pas) | `3`    |
  | `ROOM_AUTH_TIMEOUT_SECONDS`       | Délai du message `auth`                                                                                               | `5`    |

- **Démarrage** : le lifespan (`app/main.py`) remet tous les participants à déconnecté, puisqu'un processus qui démarre n'a aucun socket ouvert.
- **Robustesse** :
  - un compte dont le canal est refusé avec `4401` réessaie **une fois** avec un access token rafraîchi (le token dure 15 minutes ; un lobby ouvert plus longtemps se figerait sinon à sa reconnexion suivante) ; un second `4401` d'affilée l'arrête ;
  - après 5 ouvertures d'affilée qui n'ont jamais abouti (serveur injoignable, origine refusée, que le navigateur signale comme `1006`), le hook s'arrête et le lobby indique que les mises à jour en direct sont indisponibles ;
  - une trame binaire du client ferme le canal avec `4400` `invalid_message` ;
  - un participant qui revient pendant l'écriture de son départ est remis à connecté (`schedule_disconnect` : l'annulation ne peut pas arrêter le thread qui écrit).
- **Ordre des événements** : chaque publication est diffusée par sa propre tâche, deux événements publiés en même temps peuvent donc arriver à un socket dans le désordre. Le client voit alors un saut de version et relit la room : le résultat reste juste, au prix d'une requête.

| Couche      | Fichier                                          | Contenu                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| ----------- | ------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Route       | `api/routes/room_channel.py`                     | `WS /rooms/{code}/ws` : contrôle de l'origine, `_receive_auth`, `_find_seat` (dans le threadpool), `_serve` (présence), `_heartbeat`.                                                                                                                                                                                                                                                                                                       |
| Registre    | `services/room_channel.py`                       | `RoomEventPublisher` (protocole) et `ConnectionRegistry` (`room_connections`) : sockets ouverts par room et leur participant, `publish` confié du threadpool REST à la boucle d'événements (`call_soon_threadsafe`), départs en attente (`schedule_disconnect`, `cancel_pending_disconnect`).                                                                                                                                               |
| Service     | `services/rooms.py`                              | Publie après le commit (`_publish_joined`, réglages) ; `seat_of`, `set_presence` (n'écrit et ne publie qu'au changement), `reset_presence`.                                                                                                                                                                                                                                                                                                 |
| Dépendances | `api/dependencies.py`                            | `get_room_event_publisher`, `get_session_factory` (sessions courtes pour le canal, remplacée dans les tests). `get_connection_registry` (le registre, injecté dans la route).                                                                                                                                                                                                                                                               |
| Frontend    | `api/roomChannel.ts`                             | `useRoomEvents(code, viewer, enabled)` : ouvre `/api/rooms/<CODE>/ws`, envoie `auth` (`getAccessToken`, rafraîchi s'il manque), répond `pong`, applique les événements, relit la room après chaque (re)connexion et après un saut de version, se reconnecte avec un backoff exponentiel et de la gigue (0,5 s à 10 s). Un nouvel essai avec un token rafraîchi après `4401` ; abandonne après 5 ouvertures ratées et renvoie `unavailable`. |
| Frontend    | `components/RoomLobby.tsx`, `pages/RoomPage.tsx` | Pastille de présence (pleine en ligne, creuse hors ligne) avec un texte « en ligne » / « hors ligne » pour les lecteurs d'écran ; le hook est actif une fois la room chargée.                                                                                                                                                                                                                                                               |
| Dev         | `frontend/vite.config.ts`                        | `ws: true` sur le proxy `/api`.                                                                                                                                                                                                                                                                                                                                                                                                             |

Tests : `backend/tests/integration/test_room_channel.py`, les tests de publication de `test_rooms.py` / `test_room_guests.py` / `test_room_removal.py`, `backend/tests/test_room_connections.py` (registre), `frontend/src/api/roomChannel.test.ts` (faux `WebSocket`, `src/test/fakeWebSocket.ts`), décrits dans le [guide des tests](testing.fr.md).
