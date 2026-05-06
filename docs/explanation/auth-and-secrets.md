# Auth and secrets

There is exactly one secret in all-my-favs: the bearer token, called `AMF_API_KEY`. Everything authenticated checks against it. This document explains why it looks the way it does, and why secrets are resolved at deploy time rather than runtime.

## Why a single bearer token

all-my-favs is a single-user tool. Every client that touches it — the web dashboard (you), the Firefox extension (you), `wytcher` (your script), `cms` (your script) — operates with full privileges. Modeling a user table, sessions, OAuth, or per-client scopes would buy nothing and add a lot.

A 40-character random hex string in `Authorization: Bearer …` is enough. The interesting design choices are about *how* the string gets into the app, not how it's checked.

## Multiple acceptable transports

The same token is accepted in four places (see `app/auth.py`):

| Method                | Used by                                  |
|-----------------------|------------------------------------------|
| `Authorization: Bearer` | API clients (preferred)                |
| `X-API-Key` header    | Clients that can't easily set `Authorization` (some webhook senders) |
| `?api_key=` query     | Cookie bootstrap on first dashboard visit; CLI quick tests |
| `amf_session` cookie  | Browser sessions, set by `/login`        |

Comparison uses `hmac.compare_digest` — constant-time. That's belt-and-suspenders for a single-user tool, but it's two lines and removes a class of attack from the threat model.

## Why secrets are resolved at deploy time, not runtime

Two patterns exist for getting secrets out of 1Password into a container:

1. **Deploy-time injection** (what we use): `op run --env-file=.env -- docker compose up -d`. The `op` CLI resolves `op://...` references in `.env`, sets them as env vars in the host shell, and Compose interpolates them into the container. The container itself never talks to 1Password.

2. **Runtime fetch**: the app boots with no secret, then makes an authenticated call to 1Password Connect (or Vault, or Doppler) at startup or on every secret use.

Trade-offs:

| Concern                | Deploy-time                               | Runtime                                  |
|------------------------|-------------------------------------------|------------------------------------------|
| Network dependency on boot | None                                  | Hard fail if 1Password Connect is down   |
| Audit log of "who pulled the secret" | The host that ran `op run`      | The app, every restart                   |
| Rotation visibility    | Restart the app to pick up new value      | Picked up on next fetch (or next restart)|
| Container blast radius | Secret is in container env (visible to anything that can `docker inspect`) | Same, plus a 1Password access token must live somewhere |
| Homelab fit            | Matches existing SOPS/op patterns under `~/homelab/` | Requires a new long-lived service-account token |

Deploy-time wins for a homelab tool because there's no SLA reason to outsource a 16-byte string lookup to a network round-trip on every container start, and the runtime variant moves the credential problem rather than solving it (now you have a token to fetch the token).

## Why `min_length=16`

Pydantic refuses to start the app if `AMF_API_KEY` is shorter than 16 characters. This catches:

- Empty strings from a bad `op://` reference (would otherwise authenticate everyone).
- Placeholder values like `changeme`.
- Accidentally publishing a build with the example value still set.

The bootstrap script generates 40 chars, well above the floor.

## Cookie posture

When `/login` succeeds, the server sets `amf_session` with `HttpOnly`, `SameSite=Lax`, and `Secure` controlled by `AMF_COOKIE_SECURE` (default `false` for local dev, `true` in the homelab compose unit because Traefik terminates TLS).

`SameSite=Lax` is the right choice for a self-hosted dashboard you mostly visit directly. `Strict` would log you out every time you clicked an external link back to the dashboard; `None` would broaden CSRF surface unnecessarily. There are no sensitive POSTs from third-party origins because the token isn't accepted from cross-site requests by default.

## What's *not* in the threat model

- **Multi-tenancy** — there's one user. If you add a second one, treat that as a rewrite, not a feature.
- **Browser malware on the user's laptop** — extension storage isn't encrypted; if your laptop is owned, your bookmarks are owned. That's true of every browser extension.
- **Network adversary on the LAN** — Traefik provides TLS for the deployed instance. Local dev is `http://localhost:8787` and trusts loopback.
