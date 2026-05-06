# Back up and restore

Goal: get a portable snapshot of all bookmarks, and put one back.

There are two complementary backup strategies — pick whichever fits the situation.

| Strategy | Format | Best for | Tradeoff |
|----------|--------|----------|----------|
| **JSONL export** (recommended) | One bookmark per line, plain text | Day-to-day backups, archiving, moving data between tools, version-controlling | Loses surrogate `id`s and exact timestamps for the join table — but URLs are the natural key, so reimport is lossless for what matters |
| **`pg_dump`** | Postgres custom format (binary) | Full-fidelity disaster recovery, exact bit-for-bit restores | Locked to a Postgres major version; not human-readable; not diffable |
| **Cold restic snapshot** | Whole `/srv/all-my-favs/pgdata` directory | Off-host disaster recovery via your existing restic policy | Crash-consistent only; can't read individual bookmarks without spinning up Postgres |

The JSONL export is the one to use 99% of the time. It's a flat file, you can `grep` and `jq` it, you can hand-edit it before reimporting, and any sibling tool (wytcher, cms, your own scripts) can produce or consume the exact same shape.

### Backups land under `/srv` so restic picks them up

Both `amf-export` and `amf-backup` write to `/srv/all-my-favs/backups/`, the same `/srv/` tree your existing restic policy (`scripts/restic/backup.sh`) already covers. No separate restic config needed — exports are automatically included in the next nightly `b2` and Zima `local` snapshots.

One-time setup creates the directory and chowns it to your user:

```bash
just --justfile ~/homelab/justfile amf-backups-init
# → sudo install -d /srv/all-my-favs/backups (mode 0750, owner = you)
```

See [the JSONL format reference](../reference/backup-format.md) for the schema.

## JSONL — export

### Deployed instance

```bash
just --justfile ~/homelab/justfile amf-export
# wrote /srv/all-my-favs/backups/amf-2026-05-06.jsonl (47 bookmarks)
```

Or by hand:

```bash
KEY=$(op read "op://Private/all-my-favs/api_key")
curl -fsS -H "Authorization: Bearer $KEY" \
  https://favs.kjaymiller.dev/api/export > amf-$(date +%F).jsonl
```

### Local dev stack

```bash
cd ~/all-my-favs && just export
```

The endpoint streams — large datasets won't blow up memory.

## JSONL — restore / import

### Into the deployed instance

```bash
just --justfile ~/homelab/justfile amf-import ./amf-2026-05-06.jsonl
# {"imported":47,"created":47,"updated":0,"errors":0}
```

By hand:

```bash
KEY=$(op read "op://Private/all-my-favs/api_key")
curl -fsS -X POST \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/x-ndjson" \
  --data-binary @amf-2026-05-06.jsonl \
  https://favs.kjaymiller.dev/api/import
```

### Idempotency

Import upserts on `url` — the natural key. You can:

- Re-run the same file safely (rows already present are *updated*, not duplicated).
- Merge two exports by `cat`-ing them together.
- Hand-edit a line and reimport just that one (`tail -n 1 amf.jsonl | curl -X POST ... --data-binary @-`).

### Inspect / transform with `jq`

```bash
# Top tags by count
jq -r '.tags[]' amf.jsonl | sort | uniq -c | sort -rn | head

# Bookmarks tagged tech:python, oldest first
jq 'select(.tags|index("tech:python"))' amf.jsonl

# Strip notes from a sensitive subset before sharing a backup
jq 'select(.tags|index("private")|not) | del(.notes)' \
   amf.jsonl > amf-public.jsonl
```

### Diffing two exports

```bash
diff <(jq -S . amf-yesterday.jsonl) <(jq -S . amf-today.jsonl)
```

(`jq -S` sorts keys so semantically-equal objects compare equal.)

## Periodic JSONL backup (systemd timer)

A nightly export to `/srv/all-my-favs/backups/`. Run **before** the nightly restic job so the freshest dump rides along.

`/etc/systemd/system/amf-export.service`:

```ini
[Unit]
Description=Export all-my-favs bookmarks to JSONL
After=network-online.target docker.service
Wants=network-online.target

[Service]
Type=oneshot
User=kjaymiller
ExecStart=/home/kjaymiller/homelab/scripts/amf-export.sh
```

`/etc/systemd/system/amf-export.timer`:

```ini
[Unit]
Description=Nightly all-my-favs JSONL export

[Timer]
OnCalendar=*-*-* 02:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

`~/homelab/scripts/amf-export.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
out=/srv/all-my-favs/backups
key=$(op read "op://Private/all-my-favs/api_key")
curl -fsS -H "Authorization: Bearer $key" \
  https://favs.kjaymiller.dev/api/export > "$out/amf-$(date +%F).jsonl"
# Keep last 30 days locally; older copies still live in restic snapshots forever
find "$out" -name 'amf-*.jsonl' -mtime +30 -delete
```

Enable:

```bash
sudo systemctl enable --now amf-export.timer
systemctl list-timers amf-export.timer
```

Restic's nightly `b2` and `local` runs scoop everything under `/srv/`, so each daily JSONL flows offsite automatically.

## `pg_dump` — full-fidelity binary backup

Use this when you need an exact, restorable-into-the-same-Postgres-version snapshot:

```bash
# Export
just --justfile ~/homelab/justfile amf-backup
# → /srv/all-my-favs/backups/amf-2026-05-06.dump

# Restore (destructive — wipes existing data)
just --justfile ~/homelab/justfile amf-restore /srv/all-my-favs/backups/amf-2026-05-06.dump
```

By hand, into a fresh empty database (e.g. on another host):

```bash
docker exec amf-db createdb -U amf amf_restore
docker exec amf-db pg_restore -U amf -d amf_restore /tmp/restore.dump
```

## Cold restic snapshot

Restic backs up all of `/srv/` nightly, which means three layers of AMF state are already in your snapshots:

| Path                              | Contents               | Recover by |
|-----------------------------------|------------------------|------------|
| `/srv/all-my-favs/pgdata/`        | Postgres data dir      | `restic restore` → `just amf-up` |
| `/srv/all-my-favs/backups/*.jsonl`| Daily JSONL exports    | `restic restore` → `just amf-import <file>` |
| `/srv/all-my-favs/backups/*.dump` | Optional `pg_dump`s    | `restic restore` → `just amf-restore <file>` |

To list what's in restic for AMF specifically:

```bash
just --justfile ~/homelab/justfile backup-snapshots b2     # or `local`
restic snapshots --path /srv/all-my-favs --compact
```

To pull just AMF state from the latest snapshot:

```bash
sudo -E bash -c '. /etc/restic/k6.env && restic restore latest \
  --include /srv/all-my-favs --target /tmp/restore-amf'
ls /tmp/restore-amf/srv/all-my-favs/
```

A logical export (JSONL or `pg_dump`) is preferred over the cold pgdata snapshot when you have the option, because it tolerates major-version upgrades and corrupt indexes — but the cold snapshot is the ultimate fallback if the app itself is dead.

## Verify a backup is good

```bash
# JSONL — every line should parse
jq -e . amf.jsonl >/dev/null && echo ok

# pg_dump — list schema objects
docker run --rm -v $(pwd)/backups:/b postgres:18.3-alpine \
  pg_restore -l /b/amf-2026-05-06.dump | head
```

A `jq` failure means the export was truncated. A `pg_restore -l` failure means the dump is corrupt.
