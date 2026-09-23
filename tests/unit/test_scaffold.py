"""6단계 A(phase 6A) 패키지 골격 스모크 테스트 — `src/rag_platform` 구조가 바이블 §12 모듈 맵과 일치하는지 검증한다.

설계 근거: 바이블 §12(모듈/패키지 맵 정본), phase-6 계획서(§6A, 이전 레이아웃 `core`/`stages`/`workflows`/
`observability` 폐기 결정).

구성:
- `BIBLE_PACKAGES`/`RETIRED_PACKAGES` — §12 정본 패키지 목록과 폐기된 옛 디렉터리 목록.
- 각 §12 패키지가 임포트되고 docstring을 가짐, 최상위 패키지 집합이 정본과 정확히 일치함, 폐기 디렉터리가
  부재함, 발견되는 모든 패키지가 docstring을 가짐, `py.typed` 존재, `__version__` 문자열, CLI `--version`/
  미지정 인자 처리를 각각 확인하는 테스트 함수들.

불변식: 이 파일은 골격(스캐폴드) 자체의 존재·구조만 확인하며 각 모듈의 동작은 검증하지 않는다.
검증 계층: 1층(여기서 검증).
"""

from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path

import pytest

import rag_platform
from rag_platform.cli import main

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = REPO_ROOT / "src" / "rag_platform"

# Bible §12 module map, down to the subpackages created by the phase 6A skeleton.
BIBLE_PACKAGES = [
    "contracts",
    "sdk",
    "plugins",
    "adapters",
    "adapters.fetch",
    "adapters.parse",
    "adapters.normalize",
    "adapters.chunk",
    "adapters.enrich",
    "adapters.embed",
    "adapters.index",
    "adapters.query",
    "adapters.retrieve",
    "adapters.rerank",
    "adapters.llm",
    "pipelines",
    "retrieval",
    "retrieval.postprocess",
    "retrieval.pack",
    "render",
    "orchestration",
    "orchestration.local",
    "orchestration.temporal",
    "orchestration.outbox",
    "ledger",
    "storage",
    "security",
    "profiles",
    "profiles.builtin",
    "settings",
    "korean",
    "eval",
    "telemetry",
    "api",
    "mcp",
    "testing",
    "cli",
]

# Directories from the pre-bible layout that must not come back (phase-6 plan 6A correction).
RETIRED_PACKAGES = ["core", "stages", "workflows", "observability"]


@pytest.mark.parametrize("name", BIBLE_PACKAGES)
def test_bible_package_imports_with_docstring(name: str) -> None:
    module = importlib.import_module(f"rag_platform.{name}")
    assert module.__doc__
    assert module.__doc__.strip()


def test_top_level_packages_match_bible_map() -> None:
    top_level = {info.name for info in pkgutil.iter_modules(rag_platform.__path__) if info.ispkg}
    expected = {name for name in BIBLE_PACKAGES if "." not in name}
    assert top_level == expected


@pytest.mark.parametrize("name", RETIRED_PACKAGES)
def test_retired_layout_is_absent(name: str) -> None:
    assert not (PACKAGE_ROOT / name).exists()


def test_every_discovered_package_has_a_docstring() -> None:
    walk = pkgutil.walk_packages(rag_platform.__path__, prefix="rag_platform.")
    names = [info.name for info in walk if info.ispkg]
    assert names, "package walk found nothing"
    missing = [name for name in names if not (importlib.import_module(name).__doc__ or "").strip()]
    assert missing == []


def test_package_is_typed() -> None:
    assert (PACKAGE_ROOT / "py.typed").is_file()


def test_version_is_a_string() -> None:
    assert isinstance(rag_platform.__version__, str)
    assert rag_platform.__version__


def test_cli_version(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--version"]) == 0
    assert capsys.readouterr().out.startswith("rag-platform ")


def test_cli_rejects_unknown_arguments(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["no-such-command"]) == 2
    assert "usage: rag" in capsys.readouterr().err
