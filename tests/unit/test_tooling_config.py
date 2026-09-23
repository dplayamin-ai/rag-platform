"""툴체인 설정과 루트 개발 파일에 대한 가드 테스트 — `pyproject.toml`이 정본 값에서 벗어나지 않도록 감시한다.

설계 근거: `ADR-0035`(Python 버전·툴체인 고정), 바이블 §12(모듈 의존 방향 → `BIBLE_LAYERS`),
phase-6 계획서 §8(deferred 마커 4종·검증 계층 규약).

구성:
- `BIBLE_LAYERS` — 바이블 §12 계층 순서(최상위부터)를 하드코딩한 정본 대조표.
- Python 버전 고정, 6개 extras 선언, 최소 런타임 의존성 집합, deferred 마커 4종 등록과 기본 제외,
  import-linter 계층·금지 계약이 §12 방향과 일치함, 계층 모듈 실재, `pipelines`가 오케스트레이터/웹
  프레임워크를 금지함, C등급 패키지(`fitz`/`pymupdf`/`hwp5`) 금지, mypy strict를 각각 확인.
- `justfile`/`.pre-commit-config.yaml`/저장소 필수 디렉터리 존재 확인.

불변식: 이 테스트가 실패하면 `pyproject.toml`이 바이블·ADR과 어긋난 것이지 테스트가 틀린 것이 아니다.
검증 계층: 1층(여기서 검증).
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
PYPROJECT = REPO_ROOT / "pyproject.toml"
DEFERRED_MARKERS = ("needs_docker", "needs_model", "needs_gpu", "needs_network")

# Bible §12 dependency direction, top layer first. `telemetry` and `korean` sit beside `sdk`
# (10-development/01 §2.3); `settings` sits with `security` and `profiles` (bible §12 `settings/`).
BIBLE_LAYERS = [
    ["api", "mcp", "cli"],
    ["orchestration", "ledger", "storage", "security", "profiles", "settings", "eval"],
    ["plugins", "adapters", "pipelines", "retrieval", "render"],
    ["sdk", "telemetry", "korean"],
    ["contracts"],
]


@pytest.fixture(scope="module")
def pyproject() -> dict[str, Any]:
    with PYPROJECT.open("rb") as fh:
        return tomllib.load(fh)


def _contracts(pyproject: dict[str, Any]) -> list[dict[str, Any]]:
    contracts: list[dict[str, Any]] = pyproject["tool"]["importlinter"]["contracts"]
    return contracts


def test_python_range_is_pinned(pyproject: dict[str, Any]) -> None:
    assert pyproject["project"]["requires-python"] == ">=3.12,<3.14"
    assert pyproject["project"]["name"] == "rag-platform"
    assert (REPO_ROOT / ".python-version").read_text(encoding="utf-8").strip() == "3.12"


def test_bible_extras_are_declared(pyproject: dict[str, Any]) -> None:
    extras = set(pyproject["project"]["optional-dependencies"])
    assert extras == {"kiwi", "docling-chunker", "gpu", "opensearch", "temporal", "eval"}


def test_minimal_runtime_dependencies(pyproject: dict[str, Any]) -> None:
    names = {dep.split(">")[0].split("<")[0].split("=")[0].strip() for dep in pyproject["project"]["dependencies"]}
    assert names == {"pydantic", "pydantic-settings", "python-ulid", "blake3", "pyyaml", "jsonschema", "httpx", "anyio"}


def test_deferred_markers_registered_and_excluded_by_default(pyproject: dict[str, Any]) -> None:
    ini = pyproject["tool"]["pytest"]["ini_options"]
    registered = {entry.split(":", 1)[0] for entry in ini["markers"]}
    addopts = ini["addopts"]
    expression = addopts[addopts.index("-m") + 1]
    for marker in DEFERRED_MARKERS:
        assert marker in registered
        assert f"not {marker}" in expression
    assert "--strict-markers" in addopts
    assert ini["asyncio_mode"] == "auto"
    assert ini["testpaths"] == ["tests"]


def test_layers_follow_bible_dependency_direction(pyproject: dict[str, Any]) -> None:
    layers = next(c for c in _contracts(pyproject) if c["type"] == "layers")["layers"]
    parsed = [[part.strip().removeprefix("rag_platform.") for part in layer.split("|")] for layer in layers]
    assert parsed == BIBLE_LAYERS
    # `|` (independent siblings) is used, never `:` (non-independent siblings).
    assert all(":" not in layer for layer in layers)


def test_layer_modules_exist() -> None:
    for layer in BIBLE_LAYERS:
        for name in layer:
            assert (REPO_ROOT / "src" / "rag_platform" / name / "__init__.py").is_file(), name


def test_pipelines_forbid_orchestrator_and_web_framework(pyproject: dict[str, Any]) -> None:
    forbidden = [c for c in _contracts(pyproject) if c["type"] == "forbidden"]
    covering = [c for c in forbidden if "rag_platform.pipelines" in c["source_modules"]]
    assert covering
    banned = {m for c in covering for m in c["forbidden_modules"]}
    assert {"temporalio", "fastapi", "rag_platform.ledger"} <= banned


def test_c_grade_imports_forbidden(pyproject: dict[str, Any]) -> None:
    forbidden = {m for c in _contracts(pyproject) if c["type"] == "forbidden" for m in c["forbidden_modules"]}
    assert {"fitz", "pymupdf", "hwp5"} <= forbidden


def test_mypy_is_strict(pyproject: dict[str, Any]) -> None:
    mypy = pyproject["tool"]["mypy"]
    assert mypy["strict"] is True
    assert "pydantic.mypy" in mypy["plugins"]


def test_root_development_files_exist() -> None:
    justfile = (REPO_ROOT / "justfile").read_text(encoding="utf-8")
    for recipe in ("sync:", "lint:", "typecheck:", "test:", "check:"):
        assert recipe in justfile
    config = yaml.safe_load((REPO_ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8"))
    hook_ids = {hook["id"] for repo in config["repos"] for hook in repo["hooks"]}
    assert {"ruff-check", "ruff-format", "lint-imports", "uv-lock-check"} <= hook_ids


@pytest.mark.parametrize(
    "path",
    [
        "tests/contracts",
        "tests/adapters",
        "tests/security",
        "tests/replay",
        "tests/eval",
        "tests/unit",
        "tests/e2e",
        "plugins",
        "sidecars",
        "sdk/python",
        "sdk/typescript",
        "deploy/compose",
        "deploy/helm",
        "samples",
        "tools/verify",
    ],
)
def test_repository_directories_exist(path: str) -> None:
    assert (REPO_ROOT / path).is_dir()
