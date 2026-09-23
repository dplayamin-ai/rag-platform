#!/usr/bin/env bash
# tools/verify/run-deferred.sh — run the tier-2 (Docker) deferred verification suite on a machine
# that actually has Docker/Linux (phase-6 plan docs/12-appendix/05-phase6-implementation-kit-plan.md
# §8; items tracked in docs/12-appendix/09-deferred-verification-ledger.md). This VDI cannot run it
# (no Docker/WSL) — see the root HANDOFF.md for the full hand-off procedure.
#
# What it does:
#   1. Brings up `deploy/compose/compose.lite.yaml` (PostgreSQL, Qdrant, Valkey) with
#      `docker compose ... up --wait`. If that file does not exist yet in this checkout (a later
#      work package adds it), prints a warning and continues without it — `pytest -m needs_docker`
#      will then simply report "no tests collected" until such tests land.
#   2. Runs `uv run pytest -q -m "needs_docker"` (only tier-2 tests; every other tier — needs_model,
#      needs_gpu, needs_network — stays excluded by the default `pyproject.toml` addopts).
#   3. Writes a machine-readable result record to tools/verify/results/deferred-<UTC date>.json and
#      the full pytest log next to it.
#   4. Tears the compose stack back down (`down -v`), even if pytest failed.
#
# Usage:
#   tools/verify/run-deferred.sh [extra pytest args...]
#
# Exit code: pytest's exit code, except 5 ("no tests collected") is remapped to 0 — nothing is
# marked needs_docker yet in this revision, which is expected, not a failure (same convention as
# `tools/dev.py test-deferred`).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

COMPOSE_FILE="deploy/compose/compose.lite.yaml"
RESULTS_DIR="tools/verify/results"
DATE="$(date -u +%Y-%m-%d)"
OUT="$RESULTS_DIR/deferred-$DATE.json"
LOG="$RESULTS_DIR/deferred-$DATE.log"
mkdir -p "$RESULTS_DIR"

cleanup() {
  if [ -f "$COMPOSE_FILE" ]; then
    echo "+ docker compose -f $COMPOSE_FILE down -v"
    docker compose -f "$COMPOSE_FILE" down -v || true
  fi
}
trap cleanup EXIT

COMPOSE_USED=false
if [ -f "$COMPOSE_FILE" ]; then
  echo "+ docker compose -f $COMPOSE_FILE up --wait"
  docker compose -f "$COMPOSE_FILE" up --wait
  COMPOSE_USED=true
else
  echo "warning: $COMPOSE_FILE does not exist yet (phase-6 plan §8 work package not landed)." >&2
  echo "         proceeding without Docker services; a needs_docker test that actually needs them will fail loudly, not silently pass." >&2
fi

echo "+ uv run pytest -q -m \"needs_docker\" $*"
set +e
uv run pytest -q -m "needs_docker" "$@" 2>&1 | tee "$LOG"
CODE="${PIPESTATUS[0]}"
set -e

if [ "$CODE" -eq 5 ]; then
  STATUS="no_tests_collected"
  EFFECTIVE_CODE=0
elif [ "$CODE" -eq 0 ]; then
  STATUS="passed"
  EFFECTIVE_CODE=0
else
  STATUS="failed"
  EFFECTIVE_CODE=$CODE
fi

SUMMARY_LINE="$(grep -E '^[0-9]+ (passed|failed|error|deselected)' "$LOG" | tail -1 || true)"
SUMMARY_LINE="${SUMMARY_LINE:-(no summary line found)}"

PYTHON_VERSION="$(uv run python -c 'import sys; print(".".join(map(str, sys.version_info[:3])))' 2>/dev/null || echo unknown)"
UV_VERSION="$(uv --version 2>/dev/null || echo unknown)"

# Minimal JSON string escaping (backslash, double-quote, newline) — no JSON library dependency.
json_escape() {
  printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' | tr '\n' ' '
}

cat > "$OUT" <<JSON
{
  "generated_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "marker": "needs_docker",
  "compose_file": "$COMPOSE_FILE",
  "compose_used": $COMPOSE_USED,
  "pytest_exit_code": $CODE,
  "status": "$STATUS",
  "summary_line": "$(json_escape "$SUMMARY_LINE")",
  "python_version": "$PYTHON_VERSION",
  "uv_version": "$(json_escape "$UV_VERSION")",
  "log_file": "$LOG"
}
JSON

echo "result written to $OUT"
exit "$EFFECTIVE_CODE"
