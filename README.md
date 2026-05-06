# all-my-favs

Self-hosted URL bookmark manager. FastAPI + Postgres, REST API + dashboard, Firefox extension. Designed for a single user on their own homelab, integrating with sibling tools (`wytcher`, `cms`).

Production deployment: <https://favs.kjaymiller.dev>

## Documentation

Organized by [Diátaxis](https://diataxis.fr/):

- **[Tutorials](docs/tutorials/)** — learn by doing
  - [Getting started](docs/tutorials/getting-started.md)
- **[How-to guides](docs/how-to/)** — accomplish a task
  - [Deploy to the homelab](docs/how-to/deploy-to-homelab.md)
  - [Install the Firefox extension](docs/how-to/install-the-firefox-extension.md)
  - [Add a bookmark via the REST API](docs/how-to/add-a-bookmark-via-api.md)
  - [Rotate the API key](docs/how-to/rotate-api-key.md)
  - [Back up and restore](docs/how-to/back-up-and-restore.md)
- **[Reference](docs/reference/)** — look something up
  - [REST API](docs/reference/api.md)
  - [Configuration (env vars)](docs/reference/configuration.md)
  - [Data model](docs/reference/data-model.md)
  - [Compose unit](docs/reference/compose-unit.md)
- **[Explanation](docs/explanation/)** — understand the why
  - [Architecture](docs/explanation/architecture.md)
  - [Tag model](docs/explanation/tag-model.md)
  - [Auth and secrets](docs/explanation/auth-and-secrets.md)

New here? Start with [the getting-started tutorial](docs/tutorials/getting-started.md).

## Repository layout

```
app/                FastAPI service (routers, models, templates, static)
alembic/            Database migrations
extension/          Firefox MV3 extension
scripts/            Operational scripts (1Password bootstrap, …)
docs/               Documentation (Diátaxis)
docker-compose.yml  Local dev stack
Dockerfile          Production image
```

## Conventions

- **uv for Python** — `uv run`, `uv sync`, `uv add`. Don't fall back to `pip` / `python3`.
- **Postgres-first** — search uses `tsvector`; counters use SQL aggregates.
- **Tag wire format never changes** — sibling tools depend on the colon-string contract.
- **Secrets resolved at deploy time, not runtime** — see [auth-and-secrets](docs/explanation/auth-and-secrets.md).

## License

MIT (or your preference — update before publishing).
