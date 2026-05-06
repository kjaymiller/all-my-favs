# Add a bookmark via the REST API

Goal: save a URL programmatically (from a script, another tool, or `curl`).

## 1. Get the API key

```bash
KEY=$(op read "op://Private/all-my-favs/api_key")
```

## 2. POST it

```bash
curl -fsS -X POST https://favs.kjaymiller.dev/api/bookmarks \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://fastapi.tiangolo.com",
    "title": "FastAPI",
    "tags": ["tech:python", "tech:web"],
    "source": "shell"
  }'
```

You'll get back the full bookmark object with `id`, `domain`, and timestamps.

## 3. Idempotency

POSTing the same `url` again **updates** the existing row — `url` is the natural key. Useful when a sync script doesn't track which URLs it has already sent.

## 4. From Python

```python
import os, httpx

key = os.environ["AMF_API_KEY"]
client = httpx.Client(
    base_url="https://favs.kjaymiller.dev",
    headers={"Authorization": f"Bearer {key}"},
)

client.post("/api/bookmarks", json={
    "url": "https://example.com",
    "tags": ["inbox"],
    "source": "my-script",
}).raise_for_status()
```

## 5. Bulk import

There's no bulk endpoint in v1 — just call POST in a loop. Postgres handles a few thousand inserts/sec; if you hit rate limits or want batching, open an issue.

## See also

- [API reference](../reference/api.md) — full endpoint list, query params, response shapes
- [Tag model explanation](../explanation/tag-model.md) — what `tag:subtag` means and why
