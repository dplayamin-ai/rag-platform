"""`enrich` 결정적 보강기 3종(F2-03, WP-203) 단위·통합 테스트.

무엇을 검증하는지: (1) `deterministic_prefix.assemble_texts`가 ADR-0029 §결정 예시 문장을 글자
그대로 재현하고 (a)~(d) 왕복 불변식을 지키는지, `DeterministicPrefixEnricher.enrich()`가
`acc[chunk_id]`에 3필드만 쓰고 50청크마다 `heartbeat`를 남기는지. (2) `korean_keywords`가 kiwipiepy
경로(NNG/NNP 추출·연속 결합)와 공백 폴백 경로(불용어·마스크 토큰 제외·가중치·정렬·`max_terms`·
`user_dict_entries` 중복 유지) 모두에서 §5.1 알고리즘대로 동작하는지, 비한국어 청크는 형태소 후보를
만들지 않는지(§4.3). (3) `derived_meta`가 한국어 점 표기 날짜를 ISO로, `제n조[의m][ 제k항]`을
법령명이 있을 때만 경로로 뽑고 없으면 생략하는지("추측 금지"). (4) 세 모듈을 순서대로 실행해 만든
`acc[chunk_id]`가 실제 `common_types.Enrichment`로 조립 가능한지(계약 적합성).
설계 근거: ADR-0029(결정적 3-텍스트 규칙), 04-pipelines/11 §4.3·§5.1(보강기 알고리즘), 계약
`common_types.Enrichment`(03-contracts).
픽스처 출처: ADR-0029 §결정 표의 예시 JSON(`㈜한빛 정보보호 지침` 문장), 04-pipelines/11 §5.1
알고리즘 설명. 그 외는 이 파일이 직접 구성한 최소 `Chunk`(계약 필드만으로 충분, 외부 샘플 불필요).
검증 계층: 1층. `tests/adapters/` 하위이므로 `conftest.py`가 `component` 마커를 붙인다.
"""

from __future__ import annotations

from typing import Any

import pytest

from rag_platform.adapters.enrich.derived_meta import DerivedMetaConfig, DerivedMetaEnricher
from rag_platform.adapters.enrich.deterministic_prefix import (
    DeterministicPrefixConfig,
    DeterministicPrefixEnricher,
    assemble_texts,
)
from rag_platform.adapters.enrich.korean_keywords import KoreanKeywordsConfig, KoreanKeywordsEnricher
from rag_platform.contracts import common_types as ct
from rag_platform.sdk.hashing import blake3_hex

#: `context_prefix.deterministic` 조인 구분자(U+203A) — RUF001 회피를 위해 `chr()`로 만든다
#: (structure_aware 청커 `_CONTEXT_PREFIX_SEP`와 같은 글자, ambiguous-character 리터럴 금지).
_SEP = f" {chr(0x203A)} "


class _FakeCtx:
    """세 모듈 모두 `heartbeat()` 외에는 쓰지 않는 최소 `StageContext` 대역."""

    def __init__(self) -> None:
        self.heartbeats: list[dict[str, Any]] = []

    def heartbeat(self, details: dict[str, Any]) -> None:
        self.heartbeats.append(dict(details))


def _hex(tag: str, length: int) -> str:
    return blake3_hex(tag)[:length]


def _chunk(
    *,
    tag: str = "a",
    text: str,
    lexical_text: str | None = None,
    deterministic: str = f"문서 제목{_SEP}제1장",
    heading_path: list[str] | None = None,
    lang: str = "ko",
) -> ct.Chunk:
    """테스트 전용 최소 `Chunk` 빌더 — 계약 필수 필드만 채운다(외부 샘플 불필요)."""
    block_id = _hex(tag, 32)
    span = ct.ChunkSpan(f"{block_id}:0-{block_id}:{len(text)}")
    block_ref = ct.BlockRef(
        block_id=block_id,
        element_path=f"/p[{tag}]",
        char_start=0,
        char_end=len(text),
        original_char_start=0,
        original_char_end=len(text),
        page=None,
        bbox=None,
    )
    return ct.Chunk(
        chunk_id=blake3_hex(f"{tag}:{text}"),
        span=span,
        item_kind=ct.ItemKind.text,
        level=ct.ChunkLevel.integer_0,
        parent_chunk_id=None,
        ordinal=0,
        text=text,
        lexical_text=lexical_text if lexical_text is not None else text,
        heading_path=heading_path if heading_path is not None else ["제1장"],
        block_refs=[block_ref],
        sentence_spans=[ct.SentenceSpan1([0, len(text)])],
        token_counts=ct.TokenCounts1({"hf:BAAI/bge-m3": len(text)}),
        lang=lang,
        context_prefix=ct.ContextPrefix(deterministic=deterministic, generated=None, generated_by=None),
        text_source=ct.BlockSource.text_layer,
        ocr_confidence_min=None,
        content_hash=blake3_hex(text),
    )


def _full_enrichment(bucket: dict[str, Any]) -> ct.Enrichment:
    """부분 누산기 `bucket`에 플랫폼 합성 기본값(엔티티·리스크·상태, F2-03 범위 밖)을 더해 조립한다."""
    return ct.Enrichment(
        embed_text=bucket["embed_text"],
        index_text=bucket["index_text"],
        strip_offsets=bucket["strip_offsets"],
        keywords=bucket.get("keywords", []),
        entities=[],
        relations=None,
        dates=bucket.get("dates"),
        law_refs=bucket.get("law_refs"),
        figure_caption=None,
        figure_table_markdown=None,
        hypothetical_questions=None,
        summary=None,
        risk_flags=[],
        risk_score=0.0,
        pii_entity_counts={},
        status=ct.EnrichStatus.complete,
    )


# --------------------------------------------------------------------------------------------
# deterministic_prefix
# --------------------------------------------------------------------------------------------


def test_assemble_texts_adr0029_example() -> None:
    """ADR-0029 §결정 예시 문장을 글자 그대로 재현한다(embed_text/index_text/strip_offsets)."""
    deterministic = f"㈜한빛 정보보호 지침{_SEP}제2장 운영{_SEP}제3조 절차"
    chunk = _chunk(
        text="제3조(절차) 정보보호 책임자는 매년 1회 위험평가를 실시한다.",
        deterministic=deterministic,
        heading_path=["제2장 운영", "제3조 절차"],
    )

    embed_text, index_text, strip_offsets = assemble_texts(chunk)

    assert embed_text == f"{deterministic}\n제3조(절차) 정보보호 책임자는 매년 1회 위험평가를 실시한다."
    nfkc_deterministic = f"(주)한빛 정보보호 지침{_SEP}제2장 운영{_SEP}제3조 절차"
    assert index_text == f"{nfkc_deterministic}\n제3조(절차) 정보보호 책임자는 매년 1회 위험평가를 실시한다."
    assert strip_offsets.text_start_in_embed == 30
    assert strip_offsets.text_start_in_index == 32


def test_assemble_texts_roundtrip_invariants() -> None:
    """ADR-0029 준수 확인표 (a)~(d): embed_text/index_text 복원, 접두어 경계, text가 접두어를 포함하지 않음."""
    chunk = _chunk(text="본문 내용입니다.", deterministic=f"제목{_SEP}섹션")

    embed_text, index_text, strip_offsets = assemble_texts(chunk)
    lexical_len = len(chunk.lexical_text)
    index_end = strip_offsets.text_start_in_index + lexical_len

    assert embed_text[strip_offsets.text_start_in_embed :] == chunk.text
    assert index_text[strip_offsets.text_start_in_index : index_end] == chunk.lexical_text
    assert embed_text[: strip_offsets.text_start_in_embed] == chunk.context_prefix.deterministic + "\n"
    assert not chunk.text.startswith(chunk.context_prefix.deterministic)
    assert chunk.context_prefix.deterministic not in chunk.text


def test_assemble_texts_builds_valid_enrichment() -> None:
    """조립 결과가 실제 `common_types.Enrichment`로 구성 가능하다(계약 적합성)."""
    chunk = _chunk(text="계약 적합성 확인용 문장.", deterministic=f"제목{_SEP}섹션")
    embed_text, index_text, strip_offsets = assemble_texts(chunk)

    enrichment = _full_enrichment({"embed_text": embed_text, "index_text": index_text, "strip_offsets": strip_offsets})

    assert enrichment.embed_text == embed_text
    assert enrichment.strip_offsets.text_start_in_embed == strip_offsets.text_start_in_embed


async def test_deterministic_prefix_enricher_writes_only_own_fields() -> None:
    """`enrich()`는 `acc[chunk_id]`에 `embed_text`/`index_text`/`strip_offsets`만 쓴다."""
    enricher = DeterministicPrefixEnricher()
    chunks = [_chunk(tag="a", text="첫 번째 문장."), _chunk(tag="b", text="두 번째 문장.")]
    acc: dict[str, dict[str, Any]] = {}

    await enricher.enrich(chunks, _FakeCtx(), acc)

    for chunk in chunks:
        bucket = acc[chunk.chunk_id.root]
        assert set(bucket) == {"embed_text", "index_text", "strip_offsets"}


async def test_deterministic_prefix_enricher_heartbeats_every_50_chunks() -> None:
    """50청크마다 `ctx.heartbeat({"chunk_offset": ...})`를 호출한다(04-pipelines/11 §2.2)."""
    enricher = DeterministicPrefixEnricher()
    chunks = [_chunk(tag=f"c{i:03d}", text=f"문장 {i}.") for i in range(101)]
    ctx = _FakeCtx()

    await enricher.enrich(chunks, ctx, {})

    assert ctx.heartbeats == [{"chunk_offset": 50}, {"chunk_offset": 100}]


def test_deterministic_prefix_capabilities_and_fingerprint() -> None:
    """`capabilities()`는 `in_process`·재개 지원·`determinism=pure`, `fingerprint()`는 안정적인 hex64다."""
    enricher = DeterministicPrefixEnricher(DeterministicPrefixConfig())

    caps = enricher.capabilities()
    fingerprint = enricher.fingerprint()

    assert caps.isolation_modes == [ct.IsolationMode.in_process]
    assert caps.supports_resumable is True
    assert caps.extra == {"determinism": "pure"}
    assert len(fingerprint) == 64
    assert fingerprint == DeterministicPrefixEnricher().fingerprint()


# --------------------------------------------------------------------------------------------
# korean_keywords
# --------------------------------------------------------------------------------------------


async def test_korean_keywords_kiwi_merges_compound_nouns() -> None:
    """kiwipiepy 경로: 연속 NNG를 복합명사로 결합하고 빈도로 가중한다(§5.1 규칙 2~3)."""
    pytest.importorskip("kiwipiepy")
    enricher = KoreanKeywordsEnricher(use_kiwi=True)
    chunk = _chunk(
        tag="k",
        text="정보보호 책임자는 매년 위험평가를 실시한다. 위험평가는 중요하다.",
    )
    acc: dict[str, dict[str, Any]] = {}

    await enricher.enrich([chunk], _FakeCtx(), acc)

    keywords = acc[chunk.chunk_id.root]["keywords"]
    by_term = {kw.term: kw for kw in keywords}
    assert "정보보호" in by_term  # 정보+보호가 결합됨(분리되지 않음)
    assert "위험평가" in by_term
    assert by_term["위험평가"].weight == 1.0  # 2회 등장 = max_tf
    assert by_term["정보보호"].weight == pytest.approx(0.5)  # 1회 등장
    assert all(kw.source == ct.KeywordSource.analyzer_nng for kw in keywords)
    weights = [kw.weight for kw in keywords]
    assert weights == sorted(weights, reverse=True)


async def test_korean_keywords_whitespace_fallback_filters_and_sorts() -> None:
    """공백 폴백: 불용어·마스크 토큰 제외, `weight=tf/max_tf`, `weight` 내림차순·`term` 오름차순 정렬."""
    enricher = KoreanKeywordsEnricher(use_kiwi=False)
    chunk = _chunk(tag="w", text="placeholder", lexical_text="이것은 테스트 것 <PERSON> 문서 문서")
    acc: dict[str, dict[str, Any]] = {}

    await enricher.enrich([chunk], _FakeCtx(), acc)

    keywords = acc[chunk.chunk_id.root]["keywords"]
    assert [(kw.term, kw.weight, kw.source) for kw in keywords] == [
        ("문서", 1.0, ct.KeywordSource.analyzer_nng),
        ("이것은", 0.5, ct.KeywordSource.analyzer_nng),
        ("테스트", 0.5, ct.KeywordSource.analyzer_nng),
    ]


async def test_korean_keywords_skips_non_korean_language() -> None:
    """비한국어 청크는 형태소·폴백 후보를 만들지 않는다(§4.3)."""
    enricher = KoreanKeywordsEnricher(use_kiwi=False)
    chunk = _chunk(tag="e", text="placeholder", lexical_text="hello world test", lang="en")
    acc: dict[str, dict[str, Any]] = {}

    await enricher.enrich([chunk], _FakeCtx(), acc)

    assert acc[chunk.chunk_id.root]["keywords"] == []


async def test_korean_keywords_user_dict_keeps_duplicate_term_different_source() -> None:
    """`user_dict` 표층형 일치는 형태소 결과와 같은 term이어도 별도 항목으로 유지된다(§5.1 규칙 4)."""
    config = KoreanKeywordsConfig(user_dict_entries=("행정안전부",))
    enricher = KoreanKeywordsEnricher(config, use_kiwi=False)
    chunk = _chunk(tag="u", text="placeholder", lexical_text="행정안전부 고시")
    acc: dict[str, dict[str, Any]] = {}

    await enricher.enrich([chunk], _FakeCtx(), acc)

    keywords = acc[chunk.chunk_id.root]["keywords"]
    assert [(kw.term, kw.source) for kw in keywords] == [
        ("고시", ct.KeywordSource.analyzer_nng),
        ("행정안전부", ct.KeywordSource.analyzer_nng),
        ("행정안전부", ct.KeywordSource.user_dict),
    ]


async def test_korean_keywords_max_terms_caps_output() -> None:
    """`max_terms` 절단 — 가장 낮은 가중치/후순위 항목부터 잘린다."""
    config = KoreanKeywordsConfig(max_terms=1)
    enricher = KoreanKeywordsEnricher(config, use_kiwi=False)
    chunk = _chunk(tag="m", text="placeholder", lexical_text="가나다 마바사 아자차")
    acc: dict[str, dict[str, Any]] = {}

    await enricher.enrich([chunk], _FakeCtx(), acc)

    keywords = acc[chunk.chunk_id.root]["keywords"]
    assert len(keywords) == 1
    assert keywords[0].term == "가나다"  # 동률 가중치는 term 오름차순


def test_korean_keywords_fingerprint_stable_for_same_engine() -> None:
    """같은 `use_kiwi=False`(같은 config·엔진)이면 `fingerprint()`가 안정적이다."""
    first = KoreanKeywordsEnricher(use_kiwi=False)
    second = KoreanKeywordsEnricher(use_kiwi=False)

    assert first.capabilities().extra == {"determinism": "pure"}
    assert first.fingerprint() == second.fingerprint()


def test_korean_keywords_fingerprint_differs_by_engine() -> None:
    """`fingerprint()`는 실제 사용 엔진(analyzer_id)을 반영한다 — kiwi 유무로 값이 달라진다."""
    pytest.importorskip("kiwipiepy")
    whitespace_enricher = KoreanKeywordsEnricher(use_kiwi=False)
    kiwi_enricher = KoreanKeywordsEnricher(use_kiwi=True)

    assert whitespace_enricher.fingerprint() != kiwi_enricher.fingerprint()


# --------------------------------------------------------------------------------------------
# derived_meta
# --------------------------------------------------------------------------------------------


async def test_derived_meta_extracts_korean_dot_dates() -> None:
    """`"YYYY. M. D."`·`"YYYY.M.D"` 형식을 ISO로, 중복은 제거하고, 유효하지 않은 날짜는 건너뛴다."""
    enricher = DerivedMetaEnricher()
    chunk = _chunk(
        tag="d",
        text="이 정책은 2026. 9. 23. 부터 시행한다. 개정일은 2026.09.23 이며 2026. 13. 40. 은 오기다.",
        deterministic=f"샘플 문서{_SEP}제1장",
    )
    acc: dict[str, dict[str, Any]] = {}

    await enricher.enrich([chunk], _FakeCtx(), acc)

    assert acc[chunk.chunk_id.root]["dates"] == [ct.Date("2026-09-23")]


async def test_derived_meta_builds_law_refs_with_clause_when_law_name_found() -> None:
    """법령명(제목 접미사 패턴)이 있으면 `{법령명}/제n조/제m항` 경로를 원문자·아라비아 항 모두에서 뽑는다."""
    enricher = DerivedMetaEnricher()
    chunk = _chunk(
        tag="l",
        text="제3조(절차) 정보보호 책임자는 매년 1회 위험평가를 실시한다. ① 위험평가는 문서로 남긴다.",
        deterministic=f"㈜한빛 정보보호 지침{_SEP}제2장 운영{_SEP}제3조 절차",
        heading_path=["제2장 운영", "제3조 절차"],
    )
    acc: dict[str, dict[str, Any]] = {}

    await enricher.enrich([chunk], _FakeCtx(), acc)

    assert acc[chunk.chunk_id.root]["law_refs"] == ["㈜한빛 정보보호 지침/제3조/제1항"]


async def test_derived_meta_multiple_articles_window_clause_to_next_article() -> None:
    """조 경계 창(다음 조 시작 전까지)에서만 항을 찾는다 — 제1조는 항 없음, 제2조는 있음."""
    enricher = DerivedMetaEnricher()
    chunk = _chunk(
        tag="m",
        text="제1조 목적 이 지침은 절차를 정한다. 제2조(정의) ① 이 조에서 사용하는 용어는 다음과 같다.",
        deterministic=f"가나다 규정{_SEP}총칙",
    )
    acc: dict[str, dict[str, Any]] = {}

    await enricher.enrich([chunk], _FakeCtx(), acc)

    assert acc[chunk.chunk_id.root]["law_refs"] == ["가나다 규정/제1조", "가나다 규정/제2조/제1항"]


async def test_derived_meta_sub_article_format() -> None:
    """`제n조의m` 하위 조항 표기를 지원한다."""
    enricher = DerivedMetaEnricher()
    chunk = _chunk(
        tag="s",
        text="부칙 제5조의2(경과조치) 이 조는 시행 전 사안에 대해 제3항을 준용한다.",
        deterministic=f"샘플 시행규칙{_SEP}부칙",
    )
    acc: dict[str, dict[str, Any]] = {}

    await enricher.enrich([chunk], _FakeCtx(), acc)

    assert acc[chunk.chunk_id.root]["law_refs"] == ["샘플 시행규칙/제5조의2/제3항"]


async def test_derived_meta_omits_law_refs_when_law_name_not_found() -> None:
    """법령명 추정 실패 시 조항이 텍스트에 있어도 `law_refs`를 만들지 않는다(추측 금지)."""
    enricher = DerivedMetaEnricher()
    chunk = _chunk(tag="n", text="제5조 아무 조항.", deterministic=f"일반 문서{_SEP}섹션")
    acc: dict[str, dict[str, Any]] = {}

    await enricher.enrich([chunk], _FakeCtx(), acc)

    assert acc[chunk.chunk_id.root]["law_refs"] is None


async def test_derived_meta_omits_both_fields_when_nothing_found() -> None:
    """날짜·조항이 전혀 없으면 두 필드 모두 `None`(빈 배열이 아니라 생략, §5.4 N)."""
    enricher = DerivedMetaEnricher()
    chunk = _chunk(tag="z", text="특별한 것이 없는 문장입니다.", deterministic=f"일반 문서{_SEP}섹션")
    acc: dict[str, dict[str, Any]] = {}

    await enricher.enrich([chunk], _FakeCtx(), acc)

    bucket = acc[chunk.chunk_id.root]
    assert bucket["dates"] is None
    assert bucket["law_refs"] is None


def test_derived_meta_capabilities_and_fingerprint() -> None:
    """`capabilities()`/`fingerprint()`가 결정적 보강기 공통 계약을 만족한다."""
    enricher = DerivedMetaEnricher(DerivedMetaConfig())

    assert enricher.capabilities().extra == {"determinism": "pure"}
    assert len(enricher.fingerprint()) == 64


# --------------------------------------------------------------------------------------------
# 통합: 세 모듈 → 완전한 Enrichment
# --------------------------------------------------------------------------------------------


async def test_chain_assembles_valid_enrichment() -> None:
    """순서 1·2·4를 차례로 실행해 채운 `acc[chunk_id]`가 실제 `Enrichment`로 조립된다."""
    chunk = _chunk(
        tag="i",
        text="제3조(절차) 정보보호 책임자는 매년 1회 위험평가를 실시한다.",
        deterministic=f"㈜한빛 정보보호 지침{_SEP}제2장 운영{_SEP}제3조 절차",
        heading_path=["제2장 운영", "제3조 절차"],
    )
    acc: dict[str, dict[str, Any]] = {}
    ctx = _FakeCtx()

    await DeterministicPrefixEnricher().enrich([chunk], ctx, acc)
    await KoreanKeywordsEnricher(use_kiwi=False).enrich([chunk], ctx, acc)
    await DerivedMetaEnricher().enrich([chunk], ctx, acc)

    bucket = acc[chunk.chunk_id.root]
    enrichment = _full_enrichment(bucket)

    assert enrichment.status == ct.EnrichStatus.complete
    assert enrichment.risk_score == 0.0
    assert enrichment.entities == []
    # 공백 폴백은 조사를 분리하지 않으므로("위험평가를" 그대로) 형태소 결과("위험평가")와 다르다.
    assert any(kw.term == "위험평가를" for kw in enrichment.keywords)
    assert enrichment.law_refs == ["㈜한빛 정보보호 지침/제3조"]
