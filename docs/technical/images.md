# Images

English | [Français](images.fr.md)

How tile images are received, compressed, stored, served, cleaned up and moderated. **This is a decision, not implemented yet** (spike #75): only the upload limits exist in the code (§2.4); the rest is built in #81, and §3 will be filled in then. What a tile is for the user: [user stories](../product/milestone-1/user-stories.md) US-1.2 and US-1.3.

## 1. Functional overview

### What is needed

- A tile has a **text, an image, or both**; a tile with neither is refused. The image can be replaced or removed (US-1.2, US-1.3).
- The server **compresses** the image before storing it, and the tile shows the stored version. A file that is not a supported image, or is too large, is refused with a message.
- A template has **at most 32 tiles**, hence at most 32 images.
- Images are shown in two sizes: the **current item**, large (about 150 px in the [screens](../product/milestone-1/screens.md)), and the **tiles** of the tier list, small (about 40 px).
- **Who sees them**: the template owner; every participant of a game, guests included; and **anyone holding the public results link**, without account, with no expiry.
- **Lifecycle**: a game is frozen on a snapshot of its template ([domain model](../product/milestone-1/domain-model.md)). Replacing or deleting a tile image, deleting a template or an account must never break the images of past games.
- Only **accounts** that own templates upload images; guests never do. Every image therefore has a known author.

### Not available yet

Everything except the two upload limits of §2.4: no upload, storage or display of images exists in the code (#81).

## 2. Technical design

### 2.1 Options considered

| Topic              | Options                                                            | Choice and reason                                                                                                                                                                       |
| ------------------ | ------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Image library      | **Pillow**, pyvips, ImageMagick (Wand)                             | **Pillow**: maintained, prebuilt wheels on every platform, WebP support and a decompression bomb guard. pyvips is faster but needs the libvips system library; ImageMagick too.         |
| Storage            | PostgreSQL `bytea`, local volume, **S3-compatible object storage** | **S3**: the database stays small, the files survive redeployments, several backend instances share them, and every host offers it. A local volume ties the app to one machine.          |
| Serving            | Through the backend, **public bucket or CDN**, signed URLs         | **Public bucket or CDN**: no backend load, long caching. Signed URLs expire, which the public results link forbids.                                                                     |
| Local S3 (dev, CI) | **SeaweedFS**, Garage, RustFS, MinIO                               | **SeaweedFS**: Apache 2.0, one container, built for many small files. MinIO no longer publishes community Docker images; Garage needs a cluster layout set up first; RustFS is younger. |

### 2.2 Accepted files

- **JPEG, PNG, WebP and GIF** (only the first frame of an animated GIF is kept).
- The format is detected from the **content** of the file by Pillow, never from its extension or its `Content-Type`, which the client chooses freely.
- **Refused**: SVG (it can contain scripts, hence XSS), HEIC and AVIF (an extra decoder would be needed; browsers already convert iPhone photos to JPEG when uploading them), and anything Pillow cannot open.

### 2.3 Processing

Every accepted image goes through the same pipeline; the received file is **never stored**:

1. open and verify the file (Pillow);
2. apply the EXIF orientation (`ImageOps.exif_transpose`), so that phone photos are upright;
3. convert the color mode, **keeping transparency** (PNG, WebP, GIF);
4. shrink it to fit in **512 × 512 px**, keeping its proportions, never enlarged;
5. encode it in **WebP, quality 80**, without any metadata (EXIF, GPS position: privacy).

Why 512 px: the largest display is about 150 CSS px, and a screen with a pixel ratio of 3 needs about 450 real pixels. A single size is stored: the small tiles use the same file (no thumbnails, YAGNI). WebP is read by every current browser and is much lighter than JPEG or PNG at equal quality.

Re-encoding also neutralises files crafted to be both an image and something else (polyglots). The processing uses the CPU: the upload route is synchronous, so FastAPI runs it in its threadpool without blocking the event loop.

Fixed values become constants in `app/constants/` with #81 (`IMAGE_OUTPUT_MAX_SIDE_PX = 512`, `IMAGE_WEBP_QUALITY = 80`); values that may differ between environments are settings (§2.4).

### 2.4 Limits and settings

| Variable                  | Description                                                                                                                                                | Default             |
| ------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------- |
| `IMAGE_UPLOAD_MAX_BYTES`  | Maximum size of the received file, checked while reading it; keep it aligned with the reverse proxy limit.                                                 | `10485760` (10 MiB) |
| `IMAGE_MAX_SOURCE_PIXELS` | Maximum number of pixels of the decoded image (Pillow `MAX_IMAGE_PIXELS`): protects against decompression bombs, small files that expand into huge images. | `40000000` (40 Mpx) |

10 MiB accepts a phone photo; 40 Mpx accepts the largest phone and camera sensors. Both are in `Settings` (`app/core/config.py`) and `backend/.env.example` **now**.

Added **with #81**, together with the code that uses and tests them:

| Variable                     | Description                                                                          |
| ---------------------------- | ------------------------------------------------------------------------------------ |
| `IMAGE_S3_ENDPOINT_URL`      | S3 API address (SeaweedFS in development; empty for AWS).                            |
| `IMAGE_S3_BUCKET`            | Bucket of the images.                                                                |
| `IMAGE_S3_REGION`            | Region of the bucket.                                                                |
| `IMAGE_S3_ACCESS_KEY_ID`     | Access key.                                                                          |
| `IMAGE_S3_SECRET_ACCESS_KEY` | Secret key (`SecretStr`).                                                            |
| `IMAGE_PUBLIC_BASE_URL`      | Public address of the images (CDN or bucket URL); an image URL is this plus its key. |
| Uploads per account and hour | Limits abuse (§2.9).                                                                 |
| Garbage collection delay     | Time an unused image is kept before being erased (§2.8).                             |

### 2.5 Data model

- A table **`images`**: `id`, storage key, width, height, size in bytes, author (`owner_id`), creation date, **SHA-256 of the received file**, moderation status (`visible`, `hidden`, `deleted`).
- `tiles.image_id`: nullable foreign key to `images`. The tiles of a game snapshot will reference `image_id` the same way.
- **Immutable images**: the storage key is random (`{uuid}.webp`). Replacing the image of a tile creates a **new** image; an existing file is never overwritten. Caches can keep a file forever, and a snapshot always finds the image it was taken with.

### 2.6 API

- `POST /images` (`multipart/form-data`, one `file` field): checks the size, processes and stores the image, returns `{id, url, width, height}`.
- The tile creation and update bodies gain `image_id` (an image of the caller, otherwise `404`); `TileResponse` gains `image_url`. The rule "a text or an image" replaces today's rule "a text" (`422` when both are missing).
- Error codes, created and translated in FR and EN with #81:

| Situation                               | HTTP | API code                              |
| --------------------------------------- | ---- | ------------------------------------- |
| Not a supported image                   | 415  | `image_unsupported_format`            |
| File too large                          | 413  | `image_too_large` (param `max_bytes`) |
| Too many pixels once decoded            | 422  | `image_too_many_pixels`               |
| Unknown image, or image of another user | 404  | `image_not_found`                     |

### 2.7 Storage and serving

The **S3 API is used everywhere**, through a single `ImageStorage` service (`save`, `delete`, `url`) built on **boto3**: development and CI run exactly the production code.

| Environment        | S3 service                                                                                                                                                                                                                                                    |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Development and CI | **SeaweedFS** container (`weed server -s3`), added to `compose.yaml` and as a CI service with #81, the way Mailpit stands in for an SMTP provider. Credentials in its S3 identities file, anonymous **read** on the bucket, image pinned to an exact version. |
| Production         | An S3-compatible provider, chosen with the hosting ([TODO](../../TODO.md)). Public read through a CDN, or the bucket URL.                                                                                                                                     |

- Each object is written with `Content-Type: image/webp` and `Cache-Control: public, max-age=31536000, immutable` (the content of a key never changes).
- **Access model**: image URLs are public but **impossible to guess** (random UUID). Anyone holding a URL can see the image, which the public results link requires anyway: an image used in a game becomes public through it.

### 2.8 Cleanup

No file is deleted when a tile changes, since a snapshot may still use it. A periodic **garbage collection** erases the images that no tile and no snapshot reference since longer than a grace delay. It covers the abandoned uploads (uploaded but never attached to a tile), the purge of deleted templates and the deletion of accounts, which only remove database rows (`ON DELETE CASCADE`). It is a command run next to `scripts/purge_deleted_templates.py`.

### 2.9 Moderation

Everything is done **inside the application**, in super admin pages, without any external tool. Milestone 1 only prepares it (#81: the `sha256` and status columns, the upload limit per account); the moderation features are separate issues:

- **Traceability**: every image has an author, a date, and the tiles and snapshots that use it are found through the foreign keys. A super admin goes from an image to its author and to the games concerned.
- **Super admin pages**:
  - **role and authorization** checked server-side (#123);
  - **recent uploads**: a grid of the latest images with author, date and number of uses, for a proactive review, cheap since images are at most 512 px (#125);
  - **reports queue**: images, templates, nicknames and games reported by users, guests included, with reason and decision; it is also the notice mechanism for illegal content (#126);
  - **user page**: all the images of an account, bulk hiding, account sanctions (#127).
- **Actions** (#124), every one recorded in a moderation log (who, when, what, reason):
  - **hide** (reversible): the image gets the `hidden` status, its object is **moved out of the public path** (private quarantine prefix or bucket, kept for an appeal) and the CDN cache of its URL is purged; the API marks it as hidden and the frontend shows an "image removed" visual everywhere, public results included;
  - **delete**: the object is erased permanently; the row keeps the status and the fingerprint.
- **No re-upload**: the SHA-256 of a received file is compared with a list of banned fingerprints (the same file is refused); later, a perceptual fingerprint (dHash, computed with Pillow, no new dependency) can catch re-encoded variants (#124).
- **Abuse limits**: a maximum number of uploads per account and per hour (#81); guests cannot upload.
- **Storage constraint**: since URLs are public and cached, hiding an image must act on the **storage and the CDN**, not only on the database. The chosen provider must allow purging one URL ([TODO](../../TODO.md)).
- **Set aside**: automatic NSFW detection. It needs an AI model or an external service; at the expected scale, the uploads review and the reports are enough. Kept for later, possibly as a paid feature, with an open source model run by the backend rather than an external service (#128).

### 2.10 Dependencies

Nothing is added by this spike. With #81:

- **Pillow**: reading, checking and resizing images, WebP encoding, decompression bomb guard. No equivalent in the current dependencies.
- **boto3**: the reference S3 client, compatible with every S3 provider and with SeaweedFS.

`python-multipart`, needed to receive a file, is already installed by `fastapi[standard]`.

### 2.11 Known limitations

- No storage quota per account: 32 images per template, without limit on the number of templates.
- The blind mode answer images and future profile pictures will reuse this pipeline; their sizes are decided with them.
- Browsers that already displayed a hidden image may keep it in their cache; the CDN purge covers everyone else.

## 3. In the code

Already present: `IMAGE_UPLOAD_MAX_BYTES` and `IMAGE_MAX_SOURCE_PIXELS` in `backend/app/core/config.py`, tested by `backend/tests/test_config.py` ([testing guide](testing.md)). The rest comes with #81.
