# Architecture

```
┌──────────────────┐       ┌──────────────────┐       ┌──────────────────┐
│ Firefox extension│──┐    │ wytcher / cms    │──┐    │ Web dashboard    │
└──────────────────┘  │    └──────────────────┘  │    └──────────────────┘
                      ▼                          ▼               ▲
                ┌──────────────────────────────────────────────┐ │
                │   FastAPI service  (REST API + Web UI)       │─┘
                └──────────────────┬───────────────────────────┘
                                   ▼
                            ┌──────────────┐
                            │  Postgres 18 │  (FTS via tsvector + GIN)
                            └──────────────┘
```

all-my-favs is intentionally one service plus one database. This document explains why each piece looks the way it does.

## Why FastAPI

The same process serves the REST API and the dashboard. Splitting them into separate services would buy nothing for a single-user tool and would double the deploy/restart surface. FastAPI lets one router file (`app/routers/web.py`) emit Jinja2-rendered HTML and a sibling router (`app/routers/bookmarks.py`) emit JSON, sharing the same SQLAlchemy session and auth dependency.

OpenAPI lives at `/docs` for free, which means the next sibling tool that integrates with all-my-favs can codegen a client.

## Why Postgres (not SQLite)

The dataset for a single user is small enough that SQLite + FTS5 would handle it forever. The deciding factor was concurrent writers: the Firefox extension, the dashboard, `wytcher`, and (later) `cms` may all POST at once. Postgres handles that without contention; SQLite would need a write queue.

Postgres also fits the homelab's "Postgres-first" principle (see `~/homelab/HOMELAB.md`), which means restic, `pg_dump`, and observability patterns already exist for it.

## Why server-rendered HTML for the UI

A SPA is overkill when:

- The data lives one network hop away on the same host.
- Every page is fundamentally a list or a form.
- There's no offline mode and no mobile app.

Jinja2 + a single Chart.js bar chart gives a fast dashboard with zero build step, zero JS framework lock-in, and full functionality if the user disables JavaScript on everything except the chart.

## Why a generated `tsvector`

Computing the search vector at query time (`to_tsvector(title) @@ ...`) blocks Postgres from using an index. A generated `STORED` column lets the GIN index pre-build exactly the right terms, weighted A→D across title/description/URL/notes. Search stays fast as the table grows, and there's no application-side trigger to keep in sync.

`websearch_to_tsquery` parses what users actually type — `"exact phrase"`, `-negation`, `OR` — without the operator-soup syntax of raw `tsquery`.

## Why upsert-on-URL

Saving a tab is the most common write, and humans hit "save" twice all the time. Making `url` the natural key means the second POST updates instead of erroring. `wytcher` and `cms` can dump their full bookmark sets through the API on a schedule without de-dup logic on their end.

## Why the colon-string tag model

Treating `tag:subtag` as opaque text — instead of modeling `parent_id` — keeps the wire format identical between all-my-favs, wytcher, and any future sibling. A single `name TEXT UNIQUE` column is enough; hierarchy is recovered by splitting on `:` only when a UI wants to group. See [the tag-model explanation](tag-model.md) for the full rationale.

## Why one service, not three

Pieces that could be separate services but aren't, and why:

| Could be separate          | But isn't                                                                 |
|----------------------------|---------------------------------------------------------------------------|
| Reverse proxy / TLS        | Handled by the existing homelab Traefik — no per-service proxy needed.    |
| Static asset CDN           | Tiny CSS + a CDN-hosted Chart.js. The app serves its own `/static/`.      |
| Background job runner      | No background work in v1 — everything is request/response.                |
| Search engine (Meilisearch)| Postgres FTS handles the workload; one less piece to babysit.             |

If any of those constraints change (background imports, multi-user, large-scale fuzzy search), the migration paths are obvious — but doing it now would be premature.

## Trust boundary

There is exactly one — the bearer token. Everything inside the trust boundary (the dashboard, the REST API, the extension's saved key) operates with the same privileges, because it's a single-user tool. See [auth-and-secrets](auth-and-secrets.md).
