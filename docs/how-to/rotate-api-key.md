# Rotate the API key

Goal: replace the bearer token without losing data.

## 1. Generate and store a new key in 1Password

```bash
op item edit all-my-favs --vault Private \
  "api_key[password]=$(openssl rand -hex 24)"
```

(Or use the 1Password app: open the item → Edit → click the regenerate icon next to `api_key`.)

## 2. Restart the app so it picks up the new value

```bash
cd ~/homelab/compose/all-my-favs
op run --env-file=.env -- docker compose up -d --force-recreate amf
```

The Postgres container is untouched; only the app needs to restart.

## 3. Update every client

- **Web UI** — sign out (top-right), then sign in again with the new key.
- **Firefox extension** — toolbar icon → **Settings** → paste the new key → **Save**.
- **`wytcher` / `cms`** — re-read from 1Password (they should reference `op://Private/all-my-favs/api_key` too) and restart.

## 4. Verify

```bash
KEY=$(op read "op://Private/all-my-favs/api_key")
curl -fsS -H "Authorization: Bearer $KEY" https://favs.kjaymiller.dev/api/stats | head -c 80
```

Old sessions tied to the previous key will return `401` and be redirected to `/login`. That's expected.
