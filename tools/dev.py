"""Cross-platform developer task runner (replaces a root Makefile; 10-development/02 §1.1).

Usage::

    uv run python tools/dev.py lint           # ruff check + ruff format --check + lint-imports
    uv run python tools/dev.py type           # mypy (strict) on src/
    uv run python tools/dev.py test           # pytest, deferred-tier markers excluded (pyproject addopts)
    uv run python tools/dev.py test-deferred  # only needs_docker/needs_model/needs_gpu/needs_network tests
    uv run python tools/dev.py contracts-gen  # regenerate src/rag_platform/contracts from schemas/
    uv run python tools/dev.py check          # lint + type + test

Extra arguments after the task name are passed to the underlying tool, for example
``uv run python tools/dev.py test tests/unit -k scaffold``.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import sysconfig
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

ROOT = Path(__file__).resolve().parents[1]
DEFERRED_EXPR = "needs_docker or needs_model or needs_gpu or needs_network"
CONTRACTS_GEN = ROOT / "tools" / "contracts_gen.py"


def _tool(name: str) -> str:
    """Resolve an executable from the active environment first, then from PATH."""
    scripts = Path(sysconfig.get_path("scripts"))
    for candidate in (scripts / name, scripts / f"{name}.exe"):
        if candidate.exists():
            return str(candidate)
    found = shutil.which(name)
    if found is None:
        sys.stderr.write(f"dev.py: '{name}' not found; run `uv sync` first\n")
        raise SystemExit(127)
    return found


def _run(*cmd: str) -> int:
    print("+", " ".join(cmd), flush=True)
    return subprocess.run(cmd, cwd=ROOT, check=False).returncode


def _chain(*steps: tuple[str, ...]) -> int:
    for step in steps:
        code = _run(*step)
        if code != 0:
            return code
    return 0


def lint(extra: list[str]) -> int:
    return _chain(
        (_tool("ruff"), "check", ".", *extra),
        (_tool("ruff"), "format", "--check", "."),
        (_tool("lint-imports"),),
    )


def type_check(extra: list[str]) -> int:
    return _run(_tool("mypy"), *(extra or ["src"]))


def test(extra: list[str]) -> int:
    return _run(sys.executable, "-m", "pytest", "-q", *extra)


def test_deferred(extra: list[str]) -> int:
    # A later `-m` overrides the default exclusion expression in pyproject addopts.
    code = _run(sys.executable, "-m", "pytest", "-q", "-m", DEFERRED_EXPR, *extra)
    # Exit code 5 means "no tests collected": nothing is deferred yet, which is not a failure.
    return 0 if code == 5 else code  # noqa: PLR2004


def contracts_gen(extra: list[str]) -> int:
    if not CONTRACTS_GEN.exists():
        sys.stderr.write(f"dev.py: {CONTRACTS_GEN.relative_to(ROOT)} does not exist yet\n")
        return 2
    return _run(sys.executable, str(CONTRACTS_GEN), *extra)


def check(extra: list[str]) -> int:
    del extra
    for task in (lint, type_check, test):
        code = task([])
        if code != 0:
            return code
    return 0


TASKS: dict[str, Callable[[list[str]], int]] = {
    "lint": lint,
    "type": type_check,
    "test": test,
    "test-deferred": test_deferred,
    "contracts-gen": contracts_gen,
    "check": check,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tools/dev.py", description=__doc__.splitlines()[0])
    parser.add_argument("task", choices=sorted(TASKS))
    parser.add_argument("extra", nargs=argparse.REMAINDER, help="arguments passed to the tool")
    args = parser.parse_args(argv)
    return TASKS[args.task](list(args.extra))


if __name__ == "__main__":
    raise SystemExit(main())
