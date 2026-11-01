# Images

English | [Français](images.fr.md)

How tile images are received, compressed, stored, served, cleaned up and moderated. Decided in spike #75, **built in #81** (§3): upload, compression, storage, image tiles in the template editor, upload limit per account and garbage collection. **Moderation actions built in #124** (§2.9): hide, unhide or delete an image, refusal of a deleted file uploaded again. **Recent uploads page built in #125** (§2.9): the first super admin page that lists images and calls those actions. What a tile is for the user: [user stories](../product/milestone-1/user-stories.md) US-1.2 and US-1.3.

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

The moderation actions (§2.9) are called from the recent uploads page (#125) and from the account page (#127); the reports queue (#269) comes with its own issue.

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
2. decode it; a JPEG is decoded at a reduced scale (`draft`: down to 1/8, never under 512 px a side), so that a 40 Mpx photo does not take some 120 MB of memory per upload;
3. apply the EXIF orientation (`ImageOps.exif_transpose`), so that phone photos are upright;
4. convert the color mode, **keeping transparency** (PNG, WebP);
5. resize it so that its **longest side is 512 px**, keeping its proportions, with the **Lanczos** filter: a larger image is shrunk (4000 × 3000 gives 512 × 384), a smaller one is **enlarged** (200 × 100 gives 512 × 256), never cropped nor stretched. The short side is at least 1 px: beyond a 1024:1 ratio it would round to 0, a size Pillow refuses (2000 × 1 gives 512 × 1);
6. encode it in **WebP, quality 80**, without any metadata (EXIF, GPS position: privacy). Only the color profile (ICC) is kept, otherwise wide-gamut photos (Display P3) would look dull.

Why 512 px: the largest display is about 150 CSS px, and a screen with a pixel ratio of 3 needs about 450 real pixels. A single size is stored: the small tiles use the same file (no thumbnails, YAGNI). WebP is read by every current browser and is much lighter than JPEG or PNG at equal quality.

Why enlarge small images (decided in #81): every stored image then has the same size, and a small image is shown as sharp as possible in the large frame. Lanczos is the classic interpolation filter with the best quality, the one image editors use; it is part of Pillow, so no extra library. AI upscalers (Real-ESRGAN…) are excluded. Enlarging does not invent details: a tiny image (a 32 px icon, pixel art) comes out smooth and slightly blurred, not pixelated.

Re-encoding also neutralises files crafted to be both an image and something else (polyglots). The processing uses the CPU: the upload route is synchronous, so FastAPI runs it in its threadpool without blocking the event loop.

Fixed values are constants in `app/constants/images.py` (`IMAGE_OUTPUT_MAX_SIDE_PX = 512`, `IMAGE_WEBP_QUALITY = 80`, accepted formats); values that may differ between environments are settings (§2.4).

### 2.4 Limits and settings

| Variable                  | Description                                                                                                                                                             | Default             |
| ------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------- |
| `IMAGE_UPLOAD_MAX_BYTES`  | Maximum size of the received file; Cloudflare accepts bodies up to 100 MB ([deployment guide](deployment.md)).                                                          | `10485760` (10 MiB) |
| `IMAGE_MAX_SOURCE_PIXELS` | Maximum number of pixels of the decoded image, checked from the header before decoding: protects against decompression bombs, small files that expand into huge images. | `40000000` (40 Mpx) |

10 MiB accepts a phone photo; 40 Mpx accepts the largest phone and camera sensors.

Starlette receives the whole multipart body, and writes it to a temporary file, **before** the route runs: the backend refuses a file over `IMAGE_UPLOAD_MAX_BYTES` (it reads at most one byte more, so the file never goes into memory), but only the **proxy limit** stops a huge body before it is received: Cloudflare refuses bodies over 100 MB ([deployment guide](deployment.md)).

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
- `tiles.image_id`: nullable foreign key to `images`. `snapshot_tiles.image_id`, the tiles of a game snapshot, references it the same way ([templates guide](templates.md), §2.4).
- **Immutable images**: the storage key is random (`{uuid}.webp`). Replacing the image of a tile creates a **new** image; an existing file is never overwritten. A cached file is therefore never stale, and a snapshot always finds the image it was taken with.
- **Status and fingerprint** (used by the moderation, §2.9): the storage key never changes, the location of the file follows the status: at its key when `visible`, under `quarantine/{key}` when `hidden`, nowhere when `deleted`. The row of a deleted image is kept: its SHA-256 is the banned fingerprint (the `BannedFingerprint` of the [domain model](../product/milestone-2/domain-model.md)), so there is no table of banned fingerprints; the `ix_images_sha256` index serves the check at upload.

### 2.6 API

- `POST /images` (`multipart/form-data`, one `file` field, authenticated): checks the size, processes and stores the image, returns `201` and `{id, url, width, height}`.
- The tile creation and update bodies have `image_id` (a visible image of the caller, otherwise `404`); `TileResponse` has `image_url`, `null` without image. A tile has a text, an image or both (`422` `tile_empty` otherwise); in an update, `image_id: null` removes the image. Details in the [templates guide](templates.md). An image can be used by several tiles.
- `TileResponse` (templates) and `CurrentItemResponse` (games, results, public results link included) have `image_removed`: `true` when the image is hidden or deleted by the moderation; `image_url` is then `null`, since the file is no longer at its public address. `optional_image_url` and `is_image_removed` (`app/api/presenters/images.py`) compute both, so every response agrees.
- The moderation routes (`POST /moderation/images/{image_id}/hide`, `/unhide`, `/delete`) are described in §2.9.
- Error codes, translated in FR and EN. The frontend shows `max_bytes` in megabytes (`megabytes` i18next formatter):

| Situation                               | HTTP | API code                                           |
| --------------------------------------- | ---- | -------------------------------------------------- |
| Not a supported image, or banned file   | 415  | `image_unsupported_format`                         |
| File too large                          | 413  | `image_too_large` (param `max_bytes`)              |
| Too many pixels once decoded            | 422  | `image_too_many_pixels`                            |
| Unknown image, or image of another user | 404  | `image_not_found`                                  |
| Too many uploads in the last hour       | 429  | `image_upload_limit_reached` (param `max_uploads`) |
| Tile without text nor image             | 422  | `tile_empty`                                       |

### 2.7 Storage and serving

The **S3 API is used everywhere**, through a single `ImageStorage` service (`save`, `delete`, `url`, and for the moderation `copy_to_quarantine`, `copy_from_quarantine`, `presigned_url`) built on **boto3**: development and CI run exactly the production code.

| Environment        | S3 service                                                                                                                                                                                                                                         |
| ------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Development and CI | **SeaweedFS** container (`weed mini`: master, volume, filer and S3 in one process), the way Mailpit stands in for an SMTP provider. Same service in `compose.yaml` and in the backend CI job (`docker compose up -d --wait seaweedfs`). See below. |
| Production         | **Scaleway Object Storage**, one public bucket per environment ([deployment guide](deployment.md)). Public read through the bucket URL (`IMAGE_PUBLIC_BASE_URL`), or a CDN later.                                                                  |

SeaweedFS in development:

- Image pinned to an exact version (`chrislusf/seaweedfs:4.48`), ports published on `127.0.0.1` only: the **S3 API** on `8333` and the **filer web UI** on **http://localhost:8888**, which shows the images in `buckets/tierlist-images/` and opens them. `dev.sh` / `dev.ps1` open it on the bucket.
- The bucket is created at startup (`-bucket=tierlist-images`); the container is healthy once it exists.
- `seaweedfs/s3.json` gives two identities: the backend (`tierlist-dev` key, read, write, list and setting the ACL of its objects, on the bucket only: each image is sent `public-read`) and `anonymous` (**read** only, so that the image URLs work without authentication; listing, writing and deleting are refused). `seaweedfs/security.toml` holds a filer signing key, development only: without it SeaweedFS refuses to load the identities.
- Data is kept in the `seaweedfs-data` Docker volume.

- Each object is written with the `public-read` ACL (at Scaleway, an object stays private even in a public bucket), `Content-Type: image/webp` and `Cache-Control: public, max-age=86400`: **one day**. The content of a key never changes, so a year with `immutable` would be possible; one day is chosen (#81 review) so that an image hidden by the moderation or erased leaves the browser caches within 24 hours. There is no CDN yet, so nothing to purge; a CDN will have to purge the URL of a hidden image at once (§2.9).
- **Access model**: image URLs are public but **impossible to guess** (random UUID). Anyone holding a URL can see the image, which the public results link requires anyway: an image used in a game becomes public through it.
- **Quarantine**: the file of an image hidden by the moderation is copied under the `quarantine/` prefix (`IMAGE_QUARANTINE_PREFIX`) with the `private` ACL, then removed from its public key (§2.9). `quarantine_key(key)` gives that location; the storage key in the database does not change. The quarantine key is never sent to a client as such: super admins see a hidden image through a presigned URL (§2.9).
- **Development limitation**: the `anonymous` identity of SeaweedFS reads the whole bucket, whatever the ACL of the object, so a quarantined file can be read locally by whoever knows its key. The quarantine is private at Scaleway, where object ACLs apply.

### 2.8 Cleanup

No file is deleted when a tile changes, since a snapshot may still use it. A periodic **garbage collection** erases the images that no tile and no snapshot reference since longer than a grace delay. It covers the abandoned uploads (uploaded but never attached to a tile), the purge of deleted templates and the deletion of accounts, which only remove database rows (`ON DELETE CASCADE` on templates and tiles; the image rows stay, without author). It runs every night in the app process, with the other purges ([deployment guide](deployment.md#23-nightly-tasks), #192), and can also be run from the command line, like `scripts/purge_deleted_templates.py`:

```bash
cd backend
uv run python scripts/purge_unused_images.py   # prints "Unused images purged: n"
```

- It erases the **visible** images created more than `UNUSED_IMAGE_RETENTION_DAYS` days ago that no tile and no snapshot tile uses. The images hidden or deleted by the moderation keep their row (#124).
- The rows are deleted first, in a single query, then the files: a tile can never point to an erased file. A tile that attaches one of these images at the same moment waits for the deletion, then fails on the foreign key. A file that cannot be erased (storage down) is logged with its key, to be erased by hand.
- It can be run again safely: it only erases what has expired.

### 2.9 Moderation

Everything is done **inside the application**, in super admin pages, without any external tool. #81 prepared it (the `sha256` and status columns, the upload limit per account); #124 built the **actions** below; #125 the recent uploads page. The other pages that list images are separate issues:

- **Traceability**: every image has an author, a date, and the tiles and snapshots that use it are found through the foreign keys. A super admin goes from an image to its author and to the games concerned.
- **Super admin pages**:
  - **role and authorization** checked server-side (#123);
  - **recent uploads**: a grid of the latest images with author, date and number of uses, for a proactive review, cheap since images are at most 512 px (#125, built: `GET /moderation/images` and `/moderation/uploads`, [moderation guide](moderation.md));
  - **reports queue**: images, templates, nicknames and games reported by users, guests included, with reason and decision; it is also the notice mechanism for illegal content (#126);
  - **account page**: all the images of an account, bulk hiding, account sanctions (#127, built: `/moderation/accounts/{id}`, [moderation guide](moderation.md#28-accounts)).

  The recent uploads page and the account page call the routes below; the reports queue will too.

**Actions** (#124, US-1.4, US-1.6). Three routes, protected by `SuperAdminDep` and declaring `SUPER_ADMIN_RESPONSES` ([moderation guide](moderation.md)), each with the body `{reason}` (`ModerationReasonRequest`: 1 to 500 characters, surrounding spaces removed) and the answer `204`:

| Route                                       | Allowed from        | Effect                                                                                       |
| ------------------------------------------- | ------------------- | -------------------------------------------------------------------------------------------- |
| `POST /moderation/images/{image_id}/hide`   | `visible`           | Status `hidden`; the file moves to `quarantine/{key}`, private, kept for an appeal.          |
| `POST /moderation/images/{image_id}/unhide` | `hidden`            | Status `visible`; the file goes back to its public key.                                      |
| `POST /moderation/images/{image_id}/delete` | `visible`, `hidden` | Status `deleted`; the file is erased for good; the row keeps the status and the fingerprint. |

- Errors: `404` `image_not_found` (unknown image), `409` `image_moderation_conflict` (the action does not apply to the current status). `POST` rather than `DELETE`, since the action carries a reason and the row stays.
- `ImageModerationService(session, storage, moderation_log)` (`app/services/image_moderation.py`) reads the image with `SELECT … FOR UPDATE` (`get_image_for_update`): two super admins acting on the same image at once do not move its file twice. Every action is written to the [moderation log](moderation.md) in the same transaction as the new status: `target_type` `image`, `target_id` the image id, `target_label` its storage key (no file name is stored).
- **Order of the steps**, chosen to fail on the safe side:
  - **hide**: copy the file to `quarantine/{key}` with the `private` ACL (`copy_to_quarantine`) → status `hidden` and log entry → commit → delete the public file. If the commit fails, the transaction is rolled back and the quarantine copy deleted: the image stays public and unchanged;
  - **unhide**: copy the file back to its key (`copy_from_quarantine`: `public-read`, the same `Content-Type` and `Cache-Control` as at upload, `MetadataDirective=REPLACE`) → status `visible` and log entry → commit → delete the quarantine copy. If the commit fails, the public copy is deleted;
  - **delete**: status `deleted` and log entry → commit → delete the file where it is (its key, or `quarantine/{key}` for a hidden image).
- A file that cannot be erased **after** the commit is logged with its key, to be erased by hand, like in the garbage collection: the decision stands, and the API no longer gives the image's address. A storage error **before** the commit (storage down) is not caught and gives a `500`, like the upload; nothing has changed then.
- **Preview for super admins** (#125): the recent uploads (`GET /moderation/images`) list the visible and hidden images, never the deleted ones (no file left). A visible image is given at its public address; a hidden one through a **presigned URL** of its quarantine file (`ImageStorage.presigned_url`, valid `IMAGE_PREVIEW_URL_EXPIRES_SECONDS` = 900 s, 15 minutes, computed locally by boto3 without calling the storage). The backend serves no bytes and the quarantine stays private; whoever holds the link can read the file for 15 minutes. Only super admins receive these links.
- **Display**: a hidden or deleted image has `image_url: null` and `image_removed: true` in every response (§2.6). The frontend shows an "image removed" visual (`RemovedImage`) in its place everywhere: template editor, game and results screens, public results link included. In the editor, the owner can still replace or remove it, and a tile whose image is removed counts as having an image (its text stays optional).
- **No re-upload**: the upload computes the SHA-256 of the received file, before compressing it, and refuses it when a `deleted` image has the same one (`is_fingerprint_banned`). The refusal is the usual `415` `image_unsupported_format`, without saying why; the server logs it. Hiding does not ban: a hidden image can still be unhidden. Later, a perceptual fingerprint (dHash, computed with Pillow, no new dependency) can catch re-encoded variants.
- The [privacy policy](legal-pages.md) says that the fingerprint of an image is kept, and how long moderated images are kept.
- **Abuse limits**: a maximum number of uploads per account and per hour (#81); guests cannot upload.
- **Storage constraint**: since URLs are public and cached, hiding an image acts on the **storage**, not only on the database. There is no CDN yet; the chosen one must allow purging one URL, and hiding will then purge it ([TODO](../../TODO.md)).
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
- Browsers that already displayed a hidden image may keep it in their cache **for up to one day** (`max-age`). There is no CDN yet: once there is one, hiding must purge its cache too (§2.9).
- In development and CI, the quarantine is not private: SeaweedFS lets anyone read the whole bucket (§2.7).
- Only the recent uploads page and the account page call the moderation actions for now: the reports queue (#269) is still to come.
- The presigned URL of a hidden image can be read by whoever holds it, until it expires (15 minutes).
- Only the exact file is refused after a deletion: a re-encoded or resized copy passes until a perceptual fingerprint exists.

## 3. In the code

Backend (tests: [testing guide](testing.md)):

| File                               | Role                                                                                                                                                                                                                                                                                                                                                                                    |
| ---------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `app/api/routes/images.py`         | `POST /images`: turns the errors into `415`, `413` (param `max_bytes`), `422` and `429` (param `max_uploads`).                                                                                                                                                                                                                                                                          |
| `app/services/images.py`           | `ImageService.upload`: checks the hourly limit, reads the file without going over the size limit, refuses a banned fingerprint, compresses it, writes it under a new key, then saves the row (the file is removed if that fails; a failure of that removal is logged with the key). `purge_unused`: the garbage collection of §2.8.                                                     |
| `app/repositories/images.py`       | Visible image of an owner, image locked for the moderation (`get_image_for_update`), banned fingerprint (`is_fingerprint_banned`), number of recent uploads, deletion of the unused images; for the recent uploads page, `list_recent_images`, `template_names_by_image`, `game_counts_by_image`.                                                                                       |
| `app/services/image_moderation.py` | `ImageModerationService`: `hide`, `unhide`, `delete` (§2.9).                                                                                                                                                                                                                                                                                                                            |
| `app/api/routes/moderation.py`     | `POST /moderation/images/{image_id}/hide`, `/unhide`, `/delete`: turn the errors into `404` and `409`. Body `ModerationReasonRequest` (`app/schemas/moderation.py`). `GET /moderation/images`: the recent uploads (`RecentUploadsService`, `app/services/recent_uploads.py`), each built by `recent_upload_response` (`app/api/presenters/images.py`).                                  |
| `app/services/templates.py`        | Tiles with an image: `_check_owned_image`, rule "a text or an image" (`TileEmptyError`).                                                                                                                                                                                                                                                                                                |
| `app/schemas/templates.py`         | `TileResponse.image_url` and `image_removed` (same fields in `CurrentItemResponse`, `app/schemas/rooms.py`). The URL itself comes from `image_url` or, for a tile that may have no image or a removed one, `optional_image_url`; `is_image_removed` gives `image_removed` (`app/api/presenters/images.py`, the only place that builds a public image URL: tiles, current item, upload). |
| `app/models/tile.py`               | `Tile.image_id` and `Tile.image`; migration `a2ee58bb5b26_add_image_id_to_tiles.py`.                                                                                                                                                                                                                                                                                                    |
| `scripts/purge_unused_images.py`   | Command of the garbage collection.                                                                                                                                                                                                                                                                                                                                                      |
| `app/services/image_processing.py` | `compress_image`: the Pillow pipeline of §2.3, a pure function.                                                                                                                                                                                                                                                                                                                         |
| `app/services/image_storage.py`    | `ImageStorage` (`save`, `delete`, `url`, `copy_to_quarantine`, `copy_from_quarantine`, `presigned_url`) on a boto3 client, shared between requests; `quarantine_key`.                                                                                                                                                                                                                   |
| `app/models/image.py`              | `Image` model and `ImageStatus`; migration `ef5839ce8066_create_images.py`; index `ix_images_created_at`, migration `4840e3c37d23_add_created_at_index_to_images.py`.                                                                                                                                                                                                                   |
| `app/constants/images.py`          | Formats, output size, WebP quality, `Content-Type`, `Cache-Control` and ACL of the objects, quarantine prefix and ACL (`IMAGE_QUARANTINE_PREFIX`, `IMAGE_QUARANTINE_ACL`), lifetime of the presigned preview (`IMAGE_PREVIEW_URL_EXPIRES_SECONDS`).                                                                                                                                     |
| `app/core/config.py`               | `IMAGE_*` settings (§2.4).                                                                                                                                                                                                                                                                                                                                                              |

Development: `compose.yaml` and `seaweedfs/` (§2.7).

Frontend (details in the [templates guide](templates.md#3-in-the-code)):

- `components/ImageDropZone.tsx`: the image thumbnail of a tile, over the whole width of its card in the editor, the image shown whole (never cropped). A click opens the file picker; a file can be dropped on it, with a highlight while dragging. The chosen image is shown at once with a spinner during the upload. A small button removes the image. With `imageRemoved`, an image removed by the moderation shows the "image removed" visual, and can still be replaced or removed. A file of another known type than JPEG, PNG or WebP (`constants/images.ts`) is refused at once, without being sent; a file of unknown type is sent. The backend stays the authority.
- `components/TileEditor.tsx`: the image of each tile can be replaced (click or drop) or removed; the new tile takes a text, an image or both; an image removed by the moderation still counts as an image, so the text stays optional. An image is uploaded as soon as it is chosen, then attached by `image_id`. Several images at once (#242, `useBulkImageTiles`): each one goes through the same `POST /images`, three at a time (`BULK_IMAGE_UPLOAD_CONCURRENCY`), and counts in the hourly limit; the tiles are then created in the order of the selection. A file of a refused type and what exceeds the free slots of the template are skipped before any upload.
- `api/images.ts`: `useUploadImage` (`POST /images`, `multipart/form-data`).
- `components/RemovedImage.tsx`: the "image removed" visual (an icon, with the text `common.imageRemoved` when there is room, and that text as accessible name), the size of the image it replaces. Used by `ImageDropZone` and `GameItemView` (current item, board and results screens).
- `pages/RecentUploadsPage.tsx`, `components/UploadCard.tsx`, `components/ModerationReasonDialog.tsx`: the recent uploads page of the super admins and its actions ([moderation guide](moderation.md)).
- The error codes are translated in `src/i18n/locales/`, and `src/i18n/index.ts` defines the `megabytes` formatter.
