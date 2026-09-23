"""`pack` 2단계 `budget_cut` — 관련도순 그리디 선택 + 예산 초과 시 축소 정책 적용.

역할: `acl_recheck` 통과 항목을 `final_rank` 오름차순으로 `k_max`까지 취해 `PackedItem`으로
조립(`header`·`tables[]` 구체화 + 토큰 재카운트)한 뒤, `used_tokens > limit`이거나 직렬화
512KB를 넘는 동안 `overflow_policy` 순서(`downgrade_tables → truncate`, `compress`는 압축기
미배선이라 즉시 truncate와 동치)로 축소한다. 절단은 항상 최하위 순위부터.
설계 근거: 04-pipelines/17 §3.1(예산 산정)·§3.3(의사코드), 바이블 §9.1(pack 내부 고정 순서
2번째), 계약 `contracts/common_types.{Header,Table,Warning}`.
구성: `PackedItem` — `citation_align`까지 이어지는 작업 중간 타입(계약 아님); `BudgetCutConfig` —
`QueryPlan.pack` 대역 설정; `apply` — 문서 §3.3 `budget_cut` 의사코드 구현.
불변식·주의: `figures[]`는 `RankedResult`에 원천 필드가 없어 항상 `None`(WP-403 §7 open_issue).
표 파생물(`html_ref`) 로드는 하지 않는다(retrieval은 `storage`를 import할 수 없음) — `table_ref`
dict에 이미 있는 값만 쓴다. 상위 항목의 텍스트는 절단하지 않는다(문서 §3.3).
검증 계층: 1층(여기서 검증) — tests/retrieval/test_postprocess_pack.py.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from pydantic import AnyUrl

from rag_platform.contracts import common_types
from rag_platform.contracts.context_pack import PackOmittedEntry

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from rag_platform.contracts.common_types import RankedResult
    from rag_platform.sdk.ports import TokenCounter

__all__ = ["BudgetCutConfig", "PackedItem", "apply"]


def _root(value: Any) -> Any:
    """RootModel 래퍼(`Hex64`·`Ulid` 등)를 순수 값으로 벗긴다. 평범한 값은 그대로."""
    return value.root if hasattr(value, "root") else value


@dataclass
class PackedItem:
    """`budget_cut`이 조립해 `reorder`·`citation_align`으로 넘기는 작업 타입(계약 아님)."""

    result: RankedResult
    header: common_types.Header
    tables: list[common_types.Table] | None = None
    figures: list[common_types.Figure1] | None = None
    acl2: common_types.Acl2 | None = None
    token_count: int = 0
    position: int | None = None


@dataclass(frozen=True)
class BudgetCutConfig:
    """`QueryPlan.pack`(09 §6.9 `PackPlan`) 대역 — 이 WP는 원시 값만 받는다(WP-403 §0)."""

    k_max: int
    max_context_tokens: int
    reserved_answer_tokens: int
    overflow_policy: Sequence[common_types.OverflowPolicy] = field(
        default_factory=lambda: (common_types.OverflowPolicy.downgrade_tables, common_types.OverflowPolicy.truncate)
    )
    table_format_preference: Sequence[common_types.TableFormat] = field(
        default_factory=lambda: (common_types.TableFormat.markdown, common_types.TableFormat.html)
    )
    default_lang: str = "ko"
    max_serialized_bytes: int = 512 * 1024


def _header_of(r: RankedResult, *, default_lang: str) -> common_types.Header:
    return common_types.Header(
        title=r.title or "",
        section_path=list(r.heading_path or []),
        numbering_path=list(r.numbering_path or []),
        source_uri=r.source_uri if r.source_uri is not None else common_types.Uri(AnyUrl("urn:rag:unknown")),
        external_id=r.external_id,
        doc_date=_root(r.doc_date) if r.doc_date is not None else None,
        doc_type=r.doc_type,
        page_start=r.page_start,
        page_end=r.page_end,
        lang=_root(r.lang) if r.lang is not None else default_lang,
        doc_version_label=None,
    )


def _table_text(table: common_types.Table) -> str:
    """`format_used`가 가리키는 필드의 문자열 길이로 비용을 센다(강등 후 실제로 줄었는지 반영)."""
    by_format: dict[common_types.TableFormat, str | list[Any] | None] = {
        common_types.TableFormat.html: table.html,
        common_types.TableFormat.markdown: table.markdown,
        common_types.TableFormat.json: table.json_records,
    }
    value = by_format.get(table.format_used)
    if isinstance(value, str) and value:
        return value
    if value:
        return json.dumps(value, ensure_ascii=False)
    for candidate in (table.html, table.markdown, table.caption):
        if candidate:
            return candidate
    if table.json_records:
        return json.dumps(table.json_records, ensure_ascii=False)
    return ""


def _tables_of(
    r: RankedResult, table_format_preference: Sequence[common_types.TableFormat]
) -> list[common_types.Table] | None:
    if not r.table_ref:
        return None
    preferred = table_format_preference[0] if table_format_preference else common_types.TableFormat.markdown
    return [
        common_types.Table(
            table_id=str(r.table_ref.get("table_id", _root(r.chunk_id))),
            html=r.table_ref.get("html"),
            markdown=r.table_ref.get("markdown"),
            json_records=r.table_ref.get("json_records"),
            caption=r.table_ref.get("caption"),
            format_used=preferred,
            downgraded=False,
        )
    ]


def _header_text(header: common_types.Header) -> str:
    return " ".join(filter(None, [header.title, *header.section_path, *header.numbering_path]))


def _materialize(r: RankedResult, cfg: BudgetCutConfig) -> PackedItem:
    header = _header_of(r, default_lang=cfg.default_lang)
    tables = _tables_of(r, cfg.table_format_preference)
    return PackedItem(result=r, header=header, tables=tables, figures=None)


def _recount(item: PackedItem, counter: TokenCounter) -> None:
    total = counter.count(item.result.text or "") + counter.count(_header_text(item.header))
    for table in item.tables or []:
        total += counter.count(_table_text(table))
    item.token_count = total


def _used_tokens(packed: Sequence[PackedItem]) -> int:
    return sum(p.token_count for p in packed)


def _serialized_bytes(packed: Sequence[PackedItem]) -> int:
    payload = [{"text": p.result.text, "tables": [_table_text(t) for t in p.tables or []]} for p in packed]
    return len(json.dumps(payload, ensure_ascii=False).encode("utf-8"))


def _tables_downgradable(item: PackedItem, table_format_preference: Sequence[common_types.TableFormat]) -> bool:
    if not item.tables or not table_format_preference:
        return False
    return any(t.format_used != table_format_preference[-1] for t in item.tables)


def _downgrade_tables(item: PackedItem, table_format_preference: Sequence[common_types.TableFormat]) -> None:
    for table in item.tables or []:
        try:
            idx = list(table_format_preference).index(table.format_used)
        except ValueError:
            continue
        if idx + 1 < len(table_format_preference):
            table.format_used = table_format_preference[idx + 1]
            table.downgraded = True


def _omit(r: RankedResult) -> PackOmittedEntry:
    return PackOmittedEntry(
        chunk_id=r.chunk_id,
        collection_id=r.collection_id,
        document_id=r.document_id,
        reason=common_types.OmitReason.budget_exceeded,
    )


def apply(
    items: Sequence[RankedResult],
    cfg: BudgetCutConfig,
    counter: TokenCounter,
    acl2_by_chunk_id: Mapping[str, common_types.Acl2] | None = None,
) -> tuple[list[PackedItem], list[PackOmittedEntry], list[common_types.Warning]]:
    """문서 §3.3 `budget_cut(items, plan, counter, ctx)`의 구현."""
    acl2_by_chunk_id = acl2_by_chunk_id or {}
    kept = sorted(items, key=lambda r: r.final_rank)
    omitted = [_omit(r) for r in kept[cfg.k_max :]]
    kept = kept[: cfg.k_max]
    packed = [_materialize(r, cfg) for r in kept]
    for p in packed:
        p.acl2 = acl2_by_chunk_id.get(_root(p.result.chunk_id))
        _recount(p, counter)

    limit = cfg.max_context_tokens - cfg.reserved_answer_tokens
    policy = list(cfg.overflow_policy)
    overflowed = False
    while packed and (_used_tokens(packed) > limit or _serialized_bytes(packed) > cfg.max_serialized_bytes):
        overflowed = True
        step = policy[0] if policy else common_types.OverflowPolicy.truncate
        if step == common_types.OverflowPolicy.downgrade_tables:
            victim = next((p for p in reversed(packed) if _tables_downgradable(p, cfg.table_format_preference)), None)
            if victim is None:
                policy.pop(0)
                continue
            _downgrade_tables(victim, cfg.table_format_preference)
            _recount(victim, counter)
        else:
            # truncate(기본) 및 compress(압축기 미배선 → 문서 §3.3 의사코드 else 분기와 동치).
            victim = packed.pop()
            omitted.append(_omit(victim.result))

    warnings: list[common_types.Warning] = []
    if overflowed:
        warnings.append(
            common_types.Warning(
                code=common_types.ErrorCodeCatalog.pack_budget_overflow, message="overflow_policy applied"
            )
        )
    return packed, omitted, warnings
