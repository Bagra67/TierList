# Images

[English](images.md) | Français

Comment les images des tuiles sont reçues, compressées, stockées, servies, nettoyées et modérées. **C'est une décision, pas encore implémentée** (spike #75) : seules les limites d'upload existent dans le code (§2.4) ; le reste est construit dans #81, et le §3 sera complété à ce moment-là. Ce qu'est une tuile pour l'utilisateur : [user stories](../product/milestone-1/user-stories.fr.md) US-1.2 et US-1.3.

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

Tout, sauf les deux limites d'upload du §2.4 : aucun envoi, stockage ni affichage d'image n'existe dans le code (#81).

## 2. Conception technique

### 2.1 Options étudiées

| Sujet                | Options                                                            | Choix et raison                                                                                                                                                                                                                             |
| -------------------- | ------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Bibliothèque         | **Pillow**, pyvips, ImageMagick (Wand)                             | **Pillow** : maintenu, binaires précompilés pour toutes les plateformes, prise en charge du WebP et protection contre les bombes de décompression. pyvips est plus rapide mais demande la bibliothèque système libvips ; ImageMagick aussi. |
| Stockage             | `bytea` PostgreSQL, volume local, **stockage objet compatible S3** | **S3** : la base reste petite, les fichiers survivent aux redéploiements, plusieurs instances du backend les partagent, et tous les hébergeurs le proposent. Un volume local lie l'application à une machine.                               |
| Service des fichiers | Via le backend, **bucket public ou CDN**, URL signées              | **Bucket public ou CDN** : aucune charge sur le backend, cache long. Les URL signées expirent, ce que le lien public des résultats interdit.                                                                                                |
| S3 local (dev, CI)   | **SeaweedFS**, Garage, RustFS, MinIO                               | **SeaweedFS** : Apache 2.0, un seul conteneur, pensé pour beaucoup de petits fichiers. MinIO ne publie plus d'images Docker communautaires ; Garage demande d'abord de configurer un cluster ; RustFS est plus récent.                      |

### 2.2 Fichiers acceptés

- **JPEG, PNG, WebP et GIF** (seule la première image d'un GIF animé est gardée).
- Le format est détecté d'après le **contenu** du fichier par Pillow, jamais d'après son extension ou son `Content-Type`, que le client choisit librement.
- **Refusés** : SVG (il peut contenir des scripts, d'où des failles XSS), HEIC et AVIF (il faudrait un décodeur en plus ; les navigateurs convertissent déjà les photos d'iPhone en JPEG à l'envoi), et tout ce que Pillow ne sait pas ouvrir.

### 2.3 Traitement

Chaque image acceptée suit le même traitement ; le fichier reçu n'est **jamais stocké** :

1. ouvrir et vérifier le fichier (Pillow) ;
2. appliquer l'orientation EXIF (`ImageOps.exif_transpose`), pour que les photos de téléphone soient droites ;
3. convertir le mode de couleur, **en gardant la transparence** (PNG, WebP, GIF) ;
4. la réduire pour qu'elle tienne dans **512 × 512 px**, en gardant ses proportions, sans jamais l'agrandir ;
5. l'encoder en **WebP, qualité 80**, sans aucune métadonnée (EXIF, position GPS : vie privée).

Pourquoi 512 px : le plus grand affichage fait environ 150 px CSS, et un écran de densité 3 a besoin d'environ 450 pixels réels. Une seule taille est stockée : les petites tuiles utilisent le même fichier (pas de miniatures, YAGNI). Le WebP est lu par tous les navigateurs actuels et est bien plus léger que le JPEG ou le PNG à qualité égale.

Le réencodage neutralise aussi les fichiers conçus pour être à la fois une image et autre chose (polyglottes). Le traitement utilise le CPU : la route d'envoi est synchrone, donc FastAPI l'exécute dans son threadpool sans bloquer la boucle d'événements.

Les valeurs fixes deviennent des constantes dans `app/constants/` avec #81 (`IMAGE_OUTPUT_MAX_SIDE_PX = 512`, `IMAGE_WEBP_QUALITY = 80`) ; les valeurs qui peuvent changer selon l'environnement sont des réglages (§2.4).

### 2.4 Limites et réglages

| Variable                  | Description                                                                                                                                                                         | Défaut              |
| ------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------- |
| `IMAGE_UPLOAD_MAX_BYTES`  | Taille maximale du fichier reçu, vérifiée pendant sa lecture ; à garder alignée sur la limite du reverse proxy.                                                                     | `10485760` (10 Mio) |
| `IMAGE_MAX_SOURCE_PIXELS` | Nombre maximal de pixels de l'image décodée (`MAX_IMAGE_PIXELS` de Pillow) : protège contre les bombes de décompression, de petits fichiers qui se décompressent en images énormes. | `40000000` (40 Mpx) |

10 Mio acceptent une photo de téléphone ; 40 Mpx acceptent les plus grands capteurs de téléphones et d'appareils photo. Les deux sont dans `Settings` (`app/core/config.py`) et `backend/.env.example` **dès maintenant**.

Ajoutés **avec #81**, avec le code qui les utilise et les teste :

| Variable                       | Description                                                                                           |
| ------------------------------ | ----------------------------------------------------------------------------------------------------- |
| `IMAGE_S3_ENDPOINT_URL`        | Adresse de l'API S3 (SeaweedFS en développement ; vide pour AWS).                                     |
| `IMAGE_S3_BUCKET`              | Bucket des images.                                                                                    |
| `IMAGE_S3_REGION`              | Région du bucket.                                                                                     |
| `IMAGE_S3_ACCESS_KEY_ID`       | Clé d'accès.                                                                                          |
| `IMAGE_S3_SECRET_ACCESS_KEY`   | Clé secrète (`SecretStr`).                                                                            |
| `IMAGE_PUBLIC_BASE_URL`        | Adresse publique des images (CDN ou URL du bucket) ; l'URL d'une image est cette adresse plus sa clé. |
| Envois par compte et par heure | Limite les abus (§2.9).                                                                               |
| Délai du ramasse-miettes       | Temps pendant lequel une image inutilisée est gardée avant d'être effacée (§2.8).                     |

### 2.5 Modèle de données

- Une table **`images`** : `id`, clé de stockage, largeur, hauteur, taille en octets, auteur (`owner_id`), date de création, **SHA-256 du fichier reçu**, statut de modération (`visible`, `hidden`, `deleted`).
- `tiles.image_id` : clé étrangère nullable vers `images`. Les tuiles d'un instantané de partie référenceront `image_id` de la même façon.
- **Images immuables** : la clé de stockage est aléatoire (`{uuid}.webp`). Remplacer l'image d'une tuile crée une **nouvelle** image ; un fichier existant n'est jamais écrasé. Les caches peuvent garder un fichier indéfiniment, et un instantané retrouve toujours l'image avec laquelle il a été pris.

### 2.6 API

- `POST /images` (`multipart/form-data`, un champ `file`) : vérifie la taille, traite et stocke l'image, renvoie `{id, url, width, height}`.
- Les corps de création et de modification d'une tuile gagnent `image_id` (une image de l'appelant, sinon `404`) ; `TileResponse` gagne `image_url`. La règle « un texte ou une image » remplace la règle actuelle « un texte » (`422` quand les deux manquent).
- Codes d'erreur, créés et traduits en FR et EN avec #81 :

| Situation                                 | HTTP | Code API                              |
| ----------------------------------------- | ---- | ------------------------------------- |
| Pas une image acceptée                    | 415  | `image_unsupported_format`            |
| Fichier trop lourd                        | 413  | `image_too_large` (param `max_bytes`) |
| Trop de pixels une fois décodée           | 422  | `image_too_many_pixels`               |
| Image inconnue, ou d'un autre utilisateur | 404  | `image_not_found`                     |

### 2.7 Stockage et service

L'**API S3 est utilisée partout**, via un seul service `ImageStorage` (`save`, `delete`, `url`) construit sur **boto3** : le développement et la CI exécutent exactement le code de la production.

| Environnement       | Service S3                                                                                                                                                                                                                                                              |
| ------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Développement et CI | Conteneur **SeaweedFS** (`weed server -s3`), ajouté à `compose.yaml` et comme service de CI avec #81, comme Mailpit remplace un fournisseur SMTP. Identifiants dans son fichier d'identités S3, **lecture** anonyme sur le bucket, image épinglée à une version exacte. |
| Production          | Un fournisseur compatible S3, choisi avec l'hébergement ([TODO](../../TODO.fr.md)). Lecture publique via un CDN, ou l'URL du bucket.                                                                                                                                    |

- Chaque objet est écrit avec `Content-Type: image/webp` et `Cache-Control: public, max-age=31536000, immutable` (le contenu d'une clé ne change jamais).
- **Modèle d'accès** : les URL des images sont publiques mais **impossibles à deviner** (UUID aléatoire). Quiconque a une URL peut voir l'image, ce que le lien public des résultats impose de toute façon : une image utilisée dans une partie devient publique par ce lien.

### 2.8 Nettoyage

Aucun fichier n'est supprimé quand une tuile change, puisqu'un instantané peut encore l'utiliser. Un **ramasse-miettes** périodique efface les images qu'aucune tuile ni aucun instantané ne référence depuis plus d'un délai de grâce. Il couvre les envois abandonnés (envoyés mais jamais rattachés à une tuile), la purge des templates supprimés et la suppression des comptes, qui ne retirent que des lignes en base (`ON DELETE CASCADE`). C'est une commande lancée à côté de `scripts/purge_deleted_templates.py`.

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

Ce spike n'ajoute rien. Avec #81 :

- **Pillow** : lecture, vérification et redimensionnement des images, encodage WebP, protection contre les bombes de décompression. Aucun équivalent dans les dépendances actuelles.
- **boto3** : le client S3 de référence, compatible avec tous les fournisseurs S3 et avec SeaweedFS.

`python-multipart`, nécessaire pour recevoir un fichier, est déjà installé par `fastapi[standard]`.

### 2.11 Limites connues

- Pas de quota de stockage par compte : 32 images par template, sans limite sur le nombre de templates.
- Les images de réponse du mode à l'aveugle et les futures photos de profil réutiliseront ce traitement ; leurs tailles seront décidées avec elles.
- Les navigateurs qui ont déjà affiché une image masquée peuvent la garder dans leur cache ; la purge du CDN couvre tous les autres.

## 3. Dans le code

Déjà présent : `IMAGE_UPLOAD_MAX_BYTES` et `IMAGE_MAX_SOURCE_PIXELS` dans `backend/app/core/config.py`, testés par `backend/tests/test_config.py` ([guide des tests](testing.fr.md)). Le reste arrive avec #81.
