"""크로스플랫폼 개발 태스크 러너 — 루트 `Makefile` 대신 `lint`/`type`/`test`/`contracts-gen`/`check` 진입점을 제공한다.

설계 근거: `docs/10-development/02-local-development-setup.md` §1.1(태스크 러너와 Node 툴체인 — Windows에서도
동일하게 동작해야 하므로 셸 스크립트 대신 파이썬 러너를 둔다).

구성:
- `lint`/`type_check`/`test`/`test_deferred`/`contracts_gen`/`check` — 각각 `ruff check`+`format --check`+
  `lint-imports`, `mypy` strict, `pytest`(기본 마커 제외/`test-deferred`는 4종 마커만), `tools/contracts_gen.py`
  위임, 전체(lint+type+test) 순차 실행.
- `_tool(name)` — 활성 가상환경의 실행 파일을 우선 찾고 없으면 `PATH`에서 조회.
- `_run`/`_chain` — 서브프로세스 실행과 실패 시 조기 종료하는 단계 체이닝.

불변식: 태스크 이름 뒤의 추가 인자는 그대로 하위 도구에 전달한다(예 `test tests/unit -k scaffold`).
검증 계층: 1층(여기서 검증) — 사용: `uv run python tools/dev.py {lint|type|test|test-deferred|contracts-gen|check}`.
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
