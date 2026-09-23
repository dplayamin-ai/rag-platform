"""`enricher.korean_keywords` — 형태소 키워드(`Enrichment.keywords[]`)를 추출한다.

역할: `enrich` 체인(04-pipelines/11 §2.1 표) 순서 2 — `Chunk.lexical_text`에서 일반명사(NNG)·고유명사
(NNP) 원형과 사용자 사전 표제어를 뽑아 `keywords[]`를 채운다(F2-03, WP-203).
설계 근거: 04-pipelines/11 §5(`keywords` 추출)·§5.1(`enricher.korean_keywords` 알고리즘)·§4.3(언어별
처리), 바이블 §5.4 `Enrichment.keywords`·§5.7 `KeywordSource`; ADR-0021(Kiwi 승격·mecab-ko 임시).
구성: `KoreanKeywordsConfig` — `config_schema`(`max_terms`/`min_term_chars`/`stopwords_ref`/
`compound_join`/`user_dict_entries`); `KoreanKeywordsEnricher` — `plugin_id`/`config_schema`/
`capabilities()`/`fingerprint()`/`enrich()`, kiwipiepy 가용성에 따라 형태소 후보 또는 공백 토큰 폴백.
불변식·주의: `kiwipiepy`(B등급 LGPL, `pyproject.toml` `kiwi` extra opt-in)는 여기서만 임포트하고
미설치 시 `ImportError`만 잡아 폴백한다. 비한국어(`lang`이 `ko`/`ko-*`가 아님) 청크는 형태소 후보를
만들지 않는다(§4.3). `acc`에는 `keywords` 키만 쓴다.
검증 계층: 1층(여기서 검증) — `tests/adapters/enrich/test_enrich.py`. kiwipiepy 모델은 패키지에 이미
번들되어 있어(네트워크 다운로드 없음) `needs_model` 해당 없음.
"""

from __future__ import annotations

import json
import re
import unicodedata
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field

from rag_platform.contracts import common_types as ct
from rag_platform.sdk.hashing import hash_of

if TYPE_CHECKING:
    from collections.abc import Sequence

    from rag_platform.adapters.enrich.deterministic_prefix import EnrichmentAccumulator

__all__ = ["PLUGIN_VERSION", "KoreanKeywordsConfig", "KoreanKeywordsEnricher"]

PLUGIN_VERSION = "0.1.0"

#: 04-pipelines/11 §5.1 규칙 2 초안 불용어 목록.
_STOPWORDS = frozenset({"것", "등", "수", "때", "경우", "관련", "해당", "다음", "이상", "이하", "내용", "사항"})
#: PII 마스킹 자리표시자(`<PERSON>` 등, §5.1 규칙 2) — 형태소·폴백 후보 모두에서 제외한다.
_MASK_TOKEN_RE = re.compile(r"^<[A-Z_]+>$")
#: kiwipiepy가 NNG/NNP로 태그하는 형태소(연속 결합 대상, §5.1 규칙 2).
_NOUN_TAGS = frozenset({"NNG", "NNP"})
_HEARTBEAT_EVERY = 50


class KoreanKeywordsConfig(BaseModel):
    """`enricher.korean_keywords`의 설정 스키마(04-pipelines/11 §5.1 초안 `config_schema` 그대로).

    `stopwords_ref`는 스키마 자리만 있고 이 WP는 로딩하지 않는다(DEFERRED — `ctx.artifacts` 또는 셸
    사전 로딩 배선 필요). `user_dict_entries`는 실제 `UserDictEntry`(동의어·`dictionary_hash`) 배선
    전 간이 표층형 목록이다(DEFERRED, WP-203 open issue).
    """

    model_config = ConfigDict(extra="forbid")

    max_terms: int = Field(default=64, ge=1, description="청크당 keywords[] 상한(§5.1 규칙 5)")
    min_term_chars: int = Field(default=2, ge=1, description="1글자 명사 제외 기준(§5.1 규칙 2)")
    stopwords_ref: ct.ArtifactRef | None = Field(default=None, description="DEFERRED — 로딩 미구현, 내장 목록만 사용")
    compound_join: bool = Field(default=True, description="연속 NNG/NNP 결합(복합명사) 여부(§5.1 규칙 2)")
    user_dict_entries: tuple[str, ...] = Field(
        default_factory=tuple, description="DEFERRED 간이 사용자 사전 표층형 목록(§5.1 규칙 4)"
    )


def _kiwi_candidates(lexical_text: str, kiwi: Any) -> list[tuple[str, ct.KeywordSource]]:
    """Kiwipiepy 토큰 스트림에서 NNG/NNP 후보를 뽑고 연속 태그를 복합명사로 결합한다(§5.1 규칙 2)."""
    tokens = list(kiwi.tokenize(lexical_text))
    candidates: list[tuple[str, ct.KeywordSource]] = []
    i = 0
    total = len(tokens)
    while i < total:
        token = tokens[i]
        if token.tag not in _NOUN_TAGS:
            i += 1
            continue
        form = token.form
        is_proper = token.tag == "NNP"
        end = token.start + token.len
        j = i + 1
        while j < total and tokens[j].tag in _NOUN_TAGS and tokens[j].start == end:
            form += tokens[j].form
            is_proper = is_proper or tokens[j].tag == "NNP"
            end = tokens[j].start + tokens[j].len
            j += 1
        source = ct.KeywordSource.analyzer_nnp if is_proper else ct.KeywordSource.analyzer_nng
        candidates.append((form, source))
        i = j
    return candidates


def _whitespace_candidates(lexical_text: str) -> list[tuple[str, ct.KeywordSource]]:
    """Kiwipiepy 미설치 폴백 — 공백 토큰을 후보로 삼는다(근사치, `analyzer_nng`로 태그, WP-203 open issue)."""
    return [(token, ct.KeywordSource.analyzer_nng) for token in lexical_text.split()]


def _filter_and_weight(candidates: list[tuple[str, ct.KeywordSource]], *, min_term_chars: int) -> list[ct.Keyword]:
    """§5.1 규칙 2~3: 정규화·필터 후 `(term, source)` 단위로 집계해 `weight = tf/max_tf`를 매긴다."""
    normalized: list[tuple[str, ct.KeywordSource]] = []
    for raw_term, source in candidates:
        term = unicodedata.normalize("NFKC", raw_term).strip()
        if len(term) < min_term_chars or term in _STOPWORDS or _MASK_TOKEN_RE.match(term):
            continue
        normalized.append((term, source))
    if not normalized:
        return []
    counts: dict[tuple[str, ct.KeywordSource], int] = {}
    for key in normalized:
        counts[key] = counts.get(key, 0) + 1
    max_tf = max(counts.values())
    return [ct.Keyword(term=term, weight=tf / max_tf, source=source) for (term, source), tf in counts.items()]


def _user_dict_keywords(lexical_text: str, entries: tuple[str, ...]) -> list[ct.Keyword]:
    """§5.1 규칙 4의 간이 재현 — 표층형이 `lexical_text`에 나타나면 `weight=1.0, source=user_dict`."""
    keywords: list[ct.Keyword] = []
    for surface in entries:
        term = unicodedata.normalize("NFKC", surface).strip()
        if term and term in lexical_text:
            keywords.append(ct.Keyword(term=term, weight=1.0, source=ct.KeywordSource.user_dict))
    return keywords


class KoreanKeywordsEnricher:
    """`enricher.korean_keywords` — 체인 순서 2(04-pipelines/11 §2.1 표)."""

    plugin_id = "enricher.korean_keywords"
    config_schema = KoreanKeywordsConfig
    requires_lineage: tuple[str, ...] = ()

    def __init__(self, config: KoreanKeywordsConfig | None = None, *, use_kiwi: bool | None = None) -> None:
        """설정을 고정한다.

        Args:
            config: `config_schema` 인스턴스(없으면 기본값).
            use_kiwi: 테스트용 오버라이드. `None`(기본)이면 `kiwipiepy` 가용성을 자동 감지하고,
                `True`면 강제 사용(미설치 시 `ImportError` 그대로 전파), `False`면 항상 공백 폴백.
        """
        self.config = config or KoreanKeywordsConfig()
        self._use_kiwi_override = use_kiwi
        self._kiwi: Any | None = None
        self._kiwi_loaded = False
        self._analyzer_engine_id = "whitespace:1.0.0:none"

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
        """`H("producer", plugin_id, plugin_version, config_hash, "", analyzer_id)`(바이블 §6.2)."""
        self._resolve_kiwi()
        return hash_of("producer", self.plugin_id, PLUGIN_VERSION, self.config_hash(), "", self._analyzer_engine_id)

    def _resolve_kiwi(self) -> Any | None:
        """`use_kiwi` 오버라이드 또는 자동 감지로 kiwipiepy `Kiwi` 인스턴스를 지연 생성·캐싱한다.

        `common_types.AnalyzerId` 철자(`{engine}:{version}:{dictionary}`)의 실제 사용 엔진도
        `self._analyzer_engine_id`에 함께 기록해 `fingerprint()`가 재사용한다.
        """
        if self._use_kiwi_override is False:
            return None
        if not self._kiwi_loaded:
            self._kiwi_loaded = True
            if self._use_kiwi_override is True:
                import kiwipiepy  # noqa: PLC0415 - opt-in extra, 강제 사용 시 ImportError 그대로 전파

                self._kiwi = kiwipiepy.Kiwi()
                self._analyzer_engine_id = f"kiwi:{kiwipiepy.__version__}:none"
            else:
                try:
                    import kiwipiepy  # noqa: PLC0415 - opt-in extra(B등급 LGPL), 미설치 시 폴백
                except ImportError:
                    self._kiwi = None
                else:
                    self._kiwi = kiwipiepy.Kiwi()
                    self._analyzer_engine_id = f"kiwi:{kiwipiepy.__version__}:none"
        return self._kiwi

    async def enrich(
        self,
        chunks: Sequence[ct.Chunk],
        ctx: Any,
        acc: EnrichmentAccumulator,
    ) -> None:
        """청크마다 `keywords[]`를 계산해 `acc[chunk_id]["keywords"]`에 쓴다.

        Args:
            chunks: 이 세트의 청크(리프·부모 모두; §5.1 규칙 5는 `level=1`에도 계산하라고 명시한다).
            ctx: `StageContext`(`heartbeat` 외에는 쓰지 않는다).
            acc: `chunk_id(str) -> 부분 Enrichment 필드 매핑` 누산기.
        """
        kiwi = self._resolve_kiwi()
        for index, chunk in enumerate(chunks):
            lang = chunk.lang.root
            candidates: list[tuple[str, ct.KeywordSource]] = []
            if lang == "ko" or lang.startswith("ko-"):
                candidates = (
                    _kiwi_candidates(chunk.lexical_text, kiwi)
                    if kiwi is not None
                    else _whitespace_candidates(chunk.lexical_text)
                )
            analyzer_keywords = _filter_and_weight(candidates, min_term_chars=self.config.min_term_chars)
            dict_keywords = _user_dict_keywords(chunk.lexical_text, self.config.user_dict_entries)
            combined = [*analyzer_keywords, *dict_keywords]
            combined.sort(key=lambda kw: (-kw.weight, kw.term))
            bucket = acc.setdefault(chunk.chunk_id.root, {})
            bucket["keywords"] = combined[: self.config.max_terms]
            if (index + 1) % _HEARTBEAT_EVERY == 0:
                ctx.heartbeat({"chunk_offset": index + 1})
