# Modération

[English](moderation.md) | Français

Comment la modération des contenus publics est construite : le **journal de modération** (#267) et les premières actions, sur les **images** (#124). Le rôle super admin et sa vérification sont dans le [guide de l'authentification](authentication.fr.md#super-admins) ; ce que la modération fait pour l'utilisateur : [user stories](../product/milestone-2/user-stories.fr.md) (épopée E1), [cycles de vie](../product/milestone-2/lifecycles.fr.md).

## 1. Vue fonctionnelle

Chaque décision d'un super admin (classer un signalement sans suite, masquer, réafficher ou supprimer un contenu, bannir ou lever un bannissement) est écrite au **journal de modération** (US-1.9) : **qui** a décidé, **quand**, **quoi** (l'action et sa cible) et **pourquoi** (le motif).

- Seuls les super admins voient le journal, dans l'espace de modération (`/moderation/log`) : des plus récentes aux plus anciennes, 50 entrées à la fois (« Voir plus »), filtrées par **cible** (un texte cherché dans le nom de la cible) ou par **super admin**.
- Personne ne peut modifier ni supprimer une entrée : aucune route ne le permet. Seule la purge de nuit supprime les entrées de plus de **3 ans** (la durée annoncée par la [politique de confidentialité](legal-pages.fr.md)).
- Une entrée reste lisible après la suppression de la cible ou du compte du super admin : elle garde une copie de leurs noms.

Les premières actions qui écrivent au journal sont celles sur les images (#124) : masquer, réafficher ou supprimer une image (§2.2). Les autres cibles arrivent avec leurs issues (#268 : masquer ou supprimer un modèle).

## 2. Fonctionnement technique

### 2.1 La table `moderation_actions`

| Colonne        | Contenu                                                                                                                                    |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| `created_at`   | Heure de l'action (`clock_timestamp()`), indexée : le journal est trié dessus. Pas d'`updated_at` : une entrée ne change jamais.           |
| `actor_id`     | Le super admin (`users.id`), indexé pour le filtre. `ON DELETE SET NULL` : supprimer le compte garde l'entrée.                             |
| `actor_name`   | Copie du nom du super admin au moment de l'action.                                                                                         |
| `action`       | `ModerationActionKind` : `dismiss`, `hide`, `unhide`, `delete`, `ban`, `lift_ban`. Texte avec une contrainte CHECK (`text_enum`).          |
| `target_type`  | `ModerationTargetType` : `template`, `image`, `account`, `nickname`, `game`.                                                               |
| `target_id`    | Identifiant de la cible, **sans clé étrangère** : la cible peut être supprimée, l'entrée reste. Vide quand la cible n'a pas d'identifiant. |
| `target_label` | Copie du nom de la cible au moment de l'action (nom du modèle, du compte, pseudo…), 200 caractères au plus.                                |
| `reason`       | Le motif écrit par le super admin, 500 caractères au plus.                                                                                 |

La copie des noms suit les parties terminées (`game_players.display_name`) : le journal doit rester complet pour les autres super admins, quoi qu'il arrive ensuite au compte ou au contenu.

### 2.2 Écrire une entrée

Chaque action de modération appelle `ModerationLogService.record(actor, action, target_type, target_id, target_label, reason)` **dans sa propre transaction**. `record` ajoute l'entrée et fait un `flush`, mais **ne valide pas** la transaction : c'est l'action qui la valide, pour que l'action et sa trace réussissent ou échouent ensemble (jamais un modèle masqué sans son entrée, ni une entrée pour une action qui a échoué).

`ImageModerationService` (`app/services/image_moderation.py`) est l'exemple à suivre. Il reçoit `ModerationLogService` par injection (`get_image_moderation_service`), avec la même session que la requête, et chaque action change le statut et écrit l'entrée avant un seul commit :

```python
image.status = ImageStatus.HIDDEN
self._moderation_log.record(
    super_admin,
    ModerationActionKind.HIDE,
    ModerationTargetType.IMAGE,
    image.id,
    image.storage_key,  # aucun nom de fichier n'est gardé : la clé est unique
    reason,
)
self._session.commit()
```

Actions existantes :

| Méthode | Chemin                                 | Action et cible   | Possible depuis     |
| ------- | -------------------------------------- | ----------------- | ------------------- |
| `POST`  | `/moderation/images/{image_id}/hide`   | `hide`, `image`   | `visible`           |
| `POST`  | `/moderation/images/{image_id}/unhide` | `unhide`, `image` | `hidden`            |
| `POST`  | `/moderation/images/{image_id}/delete` | `delete`, `image` | `visible`, `hidden` |

- Corps `{reason}` (`ModerationReasonRequest` : le motif, 1 à 500 caractères, espaces de début et de fin retirés) ; réponse `204` ; `404` `image_not_found`, `409` `image_moderation_conflict` quand l'action ne s'applique pas au statut actuel. Protégées comme le journal (§2.3).
- `POST` plutôt que `DELETE` : l'action porte un motif dans son corps, et la ligne de l'image reste.
- L'image est verrouillée (`SELECT … FOR UPDATE`) pendant l'action ; son fichier passe dans une quarantaine privée ou en revient, ou est effacé, dans un ordre qui échoue du côté sûr. Détails : [guide des images](images.fr.md#29-modération).
- Aucune page n'appelle encore ces routes : les pages super admin qui listent les images (#125, #126, #127) le feront. D'ici là, elles s'essaient depuis Swagger (`/docs`).

Une nouvelle action ou un nouveau type de cible est une nouvelle valeur d'enum : `text_enum` stocke du texte avec une contrainte CHECK, la migration ne change donc que la contrainte (pas d'`ALTER TYPE`).

### 2.3 Lire le journal

| Méthode | Chemin                     | Réponse                                                                               |
| ------- | -------------------------- | ------------------------------------------------------------------------------------- |
| `GET`   | `/moderation/log`          | `{ entries, has_more }` : une page du journal, de la plus récente à la plus ancienne. |
| `GET`   | `/moderation/super-admins` | `[{ id, display_name }]` par nom : les options du filtre « Super admin ».             |

- Les deux sont protégées par `SuperAdminDep` et déclarent `SUPER_ADMIN_RESPONSES` (`401` sans session, `403` `super_admin_required` pour un autre compte).
- `/moderation/log` prend `limit` (50 par défaut, 100 au plus), `offset`, `actor_id` et `target`. La pagination fonctionne comme l'[historique](results.fr.md#28-historique) : le service lit `limit + 1` entrées pour savoir s'il reste une page, et l'ordre `created_at desc, id` ne saute jamais d'entrée entre deux pages.
- `target` est cherché dans `target_label`, sans casse (`ILIKE`), `%` et `_` étant lus comme des caractères ordinaires (`icontains(..., autoescape=True)`).

### 2.4 Purge

`ModerationLogService.purge_expired` supprime les entrées plus anciennes que `MODERATION_LOG_RETENTION_DAYS` (1095 jours par défaut) et valide la transaction. Elle tourne chaque nuit avec les autres purges (`purge_moderation_log` dans `maintenance.py`, [guide du déploiement](deployment.fr.md#23-tâches-de-nuit)) ; c'est le seul endroit où une entrée est supprimée. Pas de script en ligne de commande : la tâche de nuit suffit.

### 2.5 La page

`/moderation` mène à `/moderation/log` tant que le journal est la seule page de l'espace de modération. `ModerationLayout` affiche le menu de gauche de l'espace (seulement « Journal » pour l'instant ; les signalements et les derniers envois arriveront avec leurs issues), dans `RequireSuperAdmin`.

`ModerationLogPage` affiche un tableau (quand, qui, action, cible, motif) qui défile seul sur un petit écran. Le filtre **Cible** est appliqué à l'envoi de la recherche (bouton ou Entrée) : une requête par recherche, pas une par lettre ; le filtre **Super admin** est appliqué tout de suite. Les filtres font partie de la clé de requête de `useModerationLog` : en changer repart de la première page.

### 2.6 Réglages

| Variable                        | Rôle                                                    | Défaut |
| ------------------------------- | ------------------------------------------------------- | ------ |
| `MODERATION_LOG_RETENTION_DAYS` | Jours pendant lesquels une entrée du journal est gardée | `1095` |

La changer oblige à changer aussi la politique de confidentialité ([pages légales](legal-pages.fr.md)).

## 3. Dans le code

| Couche       | Fichier                                                                               | Contenu                                                                                                                 |
| ------------ | ------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| Routes       | `backend/app/api/routes/moderation.py`                                                | `GET /moderation/log`, `GET /moderation/super-admins`, `POST /moderation/images/{image_id}/hide`, `/unhide`, `/delete`. |
| Schémas      | `backend/app/schemas/moderation.py`                                                   | `ModerationActionResponse`, `ModerationLogResponse`, `SuperAdminResponse`, `ModerationReasonRequest`.                   |
| Service      | `backend/app/services/moderation_log.py`                                              | `ModerationLogService` : `record`, `page`, `super_admins`, `purge_expired`.                                             |
| Service      | `backend/app/services/image_moderation.py`                                            | `ImageModerationService` : `hide`, `unhide`, `delete` ([guide des images](images.fr.md)).                               |
| Repositories | `repositories/moderation_actions.py`, `repositories/users.py`                         | Requêtes : ajouter, lister avec les filtres, supprimer avant une date ; les super admins par nom.                       |
| Modèle       | `backend/app/models/moderation_action.py`                                             | `ModerationAction` (`moderation_actions`) ; enums dans `models/enums.py`.                                               |
| Constantes   | `backend/app/constants/moderation.py`                                                 | Longueurs du motif et du libellé, tailles de page.                                                                      |
| Migration    | `migrations/versions/1c5aea95404b_create_moderation_actions.py`                       | Crée la table, ses contraintes CHECK et ses index.                                                                      |
| Frontend     | `api/moderation.ts`, `components/ModerationLayout.tsx`, `pages/ModerationLogPage.tsx` | Hooks, menu de l'espace, page du journal.                                                                               |

Tests : [guide des tests](testing.fr.md) (`test_moderation_log.py`, `test_moderation_routes.py`, `test_image_moderation.py`, `ModerationLogPage.test.tsx`).
