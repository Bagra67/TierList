# Images

[English](images.md) | Français

Comment les images des tuiles sont reçues, compressées, stockées, servies, nettoyées et modérées. Décidé dans le spike #75, **construit dans #81** (§3) : envoi, compression, stockage, tuiles image dans l'éditeur de template, limite d'envois par compte et ramasse-miettes. **Actions de modération construites dans #124** (§2.9) : masquer, réafficher ou supprimer une image, refus d'un fichier supprimé envoyé de nouveau. **Page des derniers envois construite dans #125** (§2.9) : la première page super admin qui liste les images et appelle ces actions. Ce qu'est une tuile pour l'utilisateur : [user stories](../product/milestone-1/user-stories.fr.md) US-1.2 et US-1.3.

## 1. Vue fonctionnelle

### Ce qui est nécessaire

- Une tuile a un **texte, une image, ou les deux** ; une tuile sans l'un ni l'autre est refusée. L'image peut être remplacée ou retirée (US-1.2, US-1.3).
- Le serveur **compresse** l'image avant de la stocker, et la tuile affiche la version stockée. Un fichier qui n'est pas une image acceptée, ou trop lourd, est refusé avec un message.
- Un template a **au plus 32 tuiles**, donc au plus 32 images.
- Les images sont affichées en deux tailles : l'**item courant**, en grand (environ 150 px sur les [écrans](../product/milestone-1/screens.fr.md)), et les **tuiles** de la tier list, en petit (environ 40 px).
- **Qui les voit** : le propriétaire du template ; chaque participant d'une partie, invités compris ; et **toute personne qui a le lien public des résultats**, sans compte et sans expiration.
- **Cycle de vie** : une partie est figée sur un instantané de son template ([modèle du domaine](../product/milestone-1/domain-model.fr.md)). Remplacer ou supprimer l'image d'une tuile, supprimer un template ou un compte ne doit jamais casser les images des parties passées.
- Seuls les **comptes** propriétaires de templates envoient des images ; jamais les invités. Chaque image a donc un auteur connu.

### Pas encore disponible

Les actions de modération (§2.9) sont appelées depuis la page des derniers envois (#125) et depuis la page d'un compte (#127) ; la file des signalements (#269) arrive avec sa propre issue.

## 2. Conception technique

### 2.1 Options étudiées

| Sujet                | Options                                                            | Choix et raison                                                                                                                                                                                                                             |
| -------------------- | ------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Bibliothèque         | **Pillow**, pyvips, ImageMagick (Wand)                             | **Pillow** : maintenu, binaires précompilés pour toutes les plateformes, prise en charge du WebP et protection contre les bombes de décompression. pyvips est plus rapide mais demande la bibliothèque système libvips ; ImageMagick aussi. |
| Stockage             | `bytea` PostgreSQL, volume local, **stockage objet compatible S3** | **S3** : la base reste petite, les fichiers survivent aux redéploiements, plusieurs instances du backend les partagent, et tous les hébergeurs le proposent. Un volume local lie l'application à une machine.                               |
| Service des fichiers | Via le backend, **bucket public ou CDN**, URL signées              | **Bucket public ou CDN** : aucune charge sur le backend, cache long. Les URL signées expirent, ce que le lien public des résultats interdit.                                                                                                |
| S3 local (dev, CI)   | **SeaweedFS**, Garage, RustFS, MinIO                               | **SeaweedFS** : Apache 2.0, un seul conteneur, pensé pour beaucoup de petits fichiers. MinIO ne publie plus d'images Docker communautaires ; Garage demande d'abord de configurer un cluster ; RustFS est plus récent.                      |

### 2.2 Fichiers acceptés

- **JPEG, PNG et WebP** (seule la première image d'un PNG ou WebP animé est gardée).
- Le format est détecté d'après le **contenu** du fichier par Pillow, jamais d'après son extension ou son `Content-Type`, que le client choisit librement.
- **Refusés** : GIF (décision produit de #81 : les tuiles sont des images fixes), SVG (il peut contenir des scripts, d'où des failles XSS), HEIC et AVIF (il faudrait un décodeur en plus ; les navigateurs convertissent déjà les photos d'iPhone en JPEG à l'envoi), et tout ce que Pillow ne sait pas ouvrir, fichiers tronqués compris.

### 2.3 Traitement

Chaque image acceptée suit le même traitement ; le fichier reçu n'est **jamais stocké** :

1. ouvrir et vérifier le fichier (Pillow), en le refusant si son image décodée aurait trop de pixels : seul l'en-tête est lu pour ce contrôle ;
2. la décoder ; un JPEG est décodé à échelle réduite (`draft` : jusqu'à 1/8, jamais sous 512 px de côté), pour qu'une photo de 40 Mpx n'occupe pas quelque 120 Mo de mémoire par envoi ;
3. appliquer l'orientation EXIF (`ImageOps.exif_transpose`), pour que les photos de téléphone soient droites ;
4. convertir le mode de couleur, **en gardant la transparence** (PNG, WebP) ;
5. la redimensionner pour que son **plus grand côté fasse 512 px**, en gardant ses proportions, avec le filtre **Lanczos** : une image plus grande est réduite (4000 × 3000 donne 512 × 384), une plus petite est **agrandie** (200 × 100 donne 512 × 256), jamais recadrée ni étirée. Le petit côté fait au moins 1 px : au-delà d'un rapport de 1024:1, il s'arrondirait à 0, une taille que Pillow refuse (2000 × 1 donne 512 × 1) ;
6. l'encoder en **WebP, qualité 80**, sans aucune métadonnée (EXIF, position GPS : vie privée). Seul le profil de couleur (ICC) est gardé, sinon les photos en couleurs étendues (Display P3) paraîtraient ternes.

Pourquoi 512 px : le plus grand affichage en partie fait environ 150 px CSS (les pages de modération montrent les images plus larges, agrandies), et un écran de densité 3 a besoin d'environ 450 pixels réels. Une seule taille est stockée : les petites tuiles utilisent le même fichier (pas de miniatures, YAGNI). Le WebP est lu par tous les navigateurs actuels et est bien plus léger que le JPEG ou le PNG à qualité égale.

Pourquoi agrandir les petites images (décidé dans #81) : toutes les images stockées ont alors la même taille, et une petite image s'affiche aussi nette que possible dans le grand cadre. Lanczos est le filtre d'interpolation classique de meilleure qualité, celui des éditeurs d'images ; il fait partie de Pillow, donc pas de bibliothèque en plus. Les agrandisseurs à base d'IA (Real-ESRGAN…) sont exclus. Agrandir n'invente pas de détails : une toute petite image (une icône de 32 px, du pixel art) sort lisse et un peu floue, pas pixelisée.

Le réencodage neutralise aussi les fichiers conçus pour être à la fois une image et autre chose (polyglottes). Le traitement utilise le CPU : la route d'envoi est synchrone, donc FastAPI l'exécute dans son threadpool sans bloquer la boucle d'événements.

Les valeurs fixes sont des constantes dans `app/constants/images.py` (`IMAGE_OUTPUT_MAX_SIDE_PX = 512`, `IMAGE_WEBP_QUALITY = 80`, formats acceptés) ; les valeurs qui peuvent changer selon l'environnement sont des réglages (§2.4).

### 2.4 Limites et réglages

| Variable                  | Description                                                                                                                                                                                   | Défaut              |
| ------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------- |
| `IMAGE_UPLOAD_MAX_BYTES`  | Taille maximale du fichier reçu ; Cloudflare accepte des corps jusqu'à 100 Mo ([guide du déploiement](deployment.fr.md)).                                                                     | `10485760` (10 Mio) |
| `IMAGE_MAX_SOURCE_PIXELS` | Nombre maximal de pixels de l'image décodée, vérifié sur l'en-tête avant le décodage : protège contre les bombes de décompression, de petits fichiers qui se décompressent en images énormes. | `40000000` (40 Mpx) |

10 Mio acceptent une photo de téléphone ; 40 Mpx acceptent les plus grands capteurs de téléphones et d'appareils photo.

Starlette reçoit tout le corps multipart, et l'écrit dans un fichier temporaire, **avant** que la route s'exécute : un corps qui **annonce** une taille au-delà de `IMAGE_UPLOAD_MAX_BYTES` plus 64 Kio d'enveloppe multipart (`Content-Length`) est donc refusé avant, avec le même `413` `image_too_large`, par un middleware ASGI pur sur l'API (`ImageUploadSizeMiddleware`, `app/core/upload_size.py`). La route refuse ensuite un fichier au-delà de `IMAGE_UPLOAD_MAX_BYTES` (elle lit au plus un octet de plus, le fichier n'entre donc jamais en mémoire) ; pour un corps envoyé sans `Content-Length`, seule la **limite du proxy** arrête un corps énorme avant sa réception : Cloudflare refuse les corps de plus de 100 Mo ([guide du déploiement](deployment.fr.md)).

Réglages du stockage :

| Variable                     | Description                                                                                                                                        | Défaut                                  |
| ---------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------- |
| `IMAGE_S3_ENDPOINT_URL`      | Adresse de l'API S3 (SeaweedFS en développement) ; absente pour AWS S3.                                                                            | absent                                  |
| `IMAGE_S3_BUCKET`            | Bucket des images.                                                                                                                                 | `tierlist-images`                       |
| `IMAGE_S3_REGION`            | Région du bucket.                                                                                                                                  | `us-east-1`                             |
| `IMAGE_S3_ACCESS_KEY_ID`     | Clé d'accès ; absente, boto3 cherche ses identifiants habituels (variables `AWS_*`, rôle de la machine).                                           | absent                                  |
| `IMAGE_S3_SECRET_ACCESS_KEY` | Clé secrète (`SecretStr`).                                                                                                                         | absent                                  |
| `IMAGE_S3_TIMEOUT_SECONDS`   | Délai des appels au stockage (connexion, puis réponse).                                                                                            | `10`                                    |
| `IMAGE_PUBLIC_BASE_URL`      | Adresse publique des images (CDN ou URL du bucket) ; l'URL d'une image est cette adresse plus sa clé. `127.0.0.1` : SeaweedFS n'écoute qu'en IPv4. | `http://127.0.0.1:8333/tierlist-images` |

Réglages contre les abus et de nettoyage :

| Variable                      | Description                                                                                        | Défaut |
| ----------------------------- | -------------------------------------------------------------------------------------------------- | ------ |
| `IMAGE_UPLOADS_PER_HOUR_MAX`  | Nombre maximal d'images envoyées par un compte sur l'heure écoulée (§2.9) ; au-delà, `429`.        | `120`  |
| `UNUSED_IMAGE_RETENTION_DAYS` | Âge en jours à partir duquel le ramasse-miettes efface une image qu'aucune tuile n'utilise (§2.8). | `7`    |

Tous sont dans `Settings` (`app/core/config.py`) et `backend/.env.example`, qui contient les valeurs de SeaweedFS.

### 2.5 Modèle de données

- Une table **`images`** : `id`, clé de stockage, largeur, hauteur, taille en octets, auteur (`owner_id`), date de création, **SHA-256 du fichier reçu**, statut de modération (`visible`, `hidden`, `deleted`). Supprimer le compte met `owner_id` à `NULL` (`ON DELETE SET NULL`) au lieu de supprimer la ligne : le ramasse-miettes retrouve encore le fichier, et une partie passée peut encore afficher l'image.
- `tiles.image_id` : clé étrangère nullable vers `images`. `snapshot_tiles.image_id`, les tuiles d'un instantané de partie, la référence de la même façon ([guide des templates](templates.fr.md), §2.4).
- **Images immuables** : la clé de stockage est aléatoire (`{uuid}.webp`). Remplacer l'image d'une tuile crée une **nouvelle** image ; un fichier existant n'est jamais écrasé. Un fichier en cache n'est donc jamais périmé, et un instantané retrouve toujours l'image avec laquelle il a été pris.
- **Statut et empreinte** (utilisés par la modération, §2.9) : la clé de stockage ne change jamais, l'emplacement du fichier suit le statut : à sa clé quand elle est `visible`, sous `quarantine/{clé}` quand elle est `hidden`, nulle part quand elle est `deleted`. La ligne d'une image supprimée est gardée : son SHA-256 est l'empreinte bannie (le `BannedFingerprint` du [modèle du domaine](../product/milestone-2/domain-model.fr.md)), il n'y a donc pas de table des empreintes bannies ; l'index `ix_images_sha256` sert la vérification à l'envoi.

### 2.6 API

- `POST /images` (`multipart/form-data`, un champ `file`, authentifié) : vérifie la taille, traite et stocke l'image, renvoie `201` et `{id, url, width, height}`.
- Les corps de création et de modification d'une tuile ont `image_id` (une image visible de l'appelant, sinon `404`) ; `TileResponse` a `image_url`, `null` sans image. Une tuile a un texte, une image ou les deux (`422` `tile_empty` sinon) ; dans une modification, `image_id: null` retire l'image. Détails dans le [guide des templates](templates.fr.md). Une image peut servir à plusieurs tuiles.
- `TileResponse` (modèles) et `CurrentItemResponse` (parties, résultats, lien public des résultats compris) ont `image_removed` : `true` quand l'image est masquée ou supprimée par la modération ; `image_url` vaut alors `null`, puisque le fichier n'est plus à son adresse publique. `optional_image_url` et `is_image_removed` (`app/api/presenters/images.py`) calculent les deux, pour que toutes les réponses concordent.
- `TileResponse` a aussi `image_status` et `image_moderation_reason`, pour le seul propriétaire du modèle : `CurrentItemResponse` ne les montre pas aux joueurs ([guide des templates](templates.fr.md#27-modération)).
- Les routes de modération (`POST /moderation/images/{image_id}/hide`, `/unhide`, `/delete`) sont décrites au §2.9.
- Codes d'erreur, traduits en FR et EN. Le frontend affiche `max_bytes` en mégaoctets (formateur i18next `megabytes`) :

| Situation                                 | HTTP | Code API                                           |
| ----------------------------------------- | ---- | -------------------------------------------------- |
| Pas une image acceptée, ou fichier banni  | 415  | `image_unsupported_format`                         |
| Fichier trop lourd                        | 413  | `image_too_large` (param `max_bytes`)              |
| Trop de pixels une fois décodée           | 422  | `image_too_many_pixels`                            |
| Image inconnue, ou d'un autre utilisateur | 404  | `image_not_found`                                  |
| Trop d'envois sur l'heure écoulée         | 429  | `image_upload_limit_reached` (param `max_uploads`) |
| Tuile sans texte ni image                 | 422  | `tile_empty`                                       |

### 2.7 Stockage et service

L'**API S3 est utilisée partout**, via un seul service `ImageStorage` (`save`, `delete`, `url`, et pour la modération `copy_to_quarantine`, `copy_from_quarantine`, `presigned_url`) construit sur **boto3** : le développement et la CI exécutent exactement le code de la production.

| Environnement       | Service S3                                                                                                                                                                                                                                                           |
| ------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Développement et CI | Conteneur **SeaweedFS** (`weed mini` : maître, volume, filer et S3 dans un seul processus), comme Mailpit remplace un fournisseur SMTP. Même service dans `compose.yaml` et dans le job backend de la CI (`docker compose up -d --wait seaweedfs`). Voir ci-dessous. |
| Production          | **Scaleway Object Storage**, un bucket public par environnement ([guide du déploiement](deployment.fr.md)). Lecture publique par l'URL du bucket (`IMAGE_PUBLIC_BASE_URL`), ou un CDN plus tard.                                                                     |

SeaweedFS en développement :

- Image épinglée à une version exacte (`chrislusf/seaweedfs:4.48`), ports publiés sur `127.0.0.1` seulement : l'**API S3** sur `8333` et l'**interface web du filer** sur **http://localhost:8888**, qui montre les images dans `buckets/tierlist-images/` et les ouvre. `dev.sh` / `dev.ps1` l'ouvrent sur le bucket.
- Le bucket est créé au démarrage (`-bucket=tierlist-images`) ; le conteneur est prêt (healthy) dès qu'il existe.
- `seaweedfs/s3.json` définit deux identités : le backend (clé `tierlist-dev`, lecture, écriture, liste et ACL de ses objets, sur le bucket seulement : chaque image est envoyée en `public-read`) et `anonymous` (**lecture** seule, pour que les URL des images marchent sans authentification ; lister, écrire et supprimer sont refusés). `seaweedfs/security.toml` contient une clé de signature du filer, réservée au développement : sans elle, SeaweedFS refuse de charger les identités.
- Les données sont gardées dans le volume Docker `seaweedfs-data`.

- Chaque objet est écrit avec l'ACL `public-read` (chez Scaleway, un objet reste privé même dans un bucket public), `Content-Type: image/webp` et `Cache-Control: public, max-age=86400` : **un jour**. Le contenu d'une clé ne change jamais, un an avec `immutable` serait donc possible ; un jour est choisi (review de #81) pour qu'une image masquée par la modération ou effacée quitte les caches des navigateurs en 24 heures au plus. Il n'y a pas encore de CDN, donc rien à purger ; un CDN devra purger tout de suite l'URL d'une image masquée (§2.9).
- **Modèle d'accès** : les URL des images sont publiques mais **impossibles à deviner** (UUID aléatoire). Quiconque a une URL peut voir l'image, ce que le lien public des résultats impose de toute façon : une image utilisée dans une partie devient publique par ce lien.
- **Quarantaine** : le fichier d'une image masquée par la modération est copié sous le préfixe `quarantine/` (`IMAGE_QUARANTINE_PREFIX`) avec l'ACL `private`, puis retiré de sa clé publique (§2.9). `quarantine_key(clé)` donne cet emplacement ; la clé de stockage en base ne change pas. La clé de quarantaine n'est jamais envoyée telle quelle à un client : les super admins voient une image masquée par une URL signée (§2.9).
- **Limite en développement** : l'identité `anonymous` de SeaweedFS lit tout le bucket, quelle que soit l'ACL de l'objet : en local, un fichier en quarantaine se lit par qui connaît sa clé. La quarantaine est privée chez Scaleway, où les ACL des objets s'appliquent.

### 2.8 Nettoyage

Aucun fichier n'est supprimé quand une tuile change, puisqu'un instantané peut encore l'utiliser. Un **ramasse-miettes** périodique efface les images qu'aucune tuile ni aucun instantané ne référence et qui ont été créées il y a plus d'un délai de grâce : ce délai part de l'envoi, pas du dernier usage. Il couvre les envois abandonnés (envoyés mais jamais rattachés à une tuile), la purge des templates supprimés et la suppression des comptes, qui ne retirent que des lignes en base (`ON DELETE CASCADE` sur les templates et les tuiles ; les lignes des images restent, sans auteur). Il tourne chaque nuit dans le processus de l'application, avec les autres purges ([guide de déploiement](deployment.fr.md#23-tâches-de-nuit), #192), et peut aussi être lancé en ligne de commande, comme `scripts/purge_deleted_templates.py` :

```bash
cd backend
uv run python scripts/purge_unused_images.py   # affiche "Unused images purged: n"
```

- Elle efface les images **visibles** créées il y a plus de `UNUSED_IMAGE_RETENTION_DAYS` jours qu'aucune tuile ni aucune tuile d'instantané n'utilise. Les images masquées ou supprimées par la modération gardent leur ligne (#124).
- Les lignes sont supprimées d'abord, en une seule requête, puis les fichiers : une tuile ne pointe jamais vers un fichier effacé. Une tuile qui rattache l'une de ces images au même moment attend la fin de la suppression, puis échoue sur la clé étrangère. Un fichier qu'on n'arrive pas à effacer (stockage en panne) est journalisé avec sa clé, pour l'effacer à la main.
- La relancer ne pose aucun problème : elle n'efface que ce qui a expiré.

### 2.9 Modération

Tout se fait **dans l'application**, dans des pages super admin, sans outil externe. #81 l'a préparée (les colonnes `sha256` et statut, la limite d'envois par compte) ; #124 a construit les **actions** ci-dessous ; #125 la page des derniers envois. Les autres pages qui listent les images sont des issues à part :

- **Traçabilité** : chaque image a un auteur, une date, et les tuiles et instantanés qui l'utilisent se retrouvent par les clés étrangères. Un super admin remonte d'une image à son auteur et aux parties concernées.
- **Pages super admin** :
  - **rôle et autorisation** vérifiés côté serveur (#123) ;
  - **derniers envois** : une grille des dernières images avec auteur, date et nombre d'utilisations, pour une revue proactive, peu coûteuse puisque les images font au plus 512 px (#125, construite : `GET /moderation/images` et `/moderation/uploads`, [guide de la modération](moderation.fr.md)) ;
  - **file des signalements** : images, templates, pseudos et parties signalés par les utilisateurs, invités compris, avec motif et décision ; c'est aussi le mécanisme de notification des contenus illicites (#126) ;
  - **page d'un compte** : toutes les images d'un compte, masquage en masse, sanctions du compte (#127, construite : `/moderation/accounts/{id}`, [guide de la modération](moderation.fr.md#28-comptes)).

  La page des derniers envois et la page d'un compte appellent les routes ci-dessous ; la file des signalements le fera aussi.

**Actions** (#124, US-1.4, US-1.6). Trois routes, protégées par `SuperAdminDep` et qui déclarent `SUPER_ADMIN_RESPONSES` ([guide de la modération](moderation.fr.md)), chacune avec le corps `{reason}` (`ModerationReasonRequest` : 1 à 500 caractères, espaces de début et de fin retirés) et la réponse `204` :

| Route                                       | Possible depuis     | Effet                                                                                              |
| ------------------------------------------- | ------------------- | -------------------------------------------------------------------------------------------------- |
| `POST /moderation/images/{image_id}/hide`   | `visible`           | Statut `hidden` ; le fichier passe sous `quarantine/{clé}`, en privé, gardé en cas de recours.     |
| `POST /moderation/images/{image_id}/unhide` | `hidden`            | Statut `visible` ; le fichier revient à sa clé publique.                                           |
| `POST /moderation/images/{image_id}/delete` | `visible`, `hidden` | Statut `deleted` ; le fichier est effacé définitivement ; la ligne garde le statut et l'empreinte. |

- Erreurs : `404` `image_not_found` (image inconnue), `409` `image_moderation_conflict` (l'action ne s'applique pas au statut actuel). `POST` plutôt que `DELETE`, puisque l'action porte un motif et que la ligne reste.
- `ImageModerationService(session, storage, moderation_log)` (`app/services/image_moderation.py`) lit l'image avec `SELECT … FOR UPDATE` (`get_image_for_update`) : deux super admins qui agissent en même temps sur la même image ne déplacent pas son fichier deux fois. Chaque action est écrite au [journal de modération](moderation.fr.md) dans la même transaction que le nouveau statut : `target_type` `image`, `target_id` l'identifiant de l'image, `target_label` sa clé de stockage (aucun nom de fichier n'est gardé).
- **Ordre des étapes**, choisi pour échouer du côté sûr :
  - **masquer** : copier le fichier sous `quarantine/{clé}` avec l'ACL `private` (`copy_to_quarantine`) → statut `hidden` et entrée du journal → commit → effacer le fichier public. Si le commit échoue, la transaction est annulée et la copie en quarantaine effacée : l'image reste publique et inchangée ;
  - **réafficher** : recopier le fichier à sa clé (`copy_from_quarantine` : `public-read`, les mêmes `Content-Type` et `Cache-Control` qu'à l'envoi, `MetadataDirective=REPLACE`) → statut `visible` et entrée du journal → commit → effacer la copie en quarantaine. Si le commit échoue, la copie publique est effacée ;
  - **supprimer** : statut `deleted` et entrée du journal → commit → effacer le fichier là où il est (sa clé, ou `quarantine/{clé}` pour une image masquée).
- Un fichier qu'on n'arrive pas à effacer **après** le commit est journalisé avec sa clé, pour l'effacer à la main, comme dans le ramasse-miettes : la décision reste, et l'API ne donne plus l'adresse de l'image. Une erreur de stockage **avant** le commit (stockage en panne) n'est pas rattrapée et donne une `500`, comme à l'envoi ; rien n'a changé alors.
- **Aperçu pour les super admins** (#125) : les derniers envois (`GET /moderation/images`) listent les images visibles et masquées, jamais les supprimées (plus de fichier). Une image visible est donnée à son adresse publique ; une image masquée par une **URL signée** de son fichier en quarantaine (`ImageStorage.presigned_url`, valable `IMAGE_PREVIEW_URL_EXPIRES_SECONDS` = 900 s, 15 minutes, calculée localement par boto3 sans appel au stockage). Le backend ne sert aucun octet et la quarantaine reste privée ; qui détient le lien peut lire le fichier pendant 15 minutes. Seuls les super admins reçoivent ces liens.
- **Affichage** : une image masquée ou supprimée a `image_url: null` et `image_removed: true` dans toutes les réponses (§2.6). Le frontend affiche à sa place un visuel « image retirée » (`RemovedImage`) partout : éditeur de modèle, écrans de partie et de résultats, lien public des résultats compris. Dans l'éditeur, le propriétaire peut toujours la remplacer ou la retirer, et une tuile dont l'image est retirée compte comme ayant une image (son texte reste facultatif).
- **Motif** (`moderation_reason`, 500 caractères au plus) : rempli quand une image est masquée ou supprimée, vidé quand elle est réaffichée, pour que le propriétaire le lise (US-1.10, #270). Il est copié sur l'image parce que le journal de modération est purgé après 3 ans, et qu'une image peut rester retirée plus longtemps. La ligne d'une image modérée survit au compte : supprimer le compte efface le motif (`clear_moderation_reasons_of_owner`). Une image modérée avant cette colonne n'a pas de motif : les écrans ne montrent alors que la décision.
- **Pas de nouvel envoi** : l'envoi calcule le SHA-256 du fichier reçu, avant de le compresser, et le refuse quand une image `deleted` a le même (`is_fingerprint_banned`). Le refus est le `415` `image_unsupported_format` habituel, sans dire pourquoi ; le serveur le journalise. Masquer ne bannit pas : une image masquée peut encore être réaffichée. Plus tard, une empreinte perceptuelle (dHash, calculée avec Pillow, sans nouvelle dépendance) pourra repérer les variantes réencodées.
- La [politique de confidentialité](legal-pages.fr.md) indique que l'empreinte d'une image est gardée, et combien de temps les images modérées sont conservées.
- **Limites contre les abus** : un nombre maximal d'envois par compte et par heure (#81) ; les invités ne peuvent pas envoyer d'image.
- **Contrainte de stockage** : comme les URL sont publiques et mises en cache, masquer une image agit sur le **stockage**, pas seulement en base. Il n'y a pas encore de CDN ; celui qui sera choisi doit permettre de purger une URL, et masquer la purgera alors ([TODO](../../TODO.fr.md)).
- **Mis de côté** : la détection automatique de contenus NSFW. Elle demande un modèle d'IA ou un service externe ; à l'échelle prévue, la revue des envois et les signalements suffisent. Gardée pour plus tard, peut-être en fonctionnalité payante, avec un modèle open source exécuté par le backend plutôt qu'un service externe (#128).

### 2.10 Dépendances

Ajoutées avec #81 :

- **Pillow** : lecture, vérification et redimensionnement des images, encodage WebP, protection contre les bombes de décompression. Aucun équivalent dans les dépendances actuelles.
- **boto3** : le client S3 de référence, compatible avec tous les fournisseurs S3 et avec SeaweedFS.
- **boto3-stubs[s3]** (développement seulement) : types du client S3 pour Pyright.

`python-multipart`, nécessaire pour recevoir un fichier, est déjà installé par `fastapi[standard]`.

### 2.11 Limites connues

- Pas de quota de stockage par compte : 32 images par template, sans limite sur le nombre de templates.
- Les images de réponse du mode à l'aveugle et les futures photos de profil réutiliseront ce traitement ; leurs tailles seront décidées avec elles.
- Les navigateurs qui ont déjà affiché une image masquée peuvent la garder dans leur cache **jusqu'à un jour** (`max-age`). Il n'y a pas encore de CDN : quand il y en aura un, masquer devra aussi purger son cache (§2.9).
- En développement et en CI, la quarantaine n'est pas privée : SeaweedFS laisse n'importe qui lire tout le bucket (§2.7).
- Seules la page des derniers envois et la page d'un compte appellent les actions de modération pour l'instant : la file des signalements (#269) reste à faire.
- L'URL signée d'une image masquée se lit par qui la détient, jusqu'à son expiration (15 minutes).
- Seul le fichier exact est refusé après une suppression : une copie réencodée ou redimensionnée passe tant qu'il n'y a pas d'empreinte perceptuelle.

## 3. Dans le code

Backend (tests : [guide des tests](testing.fr.md)) :

| Fichier                            | Rôle                                                                                                                                                                                                                                                                                                                                                                                                                      |
| ---------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `app/api/routes/images.py`         | `POST /images` : transforme les erreurs en `415`, `413` (param `max_bytes`), `422` et `429` (param `max_uploads`).                                                                                                                                                                                                                                                                                                        |
| `app/services/images.py`           | `ImageService.upload` : vérifie la limite horaire, lit le fichier sans dépasser la limite de taille, refuse une empreinte bannie, le compresse, l'écrit sous une nouvelle clé, puis enregistre la ligne (le fichier est retiré si cela échoue ; un échec de cette suppression est journalisé avec la clé). `purge_unused` : le ramasse-miettes du §2.8.                                                                   |
| `app/repositories/images.py`       | Image visible d'un auteur, image verrouillée pour la modération (`get_image_for_update`), empreinte bannie (`is_fingerprint_banned`), nombre d'envois récents, suppression des images inutilisées ; pour la page des derniers envois, `list_recent_images`, `template_names_by_image`, `game_counts_by_image`.                                                                                                            |
| `app/services/image_moderation.py` | `ImageModerationService` : `hide`, `unhide`, `delete` (§2.9).                                                                                                                                                                                                                                                                                                                                                             |
| `app/api/routes/moderation.py`     | `POST /moderation/images/{image_id}/hide`, `/unhide`, `/delete` : transforment les erreurs en `404` et `409`. Corps `ModerationReasonRequest` (`app/schemas/moderation.py`). `GET /moderation/images` : les derniers envois (`RecentUploadsService`, `app/services/recent_uploads.py`), chacun construit par `recent_upload_response` (`app/api/presenters/images.py`).                                                   |
| `app/services/templates.py`        | Tuiles avec une image : `_check_owned_image`, règle « un texte ou une image » (`TileEmptyError`).                                                                                                                                                                                                                                                                                                                         |
| `app/schemas/templates.py`         | `TileResponse.image_url` et `image_removed` (mêmes champs dans `CurrentItemResponse`, `app/schemas/rooms.py`). L'adresse vient de `image_url` ou, pour une tuile qui peut ne pas avoir d'image ou en avoir une retirée, de `optional_image_url` ; `is_image_removed` donne `image_removed` (`app/api/presenters/images.py`, le seul endroit qui construit l'adresse publique d'une image : tuiles, item en cours, envoi). |
| `app/models/tile.py`               | `Tile.image_id` et `Tile.image` ; migration `a2ee58bb5b26_add_image_id_to_tiles.py`.                                                                                                                                                                                                                                                                                                                                      |
| `scripts/purge_unused_images.py`   | Commande du ramasse-miettes.                                                                                                                                                                                                                                                                                                                                                                                              |
| `app/services/image_processing.py` | `compress_image` : le traitement Pillow du §2.3, une fonction pure.                                                                                                                                                                                                                                                                                                                                                       |
| `app/services/image_storage.py`    | `ImageStorage` (`save`, `delete`, `url`, `copy_to_quarantine`, `copy_from_quarantine`, `presigned_url`) sur un client boto3, partagé entre les requêtes ; `quarantine_key`.                                                                                                                                                                                                                                               |
| `app/models/image.py`              | Modèle `Image` et `ImageStatus` ; migration `ef5839ce8066_create_images.py` ; index `ix_images_created_at`, migration `4840e3c37d23_add_created_at_index_to_images.py`.                                                                                                                                                                                                                                                   |
| `app/constants/images.py`          | Formats, taille de sortie, qualité WebP, `Content-Type`, `Cache-Control` et ACL des objets, préfixe et ACL de la quarantaine (`IMAGE_QUARANTINE_PREFIX`, `IMAGE_QUARANTINE_ACL`), durée de l'aperçu signé (`IMAGE_PREVIEW_URL_EXPIRES_SECONDS`).                                                                                                                                                                          |
| `app/core/config.py`               | Réglages `IMAGE_*` (§2.4).                                                                                                                                                                                                                                                                                                                                                                                                |

Développement : `compose.yaml` et `seaweedfs/` (§2.7).

Frontend (détails dans le [guide des templates](templates.fr.md#3-dans-le-code)) :

- `components/ImageDropZone.tsx` : la vignette d'image d'une tuile, sur toute la largeur de sa carte dans l'éditeur, l'image montrée entière (jamais recadrée). Un clic ouvre le sélecteur de fichier ; on peut y déposer un fichier, avec une mise en évidence pendant le glisser. L'image choisie s'affiche aussitôt, avec un indicateur pendant l'envoi. Un petit bouton retire l'image. Avec `imageRemoved`, une image retirée par la modération montre le visuel « image retirée », et peut toujours être remplacée ou retirée. Un fichier d'un autre type connu que JPEG, PNG ou WebP (`constants/images.ts`) est refusé aussitôt, sans être envoyé ; un fichier de type inconnu est envoyé. Le backend reste l'autorité.
- `components/TileEditor.tsx` : l'image de chaque tuile peut être remplacée (clic ou dépôt) ou retirée ; la nouvelle tuile prend un texte, une image ou les deux ; une image retirée par la modération compte encore comme une image, le texte reste donc facultatif. Une image est envoyée dès qu'elle est choisie, puis rattachée par `image_id`. Plusieurs images d'un coup (#242, `useBulkImageTiles`) : chacune passe par le même `POST /images`, trois à la fois (`BULK_IMAGE_UPLOAD_CONCURRENCY`), et compte dans la limite par heure ; les tuiles sont ensuite créées dans l'ordre de la sélection. Un fichier d'un type refusé et ce qui dépasse les places libres du modèle sont mis de côté avant tout envoi.
- `api/images.ts` : `useUploadImage` (`POST /images`, `multipart/form-data`).
- `components/RemovedImage.tsx` : le visuel « image retirée » (une icône, avec le texte `common.imageRemoved` quand il y a la place, et ce texte comme nom accessible), à la taille de l'image qu'il remplace. Utilisé par `ImageDropZone` et `GameItemView` (item en cours, plateau et écrans de résultats).
- `pages/RecentUploadsPage.tsx`, `components/UploadCard.tsx`, `components/ModerationReasonDialog.tsx` : la page des derniers envois des super admins et ses actions ([guide de la modération](moderation.fr.md)).
- Les codes d'erreur sont traduits dans `src/i18n/locales/`, et `src/i18n/index.ts` définit le formateur `megabytes`.
