"""전체 e2e — CLI 수집 → 질의 → `ContextPack` cite_id 왕복 → MCP `search` 동일 결과(F5-03, WP-503).

역할: `cli/main.py`가 배선한 lite 실행기를 CLI 명령 표면(argparse `main()`)과 공개 함수
(`ingest_paths`/`run_query_lite`/`build_query_deps`) 양쪽으로 exercise한다. (1) CLI로
`tests/fixtures/e2e/*`(txt/md/html) 수집 → (2) CLI 질의로 `ContextPack` 생성 → (3)
`testing.renderer_citation_roundtrip`으로 `cite_id` 왕복 검증(마크다운·`anthropic_search_result`
두 렌더러) → (4) 같은 백엔드에 `mcp.tools.search`를 배선해 CLI 질의와 같은 `document_id` 집합을
내는지 확인 → (5) API `TestClient`(있으면) 비교.
설계 근거: `docs/13-implementation/wp/WP-503-cli-and-full-e2e.md`; 바이블 §4.3(질의 파이프라인)·
§11.6(5분 기동 절차); `pipelines/query.py`·`pipelines/ingest.py`의 "배선은 F5의 몫" 공백.
구성: `_ingest_fixtures` — 픽스처 3종 수집 헬퍼; `test_ingest_then_query_*` — CLI 수집→질의→
cite_id 왕복; `test_mcp_search_handler_*` — MCP `search`와 CLI 질의 동등성; `test_api_testclient_*`
— API(있으면) 인증 경로; `test_cli_main_*`/`test_cli_profile_validate`/`test_cli_serve_*` —
argparse `main()` 표면. 픽스처: `tests/fixtures/e2e/{sample.txt,sample.md,sample.html}`(F3-03가
만든 것을 재사용).
불변식·주의: 모델 다운로드·Docker·GPU·네트워크 없음(온디스크 로컬 Qdrant + 페이크 임베더). API
비교는 `rag_platform.api.app`이 아직 없으면(F5-01 병행 진행) `importorskip`으로 건너뛴다.
검증 계층: 1층(여기서 검증). API 비교만 `# DEFERRED: F5-01 완료 후 배치 검증자가 재실행`.
"""

from __future__ import annotations

import importlib
import json
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from rag_platform.mcp import tools as mcp_tools
from rag_platform.mcp.cursor_store import CursorStore
from rag_platform.pipelines import query as query_pipeline
from rag_platform.render import anthropic_search_result, markdown
from rag_platform.testing import renderer_citation_roundtrip as roundtrip
from rag_platform.testing.doubles.in_memory_kv import InMemoryKV

if TYPE_CHECKING:
    from rag_platform.contracts.common_types import SecurityContext
    from rag_platform.contracts.context_pack import ContextPack
    from rag_platform.contracts.query_request import QueryRequest

# `importlib.import_module`로 직접 가져온다 — `rag_platform.cli/__init__.py`가 자기 자신의
# 디스패치 함수도 이름 `main`으로 노출하므로 `import rag_platform.cli.main as cli_main`(속성
# 경유)은 어느 쪽이 먼저 로드되느냐에 따라 함수를 돌려줄 수 있다(open_issues 이름 충돌 주의) —
# `import_module`은 `sys.modules`를 직접 조회해 항상 이 서브모듈 자체를 돌려준다.
cli_main = importlib.import_module("rag_platform.cli.main")

_FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "e2e"
_FIXTURE_PATHS = [_FIXTURES_DIR / "sample.txt", _FIXTURES_DIR / "sample.md", _FIXTURES_DIR / "sample.html"]
_QUERY_TEXT = "정보보호책임자"


async def _ingest_fixtures(state_dir: Path, *, collection: str = "demo") -> list[dict[str, Any]]:
    """세 픽스처를 `lite-dev` 프로파일로 수집한다(공개 진입점 `ingest_paths` 경유)."""
    return await cli_main.ingest_paths(_FIXTURE_PATHS, collection=collection, profile="lite-dev", state_dir=state_dir)


async def test_ingest_then_query_produces_context_pack_with_citation_roundtrip(tmp_path: Path) -> None:
    """CLI 수집 → CLI 질의: `ContextPack.items`가 비지 않고 `cite_id`가 두 렌더러 모두 왕복한다."""
    state_dir = tmp_path / ".rag"
    summaries = await _ingest_fixtures(state_dir)
    assert len(summaries) == len(_FIXTURE_PATHS)
    assert all(s["status"] == "committed" for s in summaries)
    assert all(s["record_count"] >= 1 for s in summaries)

    result = await cli_main.run_query_lite(_QUERY_TEXT, collection="demo", state_dir=state_dir, render=True)
    pack = result.context_pack
    assert len(pack.items) > 0
    assert pack.sufficiency.status.value in {"sufficient", "insufficient"}

    dumped_items = [item.model_dump(mode="json") for item in pack.items]
    roundtrip.assert_cite_ids_bijective_with_items(dumped_items)

    # 렌더러 2종 모두 같은 팩에서 cite_id를 그대로 왕복시킨다(마크다운은 기본 렌더러, anthropic_*는
    # `target_model.provider="anthropic"` 요청 경로에 쓰인다 — 둘 다 이 WP의 `renderers` 배선 대상).
    for render_fn in (markdown.render, anthropic_search_result.render):
        rendered = render_fn(pack, query_text=_QUERY_TEXT)
        citation_entries = [entry.model_dump(mode="json") for entry in rendered.citation_map]
        roundtrip.assert_renderer_citation_roundtrip(dumped_items, citation_entries)

    assert result.rendered is not None


async def test_requerying_unknown_collection_raises_keyerror(tmp_path: Path) -> None:
    """수집한 적 없는 컬렉션은 `KeyError`(레지스트리 미존재) — `rag query`가 이를 잡아 종료 코드 2를 낸다."""
    with pytest.raises(KeyError):
        await cli_main.run_query_lite("아무 질의", collection="never-ingested", state_dir=tmp_path / ".rag")


async def test_mcp_search_handler_matches_cli_query_document_ids(tmp_path: Path) -> None:
    """MCP `search` 핸들러(같은 백엔드 배선)가 CLI 질의와 같은 `document_id` 집합을 낸다.

    `mcp.tools.search`는 SDK 서버 기동 없이 직접 호출 가능하도록 설계됐다(그 모듈 docstring) —
    `ToolDeps.query_runner`를 `build_query_deps`(cli/main.py, `rag query`와 공유하는 배선)로 채워
    같은 인덱스를 겨냥하면 두 진입점(REST/CLI 대 MCP)이 항등 결과를 낸다는 것을 보인다.
    """
    state_dir = tmp_path / ".rag"
    await _ingest_fixtures(state_dir)
    cli_result = await cli_main.run_query_lite(_QUERY_TEXT, collection="demo", state_dir=state_dir, render=False)
    cli_document_ids = {str(item.document_id.root) for item in cli_result.context_pack.items}

    tenant_id, collection_id = cli_main.resolve_collection("demo", state_dir=state_dir)
    backend = cli_main.build_backend(state_dir)
    embedder = cli_main.build_embedder()
    query_deps = cli_main.build_query_deps(backend, embedder)
    security = cli_main.security_context_for(tenant_id=tenant_id, collection_id=collection_id)

    async def _query_runner(request: QueryRequest, security: SecurityContext) -> ContextPack:
        result = await query_pipeline.run_query(request, security, query_deps, render=False)
        return result.context_pack

    async def _document_reader(*_args: object, **_kwargs: object) -> None:
        return None

    async def _collection_lister(*_args: object, **_kwargs: object) -> list[object]:
        return []

    tool_deps = mcp_tools.ToolDeps(
        query_runner=_query_runner,
        document_reader=_document_reader,
        collection_lister=_collection_lister,
        cursor_store=CursorStore(InMemoryKV()),
    )
    try:
        mcp_result = await mcp_tools.search({"query": _QUERY_TEXT, "top_k": 10}, security, tool_deps)
    finally:
        backend.client.close()

    assert mcp_result.is_error is False
    mcp_document_ids = {item["document_id"] for item in mcp_result.structured_content["items"]}
    assert mcp_document_ids == cli_document_ids
    assert len(mcp_document_ids) > 0


async def test_api_testclient_query_reaches_shared_tenant(tmp_path: Path) -> None:
    """API `TestClient`가 CLI와 같은 tenant_id/collection_id로 인증·수락되는지 확인한다(있으면).

    F5-01(`src/rag_platform/api/app.py`)은 이 배치의 병행 작업이라 이 세션에는 없을 수 있다
    (동시 실행, `tools/phase6/wf-6f.js` F5 배치는 F5-01~03을 병렬 실행한다) — 그 경우
    `importorskip`으로 건너뛴다. **있는 경우에도** `api/query.py`는 자신의 모듈 docstring에
    명시된 대로 `pipelines.query.run_query`의 6-Protocol을 아직 배선하지 않는다
    (`_build_empty_context_pack` — 항상 빈 `ContextPack`) — 그래서 CLI가 실제로 색인한
    `document_id`와의 동등성은 아직 검증할 수 없다. 이 테스트는 그 경계까지만(인증된 요청이
    CLI와 같은 tenant_id/collection_id로 200을 받는지) 확인한다.
    `# DEFERRED: api/query.py가 실 6-Protocol을 배선한 뒤, 배치 검증자(또는 후속 WP)가 이
    테스트를 CLI `document_id` 집합과의 동등성 검사로 확장한다.`
    """
    api_app = pytest.importorskip(
        "rag_platform.api.app", reason="F5-01 (api/app.py) not available yet in this session — DEFERRED"
    )
    testclient_module = pytest.importorskip("starlette.testclient")

    state_dir = tmp_path / ".rag"
    await _ingest_fixtures(state_dir)
    tenant_id, collection_id = cli_main.resolve_collection("demo", state_dir=state_dir)

    app_instance = api_app.create_app()  # 테스트마다 격리된 상태(모듈 docstring 권고)
    app_instance.state.api_keys.register("test-key", tenant_id=tenant_id, subject="user:e2e-test")
    client = testclient_module.TestClient(app_instance)
    response = client.post(
        "/v1/query",
        json={
            "schema_version": "1.0.0",
            "query": _QUERY_TEXT,
            "collection_ids": [collection_id],
            "requested_at": "2026-09-24T00:00:00.000Z",
        },
        headers={"Authorization": "Bearer test-key"},
    )
    assert response.status_code == 200
    context_pack = response.json()["context_pack"]
    assert context_pack["tenant_id"] == tenant_id
    assert context_pack["collection_ids"] == [collection_id]
    # 알려진 현재 동작(위 docstring): 실 검색 배선 전이라 항상 빈 결과.
    assert context_pack["items"] == []


# ---------------------------------------------------------------------------------------------
# CLI 표면(argparse `main()`) — 명령행에서 실제로 호출되는 경로 자체를 검증한다.
# ---------------------------------------------------------------------------------------------


def test_cli_main_ingest_then_query_json_round_trip(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """`rag ingest ... --profile lite-dev` → `rag query ... --format json`(argparse 경로)."""
    state_dir = tmp_path / ".rag"
    ingest_argv = [
        "ingest",
        *[str(p) for p in _FIXTURE_PATHS],
        "--profile",
        "lite-dev",
        "--collection",
        "demo",
        "--state-dir",
        str(state_dir),
    ]
    exit_code = cli_main.main(ingest_argv)
    assert exit_code == 0
    ingest_stdout = capsys.readouterr().out
    ingested = json.loads(ingest_stdout)
    assert len(ingested) == len(_FIXTURE_PATHS)

    query_argv = [
        "query",
        _QUERY_TEXT,
        "--collection",
        "demo",
        "--state-dir",
        str(state_dir),
        "--format",
        "json",
    ]
    exit_code = cli_main.main(query_argv)
    assert exit_code == 0
    query_stdout = capsys.readouterr().out
    payload = json.loads(query_stdout)
    assert len(payload["context_pack"]["items"]) > 0
    roundtrip.assert_cite_ids_bijective_with_items(payload["context_pack"]["items"])


def test_cli_main_query_unknown_collection_exits_nonzero(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """수집하지 않은 컬렉션에 대한 `rag query`는 종료 코드 2를 낸다(`KeyError` 처리 경로)."""
    exit_code = cli_main.main(["query", "아무 질의", "--collection", "nope", "--state-dir", str(tmp_path / ".rag")])
    assert exit_code == 2
    assert "unknown collection" in capsys.readouterr().err


@pytest.mark.parametrize("profile_arg", ["lite", "lite-dev"])
def test_cli_profile_validate(profile_arg: str, capsys: pytest.CaptureFixture[str]) -> None:
    """`rag profile validate lite`(그리고 `lite-dev` 별칭)는 통과하고 `profile_hash`를 출력한다."""
    exit_code = cli_main.main(["profile", "validate", profile_arg])
    assert exit_code == 0
    assert "profile_hash=" in capsys.readouterr().out


def test_cli_serve_builds_expected_subprocess_argv(monkeypatch: pytest.MonkeyPatch) -> None:
    """`rag serve api|mcp`는 예상 서브프로세스 argv로 하나만 실행한다(실 서버 기동은 `needs_docker`류).

    `cli`는 `api`/`mcp`와 같은 층의 독립 형제라 인프로세스 import가 금지된다(import-linter
    `layers`) — 그래서 `serve`는 항상 서브프로세스를 띄운다. 실 uvicorn/mcp 프로세스를 여기서
    기동하지는 않는다(장수명 프로세스, 포트 바인딩) — `subprocess.run`을 가로채 호출 인자만 본다.
    `# DEFERRED: 실제 서버 기동·헬스체크는 run-deferred.sh의 needs_docker 스모크가 다룬다.`
    """
    captured: dict[str, list[str]] = {}

    def _fake_run(argv: list[str], *, check: bool) -> subprocess.CompletedProcess[bytes]:
        captured["argv"] = argv
        return subprocess.CompletedProcess(argv, 0)

    monkeypatch.setattr(cli_main.subprocess, "run", _fake_run)

    exit_code = cli_main.main(["serve", "api", "--host", "127.0.0.1", "--port", "9001"])
    assert exit_code == 0
    assert captured["argv"][-4:] == ["--host", "127.0.0.1", "--port", "9001"]
    assert "uvicorn" in captured["argv"]
    assert "rag_platform.api.app:app" in captured["argv"]

    exit_code = cli_main.main(["serve", "mcp"])
    assert exit_code == 0
    assert captured["argv"][-1] == "rag_platform.mcp.server"
