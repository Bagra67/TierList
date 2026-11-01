# Modération

[English](moderation.md) | Français

Comment la modération des contenus publics est construite : le **journal de modération** (#267), les actions sur les **images** (#124) et sur les **modèles** (#268), et la page des **derniers envois** qui appelle celles des images (#125). Le rôle super admin et sa vérification sont dans le [guide de l'authentification](authentication.fr.md#super-admins) ; ce que la modération fait pour l'utilisateur : [user stories](../product/milestone-2/user-stories.fr.md) (épopée E1), [cycles de vie](../product/milestone-2/lifecycles.fr.md).

## 1. Vue fonctionnelle

Chaque décision d'un super admin (classer un signalement sans suite, masquer, réafficher ou supprimer un contenu, bannir ou lever un bannissement) est écrite au **journal de modération** (US-1.9) : **qui** a décidé, **quand**, **quoi** (l'action et sa cible) et **pourquoi** (le motif).

- Seuls les super admins voient le journal, dans l'espace de modération (`/moderation/log`) : des plus récentes aux plus anciennes, 50 entrées à la fois (« Voir plus »), filtrées par **cible** (un texte cherché dans le nom de la cible) ou par **super admin**.
- Personne ne peut modifier ni supprimer une entrée : aucune route ne le permet. Seule la purge de nuit supprime les entrées de plus de **3 ans** (la durée annoncée par la [politique de confidentialité](legal-pages.fr.md)).
- Une entrée reste lisible après la suppression de la cible ou du compte du super admin : elle garde une copie de leurs noms.

Les actions qui écrivent au journal sont celles sur les images (#124) et sur les modèles (#268) : masquer, réafficher ou supprimer une image ou un modèle (§2.2). Les autres cibles arrivent avec leurs issues. Un modèle masqué par la modération n'ouvre plus de salle ni ne lance de partie, tandis que son propriétaire le modifie encore et voit le motif ([guide des templates](templates.fr.md#27-modération)). Aucune page n'appelle encore les actions sur les modèles : leurs boutons viendront avec la page utilisateur (#127) et la file des signalements (#269) ; d'ici là, elles s'appellent depuis Swagger (`/docs`).

Les super admins passent aussi en revue les **derniers envois** (US-1.7, #125), la première page de l'espace de modération (`/moderation/uploads`) : les dernières images, des plus récentes aux plus anciennes, avec leur auteur, leur date et leur usage (modèles, parties), filtrées par auteur, jours d'envoi et statut (§2.6). Chaque image peut y être masquée, réaffichée ou supprimée, avec un motif. Une image masquée reste visible des seuls super admins, par un lien temporaire. La [politique de confidentialité](legal-pages.fr.md) dit que les super admins voient les images envoyées avec le nom de leur auteur.

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

`ImageModerationService` (`app/services/image_moderation.py`) est l'exemple à suivre ; `TemplateModerationService` (`app/services/template_moderation.py`, injecté par `get_template_moderation_service`) fonctionne de la même façon. Il reçoit `ModerationLogService` par injection (`get_image_moderation_service`), avec la même session que la requête, et chaque action change le statut et écrit l'entrée avant un seul commit :

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

| Méthode | Chemin                                       | Action et cible      | Possible depuis                             |
| ------- | -------------------------------------------- | -------------------- | ------------------------------------------- |
| `POST`  | `/moderation/images/{image_id}/hide`         | `hide`, `image`      | `visible`                                   |
| `POST`  | `/moderation/images/{image_id}/unhide`       | `unhide`, `image`    | `hidden`                                    |
| `POST`  | `/moderation/images/{image_id}/delete`       | `delete`, `image`    | `visible`, `hidden`                         |
| `POST`  | `/moderation/templates/{template_id}/hide`   | `hide`, `template`   | visible (`moderation` `none`), non supprimé |
| `POST`  | `/moderation/templates/{template_id}/unhide` | `unhide`, `template` | `moderation` `hidden`, non supprimé         |
| `POST`  | `/moderation/templates/{template_id}/delete` | `delete`, `template` | visible ou masqué, non supprimé             |

- Corps `{reason}` (`ModerationReasonRequest` : le motif, 1 à 500 caractères, espaces de début et de fin retirés) ; réponse `204` ; `404` `image_not_found` / `template_not_found` (un modèle purgé est introuvable), `409` `image_moderation_conflict` / `template_moderation_conflict` quand l'action ne s'applique pas au statut actuel. Protégées comme le journal (§2.3).
- `POST` plutôt que `DELETE` : l'action porte un motif dans son corps, et la ligne de l'image ou du modèle reste.
- L'image est verrouillée (`SELECT … FOR UPDATE`) pendant l'action ; son fichier passe dans une quarantaine privée ou en revient, ou est effacé, dans un ordre qui échoue du côté sûr. Détails : [guide des images](images.fr.md#29-modération).
- Le modèle est verrouillé de la même façon, quel que soit son propriétaire, supprimé ou non (`get_template_for_update`). Masquer enregistre `moderation` `hidden` et copie le motif sur le modèle, puisque le journal est purgé après 3 ans ; réafficher l'efface ; supprimer renseigne `deleted_at` comme une suppression par le propriétaire (puis la purge de nuit). Le changement passe par un `UPDATE` qui garde `updated_at`, la dernière modification du propriétaire. L'entrée du journal a pour cible `template`, avec le nom du modèle pour libellé. Détails : [guide des templates](templates.fr.md#27-modération).
- La page des derniers envois (§2.6) appelle les actions sur les images ; la file des signalements (#269) et la fiche utilisateur (#127) appelleront les deux.

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

`/moderation` mène à la première page du menu, les derniers envois (`/moderation/uploads`, §2.6). `ModerationLayout` affiche le menu de gauche de l'espace, « Derniers envois » puis « Journal » (les signalements arriveront avec leur issue), dans `RequireSuperAdmin`.

`ModerationLogPage` affiche un tableau (quand, qui, action, cible, motif) qui défile seul sur un petit écran. Le filtre **Cible** est appliqué à l'envoi de la recherche (bouton ou Entrée) : une requête par recherche, pas une par lettre ; le filtre **Super admin** est appliqué tout de suite. Les filtres font partie de la clé de requête de `useModerationLog` : en changer repart de la première page.

### 2.6 Derniers envois

La première page de l'espace de modération (US-1.7, #125) : les dernières images envoyées, pour repérer un problème avant qu'on le signale, et agir tout de suite.

| Méthode | Chemin               | Réponse                                                                                                   |
| ------- | -------------------- | --------------------------------------------------------------------------------------------------------- |
| `GET`   | `/moderation/images` | `{ images, has_more }` : une page des images visibles et masquées, de la plus récente à la plus ancienne. |

- Protégée par `SuperAdminDep` et déclare `SUPER_ADMIN_RESPONSES`, comme le journal (§2.3).
- Paramètres :
  - `limit` (24 par défaut, une grille de 3 colonnes ; 96 au plus) et `offset` ;
  - `author` : un texte cherché dans le nom **ou** l'e-mail de l'auteur, sans casse, `%` et `_` étant lus comme des caractères ordinaires (`icontains(..., autoescape=True)`) ; au plus la longueur maximale d'un e-mail ;
  - `created_after` (inclus) et `created_before` (exclu) : la période d'envoi, en `AwareDatetime`. Le fuseau horaire est exigé : une date sans fuseau est refusée avec `422`, car elle serait ambiguë ;
  - `status` : `visible` ou `hidden` ; sans lui, les deux. Une image `deleted` n'a plus de fichier et n'est **jamais listée**.
- Chaque image : `{ id, url, status, created_at, author_name, template_names, game_count }`. `author_name` vaut `null` une fois le compte de l'auteur supprimé ; `template_names` sont les modèles, non supprimés, dont une tuile montre l'image, par ordre alphabétique ; `game_count` est le nombre de parties distinctes, en cours ou terminées, jouées sur un instantané qui la montre.
- Ordre `created_at desc, id` (l'identifiant départage les égalités) et `limit + 1` images lues pour remplir `has_more`, comme le journal. L'index `ix_images_created_at` (migration `4840e3c37d23`) sert le tri.
- Une page coûte **3 requêtes**, quelle que soit sa taille (pas de N+1), assemblées par `RecentUploadsService` (`app/services/recent_uploads.py`) : les images avec le nom de leur auteur (`list_recent_images`, jointure externe sur `users`), puis les noms des modèles de toutes les images de la page (`template_names_by_image`, tuiles jointes aux modèles sans `deleted_at`), puis leur nombre de parties (`game_counts_by_image`, `snapshot_tiles` joint à `games` par `snapshot_id`, parties distinctes comptées).
- **Adresse d'une image masquée** : son fichier n'est plus à son adresse publique. `recent_upload_response` (`app/api/presenters/images.py`) donne à la place une **URL signée** de son fichier en quarantaine (`ImageStorage.presigned_url`, valable 15 minutes). Le backend ne sert aucun octet et la quarantaine reste privée ; qui détient le lien peut lire le fichier pendant 15 minutes. Détails : [guide des images](images.fr.md#29-modération).

La page, `RecentUploadsPage` (`/moderation/uploads`) :

- **Filtres** : **Auteur** est appliqué à l'envoi de la recherche (bouton ou Entrée), comme **Cible** dans le journal. **Du** et **Au** sont des jours, dans le fuseau du super admin, envoyés comme le début du premier jour et le début du jour qui suit le dernier (dates ISO avec fuseau) : le dernier jour est inclus. **Statut** : tous, visibles ou masquées. Les filtres font partie de la clé de requête de `useRecentUploads` (`useInfiniteQuery`) : en changer repart de la première page ; « Voir plus » lit la page suivante, à partir du nombre d'images déjà affichées.
- **Cartes** (`UploadCard`) : l'image (son texte alternatif donne l'auteur et la date) ; un badge **Masquée** écrit en texte sur une image masquée, pas seulement une couleur ; l'auteur, ou « Compte supprimé » ; la date ; le nombre de modèles et de parties (pluriels i18next) ; les noms des modèles (formateur i18next `list`). Les noms de l'auteur et des modèles sont du texte simple : les liens arriveront avec la fiche utilisateur (#127) et une page de modèle.
- **Actions**, selon le statut : **Masquer** et **Supprimer** sur une image visible, **Réafficher** et **Supprimer** sur une image masquée. Leurs noms accessibles donnent l'auteur et la date de l'image.
- Chaque action ouvre **`ModerationReasonDialog`**, un dialogue générique (titre, description, libellés des boutons, destructif ou non) prévu aussi pour les prochaines pages de modération (#269, #127). Le motif est obligatoire et ne peut pas être fait que d'espaces, 500 caractères au plus (`MODERATION_REASON_MAX_LENGTH`, recopiée dans `frontend/src/constants/moderation.ts` ; le backend reste l'autorité). Le bouton est rouge pour une suppression et désactivé pendant l'action (pas de double envoi) ; un échec affiche son erreur traduite dans le dialogue, qui se ferme une fois l'action réussie.
- `useModerateImage` appelle la route de l'action (§2.2), puis invalide les derniers envois et le journal, qui sont relus.

### 2.7 Réglages

| Variable                        | Rôle                                                    | Défaut |
| ------------------------------- | ------------------------------------------------------- | ------ |
| `MODERATION_LOG_RETENTION_DAYS` | Jours pendant lesquels une entrée du journal est gardée | `1095` |

La changer oblige à changer aussi la politique de confidentialité ([pages légales](legal-pages.fr.md)).

## 3. Dans le code

| Couche       | Fichier                                                                                                                                                                                                               | Contenu                                                                                                                                                                                                                                    |
| ------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Routes       | `backend/app/api/routes/moderation.py`                                                                                                                                                                                | `GET /moderation/log`, `GET /moderation/super-admins`, `GET /moderation/images`, `POST /moderation/images/{image_id}/hide`, `/unhide`, `/delete`, `POST /moderation/templates/{template_id}/hide`, `/unhide`, `/delete`.                   |
| Schémas      | `backend/app/schemas/moderation.py`                                                                                                                                                                                   | `ModerationActionResponse`, `ModerationLogResponse`, `SuperAdminResponse`, `ModerationReasonRequest`, `RecentUploadResponse`, `RecentUploadsResponse`.                                                                                     |
| Présentation | `backend/app/api/presenters/images.py`                                                                                                                                                                                | `recent_upload_response` : URL publique, ou URL signée de la quarantaine pour une image masquée.                                                                                                                                           |
| Service      | `backend/app/services/moderation_log.py`                                                                                                                                                                              | `ModerationLogService` : `record`, `page`, `super_admins`, `purge_expired`.                                                                                                                                                                |
| Service      | `backend/app/services/image_moderation.py`                                                                                                                                                                            | `ImageModerationService` : `hide`, `unhide`, `delete` ([guide des images](images.fr.md)).                                                                                                                                                  |
| Service      | `backend/app/services/template_moderation.py`                                                                                                                                                                         | `TemplateModerationService` : `hide`, `unhide`, `delete` ([guide des templates](templates.fr.md#27-modération)).                                                                                                                           |
| Service      | `backend/app/services/recent_uploads.py`                                                                                                                                                                              | `RecentUploadsService.page` : une page des derniers envois avec leur usage.                                                                                                                                                                |
| Repositories | `repositories/moderation_actions.py`, `repositories/users.py`, `repositories/images.py`, `repositories/templates.py`                                                                                                  | Requêtes : ajouter, lister avec les filtres, supprimer avant une date ; les super admins par nom ; les images récentes, leurs modèles et leurs parties ; un modèle de n'importe quel propriétaire, verrouillé (`get_template_for_update`). |
| Modèle       | `backend/app/models/moderation_action.py`                                                                                                                                                                             | `ModerationAction` (`moderation_actions`) ; enums dans `models/enums.py`.                                                                                                                                                                  |
| Constantes   | `backend/app/constants/moderation.py`, `constants/images.py`                                                                                                                                                          | Longueurs du motif, du libellé et du filtre d'auteur, tailles de page ; `IMAGE_PREVIEW_URL_EXPIRES_SECONDS` (900).                                                                                                                         |
| Migration    | `migrations/versions/1c5aea95404b_create_moderation_actions.py`                                                                                                                                                       | Crée la table, ses contraintes CHECK et ses index.                                                                                                                                                                                         |
| Migration    | `migrations/versions/4840e3c37d23_add_created_at_index_to_images.py`                                                                                                                                                  | `ix_images_created_at`, le tri des derniers envois.                                                                                                                                                                                        |
| Migration    | `migrations/versions/507b5cf96d8d_add_moderation_to_templates.py`                                                                                                                                                     | `templates.moderation` et `templates.moderation_reason` ([guide des templates](templates.fr.md#27-modération)).                                                                                                                            |
| Frontend     | `api/moderation.ts`, `components/ModerationLayout.tsx`, `pages/ModerationLogPage.tsx`, `pages/RecentUploadsPage.tsx`, `components/UploadCard.tsx`, `components/ModerationReasonDialog.tsx`, `constants/moderation.ts` | Hooks (`useModerationLog`, `useRecentUploads`, `useModerateImage`), menu de l'espace, page du journal, page des derniers envois et ses cartes, dialogue du motif, longueur du motif.                                                       |

Tests : [guide des tests](testing.fr.md) (`test_moderation_log.py`, `test_moderation_routes.py`, `test_image_moderation.py`, `test_template_moderation.py`, `test_recent_uploads.py`, `ModerationLogPage.test.tsx`, `RecentUploadsPage.test.tsx`, `ModerationReasonDialog.test.tsx`).
