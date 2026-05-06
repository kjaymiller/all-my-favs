# Getting started

By the end of this tutorial you'll have all-my-favs running on your laptop, you'll have saved your first bookmark from a browser tab, and you'll see it on the dashboard. About 10 minutes.

## Prerequisites

- [Docker](https://docs.docker.com/engine/install/) (engine + compose v2)
- [`uv`](https://docs.astral.sh/uv/) (Python toolchain)
- [1Password CLI](https://developer.1password.com/docs/cli) (`op`), signed in
- Firefox (any recent version)

## 1. Get the code

```bash
git clone https://github.com/kjaymiller/all-my-favs.git ~/all-my-favs
cd ~/all-my-favs
```

## 2. Generate secrets in 1Password

The bootstrap script creates a 1Password item with a fresh API key + DB password and writes a `.env.op` that references them:

```bash
VAULT=Private ./scripts/op-bootstrap.sh
```

You should see:

```
✓ created.
✓ wrote /home/you/all-my-favs/.env.op
```

## 3. Start the stack

```bash
op run --env-file=.env.op -- docker compose up -d --build
```

This builds the app image and starts two containers:

- `all-my-favs-db-1` — Postgres 18
- `all-my-favs-app-1` — FastAPI + uvicorn

Wait ~10 seconds, then verify:

```bash
curl http://localhost:8787/healthz
# {"status":"ok"}
```

## 4. Open the dashboard

```bash
op read "op://Private/all-my-favs/api_key"   # copy the value
```

Visit <http://localhost:8787/>. You'll be redirected to `/login` — paste the API key. The dashboard appears (with all-zero stats; we haven't saved anything yet).

## 5. Install and configure the Firefox extension

In Firefox: open `about:debugging#/runtime/this-firefox` → **Load Temporary Add-on…** → pick `~/all-my-favs/extension/manifest.json`.

Click the toolbar icon → **Settings** and fill in:

- **Base URL:** `http://localhost:8787`
- **API key:** the same key you used in step 4

Save.

## 6. Save your first bookmark

Open any page (try <https://fastapi.tiangolo.com>). Click the all-my-favs toolbar icon. The URL and title pre-fill. Add a tag — try `tech:python` — then click **Save**. The popup closes after a moment.

## 7. Confirm it appears

Refresh <http://localhost:8787/>. You'll see:

- **Total: 1**, **Today: 1**
- A bar in today's slot of the *Links saved per day* chart
- The bookmark in **Recent**, with `tech:python` as a tag
- `fastapi.tiangolo.com` in **Top domains**

Click the tag to filter the bookmarks list.

## What's next

- [Deploy to your homelab](../how-to/deploy-to-homelab.md)
- [Add bookmarks programmatically via the REST API](../how-to/add-a-bookmark-via-api.md)
- Skim [the architecture explanation](../explanation/architecture.md) for the why behind these choices.
