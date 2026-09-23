# Task wrapper (10-development/02 §1.1). Every recipe reduces to one documented `uv`, `rag` or
# `docker compose` command, so the same result is reachable without `just`; the cross-platform
# equivalent is `uv run python tools/dev.py <task>`.

set windows-shell := ["powershell.exe", "-NoLogo", "-NoProfile", "-Command"]

default:
    @just --list

# Sync the workspace (all members, all extras, dev group).
sync:
    uv sync --all-packages --all-extras --group dev

# Start the development stack (needs Docker; not available on the Windows VDI).
up:
    uv run rag up --profile lite

down:
    docker compose -f deploy/compose/compose.lite.yaml down

# ruff lint + format check + import-linter contracts.
lint:
    uv run python tools/dev.py lint

typecheck:
    uv run mypy src

# Default pytest run; deferred tiers (needs_docker, needs_model, needs_gpu, needs_network) are excluded.
test:
    uv run pytest -q

# Only the deferred tiers (run where Docker, model weights, GPUs or network access exist).
test-deferred:
    uv run python tools/dev.py test-deferred

# Interpreter matrix (ADR-0035: 3.12 and 3.13 must both pass).
test-matrix:
    uv run --python 3.12 pytest -q
    uv run --python 3.13 pytest -q

# Regenerate the Pydantic contract models from schemas/.
contracts-gen:
    uv run python tools/dev.py contracts-gen

# CI-equivalent local gate.
check: lint typecheck test
    uv lock --check
