# Templates

[English](templates.md) | Français

Comment les templates sont stockés et exposés par l'API : modèle de données, endpoints, suppression logique et purge, et où cela se trouve dans le code. Ce qu'est un template pour l'utilisateur : [produit](../product/product.fr.md).

## 1. Vue fonctionnelle

Un template est ce qu'on classe : ses **tiers** (les lignes de la tier list) et ses **tuiles** (les items à classer). Il est **privé** à son propriétaire.

| Action                | Endpoint                 | Résultat                                                                                                                 |
| --------------------- | ------------------------ | ------------------------------------------------------------------------------------------------------------------------ |
| Créer un template     | `POST /templates`        | Un template avec les six tiers par défaut (S à E) et sans tuile.                                                         |
| Lister mes templates  | `GET /templates`         | Mes templates actifs, avec leur nombre de tuiles, le plus récemment modifié d'abord.                                     |
| Ouvrir un template    | `GET /templates/{id}`    | Le template, ses tiers et ses tuiles, triés par position.                                                                |
| Renommer un template  | `PATCH /templates/{id}`  | Le nouveau nom ; la date de dernière modification est mise à jour.                                                       |
| Supprimer un template | `DELETE /templates/{id}` | Le template disparaît aussitôt pour son propriétaire, puis est effacé définitivement après la durée de rétention (§2.3). |

Côté frontend, la page _Mes templates_ liste, crée et supprime les templates ; ouvrir un template affiche ses tiers, en lecture seule jusqu'à l'arrivée de l'éditeur (#79, #80). Voir §3.

### Règles

- **Nom** : 1 à 100 caractères, espaces de début et de fin retirés (un nom fait seulement d'espaces est vide, donc refusé avec une `422`).
- **Tiers par défaut**, du haut vers le bas : `S` `#FF7F7F`, `A` `#FFBF7F`, `B` `#FFDF7F`, `C` `#FFFF7F`, `D` `#BFFF7F`, `E` `#7FFF7F` (`DEFAULT_TIERS`, `app/constants/templates.py`).
- **Dernière modification** (`updated_at`) : change quand le template change, et doit aussi changer quand un de ses tiers ou une de ses tuiles change : le service la met à jour explicitement (§2.2). C'est la date montrée à l'utilisateur et l'ordre de la liste.
- **Confidentialité** : un template d'un autre utilisateur répond `404`, exactement comme un template inconnu ou supprimé : l'API ne révèle jamais qu'il existe.
- **La suppression du compte** efface les templates de l'utilisateur, y compris ceux déjà supprimés.

### Messages

L'API renvoie un **code** d'erreur ; le frontend le traduit (`errors.api.*` dans `frontend/src/i18n/locales/`).

| Situation                                            | HTTP | Code API             | Traduction (FR / EN)                                                                   |
| ---------------------------------------------------- | ---- | -------------------- | -------------------------------------------------------------------------------------- |
| Template inconnu, supprimé ou d'un autre utilisateur | 404  | `template_not_found` | `Ce template est introuvable.` / `This template could not be found.`                   |
| Nom invalide (vide, trop long)                       | 422  | `validation_error`   | `Certains champs sont invalides.` / `Some fields are invalid.`, plus l'erreur du champ |
| Access token absent ou invalide                      | 401  | `not_authenticated`  | Géré par le client API : rafraîchissement de la session, sinon retour à `/login`       |

## 2. Conception technique

### 2.1 Modèle de données

```
users ──< templates ──< tiers
              │
              └──────< tiles
```

| Table       | Colonnes                                                                                                     | Remarques                                                       |
| ----------- | ------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------- |
| `templates` | `id`, `owner_id` → `users`, `name` (100), `created_at`, `updated_at`, `deleted_at`                           | `ON DELETE CASCADE` vers `users` ; index sur `owner_id`.        |
| `tiers`     | `id`, `template_id` → `templates`, `name` (50), `color` (`#RRGGBB`), `position`, dates                       | `ON DELETE CASCADE` vers `templates` ; `position` 0 = en haut.  |
| `tiles`     | `id`, `template_id` → `templates`, `text` (200, vide pour une tuile qui n'a qu'une image), `position`, dates | `ON DELETE CASCADE` vers `templates` ; `position` 0 = première. |

`position` n'a **pas de contrainte d'unicité** : un réordonnancement la violerait le temps de décaler les autres lignes. Le service garde les positions continues.

### 2.2 Mixins des modèles

Les colonnes communes sont partagées par des mixins SQLAlchemy (`app/db/mixins.py`). Chaque modèle ne prend que ceux dont il a besoin :

| Mixin                 | Colonnes                   | Utilisé par                |
| --------------------- | -------------------------- | -------------------------- |
| `UUIDPrimaryKeyMixin` | `id` (UUID v4)             | `Template`, `Tier`, `Tile` |
| `TimestampMixin`      | `created_at`, `updated_at` | `Template`, `Tier`, `Tile` |
| `SoftDeleteMixin`     | `deleted_at` (nullable)    | `Template`                 |

- Les dates sont posées par PostgreSQL avec `clock_timestamp()` et non `now()` : `now()` est le début de la transaction, identique pour toutes les écritures d'une même transaction.
- `onupdate` ne voit que les `UPDATE` de la ligne elle-même : quand un tier ou une tuile change, le service doit mettre à jour le `updated_at` du template explicitement.
- `SoftDeleteMixin` n'est volontairement pas mis partout : une table supprimée logiquement oblige chaque requête à filtrer `deleted_at`.

### 2.3 Suppression logique et purge

`DELETE /templates/{id}` ne fait que renseigner `deleted_at`. Chaque requête du repository filtre `deleted_at IS NULL` : le template disparaît aussitôt pour son propriétaire (`404`, absent de la liste).

La commande `scripts/purge_deleted_templates.py` efface ensuite définitivement les templates supprimés depuis plus de `DELETED_TEMPLATE_RETENTION_DAYS` jours ; leurs tiers et leurs tuiles partent avec eux (`ON DELETE CASCADE`). Elle journalise et affiche le nombre de templates purgés, et peut être relancée sans risque : elle ne supprime que ce qui a expiré.

```bash
# dans backend/
uv run python scripts/purge_deleted_templates.py
```

Elle doit être planifiée une fois par jour sur le serveur (cron ou tâche planifiée de l'hébergeur) : voir la [TODO](../../TODO.fr.md). Sans elle, les templates supprimés restent en base.

### 2.4 Réglages

| Variable                          | Rôle                                                                     | Défaut |
| --------------------------------- | ------------------------------------------------------------------------ | ------ |
| `DELETED_TEMPLATE_RETENTION_DAYS` | Jours pendant lesquels un template supprimé reste en base avant la purge | `30`   |

### 2.5 Endpoints

Chaque route exige l'access token Bearer (`401` sinon).

| Méthode et chemin        | Corps    | Succès                       | Erreurs             |
| ------------------------ | -------- | ---------------------------- | ------------------- |
| `POST /templates`        | `{name}` | `201` `TemplateResponse`     | `401`, `422`        |
| `GET /templates`         | —        | `200` `TemplateListResponse` | `401`               |
| `GET /templates/{id}`    | —        | `200` `TemplateResponse`     | `401`, `404`        |
| `PATCH /templates/{id}`  | `{name}` | `200` `TemplateResponse`     | `401`, `404`, `422` |
| `DELETE /templates/{id}` | —        | `204`                        | `401`, `404`        |

- `TemplateResponse` vaut `{id, name, created_at, updated_at, tiers: [{id, name, color, position}], tiles: [{id, text, position}]}`, tiers et tuiles triés par `position`.
- `TemplateListResponse` vaut `{items: [{id, name, tile_count, updated_at}]}`. Un objet plutôt qu'un tableau, pour qu'une pagination (#105) puisse ajouter un champ sans casser le contrat. La liste est lue en **une seule requête** : la base compte les tuiles (pas de N+1).

### 2.6 Limites connues

- Pas encore de pagination de la liste (#105).
- Pas encore de vue super admin des templates supprimés (#104).
- Les tiers et les tuiles ne se modifient pas encore par l'API : seuls les tiers par défaut existent, et aucune tuile.

## 3. Dans le code

### Backend (`backend/app/`)

| Couche        | Fichier                                                                       | Contenu                                                                                                                                                     |
| ------------- | ----------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Routes        | `api/routes/templates.py`                                                     | Les cinq routes `/templates` ; traduisent `TemplateNotFoundError` en `404` `template_not_found`.                                                            |
| Dépendances   | `api/dependencies.py`, `api/responses.py`                                     | `get_template_service` ; `UNAUTHORIZED_RESPONSE`, la `401` documentée dans OpenAPI, partagée avec les routes `/auth`.                                       |
| Schémas       | `schemas/templates.py`                                                        | `CreateTemplateRequest`, `RenameTemplateRequest` (règle `TemplateName` commune), `TemplateResponse`, `TemplateListResponse`.                                |
| Service       | `services/templates.py`                                                       | `TemplateService` : création avec les tiers par défaut, liste, lecture, renommage, suppression logique, `purge_deleted`. Porte les transactions (`commit`). |
| Repository    | `repositories/templates.py`                                                   | Requêtes uniquement : template actif d'un propriétaire (avec tiers et tuiles), liste avec nombre de tuiles, purge.                                          |
| Modèles       | `models/template.py`, `models/tier.py`, `models/tile.py`, `db/mixins.py`      | Un fichier par classe ; les mixins du §2.2.                                                                                                                 |
| Exceptions    | `exceptions/templates.py`                                                     | `TemplateNotFoundError`.                                                                                                                                    |
| Constantes    | `constants/templates.py`, `constants/error_codes.py`, `constants/messages.py` | Longueurs liées au schéma, `DEFAULT_TIERS`, code `TEMPLATE_NOT_FOUND` et message pour les développeurs.                                                     |
| Configuration | `core/config.py`                                                              | `DELETED_TEMPLATE_RETENTION_DAYS`.                                                                                                                          |
| Migration     | `migrations/versions/855df2a2ea2b_create_templates_tiers_and_tiles.py`        | Crée les trois tables.                                                                                                                                      |
| Commande      | `scripts/purge_deleted_templates.py` (dans `backend/`)                        | Purge du §2.3.                                                                                                                                              |

### Frontend (`frontend/src/`)

| Couche      | Fichier                                         | Contenu                                                                                                                                                         |
| ----------- | ----------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| API         | `api/templates.ts`                              | Une fonction par endpoint utilisé (liste, lecture, création, suppression) et les hooks `useTemplates`, `useTemplate`, `useCreateTemplate`, `useDeleteTemplate`. |
| Constantes  | `constants/templates.ts`, `constants/routes.ts` | `TEMPLATE_NAME_MAX_LENGTH` (égale au backend), les clés de cache ; `ROUTES.TEMPLATES`, `ROUTES.TEMPLATE_EDITOR` et `templateEditorPath(id)`.                    |
| Pages       | `pages/TemplatesPage.tsx`                       | _Mes templates_ (`/templates`) : nom, nombre de tuiles et date de dernière modification de chaque template, état vide, états de chargement et d'erreur.         |
|             | `pages/TemplateEditorPage.tsx`                  | `/templates/:templateId` : nom et tiers du template, en lecture seule pour l'instant ; l'édition des tiers (#79) et des tuiles (#80) viendra ici.               |
| Composants  | `components/CreateTemplateDialog.tsx`           | `<dialog>` natif : nom obligatoire, erreur du champ issue de la `422`, puis ouverture du nouveau template.                                                      |
|             | `components/DeleteTemplateDialog.tsx`           | `<dialog>` natif de confirmation ; la liste est rafraîchie après la suppression.                                                                                |
| Navigation  | `components/MainNav.tsx` (dans `Layout.tsx`)    | Liens _Accueil_ et _Mes templates_ dans l'en-tête, affichés une fois connecté.                                                                                  |
| Traductions | `i18n/locales/fr.ts`, `en.ts`                   | `nav.*`, `templates.*` (nombre de tuiles avec pluriel, date formatée dans la langue de l'interface) et `errors.api.template_not_found`.                         |

Chaque modification invalide le cache `['templates']` : la liste et les templates ouverts sont relus.

### Tests

`backend/tests/integration/test_templates.py` (endpoints) et `test_template_purge.py` (purge), sur un vrai PostgreSQL ; `frontend/src/pages/TemplatesPage.test.tsx` et `TemplateEditorPage.test.tsx` pour les écrans. Tous sont décrits dans le [guide des tests](testing.fr.md).
