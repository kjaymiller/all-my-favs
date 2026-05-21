#!/usr/bin/env bash
# all-my-favs installer.
#
# Provisions Aiven for PostgreSQL via OpenTofu and emits the resulting
# connection string. The homelab deploy captures stdout via
#   DATABASE_URL=$(scripts/install.sh --provision-only --infra-dir <path>)
# and injects it into the app container env — never writing it to disk.
#
# Requires:
#   1Password CLI signed in (`op whoami`) — token fetched via `op read`
#   tofu >= 1.6, op
#
# NOTE: OpenTofu writes <infra-dir>/terraform.tfstate locally. That
# state file contains the DB password in plaintext. Treat it as a
# secret on this host. Repo-side state is rejected — see
# infra.example/README.md.

set -euo pipefail

PROVISION_ONLY=0
INFRA_DIR="${INFRA_DIR:-}"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --provision-only) PROVISION_ONLY=1; shift ;;
    --infra-dir) INFRA_DIR="$2"; shift 2 ;;
    --infra-dir=*) INFRA_DIR="${1#*=}"; shift ;;
    *) echo "error: unknown arg: $1" >&2; exit 2 ;;
  esac
done

# In provision-only mode, stdout is reserved for the DATABASE_URL payload —
# redirect human-readable logging to stderr so callers can cleanly capture
# it via `DATABASE_URL=$(install.sh --provision-only ...)`.
if [[ $PROVISION_ONLY -eq 1 ]]; then
  exec 3>&2
else
  exec 3>&1
fi
log() { echo "$@" >&3; }

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -z "$INFRA_DIR" ]]; then
  echo "error: --infra-dir <path> (or INFRA_DIR env var) is required." >&2
  echo "       See infra.example/README.md — operational state must not live in this repo." >&2
  exit 2
fi
if [[ ! -f "$INFRA_DIR/main.tf" ]]; then
  echo "error: $INFRA_DIR does not contain main.tf" >&2
  exit 2
fi
case "$INFRA_DIR" in
  "$REPO_DIR/infra.example"|"$REPO_DIR/infra.example/")
    echo "error: refusing to run against repo sample dir $INFRA_DIR." >&2
    echo "       Copy it somewhere you own and point --infra-dir there." >&2
    exit 2 ;;
esac

AIVEN_OP_REF="${AIVEN_OP_REF:-op://Private/Aiven Homelab API KEY/credential}"

for bin in tofu op; do
  if ! command -v "$bin" >/dev/null 2>&1; then
    echo "error: '$bin' not found in PATH." >&2
    exit 1
  fi
done

if ! op whoami >/dev/null 2>&1; then
  echo "error: 1Password CLI is not signed in. Run: eval \$(op signin)" >&2
  exit 1
fi

AIVEN_API_TOKEN="$(op read "$AIVEN_OP_REF")"
if [[ -z "$AIVEN_API_TOKEN" ]]; then
  echo "error: op read returned empty for $AIVEN_OP_REF" >&2
  exit 1
fi

export TF_VAR_aiven_api_token="$AIVEN_API_TOKEN"

log "==> tofu init"
tofu -chdir="$INFRA_DIR" init -input=false >&3

log "==> tofu apply (provisioning Aiven for PostgreSQL)"
tofu -chdir="$INFRA_DIR" apply -auto-approve -input=false >&3

DATABASE_URL="$(tofu -chdir="$INFRA_DIR" output -raw database_url)"
if [[ -z "$DATABASE_URL" ]]; then
  echo "error: tofu did not produce a database_url output." >&2
  exit 1
fi

if [[ $PROVISION_ONLY -eq 1 ]]; then
  printf '%s\n' "$DATABASE_URL"
  unset DATABASE_URL TF_VAR_aiven_api_token AIVEN_API_TOKEN
  exit 0
fi

# Non-provision-only mode is reserved for future use (e.g. a direct
# `install.sh && docker compose up` flow). For now the homelab is the
# only caller and always passes --provision-only.
log
log "Provisioning complete. DATABASE_URL is:"
printf '  %s\n' "$DATABASE_URL" >&3
unset DATABASE_URL TF_VAR_aiven_api_token AIVEN_API_TOKEN
