# Data model reference

Three tables, defined in `app/models.py` and created by `alembic/versions/0001_initial.py`.

## `bookmarks`

| Column          | Type                       | Notes |
|-----------------|----------------------------|-------|
| `id`            | `bigint`, PK               | Surrogate. |
| `url`           | `text`, **unique** NOT NULL| Natural key — POST with the same URL upserts. |
| `title`         | `text`                     | |
| `description`  | `text`                     | |
| `notes`         | `text`                     | Free-form notes. |
| `source`        | `text`                     | E.g. `firefox-ext`, `web`, `wytcher`. Useful for stats. |
| `favicon_url`   | `text`                     | |
| `domain`        | `text`, indexed            | Derived from `url`; `www.` stripped. Powers the "top domains" stat and `?domain=` filter. |
| `created_at`    | `timestamptz` NOT NULL     | `default now()`. Indexed for "recent" + per-day stats. |
| `updated_at`    | `timestamptz` NOT NULL     | `default now()`, `onupdate now()`. |
| `search_vector` | `tsvector`, **generated**  | `STORED` column, GIN-indexed. See below. |

### Full-text search

```sql
search_vector :=
    setweight(to_tsvector('english', coalesce(title,        '')), 'A') ||
    setweight(to_tsvector('english', coalesce(description,  '')), 'B') ||
    setweight(to_tsvector('english', coalesce(url,          '')), 'C') ||
    setweight(to_tsvector('english', coalesce(notes,        '')), 'D');
```

Querying uses `websearch_to_tsquery('english', q)` — supports `"phrase"`, `-negation`, and `OR`.

GIN index: `bookmarks_search_idx ON bookmarks USING GIN (search_vector)`.

## `tags`

| Column | Type                 | Notes |
|--------|----------------------|-------|
| `id`   | `bigint`, PK         | |
| `name` | `text`, **unique**   | The full `tag:subtag` string. Lowercased. |

There is **no** `parent_id` — hierarchy is purely lexical. See [the tag-model explanation](../explanation/tag-model.md) for why.

## `bookmark_tags`

Pure join table.

| Column        | Type                     | Notes                                      |
|---------------|--------------------------|--------------------------------------------|
| `bookmark_id` | `bigint`, PK, FK→bookmarks(id) | `ON DELETE CASCADE`                  |
| `tag_id`      | `bigint`, PK, FK→tags(id)      | `ON DELETE CASCADE`                  |

The composite `(bookmark_id, tag_id)` PK enforces uniqueness; deleting a bookmark removes its tag links automatically.
