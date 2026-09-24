---
title: "WP-106 normalize-korean"
status: active
owner: implementation
version: 1.0.0
last_updated: 2026-09-23
implementation_status: done
depends_on: ["../README.md", "../../12-appendix/10-implementation-design-gaps.md"]
---
# WP-106 normalize-korean (F1-06)

## 목표

`normalizer.chain` 스테이지(`ParsedDocument → NormalizedDocument`, 바이블 §4.2 `normalize` 행)의 축소 범위
구현. 04-pipelines/09 §2(체인 정본 순서)의 N1~N10 중 이 WP가 다루는 부분만: N1 `unicode`(NFC·제어문자·
NBSP), N2 `linebreaks`(하이픈 결합·줄바꿈 병합, 기본 꺼짐), N6 `language`(간단 휴리스틱), N7 `furniture`
(반복 머리말/꼬리말·nav), N8 `dedup`(빈·인접 중복 블록), N9 `heading`(레벨 점프 보정) + N4 `display_freeze`
동치의 `offset_map` 정규형(§4). N3 `pii`/N5 `risk_l1`/N10 `genre` 휴리스틱/N11~N15(렉시컬 한자 독음·
파생 메타·문장 분리·표 셀 뷰·리포트 세부)는 이 WP 범위 밖이며 PII는 `policy_applied=keep` 고정,
문장은 블록 전체를 단일 span으로 두는 자리표시자로 처리한다(아래 DEFERRED).

## 파일

- `src/rag_platform/adapters/normalize/korean/unicode.py` — N1: `Edit`/`apply_edits`(원문 좌표 편집 →
  `offset_map`), `clean_unicode`(제어·PUA·zero-width 제거, CR 삭제, NBSP, NFC 클러스터 합성),
  `fold_lexical`(호환 자모 보존 NFKC 폴딩, 문자 단위).
- `src/rag_platform/adapters/normalize/korean/layout.py` — N2: `merge_linebreaks`(라틴 분철 결합,
  한글 줄바꿈 결합/일반 개행 공백 치환; `enabled` 게이트, 선택적 `korean_join` 훅).
- `src/rag_platform/adapters/normalize/stage.py` — `NormalizerChainConfig`(config_schema),
  `NormalizerChainStage`(Stage 5멤버) — 블록 순회, furniture/dedup/heading/language 판정,
  `NormalizedDocument` 조립.
- `tests/adapters/normalize/test_normalize.py` — 단위(offset_map 골든 예시 3종, furniture/dedup/heading)
  + `run()` 통합 1건.

## 시그니처

```python
# korean/unicode.py
@dataclass(frozen=True)
class Edit:
    start: int; length: int; replacement: str

def apply_edits(original: str, edits: Sequence[Edit]) -> tuple[str, list[list[int]]]: ...
def clean_unicode(text: str) -> tuple[str, list[Edit], dict[str, int]]: ...
def fold_lexical(display_text: str) -> str: ...

# korean/layout.py
def merge_linebreaks(
    text: str, *, enabled: bool, korean_join: Callable[[str], str] | None = None
) -> tuple[str, list[Edit], dict[str, int]]: ...

# stage.py
class NormalizerChainConfig(BaseModel): ...
class NormalizerChainStage:
    plugin_id = "normalizer.chain"
    config_schema = NormalizerChainConfig
    def capabilities(self) -> ct.Capabilities: ...
    def fingerprint(self) -> str: ...
    async def run(self, inp: ParsedDocument, ctx: Any) -> NormalizedDocument: ...
```

## 입출력 계약 발췌 (철자 정본)

- `ParsedDocument.blocks[].{block_id, type, text, level, furniture, container, source, confidence,
  provenance.page}`, `ParsedDocument.{tenant_id, collection_id, document_id, doc_version, language,
  quality, source_kind, metadata.{page_header_text, page_footer_text, navigation_text, genre}}`.
- `NormalizedBlock{block_id, display_text, lexical_text, offset_map, sentence_spans, lang,
  boilerplate, furniture_reason, text_source, confidence}` — `offset_map: list<[disp,orig,len]>`,
  각 항목 `min_length=3`.
- `NormalizedDocument{schema_version="1.0.0", schema_type="NormalizedDocument", tenant_id,
  collection_id, producer, quality, warnings, created_at, lineage_refs{source, parsed},
  document_id, doc_version, parsed_ref, normalizer_fingerprint, analyzer_id, dictionary_hash,
  language, genre, genre_source?, blocks, heading_tree[{block_id, level, path}], annotations
  {pii_spans, content_risk?}, pii_report{policy_applied, entity_counts, detector_version,
  tokenize_mode_applied?}, normalization_report{removed_control_chars, nfd_composed,
  hanja_replaced, spacing_corrected, boilerplate_removed}, stats?, table_cell_views?}`.
- `common_types.FurnitureReason ∈ {repeated_header, nav, boilerplate}`;
  `common_types.PiiPolicy ∈ {mask, tokenize, exclude, keep, reject}`;
  `common_types.ErrorCodeCatalog.normalize_segmenter_fallback = "normalize.segmenter_fallback"`.
- 04-pipelines/09 §4 오프셋 규칙: 동일 길이 치환은 분리 없이 1:1 구간에 흡수; 삭제는 경계 마커
  `[d,o,0]`(인접 삭제는 마커 하나로 접음, 문자열 끝에서 끝나는 삭제는 마커 생략—후행 sentinel이 대신함);
  불투명 치환(m≠n)은 `[d,o,n]`; `offset_map`은 항상 `[len(display),len(original),0]` sentinel로 끝난다.

## 불변식·금지

- 블록 물리 제거·병합·생성 없음(`blocks` 는 `ParsedDocument.blocks`와 `block_id` 집합·순서 1:1); furniture/
  dedup은 `boilerplate=true`로만 표시.
- `display_text`는 NFC이고 `Cc`(tab/LF 제외)·`Cf`·`Co` 잔존 없음(위반 시 `normalize.nfd_residual`).
- 편집은 원문 좌표로 기록, 표시 좌표는 `apply_edits`가 계산(단계 간 좌표 오염 금지). 같은 원문 위치에
  두 편집이 겹치면 오류(`ValueError` → 호출측에서 `contract.violation`).
- `adapters`는 `storage`/`security`를 import하지 않는다(import-linter `adapters-no-storage`); `sdk`/
  `contracts`/`testing`만 의존.
- PII는 이 WP 범위 밖 — `pii_report.policy_applied="keep"`, `annotations.pii_spans=[]`, `table_cell_views`
  생략(계약: `policy_applied≠keep`일 때만 필수).
- StageError 코드는 §5.7 철자만(`contract.violation`, `normalize.nfd_residual`); Stage 5멤버
  (`plugin_id`/`config_schema`/`capabilities()`/`fingerprint()`/`run()`) 외 확장 금지.

## 단계

1. 블록별 N1(`clean_unicode`) 실행 → 원문 길이와 같은 `working` 버퍼 + 구조적 `Edit` 목록 + 통계.
2. 대상 블록(`source_kind≠flow`이고 `type∈{paragraph,list_item,heading,caption,footnote}`, 또는 flow +
   `source=converted`)에 N2(`merge_linebreaks`) 실행, 같은 `working` 버퍼에 이어서 적용.
3. `apply_edits(working, edits)` → `display_text`, `offset_map`.
4. `fold_lexical(display_text)` (+ `spacing_correction_enabled`이고 `ctx.analyzer` 있으면
   `analyzer.normalize()`) → `lexical_text`.
5. 언어 휴리스틱(N6): 한글 대 라틴 문자 수 비교, 둘 다 0이면 문서 언어로 폴백.
6. furniture(N7): `container∈{page_header,page_footer}`·`type=toc`·`metadata.*_text` 일치·원 `Block.
   furniture` 신호 → `furniture_reason`.
7. dedup(N8): 빈 블록, 직전 비-furniture 블록과 동일한 인접 블록 → `boilerplate=true,
   furniture_reason=boilerplate`(표·그림 등 빈 텍스트가 정상인 타입은 제외).
8. heading(N9): 레벨 점프를 `직전 heading level + 1`로 클램프, `heading_tree` 조상 경로(최대 7) 조립.
9. `NormalizationReport`/`NormalizationStats`/`normalizer_fingerprint`/`analyzer_id`/`dictionary_hash`
   조립 후 `NormalizedDocument` 반환.

## 테스트(파일·케이스)

`tests/adapters/normalize/test_normalize.py`:
- `apply_edits` 골든 3종(04-pipelines/09 §4 예시 그대로): 라틴 분철, 한글 줄바꿈 결합, CRLF.
- `clean_unicode`: NBSP 치환이 세그먼트를 쪼개지 않음(1개 identity 구간), zero-width/PUA 삭제, NFC
  자모 합성.
- `merge_linebreaks`: `enabled=False`일 때 무변화; 라틴 하이픈 결합; 한글 줄바꿈 결합.
- furniture/dedup/heading 판정 단위 테스트(가짜 블록 배열).
- `NormalizerChainStage.run()` 통합 1건: 최소 `ParsedDocument`(헤더 반복 2회 + 본문 1개 + heading 2개
  레벨 점프) → `NormalizedDocument` 필드·`boilerplate`·`heading_tree` 검증, 가짜 `ctx`(`parsed_ref`,
  `now()`).

## 완료 기준

`uv run pytest -q tests/adapters/normalize/test_normalize.py` 전부 통과, `uv run ruff check` 대상 파일
통과, mypy는 배치 검증자가 별도 실행.

## 검증 계층·DEFERRED

1층(여기서 검증). `needs_docker`/`needs_model`/`needs_gpu`/`needs_network` 해당 없음(순수 함수, 외부
자원 없음).

- DEFERRED: N13 `sentence_splitter`(kss/정규식) 미구현 — 블록 전체를 단일 `SentenceSpan`으로 두고
  문서마다 `warnings[].code=normalize.segmenter_fallback` 경고를 남겨 `quality=degraded`로 정직하게
  표시한다. 실 구현은 별도 WP.
- DEFERRED: N3 `pii`(presidio_ko), N10 `genre` 휴리스틱 본체(파서 힌트만 반영, 자체 분류 없음),
  N11 한자 독음/띄어쓰기 교정 본체(훅만 배선), N12 `derived_meta`, N14 `table_views`, N15 상세 리포트
  플래그 — 모두 별도 WP(F1 배치 후속 또는 F2)로 이월.
- DEFERRED: U+00AD(소프트 하이픈) 삭제와 N2 라틴 하이픈 결합의 상호작용(원문 문서 §3.1 "N2가 N1 삭제
  로그 참조") — 이 WP는 리터럴 `-`(U+002D) 줄끝 결합만 구현하고 소프트 하이픈 인지 결합은 이월.

## 결과: 통과 16 / xfail 0 / DEFERRED 3
