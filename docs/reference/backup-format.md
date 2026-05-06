# Backup format (JSONL)

Canonical flat-file format used by `GET /api/export` and `POST /api/import`.

## Shape

[JSON Lines](https://jsonlines.org/): one JSON object per line, UTF-8, no trailing comma, no enclosing array. Order is `created_at ASC, id ASC` — stable across exports.

```json
{"url":"https://fastapi.tiangolo.com","title":"FastAPI","description":null,"notes":null,"source":"firefox-ext","favicon_url":null,"tags":["tech:python","tech:web"],"created_at":"2026-04-29T18:24:11.123456+00:00","updated_at":"2026-04-29T18:24:11.123456+00:00"}
{"url":"https://example.com","title":null,"description":null,"notes":"read later","source":"web","favicon_url":null,"tags":["inbox"],"created_at":"2026-05-01T12:00:00+00:00","updated_at":"2026-05-01T12:00:00+00:00"}
```

## Fields

| Field          | Type                       | Required on import | Notes |
|----------------|----------------------------|--------------------|-------|
| `url`          | string (URL)               | yes                | Natural key; import upserts on this. |
| `title`        | string \| null             | no                 | |
| `description`  | string \| null             | no                 | |
| `notes`        | string \| null             | no                 | |
| `source`       | string \| null             | no                 | E.g. `firefox-ext`, `web`, `wytcher`. |
| `favicon_url`  | string (URL) \| null       | no                 | |
| `tags`         | array of strings           | no (defaults `[]`) | Wytcher-style `tag:subtag` flat strings. Lowercased + de-duplicated on import. |
| `created_at`   | string (ISO 8601) \| null  | no (informational) | Present on export. **Ignored on import** — re-creation timestamp wins. |
| `updated_at`   | string (ISO 8601) \| null  | no (informational) | Same. |

Fields not listed above are ignored on import — extending the export with extra metadata is forward-compatible. `id` and `domain` are not exported because both are derivable (`id` is a surrogate; `domain` is parsed from `url`).

## Import semantics

`POST /api/import` accepts the same JSONL format as a request body with `Content-Type: application/x-ndjson` (or `application/json` — the parser only cares about line-by-line JSON):

- Each line is parsed and validated against the same schema as `POST /api/bookmarks`.
- For each valid line, the bookmark is **upserted by URL** — re-importing the same file is safe and idempotent.
- Blank lines are skipped.
- Invalid lines are collected and reported in the response. If **no** lines succeeded, the whole import is rolled back and a 400 is returned. If at least one succeeded, the import commits and the response includes an `errors` count.

### Response

```json
{"imported": 47, "created": 47, "updated": 0, "errors": 0}
```

| Key        | Meaning |
|------------|---------|
| `imported` | Lines that were successfully inserted or updated |
| `created`  | Of those, how many were *new* (URL not seen before) |
| `updated`  | `imported - created` |
| `errors`   | How many lines failed validation; their line numbers + messages are logged |

## Why JSONL (and not …)

| Alternative | Why JSONL beats it for this use case |
|-------------|---------------------------------------|
| **Single JSON array** | Can't stream — exporter has to buffer the whole array before flushing brackets. JSONL streams naturally. |
| **CSV / TSV** | Tags are an array; embedding arrays in CSV is awkward (quoting, escaping). Notes contain newlines. |
| **YAML** | Wider syntax surface, slower to parse, harder to grep. |
| **`pg_dump -Fc`** | Binary; locked to a specific Postgres major version; can't diff or hand-edit. |
| **Netscape bookmarks HTML** | Lossy — no notes, no `source`, no structured tags; designed for browser interop, not data ownership. |

## Compatibility with sibling tools

The same JSONL shape is the canonical interchange format between all-my-favs and any sibling tool (wytcher, cms). A minimal valid line is:

```json
{"url":"https://example.com","tags":["inbox"]}
```

That's enough to round-trip a bookmark through any tool in the ecosystem with no data loss for what matters.
