# infra.example

Reference Terraform module for all-my-favs' Postgres (single Aiven for
PostgreSQL service in `do-nyc`, exposes `database_url` output).

These files are **not** used by any installer in this repo. The real
state-bearing copy lives with the deployer — for the homelab deploy
that is `~/homelab/compose/all-my-favs/infra/`. Copy this directory
somewhere you own, then point the installer at it:

```sh
./scripts/install.sh --provision-only --infra-dir /path/to/your/infra
# or
INFRA_DIR=/path/to/your/infra ./scripts/install.sh --provision-only
```

The installer never writes Terraform state inside this repo. The state
file contains the DB password in plaintext — treat the directory like
a secret on disk.
