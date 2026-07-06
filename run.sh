#!/usr/bin/env bash
# Agentic PI Migration Upgrade — quick launcher for Summit Creek oil scenario
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

: "${IDMP_URL:=http://localhost:7142}"
: "${IDMP_USER:?Set IDMP_USER (IDMP login email)}"
: "${IDMP_PASSWORD:?Set IDMP_PASSWORD}"

PYTHONPATH="$ROOT" python3 -m agentic_pi_migration.cli "$@"
