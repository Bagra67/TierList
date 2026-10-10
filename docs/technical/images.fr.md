# Images

[English](images.md) | Français

Comment les images des tuiles sont reçues, compressées, stockées, servies, nettoyées et modérées. Décidé dans le spike #75, construit dans #81 : **l'envoi, la compression, le stockage, les tuiles image, la limite d'envois par compte et le ramasse-miettes sont implémentés** (§3) ; l'éditeur arrive avec la suite de #81. Ce qu'est une tuile pour l'utilisateur : [user stories](../product/milestone-1/user-stories.fr.md) US-1.2 et US-1.3.

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

L'éditeur de template n'envoie ni n'affiche encore d'image : cela arrive avec la suite de #81. Le ramasse-miettes est une commande qui reste à planifier sur le serveur ([TODO](../../TODO.fr.md)). Les fonctionnalités de modération sont des issues à part (§2.9).

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
2. appliquer l'orientation EXIF (`ImageOps.exif_transpose`), pour que les photos de téléphone soient droites ;
3. convertir le mode de couleur, **en gardant la transparence** (PNG, WebP) ;
4. la redimensionner pour que son **plus grand côté fasse 512 px**, en gardant ses proportions, avec le filtre **Lanczos** : une image plus grande est réduite (4000 × 3000 donne 512 × 384), une plus petite est **agrandie** (200 × 100 donne 512 × 256), jamais recadrée ni étirée ;
5. l'encoder en **WebP, qualité 80**, sans aucune métadonnée (EXIF, position GPS : vie privée). Seul le profil de couleur (ICC) est gardé, sinon les photos en couleurs étendues (Display P3) paraîtraient ternes.

Pourquoi 512 px : le plus grand affichage fait environ 150 px CSS, et un écran de densité 3 a besoin d'environ 450 pixels réels. Une seule taille est stockée : les petites tuiles utilisent le même fichier (pas de miniatures, YAGNI). Le WebP est lu par tous les navigateurs actuels et est bien plus léger que le JPEG ou le PNG à qualité égale.

Pourquoi agrandir les petites images (décidé dans #81) : toutes les images stockées ont alors la même taille, et une petite image s'affiche aussi nette que possible dans le grand cadre. Lanczos est le filtre d'interpolation classique de meilleure qualité, celui des éditeurs d'images ; il fait partie de Pillow, donc pas de bibliothèque en plus. Les agrandisseurs à base d'IA (Real-ESRGAN…) sont exclus. Agrandir n'invente pas de détails : une toute petite image (une icône de 32 px, du pixel art) sort lisse et un peu floue, pas pixelisée.

Le réencodage neutralise aussi les fichiers conçus pour être à la fois une image et autre chose (polyglottes). Le traitement utilise le CPU : la route d'envoi est synchrone, donc FastAPI l'exécute dans son threadpool sans bloquer la boucle d'événements.

Les valeurs fixes sont des constantes dans `app/constants/images.py` (`IMAGE_OUTPUT_MAX_SIDE_PX = 512`, `IMAGE_WEBP_QUALITY = 80`, formats acceptés) ; les valeurs qui peuvent changer selon l'environnement sont des réglages (§2.4).

### 2.4 Limites et réglages

| Variable                  | Description                                                                                                                                                                         | Défaut              |
| ------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------- |
| `IMAGE_UPLOAD_MAX_BYTES`  | Taille maximale du fichier reçu, vérifiée pendant sa lecture ; à garder alignée sur la limite du reverse proxy.                                                                     | `10485760` (10 Mio) |
| `IMAGE_MAX_SOURCE_PIXELS` | Nombre maximal de pixels de l'image décodée (`MAX_IMAGE_PIXELS` de Pillow) : protège contre les bombes de décompression, de petits fichiers qui se décompressent en images énormes. | `40000000` (40 Mpx) |

10 Mio acceptent une photo de téléphone ; 40 Mpx acceptent les plus grands capteurs de téléphones et d'appareils photo.

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

| Variable                      | Description                                                                                                               | Défaut |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------------------- | ------ |
| `IMAGE_UPLOADS_PER_HOUR_MAX`  | Nombre maximal d'images envoyées par un compte sur l'heure écoulée (§2.9) ; au-delà, `429`.                               | `120`  |
| `UNUSED_IMAGE_RETENTION_DAYS` | Jours pendant lesquels une image qu'aucune tuile n'utilise est gardée avant d'être effacée par le ramasse-miettes (§2.8). | `7`    |

Tous sont dans `Settings` (`app/core/config.py`) et `backend/.env.example`, qui contient les valeurs de SeaweedFS.

### 2.5 Modèle de données

- Une table **`images`** : `id`, clé de stockage, largeur, hauteur, taille en octets, auteur (`owner_id`), date de création, **SHA-256 du fichier reçu**, statut de modération (`visible`, `hidden`, `deleted`). Supprimer le compte met `owner_id` à `NULL` (`ON DELETE SET NULL`) au lieu de supprimer la ligne : le ramasse-miettes retrouve encore le fichier, et une partie passée peut encore afficher l'image.
- `tiles.image_id` : clé étrangère nullable vers `images`. Les tuiles d'un instantané de partie référenceront `image_id` de la même façon.
- **Images immuables** : la clé de stockage est aléatoire (`{uuid}.webp`). Remplacer l'image d'une tuile crée une **nouvelle** image ; un fichier existant n'est jamais écrasé. Les caches peuvent garder un fichier indéfiniment, et un instantané retrouve toujours l'image avec laquelle il a été pris.

### 2.6 API

- `POST /images` (`multipart/form-data`, un champ `file`, authentifié) : vérifie la taille, traite et stocke l'image, renvoie `201` et `{id, url, width, height}`.
- Les corps de création et de modification d'une tuile ont `image_id` (une image visible de l'appelant, sinon `404`) ; `TileResponse` a `image_url`, `null` sans image. Une tuile a un texte, une image ou les deux (`422` `tile_empty` sinon) ; dans une modification, `image_id: null` retire l'image. Détails dans le [guide des templates](templates.fr.md). Une image peut servir à plusieurs tuiles.
- Codes d'erreur, traduits en FR et EN. Le frontend affiche `max_bytes` en mégaoctets (formateur i18next `megabytes`) :

| Situation                                 | HTTP | Code API                                           |
| ----------------------------------------- | ---- | -------------------------------------------------- |
| Pas une image acceptée                    | 415  | `image_unsupported_format`                         |
| Fichier trop lourd                        | 413  | `image_too_large` (param `max_bytes`)              |
| Trop de pixels une fois décodée           | 422  | `image_too_many_pixels`                            |
| Image inconnue, ou d'un autre utilisateur | 404  | `image_not_found`                                  |
| Trop d'envois sur l'heure écoulée         | 429  | `image_upload_limit_reached` (param `max_uploads`) |
| Tuile sans texte ni image                 | 422  | `tile_empty`                                       |

### 2.7 Stockage et service

L'**API S3 est utilisée partout**, via un seul service `ImageStorage` (`save`, `delete`, `url`) construit sur **boto3** : le développement et la CI exécutent exactement le code de la production.

| Environnement       | Service S3                                                                                                                                                                                                                                                           |
| ------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Développement et CI | Conteneur **SeaweedFS** (`weed mini` : maître, volume, filer et S3 dans un seul processus), comme Mailpit remplace un fournisseur SMTP. Même service dans `compose.yaml` et dans le job backend de la CI (`docker compose up -d --wait seaweedfs`). Voir ci-dessous. |
| Production          | Un fournisseur compatible S3, choisi avec l'hébergement ([TODO](../../TODO.fr.md)). Lecture publique via un CDN, ou l'URL du bucket.                                                                                                                                 |

SeaweedFS en développement :

- Image épinglée à une version exacte (`chrislusf/seaweedfs:4.48`), ports publiés sur `127.0.0.1` seulement : l'**API S3** sur `8333` et l'**interface web du filer** sur **http://localhost:8888**, qui montre les images dans `buckets/tierlist-images/` et les ouvre. `dev.sh` / `dev.ps1` l'ouvrent sur le bucket.
- Le bucket est créé au démarrage (`-bucket=tierlist-images`) ; le conteneur est prêt (healthy) dès qu'il existe.
- `seaweedfs/s3.json` définit deux identités : le backend (clé `tierlist-dev`, lecture, écriture et liste sur le bucket seulement) et `anonymous` (**lecture** seule, pour que les URL des images marchent sans authentification ; lister, écrire et supprimer sont refusés). `seaweedfs/security.toml` contient une clé de signature du filer, réservée au développement : sans elle, SeaweedFS refuse de charger les identités.
- Les données sont gardées dans le volume Docker `seaweedfs-data`.

- Chaque objet est écrit avec `Content-Type: image/webp` et `Cache-Control: public, max-age=31536000, immutable` (le contenu d'une clé ne change jamais).
- **Modèle d'accès** : les URL des images sont publiques mais **impossibles à deviner** (UUID aléatoire). Quiconque a une URL peut voir l'image, ce que le lien public des résultats impose de toute façon : une image utilisée dans une partie devient publique par ce lien.

### 2.8 Nettoyage

Aucun fichier n'est supprimé quand une tuile change, puisqu'un instantané peut encore l'utiliser. Un **ramasse-miettes** périodique efface les images qu'aucune tuile ni aucun instantané ne référence depuis plus d'un délai de grâce. Il couvre les envois abandonnés (envoyés mais jamais rattachés à une tuile), la purge des templates supprimés et la suppression des comptes, qui ne retirent que des lignes en base (`ON DELETE CASCADE` sur les templates et les tuiles ; les lignes des images restent, sans auteur). C'est une commande lancée à côté de `scripts/purge_deleted_templates.py` :

```bash
cd backend
uv run python scripts/purge_unused_images.py   # affiche "Unused images purged: n"
```

- Elle efface les images **visibles** créées il y a plus de `UNUSED_IMAGE_RETENTION_DAYS` jours qu'aucune tuile n'utilise. Les images masquées ou supprimées par la modération gardent leur ligne (#124). Les instantanés n'existent pas encore ; quand ils existeront, la requête devra aussi garder les images qu'ils utilisent.
- Les lignes sont supprimées d'abord, en une seule requête, puis les fichiers : une tuile ne pointe jamais vers un fichier effacé. Une tuile qui rattache l'une de ces images au même moment attend la fin de la suppression, puis échoue sur la clé étrangère. Un fichier qu'on n'arrive pas à effacer (stockage en panne) est journalisé avec sa clé, pour l'effacer à la main.
- La relancer ne pose aucun problème : elle n'efface que ce qui a expiré. Elle doit être planifiée une fois par jour sur le serveur ([TODO](../../TODO.fr.md)).

### 2.9 Modération

Tout se fait **dans l'application**, dans des pages super admin, sans outil externe. Le jalon 1 ne fait que la préparer (#81 : les colonnes `sha256` et statut, la limite d'envois par compte) ; les fonctionnalités de modération sont des issues à part :

- **Traçabilité** : chaque image a un auteur, une date, et les tuiles et instantanés qui l'utilisent se retrouvent par les clés étrangères. Un super admin remonte d'une image à son auteur et aux parties concernées.
- **Pages super admin** :
  - **rôle et autorisation** vérifiés côté serveur (#123) ;
  - **derniers envois** : une grille des dernières images avec auteur, date et nombre d'utilisations, pour une revue proactive, peu coûteuse puisque les images font au plus 512 px (#125) ;
  - **file des signalements** : images, templates, pseudos et parties signalés par les utilisateurs, invités compris, avec motif et décision ; c'est aussi le mécanisme de notification des contenus illicites (#126) ;
  - **fiche utilisateur** : toutes les images d'un compte, masquage en masse, sanctions du compte (#127).
- **Actions** (#124), chacune inscrite dans un journal de modération (qui, quand, quoi, motif) :
  - **masquer** (réversible) : l'image passe au statut `hidden`, son objet est **déplacé hors du chemin public** (préfixe ou bucket privé de quarantaine, gardé en cas de recours) et le cache CDN de son URL est purgé ; l'API la marque comme masquée et le frontend affiche un visuel « image retirée » partout, résultats publics compris ;
  - **supprimer** : l'objet est effacé définitivement ; la ligne garde le statut et l'empreinte.
- **Pas de nouvel envoi** : le SHA-256 d'un fichier reçu est comparé à une liste d'empreintes bannies (le même fichier est refusé) ; plus tard, une empreinte perceptuelle (dHash, calculée avec Pillow, sans nouvelle dépendance) peut repérer les variantes réencodées (#124).
- **Limites contre les abus** : un nombre maximal d'envois par compte et par heure (#81) ; les invités ne peuvent pas envoyer d'image.
- **Contrainte de stockage** : comme les URL sont publiques et mises en cache, masquer une image doit agir sur le **stockage et le CDN**, pas seulement en base. Le fournisseur choisi doit permettre de purger une URL ([TODO](../../TODO.fr.md)).
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
- Les navigateurs qui ont déjà affiché une image masquée peuvent la garder dans leur cache ; la purge du CDN couvre tous les autres.

## 3. Dans le code

Backend (tests : [guide des tests](testing.fr.md)) :

| Fichier                            | Rôle                                                                                                                                                                                                                                                            |
| ---------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `app/api/routes/images.py`         | `POST /images` : transforme les erreurs en `415`, `413` (param `max_bytes`), `422` et `429` (param `max_uploads`).                                                                                                                                              |
| `app/services/images.py`           | `ImageService.upload` : vérifie la limite horaire, lit le fichier sans dépasser la limite de taille, le compresse, l'écrit sous une nouvelle clé, puis enregistre la ligne (le fichier est retiré si cela échoue). `purge_unused` : le ramasse-miettes du §2.8. |
| `app/repositories/images.py`       | Image d'un auteur, nombre d'envois récents, suppression des images inutilisées.                                                                                                                                                                                 |
| `app/services/templates.py`        | Tuiles avec une image : `_check_owned_image`, règle « un texte ou une image » (`TileEmptyError`).                                                                                                                                                               |
| `app/schemas/templates.py`         | `TileResponse.image_url`, construite avec `ImageStorage.url` donné dans le contexte de validation.                                                                                                                                                              |
| `app/models/tile.py`               | `Tile.image_id` et `Tile.image` ; migration `a2ee58bb5b26_add_image_id_to_tiles.py`.                                                                                                                                                                            |
| `scripts/purge_unused_images.py`   | Commande du ramasse-miettes.                                                                                                                                                                                                                                    |
| `app/services/image_processing.py` | `compress_image` : le traitement Pillow du §2.3, une fonction pure.                                                                                                                                                                                             |
| `app/services/image_storage.py`    | `ImageStorage` (`save`, `delete`, `url`) sur un client boto3, partagé entre les requêtes.                                                                                                                                                                       |
| `app/models/image.py`              | Modèle `Image` et `ImageStatus` ; migration `ef5839ce8066_create_images.py`.                                                                                                                                                                                    |
| `app/constants/images.py`          | Formats, taille de sortie, qualité WebP, `Content-Type` et `Cache-Control` des objets.                                                                                                                                                                          |
| `app/core/config.py`               | Réglages `IMAGE_*` (§2.4).                                                                                                                                                                                                                                      |

Développement : `compose.yaml` et `seaweedfs/` (§2.7). Frontend : les codes d'erreur sont traduits dans `src/i18n/locales/`, et `src/i18n/index.ts` définit le formateur `megabytes`.
