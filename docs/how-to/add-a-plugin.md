# Add a plugin

Goal: add a per-fav action button that fires a backend REST call to another service when a fav's
URL matches a pattern.

Plugins are **data, not code** — they live in a JSON ruleset (`app/plugins.json`, overridable with
`AMF_PLUGINS_CONFIG`). all-my-favs renders a button on every matching fav; clicking it makes the
configured request **server-side**, so secrets never reach the browser.

## 1. The ruleset

```json
{
  "plugins": [
    {
      "key": "microblog",
      "label": "Microblog",
      "pattern": ".",
      "url": "https://cms.kjaymiller.dev/microblog/new",
      "method": "GET",
      "params": { "url": "{url}", "description": "{description}", "tags": "{tags}" }
    },
    {
      "key": "wytcher",
      "label": "Add to wytcher",
      "pattern": "youtube\\.com|youtu\\.be",
      "url": "https://wytchr.kjaymiller.dev/channels/add",
      "method": "POST",
      "params": { "url": "{url}" },
      "headers": { "X-Plugin-Secret": "${WYTCHER_WEBHOOK_SECRET}" }
    }
  ]
}
```

| Field | Meaning |
|---|---|
| `key` | Stable id used in the button's route (`/bookmarks/{id}/plugins/{key}`). |
| `label` | Button text. |
| `pattern` | Regex matched (case-insensitive) against the fav's URL. `.` matches every link. |
| `url` | Target route to call. Supports `${ENV_VAR}` substitution. |
| `method` | `GET` (default) or `POST` / any verb. |
| `params` | Values sent to the target. See placeholders below. |
| `headers` | Optional request headers. Supports `${ENV_VAR}`. |

## 2. Placeholders

`params` (and `url`/`headers`) values can interpolate fields from the fav:

`{url}`, `{title}`, `{description}`, `{tags}` (comma-joined tag names), `{domain}`.

Unknown placeholders render as empty strings.

- **`GET`** → `params` are sent as the query string.
- **`POST`** (or any non-GET) → `params` are sent as a JSON body.

## 3. Secrets

Reference an environment variable with `${VAR}` in `url` or `headers`. The value is resolved from
the process environment at startup, so the secret stays out of the JSON. Example: the `wytcher`
rule sends `X-Plugin-Secret: ${WYTCHER_WEBHOOK_SECRET}` — set `WYTCHER_WEBHOOK_SECRET` in the
environment (see `.env.op.example`). Note: these are plain env vars, **not** `AMF_`-prefixed.

## 4. Add your own

Append a rule to `app/plugins.json` and restart the app. No migration, no code change. The button
appears automatically on every fav whose URL matches `pattern`.
