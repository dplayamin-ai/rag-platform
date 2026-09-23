"""`enricher.derived_meta` — 날짜·법령 조항 파생 메타(`Enrichment.dates`·`law_refs`)를 채운다.

역할: `enrich` 체인(04-pipelines/11 §2.1 표) 순서 4 — 한국어 점 표기 날짜("2026. 9. 23.")와
`제n조[의m][ 제k항]` 법령 조항을 규칙 기반으로 뽑는다(F2-03, WP-203).
설계 근거: 04-pipelines/11 §4.1(`enricher.derived_meta` 투영 규칙), 바이블 §5.4 `Enrichment.dates`·
`law_refs`(둘 다 N, "없으면 생략"). 04-pipelines/11 §4.1 정본 경로는
`NormalizedDocument.derived_meta.entities_normalized[]` 투영이지만, 그 생산은 WP-106(normalize)이
DEFERRED로 남겼다 — 이 WP는 그 공백을 메우려 `Chunk.text`/`context_prefix.deterministic`에 대한
자체 정규식 추출로 같은 출력 모양을 낸다(설계 갭, WP 문서 DEFERRED 절·open_issues 참조).
구성: `DerivedMetaConfig` — 빈 설정; `DerivedMetaEnricher` — `plugin_id`/`config_schema`/
`capabilities()`/`fingerprint()`/`enrich()`.
불변식·주의: 법령명을 추정하지 못하면 `law_refs` 항목을 만들지 않는다("추측 금지", §4.1 규칙 3).
날짜는 `datetime.date`로 유효성만 검사하고(월·일 범위) 새 값을 합성하지 않는다. `acc`에는 `dates`/
`law_refs` 키만 쓴다.
검증 계층: 1층(여기서 검증) — `tests/adapters/enrich/test_enrich.py`. 외부 자원 없음.
"""

from __future__ import annotations

import json
import re
from datetime import date
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict

from rag_platform.contracts import common_types as ct
from rag_platform.sdk.hashing import hash_of

if TYPE_CHECKING:
    from collections.abc import Sequence

    from rag_platform.adapters.enrich.deterministic_prefix import EnrichmentAccumulator

__all__ = ["PLUGIN_VERSION", "DerivedMetaConfig", "DerivedMetaEnricher"]

PLUGIN_VERSION = "0.1.0"
_HEARTBEAT_EVERY = 50

#: 한국어 점 표기 날짜("2026. 9. 23." 또는 "2026.9.23"); 월·일 자릿수 유연.
_KOREAN_DATE_RE = re.compile(r"(?P<y>\d{4})\.\s*(?P<m>\d{1,2})\.\s*(?P<d>\d{1,2})\.?")
#: `제n조` 또는 `제n조의m`(법령 하위 조항).
_ARTICLE_RE = re.compile(r"제\s*(?P<article>\d+)\s*조(?:\s*의\s*(?P<sub>\d+))?")
#: `제n항`(아라비아 숫자 항).
_CLAUSE_RE = re.compile(r"제\s*(?P<clause>\d+)\s*항")
#: 원문자 항 번호(① = 1 … ⑩ = 10, U+2460..U+2469).
_CIRCLED_CLAUSE = {chr(0x2460 + offset): offset + 1 for offset in range(10)}
#: 법령명으로 볼 수 있는 제목 접미사(04-pipelines/11 §4.1 규칙 3 "법령명 패턴").
_LAW_NAME_SUFFIX_RE = re.compile(r"(법률|시행령|시행규칙|조례|고시|훈령|예규|규정|지침|법)$")
#: `context_prefix.deterministic` 조인 구분자(U+203A, structure_aware 청커 `_CONTEXT_PREFIX_SEP`와 동일
#: 글자 — RUF001 회피를 위해 `chr()`로 만든다, ambiguous-character 리터럴 금지).
_HEADING_SEP = f" {chr(0x203A)} "


def _extract_dates(text: str) -> list[str]:
    """`text`에서 `"YYYY. M. D."` 날짜를 뽑아 ISO(`YYYY-MM-DD`) 값으로 중복 제거·정렬한다."""
    found: set[str] = set()
    for match in _KOREAN_DATE_RE.finditer(text):
        year, month, day = int(match["y"]), int(match["m"]), int(match["d"])
        try:
            iso = date(year, month, day).isoformat()
        except ValueError:
            continue
        found.add(iso)
    return sorted(found)


def _document_title(chunk: ct.Chunk) -> str | None:
    """`context_prefix.deterministic`의 첫 구분 세그먼트(문서 제목)를 돌려준다(04 §3 조립 순서)."""
    deterministic = chunk.context_prefix.deterministic
    if _HEADING_SEP not in deterministic:
        return None
    title = deterministic.split(_HEADING_SEP, 1)[0].strip()
    return title or None


def _law_name(chunk: ct.Chunk) -> str | None:
    """문서 제목이 법령명 패턴(§4.1 규칙 3)이면 그 값을, 아니면 `None`을 돌려준다(추측 금지)."""
    title = _document_title(chunk)
    if title and _LAW_NAME_SUFFIX_RE.search(title):
        return title
    return None


def _find_clause(window: str) -> int | None:
    """다음 조 앞까지의 `window`에서 아라비아 `제k항` 또는 원문자 항 번호를 찾는다."""
    clause_match = _CLAUSE_RE.search(window)
    if clause_match:
        return int(clause_match["clause"])
    for char in window:
        if char in _CIRCLED_CLAUSE:
            return _CIRCLED_CLAUSE[char]
    return None


def _extract_law_refs(text: str, law_name: str | None) -> list[str]:
    """`law_name`이 있을 때만 `{법령명}/제n조[의m][/제k항]` 경로를 뽑는다(§4.1 규칙 3)."""
    if law_name is None:
        return []
    matches = list(_ARTICLE_RE.finditer(text))
    refs: set[str] = set()
    for index, match in enumerate(matches):
        article_no = int(match["article"])
        sub = match["sub"]
        window_end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        clause = _find_clause(text[match.end() : window_end])
        article_part = f"제{article_no}조" + (f"의{sub}" if sub else "")
        ref = f"{law_name}/{article_part}"
        if clause is not None:
            ref = f"{ref}/제{clause}항"
        refs.add(ref)
    return sorted(refs)


class DerivedMetaConfig(BaseModel):
    """`enricher.derived_meta`의 설정 스키마 — 조정 가능한 값 없음(정규식·유효성 규칙은 코드 고정)."""

    model_config = ConfigDict(extra="forbid")


class DerivedMetaEnricher:
    """`enricher.derived_meta` — 체인 순서 4(04-pipelines/11 §2.1 표)."""

    plugin_id = "enricher.derived_meta"
    config_schema = DerivedMetaConfig
    requires_lineage: tuple[str, ...] = ()

    def __init__(self, config: DerivedMetaConfig | None = None) -> None:
        """설정을 고정한다(현재 필드 없음, `config_hash`/`fingerprint()` 입력 자리만 유지)."""
        self.config = config or DerivedMetaConfig()

    def config_hash(self) -> str:
        """`H("config", canonical_json(config))`(바이블 §6.2)."""
        canonical = json.dumps(
            self.config.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
        return hash_of("config", canonical)

    def capabilities(self) -> ct.Capabilities:
        """결정적 보강기 공통 선언(04-pipelines/11 §2.2 표): `in_process`, 재개 지원, `determinism=pure`."""
        return ct.Capabilities(
            isolation_modes=[ct.IsolationMode.in_process],
            supports_resumable=True,
            contracts_compat=ct.ContractsCompat(">=1.0,<2.0"),
            input_formats=[],
            requires_gpu=False,
            extra={"determinism": "pure"},
        )

    def fingerprint(self) -> str:
        """`H("producer", plugin_id, plugin_version, config_hash, "", "")`(모델 없음, 바이블 §6.2)."""
        return hash_of("producer", self.plugin_id, PLUGIN_VERSION, self.config_hash(), "", "")

    async def enrich(
        self,
        chunks: Sequence[ct.Chunk],
        ctx: Any,
        acc: EnrichmentAccumulator,
    ) -> None:
        """청크마다 `dates`/`law_refs`를 계산해 `acc[chunk_id]`에 쓴다(둘 다 없으면 `None`, N).

        Args:
            chunks: 이 세트의 청크.
            ctx: `StageContext`(`heartbeat` 외에는 쓰지 않는다).
            acc: `chunk_id(str) -> 부분 Enrichment 필드 매핑` 누산기.
        """
        for index, chunk in enumerate(chunks):
            dates = _extract_dates(chunk.text)
            law_refs = _extract_law_refs(chunk.text, _law_name(chunk))
            bucket = acc.setdefault(chunk.chunk_id.root, {})
            bucket["dates"] = [ct.Date(value) for value in dates] if dates else None
            bucket["law_refs"] = law_refs or None
            if (index + 1) % _HEARTBEAT_EVERY == 0:
                ctx.heartbeat({"chunk_offset": index + 1})
