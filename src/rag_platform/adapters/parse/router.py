"""`parser.router` — 플랫폼 소유 합성 스테이지: `detect` 실행 → 포맷별 후보 파서 체인 시도 → 첫 성공 반환.

설계 근거: 04-pipelines/03 §3(라우터 구성: `parse.router` 항목 문법·후보 체인)·§4.1(후보 선별·격리 해석)·
§6(부분 성공과 폴백: 진행/중단 조건·품질 신호 폴백 트리거·`quality` 판정)·§7.2(라우터가 채우는 필드)·
§9(라우터 의사코드), 바이블 §4.2 `parse` 행·§11.3 재시도 4분류(`RetryClass.FALLBACK`), ADR-0033.
구성: `DEFAULT_ROUTE_TABLE` — 04-pipelines/03 §3.2 후보 체인을 이 WP 범위(hwpx·pdf·html·txt/md/json,
docx는 `needs_model` 미등록 슬롯)로 옮긴 정본표; `StageBuilder` — `PluginRegistry.build_stage`와
구조적으로만 호환하는 최소 포트(어댑터는 `plugins`를 임포트하지 않는다, layers 계약); `ParseRouterStage`
— 5멤버 스테이지(`run`이 `format_detector.detect_source` → 후보 순차 실행 → §6.1 폴백/중단 판정 →
§6.3 빈 산출 재라우팅 → §6.4 `quality` 승격을 수행).
불변식·주의: 후보 배열 순서는 유일한 우선순위이며 재배열하지 않는다(건너뛰기만 허용, §4.1). 폴백 대상은
`parse.sidecar_unavailable`·`parse.conversion_failed`뿐이고 그 외 코드·`contract.violation`은 체인을
즉시 중단한다(§6.1). 벤더 라이브러리를 임포트하지 않는다 — 후보 스테이지는 `StageBuilder`로만 만든다.
검증 계층: 1층(여기서 검증) — `tests/adapters/parse/test_router.py`. Docker·모델·GPU·네트워크 불필요
(docx 후보는 `needs_model`이라 이 WP에서는 미등록 → `parse.unsupported_format`로 자연 폴백).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

from pydantic import BaseModel, ConfigDict

from rag_platform.adapters.parse.format_detector import FormatDetectorConfig, FormatDetectorStage
from rag_platform.contracts import common_types as ct
from rag_platform.sdk.hashing import hash_of
from rag_platform.sdk.stage import StageError

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from rag_platform.contracts.parsed_document import ParsedDocument
    from rag_platform.contracts.source_document import SourceDocument

__all__ = [
    "DEFAULT_ROUTE_TABLE",
    "PLUGIN_ID",
    "PLUGIN_VERSION",
    "ParseRouterConfig",
    "ParseRouterStage",
    "RouteEntry",
    "StageBuilder",
]

PLUGIN_ID = "parser.router"
PLUGIN_VERSION = "0.1.0"

#: 후보 체인(배열, 순서가 유일한 우선순위) 또는 종결 코드(문자열, §3.1 "종결 코드" 형).
RouteEntry = tuple[str, ...] | str

# 04-pipelines/03 §3.2 표를 이 WP 범위로 옮긴 기본 라우팅 표. F1-02 지시의 "사양 요지"가 명시한 네 포맷만
# 실제로 등록되는 것을 전제한다(hwpx·pdf·html·txt/md/json은 F1 배치의 다른 WP가 같은 배치에서 구현);
# 나머지(hwp5·hwp3·doc·rtf·odt·docx)는 §3.2 정본 plugin_id를 그대로 적어 두되 이 WP는 등록하지 않는다 —
# `StageBuilder.build_stage`가 `KeyError`를 던지면 §4.1 3단계("미설치 후보 건너뛴다")로 처리되어 후보가
# 0개로 줄고 `parse.unsupported_format`이 된다. `docx`가 바로 이 경로로 "needs_model 자리"를 표현한다.
DEFAULT_ROUTE_TABLE: dict[ct.SourceFormat, RouteEntry] = {
    ct.SourceFormat.hwpx: ("parser.hwpx_python_hwpx",),
    ct.SourceFormat.hwp5: (
        "parser.hwp5_java_sidecar",
        "parser.hwp5_unhwp",
        "parser.hwp5_hwp_hwpx_parser",
    ),
    ct.SourceFormat.hwp3: "parse.unsupported_variant",
    ct.SourceFormat.pdf: ("parser.pdf_fast_pdftext",),
    ct.SourceFormat.docx: ("parser.docx_docling_docx2python",),  # needs_model — 이 WP는 미등록
    ct.SourceFormat.doc: ("parser.office_lo_sidecar",),
    ct.SourceFormat.rtf: ("parser.office_lo_sidecar", "parser.rtf_striprtf"),
    ct.SourceFormat.odt: ("parser.office_lo_sidecar", "parser.odt_odfdo"),
    ct.SourceFormat.html: ("parser.html_trafilatura_docling",),
    ct.SourceFormat.txt: ("parser.text_charset_markdown_it",),
    ct.SourceFormat.md: ("parser.text_charset_markdown_it",),
    # §4.7 분할 라우팅(SplitRoute)은 이 WP 범위 밖(미해결 이슈) — split_hint=none 단순화만 반영해 txt와
    # 같은 후보로 둔다.
    ct.SourceFormat.json: ("parser.text_charset_markdown_it",),
}

_CONVERSION_FAILED = "parse.conversion_failed"
_UNSUPPORTED_FORMAT = "parse.unsupported_format"
_PROFILE_INVALID = "profile.invalid"
#: §6.1 폴백 진행 조건(바이블 §11.3 `RetryClass.FALLBACK`). 그 외 코드·`contract.violation`은 체인 중단.
_FALLBACK_CODES = frozenset({"parse.sidecar_unavailable", _CONVERSION_FAILED})
#: §5.2 잔여 시간 규칙의 이 WP 축소판 — 후보 1개를 최소한이라도 시도할 예산(sidecar/GPU 대기 없음).
_MIN_CANDIDATE_BUDGET_MS = 1000
_EMPTY_OUTPUT_DETAIL = "empty output (04-pipelines/03 §6.3 빈 산출)"
_STRUCTURED_BLOCK_TYPES = frozenset({ct.BlockType.table, ct.BlockType.figure})


class StageBuilder(Protocol):
    """`PluginRegistry.build_stage`와 구조적으로만 호환하는 포트(어댑터는 `plugins`를 임포트하지 않는다).

    `layers` import-linter 계약(pyproject.toml)에서 `adapters`와 `plugins`는 같은 층의 독립 패키지다 —
    라우터는 실제 `rag_platform.plugins.registry.PluginRegistry`를 구조적 타입으로만 받는다.
    """

    def build_stage(self, plugin_id: str, config: Mapping[str, Any], services: Any = None) -> Any:
        """`plugin_id`의 `Stage[In, Out]` 인스턴스를 만든다. 미등록이면 `KeyError`(§4.1 3단계 "건너뛴다")."""
        ...


@dataclass(frozen=True)
class _Attempt:
    """시도한 후보 하나 — 성공하면 `error is None`(§7.2 `parser_chain[]` 기록 단위)."""

    plugin_id: str
    error: StageError | None


class ParseRouterConfig(BaseModel):
    """`parser.router`의 v1 설정 — 라우팅 표만 담는다.

    프로파일 `parse.router`·`parse.options` 전체를 반영하는 완전한 스키마는 15 문서가 소유한다;
    이 WP는 포맷별 후보 튜플만 다룬다.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)


def _is_empty_output(parsed: ParsedDocument, source_size_bytes: int) -> bool:
    """§6.3 "빈 산출": `text_length=0`이고 표·그림 블록이 없고 원본 `size_bytes>0`."""
    if source_size_bytes <= 0 or parsed.text_length != 0:
        return False
    return not any(block.type in _STRUCTURED_BLOCK_TYPES for block in parsed.blocks)


def _finalize(out: ParsedDocument, attempts: Sequence[_Attempt], *, force_full: bool) -> ParsedDocument:
    """`parser_chain[]`을 실제 시도 순서로 교체하고 §6.4 규칙대로 `quality`를 승격한다."""
    fallback_occurred = any(attempt.error is not None for attempt in attempts[:-1])
    if force_full:
        quality = ct.Quality.full
    elif fallback_occurred:
        quality = ct.Quality.degraded
    else:
        quality = out.quality
    parser_chain = [ct.PluginId(attempt.plugin_id) for attempt in attempts]
    return out.model_copy(update={"parser_chain": parser_chain, "quality": quality})


class ParseRouterStage:
    """`parser.router` — `detect` + 후보 체인 실행 + 폴백/부분 성공 판정을 합친 합성 스테이지.

    `Stage[SourceDocument, ParsedDocument]`(5멤버). 실제 파서 후보는 생성자로 받은 `StageBuilder`로만
    만든다 — 이 파일 자신은 어떤 포맷별 어댑터도 임포트하지 않는다(§9 "벤더 라이브러리 임포트 없음").
    """

    plugin_id = PLUGIN_ID
    config_schema = ParseRouterConfig
    requires_lineage: tuple[str, ...] = ()

    def __init__(
        self,
        builder: StageBuilder,
        route_table: Mapping[ct.SourceFormat, RouteEntry] | None = None,
        *,
        config: ParseRouterConfig | None = None,
    ) -> None:
        """`builder`(후보 스테이지 팩토리)와 라우팅 표(생략 시 `DEFAULT_ROUTE_TABLE`)를 고정한다."""
        self._builder = builder
        self._route_table: Mapping[ct.SourceFormat, RouteEntry] = route_table or DEFAULT_ROUTE_TABLE
        self.config = config or ParseRouterConfig()
        self._detector = FormatDetectorStage(FormatDetectorConfig())

    def config_hash(self) -> str:
        """`H("config", canonical_json(route_table))`(§7.2: 체인 멤버 개별 지문 합성은 미해결 이슈로 남김)."""
        serializable = {
            fmt.value: (list(entry) if isinstance(entry, tuple) else entry) for fmt, entry in self._route_table.items()
        }
        canonical = json.dumps(serializable, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hash_of("config", canonical)

    def capabilities(self) -> ct.Capabilities:
        """라우터 자신은 `in_process`(후보별 격리 해석·`execute_isolated`/`SidecarStage`는 미해결 이슈)."""
        return ct.Capabilities(
            isolation_modes=[ct.IsolationMode.in_process],
            supports_resumable=False,
            contracts_compat=ct.ContractsCompat(">=1.0,<2.0"),
            input_formats=None,
            requires_gpu=False,
        )

    def fingerprint(self) -> str:
        """`H("producer", plugin_id, plugin_version, config_hash, "", "")`(인프로세스: image digest 없음)."""
        return hash_of("producer", self.plugin_id, PLUGIN_VERSION, self.config_hash(), "", "")

    async def run(self, inp: SourceDocument, ctx: Any) -> ParsedDocument:
        """`detect` → 후보 체인 순차 실행 → §6.1 폴백/중단 → §6.3 빈 산출 재라우팅 → §6.4 승격."""
        source = await self._detector.run(inp, ctx)
        entry = self._route_table.get(source.format)
        if entry is None:
            msg = f"parse.router에 format={source.format.value!r} 항목이 없다(바이블 §7.4 (10))"
            raise StageError(_PROFILE_INVALID, stage="parse", plugin_id=self.plugin_id, detail=msg)
        if isinstance(entry, str):
            detail = f"format={source.format.value} terminal route (04-pipelines/03 §3.1)"
            raise StageError(entry, stage="parse", plugin_id=self.plugin_id, detail=detail)
        return await self._run_chain(entry, source, ctx)

    def _select_viable(self, candidates: Sequence[str]) -> list[tuple[str, Any]]:
        """§4.1 3단계(설치·옵트인 필터)를 이 WP에서 구현 가능한 신호(`KeyError`)만으로 적용한다."""
        viable: list[tuple[str, Any]] = []
        for plugin_id in candidates:
            try:
                stage = self._builder.build_stage(plugin_id, {}, None)
            except KeyError:
                continue  # 미설치·미등록 후보는 건너뛴다(docx의 needs_model 자리가 이 경로)
            viable.append((plugin_id, stage))
        return viable

    async def _run_chain(self, candidates: Sequence[str], source: SourceDocument, ctx: Any) -> ParsedDocument:
        """§9 의사코드의 후보 루프: 필터(§4.1) → 폴백(§6.1) → 빈 산출 재시도(§6.3) → 승격(§6.4)."""
        viable = self._select_viable(candidates)
        if not viable:
            detail = f"format={source.format.value}: no installed candidate (04-pipelines/03 §4.1 step 3)"
            raise StageError(_UNSUPPORTED_FORMAT, stage="parse", plugin_id=self.plugin_id, detail=detail)
        attempts: list[_Attempt] = []
        last_error: StageError | None = None
        for index, (plugin_id, stage) in enumerate(viable):
            remaining = ctx.remaining_ms()
            if remaining is not None and remaining < _MIN_CANDIDATE_BUDGET_MS:
                break
            is_last = index == len(viable) - 1
            try:
                out = await stage.run(source, ctx)
            except StageError as err:
                attempts.append(_Attempt(plugin_id=plugin_id, error=err))
                last_error = err
                if err.code not in _FALLBACK_CODES:
                    raise
                continue
            empty = _is_empty_output(out, source.size_bytes)
            if empty and not is_last:
                empty_error = StageError(
                    _CONVERSION_FAILED, stage="parse", plugin_id=plugin_id, detail=_EMPTY_OUTPUT_DETAIL
                )
                attempts.append(_Attempt(plugin_id=plugin_id, error=empty_error))
                last_error = empty_error
                continue
            attempts.append(_Attempt(plugin_id=plugin_id, error=None))
            return _finalize(out, attempts, force_full=empty)
        if not attempts:
            detail = "remaining_ms below per-candidate budget before any attempt (04-pipelines/03 §5.2)"
            raise StageError(_CONVERSION_FAILED, stage="parse", plugin_id=self.plugin_id, detail=detail)
        detail = f"parser chain exhausted after {len(attempts)} adapters"
        raise StageError(
            _CONVERSION_FAILED,
            stage="parse",
            plugin_id=attempts[-1].plugin_id,
            detail=detail,
            cause=last_error,
        )
