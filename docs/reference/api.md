# API reference

Base URL (production): `https://favs.kjaymiller.dev`
Base URL (local dev): `http://localhost:8787`

All `/api/*` endpoints require authentication. The web routes (`/`, `/bookmarks`, …) accept the same credentials and additionally support a session cookie set by `/login`.

## Authentication

Send the API key via any of these:

| Method                | Header / value                            |
|-----------------------|-------------------------------------------|
| Bearer (preferred)    | `Authorization: Bearer <api_key>`         |
| Custom header         | `X-API-Key: <api_key>`                    |
| Query string          | `?api_key=<api_key>`                      |
| Cookie (browser only) | `amf_session=<api_key>` (set by `/login`) |

Missing or wrong → `401 Unauthorized`.

## Bookmarks

### Create / upsert

```
POST /api/bookmarks
Content-Type: application/json
```

```json
{
  "url": "https://example.com/post",
  "title": "Example",
  "description": "...",
  "notes": "...",
  "source": "firefox-ext",
  "favicon_url": "https://example.com/favicon.ico",
  "tags": ["tech:python", "reading:longform"]
}
```

- `url` is the natural key. Posting again with the same URL **updates** the existing row (URL is unique).
- `tags` is a JSON array of `tag:subtag` strings. Lowercased + de-duplicated server-side.
- `domain` is derived from `url` automatically.

**Response:** `201 Created`, full `Bookmark` object.

### List / search

```
GET /api/bookmarks
  ?q=<full-text query>          # websearch_to_tsquery on title/desc/url/notes
  &tag=tech:python              # repeatable; AND semantics across tags
  &domain=example.com
  &limit=50                     # 1..500, default 50
  &offset=0
```

When `q` is set, results are ranked by `ts_rank`. Otherwise, ordered by `created_at DESC`.

**Response:** `200 OK`, array of `Bookmark`.

### Fetch / update / delete

```
GET    /api/bookmarks/{id}
PATCH  /api/bookmarks/{id}     # partial; tags array (if sent) replaces existing
DELETE /api/bookmarks/{id}     # 204 No Content
```

### `Bookmark` shape

```json
{
  "id": 42,
  "url": "https://example.com/post",
  "title": "Example",
  "description": null,
  "notes": null,
  "source": "firefox-ext",
  "favicon_url": null,
  "domain": "example.com",
  "created_at": "2026-05-06T18:24:11.123456+00:00",
  "updated_at": "2026-05-06T18:24:11.123456+00:00",
  "tags": ["tech:python", "reading:longform"]
}
```

## Tags

```
GET /api/tags
```

```json
[
  { "name": "tech:python",      "count": 42 },
  { "name": "reading:longform", "count": 17 }
]
```

Sorted by descending count, then name ascending.

## Stats

```
GET /api/stats?days=30&top=10
```

```json
{
  "total": 482,
  "added_today": 3,
  "added_last_7d": 21,
  "added_last_30d": 84,
  "per_day": [
    { "day": "2026-04-07", "count": 0 },
    { "day": "2026-04-08", "count": 5 }
  ],
  "top_domains": [
    { "domain": "github.com", "count": 51 }
  ],
  "top_tags": [
    { "name": "tech:python", "count": 42 }
  ]
}
```

- `days`: 1..365, default 30. `per_day` always has exactly `days` entries (zero-filled).
- `top`: 1..50, default 10.

## Health

```
GET /healthz
```

Unauthenticated. Returns `{"status":"ok"}` while the app process is alive. Used by the Docker `HEALTHCHECK` and the kuma uptime monitor.

## Errors

Standard HTTP semantics. Error bodies are JSON:

```json
{ "detail": "bookmark not found" }
```

For browser routes (anything outside `/api/`), a `401` is rewritten to a `303` redirect to `/login?next=<path>` instead of a JSON body — this lets the dashboard/bookmarks pages "just work" with the session cookie.

## Examples

```bash
KEY=$(op read "op://Private/all-my-favs/api_key")

# Save a bookmark
curl -fsS -X POST https://favs.kjaymiller.dev/api/bookmarks \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://fastapi.tiangolo.com","tags":["tech:python","tech:web"]}'

# Search
curl -fsS "https://favs.kjaymiller.dev/api/bookmarks?q=fastapi&tag=tech:python" \
  -H "Authorization: Bearer $KEY"

# Stats for a chart
curl -fsS "https://favs.kjaymiller.dev/api/stats?days=14" \
  -H "Authorization: Bearer $KEY"
```
