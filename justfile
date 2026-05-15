# all-my-favs — project task runner.
# `just` lists recipes; pair with the homelab `[all-my-favs]` group for ops.

set shell := ["bash", "-euo", "pipefail", "-c"]

[private]
_root := justfile_directory()
[private]
_homelab := env_var_or_default('HOMELAB_ROOT', env_var('HOME') + "/homelab")

# Default: show available recipes grouped.
default:
    @just --list --unsorted

# ── Local dev ────────────────────────────────────────────────────────────

[doc('First-time setup: create the 1Password item and write .env.op')]
[group('dev')]
bootstrap:
    {{ _root }}/scripts/op-bootstrap.sh

[doc('Build and run the local dev stack (Postgres + app on :8787)')]
[group('dev')]
dev:
    op run --env-file={{ _root }}/.env.op -- docker compose -f {{ _root }}/docker-compose.yml up -d --build

[doc('Rebuild & restart only the app container — reuses env from the running stack, never touches the db')]
[group('dev')]
rebuild:
    #!/usr/bin/env bash
    set -euo pipefail
    cd {{ _root }}
    proj=all-my-favs
    app_id="$(docker ps -q --filter label=com.docker.compose.project=$proj --filter label=com.docker.compose.service=app)"
    db_id="$(docker ps -q --filter label=com.docker.compose.project=$proj --filter label=com.docker.compose.service=db)"
    if [[ -z "$app_id" ]]; then
        echo "no running app container — use \`just dev\` for a first-time start" >&2
        exit 1
    fi
    tmp_env="$(mktemp)"
    trap 'rm -f "$tmp_env"' EXIT
    docker exec "$app_id" sh -c 'printf "AMF_API_KEY=%s\n" "$AMF_API_KEY"' >> "$tmp_env"
    if [[ -n "$db_id" ]]; then
        docker exec "$db_id" sh -c 'printf "AMF_DB_PASSWORD=%s\n" "$POSTGRES_PASSWORD"' >> "$tmp_env"
    fi
    docker compose --env-file "$tmp_env" build app
    docker compose --env-file "$tmp_env" up -d --no-deps app
    echo "rebuilt and restarted app (db left alone)"

[doc('Stop the local dev stack')]
[group('dev')]
down:
    docker compose -f {{ _root }}/docker-compose.yml down

[doc('Tail logs for the local dev stack')]
[group('dev')]
logs:
    docker compose -f {{ _root }}/docker-compose.yml logs -f --tail=200

[doc('Open a shell in the local app container')]
[group('dev')]
shell:
    docker compose -f {{ _root }}/docker-compose.yml exec app bash

[doc('Open psql in the local db container')]
[group('dev')]
psql:
    docker compose -f {{ _root }}/docker-compose.yml exec db psql -U amf -d amf

# ── Code quality ─────────────────────────────────────────────────────────

[doc('Sync Python deps with uv')]
[group('python')]
sync:
    uv sync

[doc('Lint with ruff')]
[group('python')]
lint:
    uv run ruff check app alembic

[doc('Format with ruff')]
[group('python')]
fmt:
    uv run ruff format app alembic

[doc('Run pytest (no-op if no tests yet)')]
[group('python')]
test:
    uv run pytest

[doc('Quick app-import smoke test')]
[group('python')]
smoke:
    AMF_API_KEY=test-key-1234567890ab AMF_DATABASE_URL=sqlite:///:memory: uv run python -c "from app.main import app; print(f'ok — {len(app.routes)} routes')"

# ── Migrations ───────────────────────────────────────────────────────────

[doc('Generate a new Alembic revision: `just migration "add column foo"`')]
[group('migrations')]
migration message:
    op run --env-file={{ _root }}/.env.op -- uv run alembic revision --autogenerate -m "{{ message }}"

[doc('Export all bookmarks to ./backups/amf-YYYY-MM-DD.jsonl from the local dev stack')]
[group('backup')]
export:
    #!/usr/bin/env bash
    set -euo pipefail
    out="{{ _root }}/backups"
    mkdir -p "$out"
    file="$out/amf-$(date +%F).jsonl"
    key="$(op read 'op://Private/all-my-favs/api_key')"
    curl -fsS -H "Authorization: Bearer $key" \
      http://localhost:8787/api/export > "$file"
    lines=$(wc -l < "$file")
    echo "wrote $file ($lines bookmarks)"

[doc('Import a JSONL file into the local dev stack: `just import path/to/amf.jsonl`')]
[group('backup')]
import file:
    #!/usr/bin/env bash
    set -euo pipefail
    if [[ ! -f "{{ file }}" ]]; then
        echo "no such file: {{ file }}" >&2
        exit 1
    fi
    key="$(op read 'op://Private/all-my-favs/api_key')"
    curl -fsS -X POST \
      -H "Authorization: Bearer $key" \
      -H "Content-Type: application/x-ndjson" \
      --data-binary "@{{ file }}" \
      http://localhost:8787/api/import

[doc('Apply pending migrations against the local dev DB')]
[group('migrations')]
upgrade:
    op run --env-file={{ _root }}/.env.op -- uv run alembic upgrade head

[doc('Show current Alembic head')]
[group('migrations')]
current:
    op run --env-file={{ _root }}/.env.op -- uv run alembic current

# ── Extension ────────────────────────────────────────────────────────────

[doc('Build the Firefox extension (writes extension/dist/*.zip)')]
[group('extension')]
ext-build:
    cd {{ _root }}/extension && npm install && npm run build

[doc('Launch a temp Firefox with the extension auto-reloading')]
[group('extension')]
ext-run:
    cd {{ _root }}/extension && npm install && npm run run

[doc('Lint the extension manifest with web-ext')]
[group('extension')]
ext-lint:
    cd {{ _root }}/extension && npm install && npm run lint

# ── Release ──────────────────────────────────────────────────────────────

[doc('Bump calver version (YYYY.M.P) in pyproject.toml + extension/manifest.json. Part is minor|patch; year auto-rolls.')]
[group('release')]
version-bump part:
    #!/usr/bin/env bash
    set -euo pipefail
    cd {{ _root }}
    case "{{ part }}" in minor|patch) ;; *) echo "part must be minor|patch" >&2; exit 2 ;; esac
    cur="$(uv run python -c 'import tomllib; print(tomllib.loads(open("pyproject.toml","rb").read().decode())["project"]["version"])')"
    IFS=. read -r y m p <<<"$cur"
    yr="$(date +%Y)"; mo="$(date +%-m)"
    if [[ "$yr" != "$y" ]]; then
        new="${yr}.${mo}.0"
    else
        case "{{ part }}" in
            minor) new="${y}.$((m+1)).0" ;;
            patch) new="${y}.${m}.$((p+1))" ;;
        esac
    fi
    echo "bumping $cur -> $new"
    sed -i "s/^version = \"$cur\"$/version = \"$new\"/" pyproject.toml
    sed -i "s/\"version\": \"$cur\"/\"version\": \"$new\"/" extension/manifest.json
    uv lock >/dev/null
    echo "updated pyproject.toml, extension/manifest.json, uv.lock"
    echo "next: git commit -am \"chore: bump version to $new\" && git tag v$new && git push && git push --tags"

[doc('Show the current version from pyproject.toml')]
[group('release')]
version:
    @uv run python -c 'import tomllib; print(tomllib.loads(open("pyproject.toml","rb").read().decode())["project"]["version"])'

# ── Deploy (delegates to ~/homelab/justfile) ─────────────────────────────

[doc('Deploy / redeploy the homelab stack at favs.kjaymiller.dev')]
[group('deploy')]
deploy:
    just --justfile {{ _homelab }}/justfile amf-up

[doc('Restart only the deployed app (after rotating the API key)')]
[group('deploy')]
deploy-restart:
    just --justfile {{ _homelab }}/justfile amf-restart

[doc('Tail logs from the deployed stack')]
[group('deploy')]
deploy-logs:
    just --justfile {{ _homelab }}/justfile amf-logs

[doc('Show status of the deployed stack')]
[group('deploy')]
deploy-status:
    just --justfile {{ _homelab }}/justfile amf-status
