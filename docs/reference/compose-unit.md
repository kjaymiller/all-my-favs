# Compose unit reference

The production deployment lives at `~/homelab/compose/all-my-favs/compose.yml`.

## Services

| Service  | Image                | Container name  | Networks            | Notes |
|----------|----------------------|-----------------|---------------------|-------|
| `amf-db` | `postgres:18.3-alpine` | `amf-db`      | `amf_net`           | Private bridge network only — never on `proxy_net`. Healthcheck: `pg_isready -U amf -d amf`. Volume: `/srv/all-my-favs/pgdata:/var/lib/postgresql/data`. |
| `amf`    | `all-my-favs:local`  | `all-my-favs`   | `amf_net`, `proxy_net` | Built from `~/all-my-favs` via the `Dockerfile`. Depends on `amf-db` being healthy. |

## Networks

| Network     | Mode      | Purpose |
|-------------|-----------|---------|
| `amf_net`   | bridge    | DB ↔ app communication. Local to this compose unit. |
| `proxy_net` | external  | Created by the Traefik compose unit. The app joins it so Traefik can reach port 8000. |

## Traefik labels

```yaml
- "traefik.enable=true"
- "traefik.http.routers.all-my-favs.rule=Host(`favs.kjaymiller.dev`)"
- "traefik.http.routers.all-my-favs.entrypoints=websecure"
- "traefik.http.routers.all-my-favs.tls=true"
- "traefik.http.services.all-my-favs.loadbalancer.server.port=8000"
- "traefik.docker.network=proxy_net"
```

`tls=true` triggers your existing wildcard cert resolver — no per-service ACME config needed.

## kuma uptime labels

```yaml
- "kuma.all-my-favs.http.name=All My Favs"
- "kuma.all-my-favs.http.url=https://favs.kjaymiller.dev/healthz"
- "kuma.all-my-favs.http.interval=60"
```

Picked up by the kuma autodiscover sidecar — no manual monitor creation.

## Resource limits

| Service | Memory  | CPU  |
|---------|---------|------|
| `amf-db`| 256 MB  | 0.5  |
| `amf`   | 384 MB  | 0.5  |

Plenty of headroom for a single-user dataset of millions of rows; revisit if you start ingesting from a high-volume source.

## Required environment

Compose substitutes from the host environment. With `op run --env-file=.env -- docker compose up -d`:

| Variable           | Comes from                                     |
|--------------------|------------------------------------------------|
| `AMF_API_KEY`      | `op://Private/all-my-favs/api_key`             |
| `AMF_DB_PASSWORD`  | `op://Private/all-my-favs/db_password`         |

Both are validated with the `${VAR:?...}` pattern — if either is unset, `compose up` aborts immediately with a clear message.

## State on disk

| Path                              | Contents          | Backups |
|-----------------------------------|-------------------|---------|
| `/srv/all-my-favs/pgdata`         | Postgres data dir | Restic (via `/srv/` policy) |

Nothing else persists outside the image — the app is fully stateless.
