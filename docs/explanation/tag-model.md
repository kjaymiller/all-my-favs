# The tag model

Tags are flat, lowercase, colon-separated strings:

```
tech:python
reading:longform
inbox
```

This is deliberate. This document explains why it's not, say, a `tags` table with a `parent_id`, or a JSON array on `bookmarks`, or a richer object with `color` and `description`.

## Goal: one wire format across tools

all-my-favs is one corner of an ecosystem. `wytcher` already uses `tag:subtag` strings; `cms` will too; the Firefox extension's text input is also a comma-separated list of strings.

If every tool serialized tags differently — one as `{"name": "x", "parent": "y"}`, another as `["y/x"]`, another as `"y::x"` — round-tripping a bookmark through two tools would mangle its tags. Picking the simplest format (a string) and standardizing on it across tools makes integration boring, which is the goal.

## Why not model hierarchy as `parent_id`?

A relational hierarchy would let you query "all bookmarks under `tech:*`" with a recursive CTE. Worth it?

Cost:

- Every tag write becomes "look up parent → create chain → insert".
- The wire format becomes objects with IDs, or you keep the string format and pay the modeling cost twice.
- Tools that don't care about hierarchy (most of them) still pay the schema complexity.

Benefit: a single query pattern (`name LIKE 'tech:%'`) you'd otherwise write as a CTE.

`LIKE 'tech:%'` against an indexed `name` column is fine for the dataset size involved. Storing the string is simpler everywhere — code, API, UI, sibling tools — for a query pattern that almost never appears in practice.

## Why not a JSON array on `bookmarks`?

```sql
ALTER TABLE bookmarks ADD COLUMN tags text[];
```

Tempting. Skips the join table entirely.

It loses:

- Tag-level metadata if we ever want it (counts, last-used).
- Renaming a tag globally (now you UPDATE every row whose array contains the old name).
- A normalized place to enforce the regex once.

The current schema (`tags` + `bookmark_tags`) costs one join and gains all of those.

## Why lowercase + a regex?

Validated against `[a-z0-9][a-z0-9._-]*(:[a-z0-9][a-z0-9._-]*)*` and lowercased before storage:

- **Lowercase** prevents `Tech:Python` and `tech:python` from being treated as different tags. Users will mistype case constantly.
- **Regex** keeps the wire format predictable so URLs (`?tag=tech:python`) don't need escaping for spaces, `/`, or punctuation that Postgres' `tsquery` parser cares about.
- **Allowed chars** include `.` `_` `-` so things like `tech:c++` would not validate (intentional — c++ becomes `tech:cpp` or `tech:c-plus-plus`); permissiveness here is a slippery slope.

## When this falls down

- **Display grouping** — if the dashboard ever wants a tree view, it splits on `:` at render time. No schema change needed.
- **Mass rename** — currently a single `UPDATE tags SET name=...` works because every bookmark references via `bookmark_tags.tag_id`, not the string. Cheap.
- **Aliasing** ("tech:py" → "tech:python") — would require a `tag_aliases` table. Out of scope for v1; revisit if it actually comes up.

## Practical guidance

- Reach for two-level tags for things that benefit from grouping (`tech:python`, `tech:rust`, `reading:longform`, `reading:shortform`).
- Use a single token for cross-cutting state (`inbox`, `archived`, `favorite`).
- Don't go three levels deep (`tech:python:django`) unless you really need it. The tag list UI gets noisy fast.
