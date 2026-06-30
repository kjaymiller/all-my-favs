# Add a URL route

Goal: add a per-fav link button that opens another service with the fav's data prefilled when the
fav's URL matches a pattern.

Routes are **data, not code** — they live in a JSON file (`app/plugins.json`, overridable with
`AMF_PLUGINS_CONFIG`). all-my-favs renders a button on every matching fav; clicking it sends the
fav's fields to the target service in one of two ways:

- **url params** (`"method": "GET"`, the default) — a plain link with the params as a query string.
- **body params** (`"method": "POST"`) — a form the browser submits with the params as fields.

Either way the **browser** makes the request, so there are no server-side calls and no secrets.

The shipped `app/plugins.json` is empty. See `app/plugins.example.json` for the shape:

```json
{
  "plugins": [
    {
      "label": "Microblog",
      "pattern": ".",
      "url": "https://cms.kjaymiller.dev/microblog/new",
      "method": "GET",
      "params": { "url": "{url}", "description": "{description}", "tags": "{tags}" }
    },
    {
      "label": "Add to wytcher",
      "pattern": "youtube\\.com|youtu\\.be",
      "url": "https://wytchr.kjaymiller.dev/channels/add",
      "method": "POST",
      "params": { "url": "{url}" }
    }
  ]
}
```

| Field | Meaning |
|---|---|
| `label` | Button text. |
| `pattern` | Regex matched (case-insensitive) against the fav's URL. `.` matches every link. |
| `url` | Target route. |
| `method` | `GET` (default) sends params in the URL; `POST` sends them as the form body. |
| `params` | Values sent to `url`. They can interpolate fav fields (see below). |

## Placeholders

`params` values can interpolate fields from the fav:

`{url}`, `{title}`, `{description}`, `{tags}` (comma-joined tag names), `{domain}`.

Unknown placeholders render as empty strings.

## Add your own

Append an entry to `app/plugins.json` and restart the app. No migration, no code change. The link
appears automatically on every fav whose URL matches `pattern`.
