# Install the Firefox extension

Goal: save the current tab to all-my-favs from your browser toolbar.

## Load the extension

### Option A — load directly from source (fastest for dev)

1. Open `about:debugging#/runtime/this-firefox`.
2. Click **Load Temporary Add-on…**.
3. Pick `~/all-my-favs/extension/manifest.json`.

The toolbar icon appears immediately. Temporary add-ons are removed when Firefox restarts — fine for a dev loop.

### Option B — build a zip and install that

```bash
cd ~/all-my-favs/extension
npm install
npm run build         # writes dist/all_my_favs-0.1.0.zip
```

Mozilla won't let regular Firefox install unsigned add-ons permanently. Two ways around it:

- Use Firefox **Developer Edition** or **Nightly**, set `xpinstall.signatures.required=false` in `about:config`, then drag-drop the zip onto `about:addons`.
- Submit the zip to <https://addons.mozilla.org/developers/> for self-distribution signing (free).

## Configure

Click the toolbar icon → **Settings** and fill in:

| Field      | Value                                                   |
|------------|---------------------------------------------------------|
| Base URL   | `https://favs.kjaymiller.dev` (or `http://localhost:8787` for local dev) |
| API key    | `op read "op://Private/all-my-favs/api_key"`            |

The values are stored in `browser.storage.local` — they're per-profile, not synced.

## Use it

1. Open any page.
2. Click the all-my-favs toolbar icon. URL and title pre-fill from the active tab.
3. Add tags, comma-separated, in `tag:subtag` form: `tech:python, reading:longform`.
4. Click **Save**. The popup closes when the API confirms.

`source` is automatically set to `firefox-ext` so you can filter dashboard stats by it later.

## Live development

```bash
cd ~/all-my-favs/extension
npm run run     # opens a temp Firefox with the extension auto-reloaded on changes
```
