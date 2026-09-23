---
title: "WP-203 enrich-deterministic"
status: done
owner: implementation
---

# WP-203 enrich-deterministic (F2-03)

## 목표

`enrich` 스테이지(바이블 §4.2 `enrich` 행)의 결정적(규칙 기반, LLM 미사용) 보강기 체인 중 3종을
구현한다: 체인 순서 1 `enricher.deterministic_prefix`(ADR-0029 3-텍스트 조립: `embed_text`/
`index_text`/`strip_offsets`), 순서 2 `enricher.korean_keywords`(형태소 키워드, kiwipiepy extra
있으면 NNG/NNP, 없으면 공백 토큰 폴백), 순서 4 `enricher.derived_meta`(날짜·조항 파생 메타). 순서 3
`enricher.gliner2_entities`와 순서 5 플랫폼 합성(pii·risk 집계, `status`)·전체를 묶는
`enricher.pipeline`(Stage 5멤버 `run()`, `EnrichedChunkSet` 조립)은 이 WP 범위 밖(DEFERRED, 별도 WP).

## 파일

- `src/rag_platform/adapters/enrich/deterministic_prefix.py` — `assemble_texts(chunk)`(순수 함수,
  `embed_text`/`index_text`/`StripOffsets` 계산), `DeterministicPrefixConfig`, `DeterministicPrefixEnricher`,
  `EnrichmentAccumulator` 타입 별칭(세 모듈이 공유하는 `acc` 모양).
- `src/rag_platform/adapters/enrich/korean_keywords.py` — `KoreanKeywordsConfig`,
  `KoreanKeywordsEnricher`(kiwipiepy 있으면 NNG/NNP 형태소 후보 + 연속 복합명사 결합, 없으면 공백
  토큰 폴백; 사용자 사전은 `config.user_dict_entries`로 받는 간이 표층형 매칭).
- `src/rag_platform/adapters/enrich/derived_meta.py` — `DerivedMetaConfig`, `DerivedMetaEnricher`(정규식
  기반 한국어 날짜 `"YYYY. M. D."` → ISO, `제n조[의m][ 제k항]` 법령 조항 추출; 법령명은
  `Chunk.context_prefix.deterministic`의 첫 `" › "` 세그먼트가 법령명 접미사 패턴이면 사용).
- `tests/adapters/enrich/test_enrich.py` — 세 모듈 단위·통합 테스트.

## 시그니처

```python
# deterministic_prefix.py
EnrichmentAccumulator = MutableMapping[str, MutableMapping[str, Any]]

def assemble_texts(chunk: ct.Chunk) -> tuple[str, str, ct.StripOffsets]: ...

class DeterministicPrefixConfig(BaseModel): ...  # 필드 없음(조립식은 ADR-0029 고정)

class DeterministicPrefixEnricher:
    plugin_id = "enricher.deterministic_prefix"
    config_schema = DeterministicPrefixConfig
    def capabilities(self) -> ct.Capabilities: ...
    def fingerprint(self) -> str: ...
    async def enrich(self, chunks: Sequence[ct.Chunk], ctx: Any, acc: EnrichmentAccumulator) -> None: ...

# korean_keywords.py
class KoreanKeywordsConfig(BaseModel):
    max_terms: int = 64
    min_term_chars: int = 2
    stopwords_ref: ct.ArtifactRef | None = None
    compound_join: bool = True
    user_dict_entries: tuple[str, ...] = ()

class KoreanKeywordsEnricher:
    plugin_id = "enricher.korean_keywords"
    config_schema = KoreanKeywordsConfig
    def __init__(self, config=None, *, use_kiwi: bool | None = None) -> None: ...
    def capabilities(self) -> ct.Capabilities: ...
    def fingerprint(self) -> str: ...
    async def enrich(self, chunks, ctx, acc: EnrichmentAccumulator) -> None: ...

# derived_meta.py
class DerivedMetaConfig(BaseModel): ...  # 필드 없음

class DerivedMetaEnricher:
    plugin_id = "enricher.derived_meta"
    config_schema = DerivedMetaConfig
    def capabilities(self) -> ct.Capabilities: ...
    def fingerprint(self) -> str: ...
    async def enrich(self, chunks, ctx, acc: EnrichmentAccumulator) -> None: ...
```

## 입출력 계약 발췌 (철자 정본)

- `common_types.Chunk{chunk_id, text, lexical_text, heading_path, numbering_path?, context_prefix
  {deterministic, generated, generated_by}, lang, content_hash, ...}` — `text`·`lexical_text`·
  `context_prefix`는 불변(K1·K2).
- `common_types.Enrichment{embed_text, index_text, strip_offsets{text_start_in_embed,
  text_start_in_index}, keywords[{term, weight, source}], entities[], dates?, law_refs?,
  risk_flags, risk_score, pii_entity_counts, status}` — 이 WP는 `embed_text`/`index_text`/
  `strip_offsets`/`keywords`/`dates`/`law_refs`만 채운다.
- `common_types.KeywordSource ∈ {analyzer_nng, analyzer_nnp, sparse_top, user_dict}`;
  `common_types.EnrichStatus ∈ {complete, partial}`; `common_types.Date` 패턴 `YYYY-MM-DD`.
- 조립식(ADR-0029, G 없음 — LLM 보강 기본 꺼짐이라 이 WP는 항상 G 슬롯 생략): `embed_text =
  deterministic + "\n" + text`, `index_text = NFKC(deterministic) + "\n" + lexical_text`,
  `strip_offsets = {len(deterministic)+1, len(NFKC(deterministic))+1}`(코드포인트).
- 04-pipelines/11 §5.1 `enricher.korean_keywords` 알고리즘: NNG/NNP 후보 → 연속 결합(복합명사) →
  1글자·SN/SW·마스크 토큰(`^<[A-Z_]+>$`)·불용어(것,등,수,때,경우,관련,해당,다음,이상,이하,내용,사항)
  제외 → `weight = tf/max_tf` → `weight` 내림차순·`term` 오름차순 → `max_terms` 절단.

## 불변식·금지

- `Chunk.text`·`lexical_text`·`context_prefix`·`chunk_id`·`content_hash`를 변경하지 않는다(K1·K2);
  세 모듈 모두 순수 함수(무작위·시각·I/O 없음), `ctx`는 `heartbeat`(50청크마다)만 호출한다.
- `enrich()`는 `acc[str(chunk.chunk_id)]`에 **자기 필드만** 쓴다(04-pipelines/11 §2.2). `run()`은
  구현하지 않는다 — 아직 없는 `enricher.pipeline` 합성 스테이지(Stage 5멤버, `EnrichedChunkSet`
  조립)의 책임이며 이 WP 범위 밖.
- `korean_keywords`는 `sdk.ports.KoreanAnalyzer`(POS 태그 없는 `tokenize() -> tuple[str,...]`)를
  거치지 않고 `kiwipiepy`를 직접 임포트한다(POS 태그가 알고리즘에 필수) — `pyproject.toml`의
  `kiwi` extra(B등급 LGPL, opt-in) 규약을 따르며 미설치 시 `ImportError`를 잡아 공백 토큰 폴백으로
  내려간다(모듈을 손대지 않음).
- `derived_meta`는 04-pipelines/11 §4.1이 정한 "`NormalizedDocument.derived_meta.entities_normalized[]`
  투영" 대신 `Chunk.text`/`context_prefix.deterministic`에 대한 자체 정규식 추출을 쓴다 — 설계 갭이며
  아래 DEFERRED·open_issues에 기록.
- StageError 코드는 미사용(이 세 모듈은 실패하지 않는다 — 입력이 계약을 만족하면 항상 성공).

## 단계

1. `deterministic_prefix.assemble_texts`: `context_prefix.deterministic`을 그대로(재계산 없이) 읽어
   `embed_text`/`index_text`/`strip_offsets` 조립.
2. `korean_keywords`: 언어 게이트(`lang` `ko`/`ko-*`만 형태소 후보 생성) → kiwipiepy 가용성 판정
   (생성자 `use_kiwi` 오버라이드 → 자동 감지) → NNG/NNP 후보(연속 결합) 또는 공백 폴백(`analyzer_nng`로
   태그, 근사치) → 필터·가중치 → `user_dict_entries` 표층형 매칭(`weight=1.0`) 병합 → 정렬·절단.
3. `derived_meta`: 정규식으로 `"YYYY. M. D."` 날짜 스캔(`datetime.date`로 유효성 검사) → ISO 정렬;
   `제n조[의m]` 스캔 → 다음 조 앞까지 창에서 `제k항` 또는 원문자 `①`–`⑩`(1~10) 탐색 → 법령명(
   `context_prefix.deterministic`의 첫 `" › "` 세그먼트가 법령 접미사 패턴일 때만) 접두 → 못 찾으면
   생략(추측 금지).
4. 세 모듈 모두 50청크마다 `ctx.heartbeat({"chunk_offset": i})` 호출(04-pipelines/11 §2.2 재개 행).

## 테스트(파일·케이스)

`tests/adapters/enrich/test_enrich.py`:
- `assemble_texts`: ADR-0029 예시 문장으로 (a)~(d) 불변식(embed_text 복원, index_text 복원,
  `strip_offsets` 접두어 경계, `not text.startswith(deterministic)`) 골든 벡터 검증 + 실제
  `common_types.Enrichment` 생성으로 스키마 적합성 확인.
- `korean_keywords`: (1) `use_kiwi=True`로 실제 kiwipiepy 경로 — NNG/NNP 추출·복합명사 결합·불용어/
  마스크 토큰 제외·정렬·`max_terms` 절단. (2) `use_kiwi=False`로 공백 폴백 경로. (3) 비한국어 청크는
  형태소 후보 0개(§4.3 게이트). (4) `user_dict_entries` 매칭이 `source=user_dict, weight=1.0`.
- `derived_meta`: (1) "2026. 9. 23." → `["2026-09-23"]`. (2) 법령명 있는 heading("...지침" 접미사) +
  "제3조(절차)... ① ..." → `law_refs`에 조·항 경로. (3) 법령명 추정 실패 시 `law_refs=None`(추측 금지).
  (4) 날짜·조항 모두 없으면 두 필드 `None`.
- 통합: 세 모듈을 순서대로 실행해 하나의 `acc[chunk_id]`를 채우고, 나머지(엔티티·리스크 등) 기본값을
  더해 `common_types.Enrichment`를 실제로 구성 — 계약 적합성(§5.4) 최종 확인.

## 완료 기준

`uv run pytest -q tests/adapters/enrich/test_enrich.py` 전부 통과, `uv run ruff check
src/rag_platform/adapters/enrich/deterministic_prefix.py src/rag_platform/adapters/enrich/korean_keywords.py
src/rag_platform/adapters/enrich/derived_meta.py tests/adapters/enrich/test_enrich.py` 통과. mypy는
배치 검증자가 별도 실행.

## 검증 계층·DEFERRED

1층(여기서 검증) — 순수 함수, 외부 자원 없음. kiwipiepy는 `kiwipiepy-model`이 이미 로컬 wheel에
번들되어 있어(런타임 네트워크 다운로드 없음) `needs_model`/`needs_network` 해당 없음.

- DEFERRED: `enricher.gliner2_entities`(체인 순서 3), 플랫폼 합성(pii·risk 집계·`status`, 순서 5),
  `enricher.pipeline`(Stage 5멤버 `run()`, `EnrichedChunkSet` 조립·`enricher_fingerprint`·`stats`) —
  모두 별도 WP(F2 배치 후속).
- DEFERRED: `derived_meta`가 문서(04-pipelines/11 §4.1) 정본 경로인
  `NormalizedDocument.derived_meta.entities_normalized[]` 투영 대신 자체 정규식 추출을 쓴다 — N12
  `derived_meta` 생산이 WP-106(normalize)에서 이미 DEFERRED였기 때문(업스트림 부재). `enrich`가
  `requires_lineage=("NormalizedDocument",)`를 얻고 N12가 구현되면, 투영 우선·정규식 폴백으로
  재작성해야 한다(open_issues 참조).
- DEFERRED: `korean_keywords`의 `user_dict_entries`는 실제 `contracts.UserDictEntry`/
  `dictionary_hash`/동의어(`synonyms`) 배선이 아니라 표층형 문자열 목록 간이 구현이다(§5.1 규칙 4
  전체 재현은 컬렉션 사전 로딩 배선이 있는 후속 WP).
- DEFERRED: `KoreanKeywordsConfig.stopwords_ref`는 스키마 자리만 있고 로딩하지 않는다(항상 내장
  불용어 목록 사용) — `ctx.artifacts` 확장 또는 셸 사전 로딩이 있는 후속 WP.

## 결과: 통과 21 / xfail 0 / DEFERRED 4
