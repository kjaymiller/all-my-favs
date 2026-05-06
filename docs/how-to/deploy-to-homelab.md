# Deploy to the homelab

Goal: run all-my-favs on the K6 behind Traefik at <https://favs.kjaymiller.dev>.

This assumes you've already used [the getting-started tutorial](../tutorials/getting-started.md) once locally and that your homelab Traefik + DNS for `*.kjaymiller.dev` is already set up.

## One-time setup

```bash
# 1. Generate the 1Password item + .env.op (in the project repo)
cd ~/all-my-favs
VAULT=Private ./scripts/op-bootstrap.sh

# 2. Wire up the homelab compose unit
cd ~/homelab/compose/all-my-favs
cp .env.example .env
# .env now contains:
#   AMF_API_KEY="op://Private/all-my-favs/api_key"
#   AMF_DB_PASSWORD="op://Private/all-my-favs/db_password"

# 3. First boot (builds the image from ~/all-my-favs)
op run --env-file=.env -- docker compose up -d --build
```

The Postgres data lives at `/srv/all-my-favs/pgdata`, picked up by your existing restic policy on `/srv/`.

## Verify

```bash
docker ps --filter name=all-my-favs
curl -fsS https://favs.kjaymiller.dev/healthz
# {"status":"ok"}
```

In the kuma autodiscover dashboard you should see a new monitor **All My Favs** turning green within a minute.

## Updating

When source under `~/all-my-favs` changes:

```bash
cd ~/homelab/compose/all-my-favs
op run --env-file=.env -- docker compose up -d --build
```

Migrations run automatically on container start (`alembic upgrade head`).

## Troubleshooting

| Symptom                                                  | Likely cause                                        | Fix |
|----------------------------------------------------------|-----------------------------------------------------|-----|
| `AMF_API_KEY must be set …` on `compose up`              | `.env` missing or `op run` not wrapping the command | `op run --env-file=.env -- docker compose up -d` |
| `op run` says it's not signed in                         | 1Password CLI session expired                       | `eval $(op signin)` |
| App restart-loops, log shows `alembic` error             | DB not healthy yet on first boot                    | Wait for `amf-db` to go healthy, then restart `amf` |
| Traefik 404 for `favs.kjaymiller.dev`                    | `proxy_net` external network not attached           | `docker network inspect proxy_net` and confirm `all-my-favs` is on it |

Logs:

```bash
docker logs -f all-my-favs
docker logs -f amf-db
```

## See also

- [Compose unit reference](../reference/compose-unit.md) — every label and resource limit, explained
- [Auth and secrets explanation](../explanation/auth-and-secrets.md) — why `op run` injects at deploy time instead of runtime
- [Rotate the API key](rotate-api-key.md)
- [Back up and restore](back-up-and-restore.md)
