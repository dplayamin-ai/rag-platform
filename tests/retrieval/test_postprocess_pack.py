"""F4-03(postprocess-and-pack) 단위 테스트 — 후처리 4단계 + pack 4단계 + `packer.pack` 종단.

역할: `src/rag_platform/retrieval/postprocess/{relevance_gate,dedup,mmr,parent_expand}.py`와
`src/rag_platform/retrieval/pack/{acl_recheck,budget_cut,reorder,citation_align,packer}.py`가
WP-403(§3 시그니처·§6 절차)를 만족하는지 검증한다. 픽스처는 이 파일이 직접 합성한다(외부
데이터 없음, `sdk.hashing.blake3_hex`로 결정적 `Hex64`/`Ulid` 생성).
설계 근거: docs/13-implementation/wp/WP-403-postprocess-and-pack.md §8(테스트 목록),
04-pipelines/17-post-processing-and-context-packing.md §2~§3(예시 값 참고).
구성: 팩토리(`make_result`/`make_acl`/`make_security`/`hex64`/`ulid`) + 단계별 `Test*` 클래스.
불변식·주의: 모델 다운로드·Docker·GPU·네트워크 의존 없음(순수 함수, 페이크 `TokenCounter`/
`ChunkTextStore`). `rag_platform.testing.litm_order`/`renderer_citation_roundtrip`(적합성 키트)로
`litm_alternating`·`cite_id` 불변식을 대조한다.
검증 계층: 1층(여기서 검증) — `uv run pytest -q tests/retrieval/test_postprocess_pack.py`.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from rag_platform.contracts import common_types as ct
from rag_platform.contracts.common_types import RankedResult, SecurityContext
from rag_platform.contracts.context_pack import RenderHints, TokenizerSpec
from rag_platform.contracts.ranked_set import RankedSet
from rag_platform.retrieval.pack import acl_recheck, budget_cut, citation_align, packer, reorder
from rag_platform.retrieval.postprocess import dedup, mmr, parent_expand, relevance_gate
from rag_platform.sdk.hashing import blake3_hex
from rag_platform.testing import litm_order, renderer_citation_roundtrip

_ULID_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def ulid(tag: str) -> str:
    """`tag`에서 결정적으로 26자 ULID 형식 문자열을 만든다(테스트 전용)."""
    digest = blake3_hex(tag)
    return "".join(_ULID_ALPHABET[int(c, 16) % len(_ULID_ALPHABET)] for c in digest[:26])


def hex64(tag: str) -> str:
    """`tag`에서 결정적으로 64자 hex 문자열을 만든다(테스트 전용)."""
    return blake3_hex(tag)


def hex32(tag: str) -> str:
    """`tag`에서 결정적으로 32자 hex 문자열을 만든다(테스트 전용, `block_id`)."""
    return blake3_hex(tag)[:32]


TENANT = ulid("tenant")
COLLECTION = ulid("collection")
DOCUMENT_A = ulid("doc-a")


class FakeTokenCounter:
    """`sdk.ports.TokenCounter` 대역 — 문자 길이를 그대로 토큰 수로 쓴다."""

    tokenizer_id = "hf:test"

    def count(self, text: str) -> int:
        return len(text)


class FakeChunkTextStore:
    """`parent_expand.ChunkTextStore` 대역 — 딕셔너리 기반 인메모리 번들."""

    def __init__(self, bundles: dict[str, parent_expand.ParentEntry]) -> None:
        self._bundles = bundles

    def get_many(
        self, _chunk_set_blake3: str, parent_chunk_ids: list[str], _security: SecurityContext
    ) -> dict[str, parent_expand.ParentEntry]:
        return {pid: self._bundles[pid] for pid in parent_chunk_ids if pid in self._bundles}


def score_breakdown(fused: float, *, rerank_normalized: float | None = None) -> dict[str, Any]:
    return {
        "dense": None,
        "sparse": None,
        "lexical": None,
        "graph": None,
        "tree": None,
        "visual": None,
        "late_interaction": None,
        "fused": fused,
        "fused_rank": 1,
        "rerank_raw": None,
        "rerank_normalized": rerank_normalized,
        "normalization": "identity",
    }


def make_acl(
    *,
    allow: list[str] | None = None,
    deny: list[str] | None = None,
    visibility: str = "tenant",
    classification: str = "internal",
    embargo_until: str | None = None,
    expires_at: str | None = None,
    tag: str = "acl",
) -> dict[str, Any]:
    return {
        "allow": allow or ["user:alice"],
        "deny": deny or [],
        "visibility": visibility,
        "classification": classification,
        "embargo_until": embargo_until,
        "expires_at": expires_at,
        "acl_hash": hex64(f"aclhash-{tag}"),
    }


def make_security(
    *,
    principals: list[str] | None = None,
    visible_set: list[str] | None = None,
    classification_max: str = "internal",
    as_of: str = "2026-09-23T00:00:00.000Z",
) -> SecurityContext:
    return SecurityContext(
        tenant_id=TENANT,
        principals=principals or ["user:alice"],
        collection_ids=[COLLECTION],
        as_of=as_of,
        classification_max=classification_max,
        policy_version="v1",
        auth_method="oidc",
        visible_set=visible_set or ["public", "tenant"],
    )


def make_result(
    tag: str,
    *,
    rank: int,
    score: float,
    document_id: str = DOCUMENT_A,
    chunk_id: str | None = None,
    record_id: str | None = None,
    item_kind: str = "text",
    level: int = 0,
    parent_chunk_id: str | None = None,
    text: str = "본문 텍스트",
    explain: list[str] | None = None,
    channels_hit: list[str] | None = None,
    variant_ids: list[str] | None = None,
    block_refs: list[dict[str, Any]] | None = None,
    sentence_spans: list[list[int]] | None = None,
    acl: dict[str, Any] | None = None,
    chunk_set_blake3: str | None = None,
    token_count_primary: int | None = None,
    ordinal: int | None = None,
    expanded_from: list[str] | None = None,
    heading_path: list[str] | None = None,
    title: str = "제목",
    source_uri: str | None = "s3://bucket/doc.pdf",
    duplicates_of: str | None = None,
) -> RankedResult:
    cid = chunk_id or hex64(tag)
    if record_id is not None:
        rid = record_id
    elif item_kind == "parent":
        rid = None
    else:
        rid = hex64(f"record-{tag}")
    return RankedResult(
        record_id=rid,
        chunk_id=cid,
        collection_id=COLLECTION,
        document_id=document_id,
        doc_version=hex64(f"version-{document_id}"),
        item_kind=item_kind,
        level=level,
        parent_chunk_id=parent_chunk_id,
        final_rank=rank,
        final_score=score,
        fused_score=score,
        fused_rank=rank,
        score_breakdown=score_breakdown(score),
        channels_hit=channels_hit or ["dense"],
        variant_ids=variant_ids or [ulid(f"variant-{tag}")],
        text=text,
        heading_path=heading_path,
        title=title,
        source_uri=source_uri,
        explain=explain or [],
        acl=acl,
        block_refs=block_refs,
        sentence_spans=sentence_spans,
        chunk_set_blake3=chunk_set_blake3,
        token_count_primary=token_count_primary,
        ordinal=ordinal,
        expanded_from=expanded_from,
        duplicates_of=duplicates_of,
    )


def dummy_header() -> ct.Header:
    return ct.Header(title="t", section_path=[], numbering_path=[], source_uri="urn:rag:unknown", lang="ko")


# --------------------------------------------------------------------------------------------
# relevance_gate
# --------------------------------------------------------------------------------------------


def test_relevance_gate_filters_below_tau() -> None:
    kept = make_result("a", rank=1, score=0.9)
    dropped = make_result("b", rank=2, score=0.2)
    out = relevance_gate.apply([kept, dropped], tau=0.3)
    assert [r.chunk_id.root for r in out.results] == [kept.chunk_id.root]
    assert out.removed == 1
    assert out.gate is not None
    assert out.gate.passed is True
    assert out.omitted[0].reason.value == "below_threshold"
    assert ct.ExplainCode.below_gate in out.omitted[0].explain


def test_relevance_gate_empty_input_max_score_zero() -> None:
    out = relevance_gate.apply([], tau=0.1)
    assert out.gate is not None
    assert out.gate.max_score == 0.0
    assert out.gate.passed is False
    assert out.results == []


# --------------------------------------------------------------------------------------------
# dedup
# --------------------------------------------------------------------------------------------


def test_dedup_removes_exact_and_near_duplicates() -> None:
    shared_chunk = hex64("dup-shared")
    exact = make_result("dup1", rank=1, score=0.9, chunk_id=shared_chunk)
    exact_dup = make_result("dup2", rank=2, score=0.8, chunk_id=shared_chunk)
    near_dup = make_result("near", rank=3, score=0.7, text="본문 텍스트")
    distinct = make_result("distinct", rank=4, score=0.6, text="완전히 다른 내용의 문장입니다")
    out = dedup.apply([exact, exact_dup, near_dup, distinct])
    kept_ids = {r.chunk_id.root for r in out.results}
    assert kept_ids == {exact.chunk_id.root, distinct.chunk_id.root}
    assert out.removed == 2
    reasons = {o.reason.value for o in out.omitted}
    assert reasons == {"duplicate"}


def test_dedup_removes_parent_merged_children() -> None:
    child1 = make_result("child1", rank=2, score=0.5)
    child2 = make_result("child2", rank=3, score=0.4)
    parent = make_result(
        "parent",
        rank=1,
        score=0.9,
        item_kind="parent",
        level=1,
        chunk_id=hex64("parent-chunk"),
        expanded_from=[child1.chunk_id.root, child2.chunk_id.root],
    )
    out = dedup.apply([parent, child1, child2])
    kept_ids = {r.chunk_id.root for r in out.results}
    assert kept_ids == {parent.chunk_id.root}
    assert {o.reason.value for o in out.omitted} == {"parent_merged"}
    assert all(o.related_chunk_id.root == parent.chunk_id.root for o in out.omitted)


# --------------------------------------------------------------------------------------------
# mmr
# --------------------------------------------------------------------------------------------


def test_mmr_reorders_and_marks_demoted() -> None:
    rid1, rid2, rid3 = hex64("rec-1"), hex64("rec-2"), hex64("rec-3")
    r1 = make_result("r1", rank=1, score=1.0, record_id=rid1)
    r2 = make_result("r2", rank=2, score=0.95, record_id=rid2)
    r3 = make_result("r3", rank=3, score=0.5, record_id=rid3)
    vectors = {rid1: [1.0, 0.0], rid2: [0.99, 0.01], rid3: [0.0, 1.0]}
    out = mmr.apply([r1, r2, r3], vectors, 0.5)
    order = [r.chunk_id.root for r in out.results]
    assert order == [r1.chunk_id.root, r3.chunk_id.root, r2.chunk_id.root]
    assert ct.ExplainCode.mmr_demoted in out.results[2].explain
    assert ct.ExplainCode.mmr_demoted not in out.results[0].explain


def test_mmr_noop_when_lambda_disabled() -> None:
    results = [
        make_result("a", rank=1, score=0.9),
        make_result("b", rank=2, score=0.5),
        make_result("c", rank=3, score=0.4),
    ]
    assert mmr.apply(results, None, None).results == results
    assert mmr.apply(results, None, 1.0).results == results


# --------------------------------------------------------------------------------------------
# parent_expand
# --------------------------------------------------------------------------------------------


def test_parent_expand_merges_majority_children() -> None:
    cs_hash = hex64("chunk-set")
    parent_id = hex64("parent-x")
    child1 = make_result(
        "c1", rank=1, score=0.9, parent_chunk_id=parent_id, chunk_set_blake3=cs_hash, token_count_primary=10
    )
    child2 = make_result(
        "c2", rank=2, score=0.8, parent_chunk_id=parent_id, chunk_set_blake3=cs_hash, token_count_primary=10
    )
    parent_entry = parent_expand.ParentEntry(
        text="부모 전체 텍스트",
        heading_path=["섹션"],
        numbering_path=["1"],
        token_counts={"hf:test": 30},
        block_refs=None,
        sentence_spans=None,
        text_source=None,
        ocr_confidence_min=None,
        page_start=None,
        page_end=None,
        n_children=2,
    )
    store = FakeChunkTextStore({parent_id: parent_entry})
    out = parent_expand.apply(
        [child1, child2],
        text_store=store,
        security=make_security(),
        token_counter=FakeTokenCounter(),
        max_context_tokens=20000,
        reserved_answer_tokens=2000,
    )
    assert out.added == 1
    assert len(out.results) == 2
    parent_item = next(r for r in out.results if r.item_kind.value == "parent")
    assert parent_item.text == "부모 전체 텍스트"
    assert parent_item.record_id is None
    assert {c.root for c in parent_item.expanded_from} == {child1.chunk_id.root, child2.chunk_id.root}
    assert ct.ExplainCode.parent_of_n_hits in parent_item.explain


def test_parent_expand_skips_when_over_budget_guard() -> None:
    cs_hash = hex64("chunk-set-2")
    parent_id = hex64("parent-y")
    child1 = make_result(
        "d1", rank=1, score=0.9, parent_chunk_id=parent_id, chunk_set_blake3=cs_hash, token_count_primary=1000
    )
    child2 = make_result(
        "d2", rank=2, score=0.8, parent_chunk_id=parent_id, chunk_set_blake3=cs_hash, token_count_primary=1000
    )
    parent_entry = parent_expand.ParentEntry(
        text="부모 전체 텍스트" * 50,
        heading_path=None,
        numbering_path=None,
        token_counts={"hf:test": 5000},
        block_refs=None,
        sentence_spans=None,
        text_source=None,
        ocr_confidence_min=None,
        page_start=None,
        page_end=None,
        n_children=2,
    )
    store = FakeChunkTextStore({parent_id: parent_entry})
    out = parent_expand.apply(
        [child1, child2],
        text_store=store,
        security=make_security(),
        token_counter=FakeTokenCounter(),
        max_context_tokens=2000,
        reserved_answer_tokens=0,
        budget_guard_ratio=0.8,
    )
    assert out.added == 0
    assert [r.chunk_id.root for r in out.results] == [child1.chunk_id.root, child2.chunk_id.root]


# --------------------------------------------------------------------------------------------
# acl_recheck
# --------------------------------------------------------------------------------------------


def test_acl_recheck_denies_on_classification_and_embargo() -> None:
    allowed = make_result("ok", rank=1, score=0.9, acl=make_acl(classification="internal", tag="ok"))
    too_high = make_result("secret", rank=2, score=0.8, acl=make_acl(classification="secret", tag="secret"))
    embargoed = make_result(
        "embargo", rank=3, score=0.7, acl=make_acl(embargo_until="2099-01-01T00:00:00.000Z", tag="embargo")
    )
    security = make_security(classification_max="internal", as_of="2026-09-23T00:00:00.000Z")
    passed, denied, report, acl2_by_chunk_id = acl_recheck.apply([allowed, too_high, embargoed], security)
    assert [r.chunk_id.root for r in passed] == [allowed.chunk_id.root]
    assert report.checked == 3
    assert report.denied == 2
    assert allowed.chunk_id.root in acl2_by_chunk_id
    assert {o.reason.value for o in denied} == {"acl_denied"}


def test_acl_recheck_prefers_revocation_hint() -> None:
    doc_id = ulid("doc-hint")
    # payload는 visibility=tenant(default_visible_set에 포함)라 힌트가 없으면 통과할 값이다 — 힌트가
    # visibility=restricted + allow에 없는 주체로 뒤집어야만 거부되므로 "힌트를 우선한다"가 증명된다.
    r = make_result(
        "hinted", rank=1, score=0.9, document_id=doc_id, acl=make_acl(classification="internal", tag="orig")
    )
    security = make_security(classification_max="internal")
    hint = acl_recheck.RevocationHint(
        acl_hash=hex64("different-hash"),
        allow=["user:bob"],
        deny=[],
        visibility=ct.Visibility.restricted,
        classification=ct.Classification.internal,
    )
    passed, denied, report, _acl2 = acl_recheck.apply([r], security, revocation_hints={doc_id: hint})
    assert passed == []
    assert report.hint_hits == 1
    assert denied[0].reason.value == "acl_denied"


def test_acl_recheck_denies_deletion_hint_even_when_acl_hash_matches_payload() -> None:
    """E9/§9.1: 삭제는 ACL을 바꾸지 않으므로 `deleted=True` 힌트의 `acl_hash`가 payload와 같을 수
    있다 — 그래도 "deleted=True면 무조건 거부"다(골든 시나리오 "삭제 → 전파 전 질의 → 미반환").
    """
    doc_id = ulid("doc-deleted")
    acl = make_acl(classification="internal", tag="same")
    r = make_result("deleted", rank=1, score=0.9, document_id=doc_id, acl=acl)
    security = make_security(classification_max="internal")
    hint = acl_recheck.RevocationHint(
        acl_hash=acl["acl_hash"],  # payload와 동일한 acl_hash
        allow=acl["allow"],
        deny=acl["deny"],
        visibility=ct.Visibility(acl["visibility"]),
        classification=ct.Classification(acl["classification"]),
        deleted=True,
    )
    passed, denied, report, _acl2 = acl_recheck.apply([r], security, revocation_hints={doc_id: hint})
    assert passed == []
    assert denied[0].reason.value == "acl_denied"
    # payload만 봤다면(힌트 무시) 통과했을 것 — 회귀 시 이 항목은 `passed`에 들어간다.
    assert report.denied == 1


@pytest.mark.parametrize(
    ("visibility", "allow", "principals", "expect_passed"),
    [
        # public: allow 검사를 생략 — allow에 없는 주체도 통과(§10.1).
        ("public", ["group:other"], ["user:alice"], True),
        # tenant: visible_set에 포함된 인증 사용자는 allow와 무관하게 통과(§10.1·§10.2(a) OR).
        ("tenant", ["group:other"], ["user:alice"], True),
        # restricted: visible_set에 없으므로 allow 멤버십으로만 판정 — 포함되면 통과.
        ("restricted", ["user:alice"], ["user:alice"], True),
        # restricted + allow에 없는 주체는 여전히 거부(fail-closed 유지).
        ("restricted", ["user:bob"], ["user:alice"], False),
        # tenant지만 principals가 service 전용(visible_set에 tenant 없음)이고 allow에도 없으면 거부.
        ("tenant", ["group:other"], ["service:worker"], False),
        # tenant + service 전용 principals가 allow에 명시되어 있으면 통과(§10.1 "service: 전용
        # 주체는 allow_principals에 있어야 함").
        ("tenant", ["service:worker"], ["service:worker"], True),
    ],
)
def test_acl_recheck_matches_bible_10_2_a_or_semantics(
    visibility: str, allow: list[str], principals: list[str], expect_passed: bool
) -> None:
    acl = make_acl(allow=allow, visibility=visibility, classification="internal", tag=f"{visibility}-{allow}")
    r = make_result("case", rank=1, score=0.9, acl=acl)
    # service 전용 호출자는 visible_set에 `tenant`가 빠진다(§10.2 "auth_method=api_key이고 service:
    # 주체만이면 visible_set=[public]").
    visible_set = ["public"] if principals == ["service:worker"] else ["public", "tenant"]
    security = make_security(principals=principals, visible_set=visible_set, classification_max="internal")
    passed, denied, _report, _acl2 = acl_recheck.apply([r], security)
    assert (len(passed) == 1) == expect_passed
    if not expect_passed:
        assert denied[0].reason.value == "acl_denied"


def test_acl_recheck_deny_always_wins_over_visible_set() -> None:
    """`deny`가 `visible_set` 포함 여부와 무관하게 항상 우선한다(§10.1 "deny_principals는 항상 우선")."""
    acl = make_acl(allow=["tenant:*"], deny=["user:alice"], visibility="tenant", classification="internal")
    r = make_result("denied-wins", rank=1, score=0.9, acl=acl)
    security = make_security(principals=["user:alice"], visible_set=["public", "tenant"])
    passed, denied, _report, _acl2 = acl_recheck.apply([r], security)
    assert passed == []
    assert denied[0].reason.value == "acl_denied"


# --------------------------------------------------------------------------------------------
# budget_cut
# --------------------------------------------------------------------------------------------


def test_budget_cut_truncates_lowest_rank_first() -> None:
    results = [make_result(f"r{i}", rank=i, score=1.0 - i * 0.01, text="x" * 50) for i in range(1, 6)]
    cfg = budget_cut.BudgetCutConfig(k_max=5, max_context_tokens=60, reserved_answer_tokens=0)
    packed, omitted, warnings = budget_cut.apply(results, cfg, FakeTokenCounter())
    assert len(packed) == 1
    assert packed[0].result.final_rank == 1
    assert len(omitted) == 4
    assert any(w.code.value == "pack.budget_overflow" for w in warnings)


def test_budget_cut_downgrades_tables() -> None:
    table_ref = {"html": "<table>" + "x" * 200 + "</table>", "markdown": "| x |", "caption": "표"}
    r = make_result("tbl", rank=1, score=0.9, text="본문", item_kind="table")
    r = r.model_copy(update={"table_ref": table_ref})
    cfg = budget_cut.BudgetCutConfig(
        k_max=1,
        max_context_tokens=50,
        reserved_answer_tokens=0,
        table_format_preference=(ct.TableFormat.html, ct.TableFormat.markdown),
    )
    packed, _omitted, _warnings = budget_cut.apply([r], cfg, FakeTokenCounter())
    assert len(packed) == 1
    assert packed[0].tables is not None
    assert packed[0].tables[0].format_used == ct.TableFormat.markdown
    assert packed[0].tables[0].downgraded is True


# --------------------------------------------------------------------------------------------
# reorder
# --------------------------------------------------------------------------------------------


def test_reorder_litm_alternating_matches_pinned_table() -> None:
    for k_total in range(1, 6):
        results = [make_result(f"r{i}", rank=i, score=1.0 - i * 0.01) for i in range(1, k_total + 1)]
        packed = [budget_cut.PackedItem(result=r, header=dummy_header()) for r in results]
        ordered, applied = reorder.apply(packed, ct.OrderingStrategy.litm_alternating)
        assert applied is True
        order = [p.result.final_rank for p in ordered]
        litm_order.assert_litm_alternating_invariants(order, k_total)


def test_reorder_document_order_fallback() -> None:
    r1 = make_result("a", rank=1, score=0.9)
    r2 = make_result("b", rank=2, score=0.8)
    packed = [
        budget_cut.PackedItem(result=r1, header=dummy_header()),
        budget_cut.PackedItem(result=r2, header=dummy_header()),
    ]
    ordered, applied = reorder.apply(packed, ct.OrderingStrategy.document_order)
    assert applied is False
    assert [p.position for p in ordered] == [0, 1]


# --------------------------------------------------------------------------------------------
# citation_align
# --------------------------------------------------------------------------------------------


def _block_ref(tag: str) -> dict[str, Any]:
    return {
        "block_id": hex32(tag),
        "element_path": f"/p[{tag}]",
        "char_start": 0,
        "char_end": 10,
        "original_char_start": 0,
        "original_char_end": 10,
        "page": None,
        "bbox": None,
        "section_index": 0,
    }


def test_citation_align_cite_ids_are_d1_dk_continuous() -> None:
    header = dummy_header()
    results = [
        make_result(f"c{i}", rank=i, score=1.0 - i * 0.1, text="본문 텍스트입니다", block_refs=[_block_ref(f"c{i}")])
        for i in range(1, 4)
    ]
    packed_items = [
        budget_cut.PackedItem(result=r, header=header, token_count=10, position=idx) for idx, r in enumerate(results)
    ]
    items, _warnings = citation_align.apply(packed_items, as_of="2026-09-23T00:00:00.000Z")
    assert [i.cite_id.root for i in items] == ["d1", "d2", "d3"]
    renderer_citation_roundtrip.assert_cite_ids_bijective_with_items([i.model_dump(mode="json") for i in items])
    for item in items:
        assert item.provenance
        assert item.segments


# --------------------------------------------------------------------------------------------
# packer — 종단 테스트
# --------------------------------------------------------------------------------------------


def test_packer_end_to_end_builds_valid_context_pack() -> None:
    results = [
        make_result(
            f"item{i}",
            rank=i,
            score=1.0 - i * 0.05,
            text="문서 본문 내용입니다",
            block_refs=[_block_ref(f"item{i}")],
            acl=make_acl(tag=f"acl{i}"),
        )
        for i in range(1, 7)
    ]
    ranked = RankedSet(
        schema_version="1.0.0",
        schema_type="RankedSet",
        tenant_id=TENANT,
        collection_ids=[COLLECTION],
        producer={
            "plugin_id": "postprocessor.default",
            "plugin_version": "1.0.0",
            "config_hash": hex64("cfg"),
            "image_digest": None,
        },
        warnings=[],
        degraded=[],
        created_at="2026-09-23T00:00:00.000Z",
        ranked_set_id=ulid("ranked"),
        plan_id=ulid("plan"),
        query_id=ulid("query"),
        stage="postprocessed",
        hydrated=True,
        fusion={
            "method": "rrf",
            "k": 60,
            "weights": {},
            "variant_query_weight": 1.0,
            "candidates_in": 6,
            "candidates_out": 6,
        },
        relevance_gate={"tau": 0.1, "max_score": 0.95, "passed": True, "retries": 0},
        results=[r.model_dump(mode="json") for r in results],
        omitted=[],
        stats={"n_in": 6, "n_out": 6, "hydrated_n": 6, "gate_passed": True},
    )
    security = make_security()
    cfg = packer.PackConfig(
        security=security,
        token_counter=FakeTokenCounter(),
        budget_cut=budget_cut.BudgetCutConfig(k_max=20, max_context_tokens=24000, reserved_answer_tokens=4000),
        ordering_strategy=ct.OrderingStrategy.litm_alternating,
        tokenizer=TokenizerSpec(provider="anthropic", model="claude-opus-5", name="anthropic:claude-opus-5"),
        count_method=ct.CountMethod.exact_local,
        render_hints=RenderHints(
            preferred_renderer=ct.Renderer.markdown,
            citation_style=ct.CitationStyle.bracket_id,
            instructions_template_id="rag-answer-ko@1",
            table_format_preference=[ct.TableFormat.markdown, ct.TableFormat.html, ct.TableFormat.json],
            language="ko",
            expose_confidence=True,
            data_marking=ct.DataMarking.none,
        ),
        profile_id="standard",
        profile_hash=hex64("profile"),
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
        producer=ct.Producer(
            plugin_id="packer.standard", plugin_version="1.0.0", config_hash=hex64("packcfg"), image_digest=None
        ),
        pack_id=ulid("pack"),
    )
    context_pack = packer.pack(ranked, cfg, now=datetime(2026, 9, 23, tzinfo=UTC))
    assert len(context_pack.items) == 6
    assert context_pack.budget.used_tokens > 0
    assert context_pack.content_hash
    litm_order.assert_items_follow_litm_alternating(context_pack.items)
    renderer_citation_roundtrip.assert_cite_ids_bijective_with_items(
        [i.model_dump(mode="json") for i in context_pack.items]
    )
