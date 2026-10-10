# Images

English | [Français](images.fr.md)

How tile images are received, compressed, stored, served, cleaned up and moderated. Decided in spike #75, built in #81: **the upload, the compression, the storage, the image tiles, the upload limit per account and the garbage collection are implemented** (§3); the editor comes with the rest of #81. What a tile is for the user: [user stories](../product/milestone-1/user-stories.md) US-1.2 and US-1.3.

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

The template editor does not upload nor show images yet: it comes with the rest of #81. The garbage collection is a command that still has to be scheduled on the server ([TODO](../../TODO.md)). The moderation features are separate issues (§2.9).

## 2. Technical design

### 2.1 Options considered

| Topic              | Options                                                            | Choice and reason                                                                                                                                                                       |
| ------------------ | ------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Image library      | **Pillow**, pyvips, ImageMagick (Wand)                             | **Pillow**: maintained, prebuilt wheels on every platform, WebP support and a decompression bomb guard. pyvips is faster but needs the libvips system library; ImageMagick too.         |
| Storage            | PostgreSQL `bytea`, local volume, **S3-compatible object storage** | **S3**: the database stays small, the files survive redeployments, several backend instances share them, and every host offers it. A local volume ties the app to one machine.          |
| Serving            | Through the backend, **public bucket or CDN**, signed URLs         | **Public bucket or CDN**: no backend load, long caching. Signed URLs expire, which the public results link forbids.                                                                     |
| Local S3 (dev, CI) | **SeaweedFS**, Garage, RustFS, MinIO                               | **SeaweedFS**: Apache 2.0, one container, built for many small files. MinIO no longer publishes community Docker images; Garage needs a cluster layout set up first; RustFS is younger. |

### 2.2 Accepted files

- **JPEG, PNG and WebP** (only the first frame of an animated PNG or WebP is kept).
- The format is detected from the **content** of the file by Pillow, never from its extension or its `Content-Type`, which the client chooses freely.
- **Refused**: GIF (product decision in #81: tiles are still pictures), SVG (it can contain scripts, hence XSS), HEIC and AVIF (an extra decoder would be needed; browsers already convert iPhone photos to JPEG when uploading them), and anything Pillow cannot open, truncated files included.

### 2.3 Processing

Every accepted image goes through the same pipeline; the received file is **never stored**:

1. open and verify the file (Pillow), refusing it if its decoded image would have too many pixels: only the header is read for that check;
2. apply the EXIF orientation (`ImageOps.exif_transpose`), so that phone photos are upright;
3. convert the color mode, **keeping transparency** (PNG, WebP);
4. resize it so that its **longest side is 512 px**, keeping its proportions, with the **Lanczos** filter: a larger image is shrunk (4000 × 3000 gives 512 × 384), a smaller one is **enlarged** (200 × 100 gives 512 × 256), never cropped nor stretched;
5. encode it in **WebP, quality 80**, without any metadata (EXIF, GPS position: privacy). Only the color profile (ICC) is kept, otherwise wide-gamut photos (Display P3) would look dull.

Why 512 px: the largest display is about 150 CSS px, and a screen with a pixel ratio of 3 needs about 450 real pixels. A single size is stored: the small tiles use the same file (no thumbnails, YAGNI). WebP is read by every current browser and is much lighter than JPEG or PNG at equal quality.

Why enlarge small images (decided in #81): every stored image then has the same size, and a small image is shown as sharp as possible in the large frame. Lanczos is the classic interpolation filter with the best quality, the one image editors use; it is part of Pillow, so no extra library. AI upscalers (Real-ESRGAN…) are excluded. Enlarging does not invent details: a tiny image (a 32 px icon, pixel art) comes out smooth and slightly blurred, not pixelated.

Re-encoding also neutralises files crafted to be both an image and something else (polyglots). The processing uses the CPU: the upload route is synchronous, so FastAPI runs it in its threadpool without blocking the event loop.

Fixed values are constants in `app/constants/images.py` (`IMAGE_OUTPUT_MAX_SIDE_PX = 512`, `IMAGE_WEBP_QUALITY = 80`, accepted formats); values that may differ between environments are settings (§2.4).

### 2.4 Limits and settings

| Variable                  | Description                                                                                                                                                | Default             |
| ------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------- |
| `IMAGE_UPLOAD_MAX_BYTES`  | Maximum size of the received file, checked while reading it; keep it aligned with the reverse proxy limit.                                                 | `10485760` (10 MiB) |
| `IMAGE_MAX_SOURCE_PIXELS` | Maximum number of pixels of the decoded image (Pillow `MAX_IMAGE_PIXELS`): protects against decompression bombs, small files that expand into huge images. | `40000000` (40 Mpx) |

10 MiB accepts a phone photo; 40 Mpx accepts the largest phone and camera sensors.

Storage settings:

| Variable                     | Description                                                                                                                       | Default                                 |
| ---------------------------- | --------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------- |
| `IMAGE_S3_ENDPOINT_URL`      | S3 API address (SeaweedFS in development); unset for AWS S3.                                                                      | unset                                   |
| `IMAGE_S3_BUCKET`            | Bucket of the images.                                                                                                             | `tierlist-images`                       |
| `IMAGE_S3_REGION`            | Region of the bucket.                                                                                                             | `us-east-1`                             |
| `IMAGE_S3_ACCESS_KEY_ID`     | Access key; unset, boto3 looks for its usual credentials (`AWS_*` variables, machine role).                                       | unset                                   |
| `IMAGE_S3_SECRET_ACCESS_KEY` | Secret key (`SecretStr`).                                                                                                         | unset                                   |
| `IMAGE_S3_TIMEOUT_SECONDS`   | Timeout of the storage calls (connection, then response).                                                                         | `10`                                    |
| `IMAGE_PUBLIC_BASE_URL`      | Public address of the images (CDN or bucket URL); an image URL is this plus its key. `127.0.0.1`: SeaweedFS only listens on IPv4. | `http://127.0.0.1:8333/tierlist-images` |

Abuse and cleanup settings:

| Variable                      | Description                                                                                  | Default |
| ----------------------------- | -------------------------------------------------------------------------------------------- | ------- |
| `IMAGE_UPLOADS_PER_HOUR_MAX`  | Maximum number of images uploaded by an account over the last hour (§2.9); beyond it, `429`. | `120`   |
| `UNUSED_IMAGE_RETENTION_DAYS` | Days an image that no tile uses is kept before the garbage collection erases it (§2.8).      | `7`     |

All of them are in `Settings` (`app/core/config.py`) and `backend/.env.example`, which holds the SeaweedFS values.

### 2.5 Data model

- A table **`images`**: `id`, storage key, width, height, size in bytes, author (`owner_id`), creation date, **SHA-256 of the received file**, moderation status (`visible`, `hidden`, `deleted`). Deleting the account sets `owner_id` to `NULL` (`ON DELETE SET NULL`) instead of deleting the row: the garbage collection still finds the file, and a past game can still show the image.
- `tiles.image_id`: nullable foreign key to `images`. The tiles of a game snapshot will reference `image_id` the same way.
- **Immutable images**: the storage key is random (`{uuid}.webp`). Replacing the image of a tile creates a **new** image; an existing file is never overwritten. Caches can keep a file forever, and a snapshot always finds the image it was taken with.

### 2.6 API

- `POST /images` (`multipart/form-data`, one `file` field, authenticated): checks the size, processes and stores the image, returns `201` and `{id, url, width, height}`.
- The tile creation and update bodies have `image_id` (a visible image of the caller, otherwise `404`); `TileResponse` has `image_url`, `null` without image. A tile has a text, an image or both (`422` `tile_empty` otherwise); in an update, `image_id: null` removes the image. Details in the [templates guide](templates.md). An image can be used by several tiles.
- Error codes, translated in FR and EN. The frontend shows `max_bytes` in megabytes (`megabytes` i18next formatter):

| Situation                               | HTTP | API code                                           |
| --------------------------------------- | ---- | -------------------------------------------------- |
| Not a supported image                   | 415  | `image_unsupported_format`                         |
| File too large                          | 413  | `image_too_large` (param `max_bytes`)              |
| Too many pixels once decoded            | 422  | `image_too_many_pixels`                            |
| Unknown image, or image of another user | 404  | `image_not_found`                                  |
| Too many uploads in the last hour       | 429  | `image_upload_limit_reached` (param `max_uploads`) |
| Tile without text nor image             | 422  | `tile_empty`                                       |

### 2.7 Storage and serving

The **S3 API is used everywhere**, through a single `ImageStorage` service (`save`, `delete`, `url`) built on **boto3**: development and CI run exactly the production code.

| Environment        | S3 service                                                                                                                                                                                                                                         |
| ------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Development and CI | **SeaweedFS** container (`weed mini`: master, volume, filer and S3 in one process), the way Mailpit stands in for an SMTP provider. Same service in `compose.yaml` and in the backend CI job (`docker compose up -d --wait seaweedfs`). See below. |
| Production         | An S3-compatible provider, chosen with the hosting ([TODO](../../TODO.md)). Public read through a CDN, or the bucket URL.                                                                                                                          |

SeaweedFS in development:

- Image pinned to an exact version (`chrislusf/seaweedfs:4.48`), ports published on `127.0.0.1` only: the **S3 API** on `8333` and the **filer web UI** on **http://localhost:8888**, which shows the images in `buckets/tierlist-images/` and opens them. `dev.sh` / `dev.ps1` open it on the bucket.
- The bucket is created at startup (`-bucket=tierlist-images`); the container is healthy once it exists.
- `seaweedfs/s3.json` gives two identities: the backend (`tierlist-dev` key, read, write and list on the bucket only) and `anonymous` (**read** only, so that the image URLs work without authentication; listing, writing and deleting are refused). `seaweedfs/security.toml` holds a filer signing key, development only: without it SeaweedFS refuses to load the identities.
- Data is kept in the `seaweedfs-data` Docker volume.

- Each object is written with `Content-Type: image/webp` and `Cache-Control: public, max-age=31536000, immutable` (the content of a key never changes).
- **Access model**: image URLs are public but **impossible to guess** (random UUID). Anyone holding a URL can see the image, which the public results link requires anyway: an image used in a game becomes public through it.

### 2.8 Cleanup

No file is deleted when a tile changes, since a snapshot may still use it. A periodic **garbage collection** erases the images that no tile and no snapshot reference since longer than a grace delay. It covers the abandoned uploads (uploaded but never attached to a tile), the purge of deleted templates and the deletion of accounts, which only remove database rows (`ON DELETE CASCADE` on templates and tiles; the image rows stay, without author). It is a command run next to `scripts/purge_deleted_templates.py`:

```bash
cd backend
uv run python scripts/purge_unused_images.py   # prints "Unused images purged: n"
```

- It erases the **visible** images created more than `UNUSED_IMAGE_RETENTION_DAYS` days ago that no tile uses. The images hidden or deleted by the moderation keep their row (#124). Snapshots do not exist yet; when they do, the query must also keep the images they use.
- The rows are deleted first, in a single query, then the files: a tile can never point to an erased file. A tile that attaches one of these images at the same moment waits for the deletion, then fails on the foreign key. A file that cannot be erased (storage down) is logged with its key, to be erased by hand.
- It can be run again safely: it only erases what has expired. It must be scheduled once a day on the server ([TODO](../../TODO.md)).

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

Added with #81:

- **Pillow**: reading, checking and resizing images, WebP encoding, decompression bomb guard. No equivalent in the current dependencies.
- **boto3**: the reference S3 client, compatible with every S3 provider and with SeaweedFS.
- **boto3-stubs[s3]** (development only): types of the S3 client for Pyright.

`python-multipart`, needed to receive a file, is already installed by `fastapi[standard]`.

### 2.11 Known limitations

- No storage quota per account: 32 images per template, without limit on the number of templates.
- The blind mode answer images and future profile pictures will reuse this pipeline; their sizes are decided with them.
- Browsers that already displayed a hidden image may keep it in their cache; the CDN purge covers everyone else.

## 3. In the code

Backend (tests: [testing guide](testing.md)):

| File                               | Role                                                                                                                                                                                                                                                |
| ---------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `app/api/routes/images.py`         | `POST /images`: turns the errors into `415`, `413` (param `max_bytes`), `422` and `429` (param `max_uploads`).                                                                                                                                      |
| `app/services/images.py`           | `ImageService.upload`: checks the hourly limit, reads the file without going over the size limit, compresses it, writes it under a new key, then saves the row (the file is removed if that fails). `purge_unused`: the garbage collection of §2.8. |
| `app/repositories/images.py`       | Image of an owner, number of recent uploads, deletion of the unused images.                                                                                                                                                                         |
| `app/services/templates.py`        | Tiles with an image: `_check_owned_image`, rule "a text or an image" (`TileEmptyError`).                                                                                                                                                            |
| `app/schemas/templates.py`         | `TileResponse.image_url`, built with the `ImageStorage.url` given in the validation context.                                                                                                                                                        |
| `app/models/tile.py`               | `Tile.image_id` and `Tile.image`; migration `a2ee58bb5b26_add_image_id_to_tiles.py`.                                                                                                                                                                |
| `scripts/purge_unused_images.py`   | Command of the garbage collection.                                                                                                                                                                                                                  |
| `app/services/image_processing.py` | `compress_image`: the Pillow pipeline of §2.3, a pure function.                                                                                                                                                                                     |
| `app/services/image_storage.py`    | `ImageStorage` (`save`, `delete`, `url`) on a boto3 client, shared between requests.                                                                                                                                                                |
| `app/models/image.py`              | `Image` model and `ImageStatus`; migration `ef5839ce8066_create_images.py`.                                                                                                                                                                         |
| `app/constants/images.py`          | Formats, output size, WebP quality, `Content-Type` and `Cache-Control` of the objects.                                                                                                                                                              |
| `app/core/config.py`               | `IMAGE_*` settings (§2.4).                                                                                                                                                                                                                          |

Development: `compose.yaml` and `seaweedfs/` (§2.7). Frontend: the error codes are translated in `src/i18n/locales/`, and `src/i18n/index.ts` defines the `megabytes` formatter.
