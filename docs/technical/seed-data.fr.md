# Jeu de données de test

[English](seed-data.md) | Français

Un jeu de données de test réaliste (comptes, modèles, images, parties terminées, salles ouvertes, journal de modération) pour essayer l'application en vrai, en développement local et sur staging. Jamais en production.

## 1. Ce qui est créé

| Données               | Quantité et cas                                                                                                                                                                                    |
| --------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Comptes               | 36 : 6 super admins (`seed-admin-1` à `-6`), 24 joueurs confirmés (`seed-player-1` à `-24`), 3 adresses non confirmées (`seed-unverified-…`), 3 comptes Google sans mot de passe (`seed-google-…`) |
| Modèles               | 30 : 3 vides, 9 en texte (6 à 10 tuiles), 6 avec images (12 tuiles), 6 pleins (32 tuiles, le maximum), 6 supprimés                                                                                 |
| Images                | 72, générées (une couleur, une forme, un numéro), envoyées sur le vrai stockage d'images                                                                                                           |
| Parties terminées     | 75 sur 90 jours, de 2 à 8 joueurs avec des invités, des votes absents et des éléments que personne n'a placés. `seed-player-1` est dans 65 d'entre elles : un historique de 4 pages                |
| Salles ouvertes       | 9 : 3 dont le salon montre les parties passées, 3 pleines (10 places), 3 avec un compte et un invité bannis, aux réglages variés                                                                   |
| Journal de modération | 180 entrées des 6 super admins sur 120 jours, toutes les actions et cibles : 4 pages                                                                                                               |

- Toutes les adresses sont en `seed-…@seed.example.com` : un domaine réservé, aucun e-mail ne peut y arriver.
- Tous les comptes ont le même mot de passe : `seed-password-local` en local, le secret `SEED_PASSWORD` sur staging.
- Les données sont les mêmes à chaque lancement : les tirages aléatoires utilisent une graine fixe.

## 2. Le lancer

**En local**, avec la base et le stockage d'images de `compose.yaml` démarrés (environ 15 secondes) :

```bash
cd backend
uv run python scripts/seed.py
```

**Sur staging** : GitHub → Actions → **Seed staging** → Run workflow (`seed-staging.yml`). Le pod de staging n'a pas de shell : le script tourne sur un runner GitHub, avec les réglages de base et de stockage d'images de l'environnement `staging`. Avant le premier lancement, ajoutez le secret `SEED_PASSWORD` à cet environnement. Si l'adresse de la base vue d'un runner diffère de celle du pod de l'application, remplissez les variables `SEED_POSTGRES_HOST` et `SEED_POSTGRES_PORT`.

Le script journalise chacune de ses 6 étapes avec sa durée, et sa progression dans les plus longues (chaque modèle, chaque image, chaque partie terminée, toutes les 30 entrées du journal) : le journal du workflow montre où il en est. Il finit par ce qu'il a supprimé et créé, et le temps passé.

## 3. Règles

- **Il remplace ses propres données, et seulement elles.** Chaque lancement supprime d'abord tout ce qui appartient aux comptes `seed-…@seed.example.com`, puis crée un nouveau jeu. Les autres comptes ne sont jamais touchés : sur staging, les vrais comptes de test restent. Les parties d'une salle seed jouées par un vrai compte partent avec les données seed.
- **Jamais en production.** Le script refuse toute base qui n'est ni `tierlist` (local) ni `…_staging`, et le workflow n'est relié qu'à l'environnement `staging`.
- **Pas de mot de passe connu sur un site public.** Sur une base `…_staging`, `SEED_PASSWORD` est obligatoire : le mot de passe local est écrit dans le dépôt et donnerait à n'importe qui un compte super admin.
- **Les salles ouvertes ne durent pas.** Une salle où personne n'est connecté est fermée après `ROOM_INACTIVITY_HOURS` (24 h). Relancez le jeu de données pour retrouver les salles ; les parties terminées restent.
- **Les modèles supprimés** le sont au moment du lancement : la purge de nuit les efface 30 jours plus tard.

## 4. Comment il est construit

`backend/app/seed/`, un module par domaine, enchaînés par `run.py` :

| Module          | Contenu                                                                                                                                                                                                        |
| --------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `sizes.py`      | `FULL_SIZE` (le jeu ci-dessus) et `SMALL_SIZE` (les mêmes cas, en moins grand nombre, pour les tests).                                                                                                         |
| `guard.py`      | La vérification de la base et la règle de `SEED_PASSWORD`.                                                                                                                                                     |
| `cleanup.py`    | Supprime les données seed dans un ordre qui ne laisse aucune ligne orpheline (journal, parties, instantanés, images et leurs fichiers, puis comptes), car plusieurs liens vers les comptes sont en `SET NULL`. |
| `accounts.py`   | `AuthService.register`, puis le rôle et l'adresse confirmée ; les comptes Google comme une première connexion avec Google.                                                                                     |
| `templates.py`  | `TemplateService` et `ImageService.upload` (un propriétaire d'images par modèle à images : au plus 120 envois par heure et par compte).                                                                        |
| `games.py`      | Les parties terminées, écrites directement dans leur état de clôture (ci-dessous), et les salles ouvertes qui gardent leurs parties.                                                                           |
| `rooms.py`      | Les salles pleines et les salles avec bannissements, par `RoomService` (avec un publisher qui n'envoie rien : personne n'est connecté).                                                                        |
| `moderation.py` | `ModerationLogService.record`, puis daté dans le passé.                                                                                                                                                        |

Tout passe par les vrais services, sauf les **parties terminées** : les jouer par `GameService`, un placement à la fois, recharge la salle à chaque appel (245 000 requêtes pour 75 parties : 5 minutes en local, bien plus sur staging à travers Internet). Elles sont écrites dans l'état que laisse `GameService._close_game` : un instantané pris par `TemplateService.take_snapshot`, un tour par tuile, un joueur figé par personne qui joue, un placement de tour par élément (sans tier pour un vote absent) et un placement final au même endroit pour chaque élément placé, des positions continues dans chaque tier, et un lien de résultats.

### Le garder à jour

Quand une fonctionnalité ajoute des données ou des cas à essayer en vrai (signalements, modèles publics, j'aime…), le jeu de données les couvre dans la même pile ([AGENTS.md](../../AGENTS.md)) : un nouveau module ou de nouveaux cas dans un module existant, une quantité dans `sizes.py`, la suppression dans `cleanup.py` si un nouveau lien vers les comptes est en `SET NULL`, et les tests (`test_seed.py`).

Tests : [guide des tests](testing.fr.md) (`test_seed.py`, `test_seed_guard.py`).
