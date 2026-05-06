# Configuration reference

All settings are read from environment variables prefixed `AMF_`. They're parsed by `app/config.py` (`pydantic-settings`).

## App settings

| Variable             | Required | Default                                              | Notes |
|----------------------|----------|------------------------------------------------------|-------|
| `AMF_API_KEY`        | yes      | —                                                    | Bearer token. `min_length=16`. App refuses to start if missing or too short. |
| `AMF_DATABASE_URL`   | no       | `postgresql+psycopg://amf:amf@db:5432/amf`           | Any SQLAlchemy URL works; project is built around Postgres. |
| `AMF_COOKIE_NAME`    | no       | `amf_session`                                        | Session cookie name set by `/login`. |
| `AMF_COOKIE_SECURE`  | no       | `false`                                              | Set `true` behind HTTPS so the browser only sends the cookie over TLS. |

## Compose-only variables

These are consumed by `docker-compose.yml` / `~/homelab/compose/all-my-favs/compose.yml`, not by the app process directly:

| Variable             | Default | Notes |
|----------------------|---------|-------|
| `AMF_DB_PASSWORD`    | `amf`   | Used to build `AMF_DATABASE_URL` and the `POSTGRES_PASSWORD` env var. |
| `AMF_PORT`           | `8787`  | Host-side bind port (local dev compose only; the homelab unit goes through Traefik). |

## Where values come from in production

```
1Password item                              .env (resolved by op run)              container env
"all-my-favs" (vault: Private)              ─────────────────────────────────►     AMF_API_KEY
  ├── api_key                                                                       AMF_DB_PASSWORD
  └── db_password                                                                   ...
```

The `.env.op` (project repo) and `.env` (homelab compose unit) hold `op://...` references — never literal secrets. `op run --env-file=... -- docker compose up` resolves them, sets them in the host environment, and Compose interpolates them into the container `environment:` block.

## Where they come from in dev

The app will read a literal `.env` file at the project root if present (Pydantic settings does this). Use it for ad-hoc testing **without** secrets — keep secrets in 1Password.
