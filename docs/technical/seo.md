# Search engines and link previews

How TierList is read by search engines and by link previews (Discord, WhatsApp, X…), #458. TierList is a single-page app: these readers often run no JavaScript, so everything they need is written by the backend into the page it serves.

## 1. How it works

FastAPI serves the Vite build ([deployment guide](deployment.md#21-one-origin-the-api-under-api)). For every path that is not a file of the build, the catch-all of `app/core/frontend.py` answers `index.html` with the `<head>` of that page:

1. `get_page_head` (`api/dependencies.py`) picks the language from `Accept-Language` (`seo/language.py`) and asks `SeoService.page_head` (`services/seo.py`) for a `PageHead`: title, description, image, canonical URL and HTTP status.
2. `render_page` (`seo/head.py`) replaces the `<title>` and the `lang` of `<html>`, then writes the tags before `</head>`.
3. The response sends `Vary: Accept-Language`, and `X-Robots-Tag: noindex` when the page is not indexable.

In the browser, the frontend then names the tab as the user navigates (`useDocumentTitle`, §5).

## 2. Pages

| Page                                           | Indexable        | Title                                    | Image                                  |
| ---------------------------------------------- | ---------------- | ---------------------------------------- | -------------------------------------- |
| `/`                                            | yes              | `TierList · Classez ensemble, en direct` | `/og-image.png`                        |
| `/marketplace`, `/privacy`, `/terms`, `/legal` | yes              | `<page title> · TierList`                | `/og-image.png`                        |
| `/marketplace/templates/{id}`, listed template | yes              | `<template name> · TierList`             | first visible tile image, else default |
| `/marketplace/templates/{id}`, otherwise       | no, **HTTP 404** | site title                               | `/og-image.png`                        |
| any other path (rooms, results, sign-in…)      | no               | site title                               | `/og-image.png`                        |

- **Indexable** means a canonical URL (`<link rel="canonical">`, `og:url`) and no `noindex`. The canonical URL is built from `FRONTEND_BASE_URL`, never from the host of the request, and a template's from its parsed id (one URL per template, whatever the case of the id).
- **Template pages** go through `MarketplaceService.get_template`, so they follow the listing rule of the public page ([templates guide](templates.md#210-public-template-page)). A private, hidden or deleted template, a banned owner, an unknown id or an id that is not a UUID in its usual form (`8-4-4-4-12` hex digits, any case, as the frontend checks) all get the same 404. React still shows its "unavailable template" page.
- **Rooms and results** are shared by link and are never indexed, but their link previews still get the site title and image.
- **Tags written**: `<title>`, `description`, `og:type`, `og:site_name`, `og:locale`, `og:title`, `og:description`, `og:image`, `twitter:card` (`summary_large_image`), plus `canonical` and `og:url` when indexable. Every value goes through `html.escape`: a template or owner name cannot inject HTML.

## 3. Language

There is one URL per page, without the language: the page is written in the language the browser prefers among French and English (highest `q` in `Accept-Language`, then the first listed), in French otherwise. Crawlers often send no `Accept-Language`, so they mostly read the French version. There are no `hreflang` links.

The browser picks its language differently (the choice saved in the settings first, then `navigator.languages`, [i18n guide](i18n.md)): someone who chose English on a French browser first gets the French title and description from the server, then the English tab title once the app runs.

The texts are in `seo/texts.py`, in both languages. As for emails, this is a case where the backend writes text meant for the user ([i18n guide](i18n.md)): crawlers and link previews never run the frontend's translations. Keep them in line with the matching frontend keys (`home.visitor.*`, `marketplace.title`, `privacy.title`, `terms.title`, `legalNotice.title`, `documentTitle.*`).

## 4. robots.txt, sitemap and the setting

`SEARCH_INDEXING_ENABLED` (default `false`) decides whether the site may be indexed. It is `true` in production only ([deployment guide](deployment.md#3-environment-variables-pod-env)).

| Setting | `/robots.txt`                                    | `/sitemap.xml` | Pages                           |
| ------- | ------------------------------------------------ | -------------- | ------------------------------- |
| `false` | `Disallow: /`                                    | 404            | all `noindex`, no canonical URL |
| `true`  | `Allow: /`, then `Sitemap: <origin>/sitemap.xml` | XML            | as in §2                        |

- Both files are routes of the root app (`api/routes/seo.py`), outside `/api` and outside the OpenAPI schema.
- The sitemap lists `/`, `/marketplace`, `/privacy`, `/terms`, `/legal`, then the listed templates, newest first, with `lastmod` = the day of their `updated_at` (`MarketplaceService.list_template_updates`, same listing rule), up to 50,000 URLs (`SITEMAP_MAX_URLS`, the limit of one sitemap file).
- Pages that are not indexable are not blocked in `robots.txt` on purpose: a crawler has to read a page to see its `noindex`.
- `/api/` is not blocked either: the pages are rendered by JavaScript from it, and Googlebot respects `robots.txt` for the calls a page makes while rendering. Blocked, every page rendered as an error, which Search Console reported as a soft 404 (#485). Every `/api/` answer carries `X-Robots-Tag: noindex` instead (`NoindexMiddleware`, `app/core/noindex.py`), so the JSON answers stay out of the results.

## 5. Frontend

- `useDocumentTitle(page)` (`components/useDocumentTitle.ts`) sets `<page> · TierList` (`documentTitle.page`). When the page goes away, it gives back the site title (`documentTitle.site`). While the name is unknown (loading), it leaves the title alone, so a nested `NotFoundPage` keeps its own. It uses `document.title` rather than React's `<title>`, which would add a second `<title>` next to the server's.
- `CenteredCardPage` and `LegalPage` call it with their heading; every other page with its own heading calls it too. The home page keeps the site title.
- `frontend/public/`: `og-image.png` (1200×630, the default preview, with no text to translate), `apple-touch-icon.png` (180×180) and `favicon-48x48.png`, linked from `index.html` next to `favicon.svg`.

## 6. After a release

- Declare `https://tierlist.ladwein.dev` in Google Search Console and Bing Webmaster Tools (a DNS `TXT` record at Cloudflare proves the domain), then submit `/sitemap.xml`.
- Check a link preview with a debugger (or by pasting a public template's link in Discord) after a change of the tags or of `og-image.png`: previews are cached by each service.

## 7. Limits

- No per-language URLs, no `hreflang`, no JSON-LD, no template slug in the URL.
- The page body is still rendered by JavaScript: a crawler that runs none reads the tags but not the content.
- The sitemap is computed at each request; worth caching once the catalog is large.
- If the database fails, a template page answers `500` instead of the app.
