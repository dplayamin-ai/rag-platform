---
title: "WP-103 parse-text-markdown-csv"
status: implemented
task: F1-03
---

# WP-103 — `parser.text_charset_markdown_it` (TXT·Markdown·CSV)

## 목표

`04-pipelines/08-parser-txt-md-and-others.md`가 정의하는 텍스트 계열 파서 플러그인
`parser.text_charset_markdown_it`를 구현한다. `SourceDocument{format ∈ {txt, md}}` 바이트를 받아
`ParsedDocument`를 만든다. 범위는 이 WP의 지시(F1-03 사양 요지)로 좁힌다:

- TXT: charset-normalizer 인코딩 감지(EUC-KR/CP949 포함), 줄바꿈 정규화, 빈 줄 단락, 번호·기호
  heading 패턴(P1·P2·P3·P4·P6), 개조식 목록(§4.3 마커 사다리).
- Markdown: markdown-it-py 토큰 → heading/list/table/code/quote, YAML 프론트매터 → `metadata`.
- CSV(TXT 하위 힌트 경로): 표 블록 1개 + 헤더 감지 + 크기 분할.
- `element_path`·블록 상대 char offset provenance(`page`·`bbox` = null 고정).

**의도적 축소(설계 문서 대비, §12 미해결 이슈에 준하는 국소 결정 — open_issues 참조):** ftfy 모지바케
재투표(§3.3), mdit_py_plugins(footnote·tasklists·front_matter 플러그인·dollarmath), clevercsv,
JSON/JSONL/XML 하위 경로, 대용량 스트리밍·문단 병합 모드(§3.6), Markdown 링크·이미지·각주·수식,
TXT P5(setext) 패턴, `delimited_and_aligned` 표 감지는 이번 WP 범위 밖이다 — 이 작업 지시의 "사양
요지"에 없고, 허용 패키지 목록(charset-normalizer, markdown-it-py만 신규 사용; 나머지는 이미
pyproject에 있는 pyyaml·표준 라이브러리 `csv`)에도 없다.

## 파일

- `src/rag_platform/adapters/parse/text_charset_markdown_it.py` (신규)
- `tests/adapters/parse/test_text_markdown.py` (신규)
- `tests/fixtures/parse_text/notice_cp949.txt`, `overview_frontmatter.md`, `status.csv` (신규 픽스처)

## 시그니처

```python
class TextParserConfig(BaseModel):  # frozen, extra="forbid" — ingest.parse.options.text 부분집합
    encoding: EncodingConfig
    txt: TxtConfig
    md: MdConfig
    csv: CsvConfig
    # limits(max_block_chars 등)는 이번 WP 범위 밖(§3.6·§4.5 /part[n] 크기 분할 미구현, open_issues 참조)

class TextCharsetMarkdownItParser:
    plugin_id = "parser.text_charset_markdown_it"
    config_schema = TextParserConfig
    def capabilities(self) -> ct.Capabilities: ...
    def fingerprint(self) -> str: ...
    async def run(self, inp: SourceDocument, ctx: Any) -> ParsedDocument: ...
    async def parse_bytes(self, data: bytes, inp: SourceDocument, ctx: Any) -> ParsedDocument: ...
```

## 입출력 계약 발췌(철자 정본)

- `ParsedDocument.source_kind = SourceKind.flow`, `page_count = None`, 모든 `Block.provenance = {element_path, char_start=0, char_end=len(text), page=null, bbox=null}`(04 §4.5·§5.8).
- `Block.block_id = H("block", doc_version, element_path)[:32]`(`rag_platform.sdk.hashing.block_id`).
- `parser_fingerprint.parser_version`: TXT/CSV = `charset-normalizer==3.5.1`, MD = `markdown-it-py==4.2.0`(04 §1.2).
- `parser_fingerprint.profile_option`: `txt_standard` / `md_standard` / `csv_experimental`(04 §1.2·§2 표).
- `source_encoding`: 04 §3.2 정규화 표(EUC-KR 계열 → `cp949`).
- `BlockType`: heading, paragraph, list_item, table, code (04 §5.2; quote는 블록이 아니라 `element_path`의 `/quote` 접미, 04 §5.5).
- `TableData.quality.structure_source`: TXT = `line_based`, MD/CSV = `native`(바이블 §5.4 `TableData`).
- 오류 코드는 §5.7 카탈로그만: `parse.unsupported_variant`(NUL 비율 초과·CSV 열 상한 초과), `parse.conversion_failed`(모든 인코딩 후보 strict 실패 + `fallback=fail` 또는 `replace_max_ratio` 초과).

## 불변식·금지

- `blocks`는 문서 순서 평탄 리스트, 계층은 `parent_block_id`·`ordinal`(0-based, 부모별 연속).
- `element_path`는 문서 내 유일(P-2). TXT `/txt/para[n]`·`/txt/table[k]/row[r]/cell[c]`, MD `/md/block[n]`(+`/item[i]`·`/quote`·`/row[r]/cell[c]`), CSV `/csv/table[0]`(+`/part[n]/row[r]/cell[c]`).
- `Block.text`는 원문(NFC 미적용, 마커 원문 보존 — TXT heading/list의 `numbering_label`은 `text`에서 지우지 않는다; MD 목록 마커는 문법이라 `text`에서 제외, 04 §5.2).
- `metadata.title`: 조건 충족 시 항상 채움(요청 title 유무 무관) — TXT 첫 3세그먼트 안의 `level=1` heading, MD 프론트매터 `title` 없으면 유일한 첫 `h1`.
- `level=0`(문서 제목) heading은 어느 경로에서도 만들지 않는다.
- 순수성: 파일시스템·네트워크 접근 없음. 부수효과는 `ctx.artifacts.put_derived`·`ctx.now()`만.
- 어댑터는 `rag_platform.storage`/`rag_platform.security`를 임포트하지 않는다(import-linter `adapters-no-storage`).
- 계약 생성물(`src/rag_platform/contracts/**`)은 손편집 금지.

## 단계

1. `_decode(data, inp, cfg)`: BOM → `http_metadata.charset`(별칭 정규화) → `charset_normalizer.from_bytes` → UTF-8 → cp949 → `fallback`. 한글 비율 재투표(언어 힌트 `ko`, 임계 `hangul_min_ratio`)로 cp949 우선 재시도. 줄바꿈 정규화(`\r\n`·`\r`→`\n`). NUL 비율 초과 시 `parse.unsupported_variant`. **국소 결정(구현 중 발견):** 바이트열이 이미 유효한 UTF-8(비ASCII 포함)이면 감지기(`charset_normalizer`) 호출 자체를 건너뛴다 — 감지기가 짧거나 스크립트가 섞인 유효한 UTF-8을 단일 바이트 코드페이지(예 `cp874`)로 오판해도 그 오판된 strict 디코딩은 "성공"하므로(단일 바이트 코덱은 모든 바이트를 해석), 04 §3.1 표의 우선순위(감지기 > UTF-8)를 문자 그대로 따르면 정상 UTF-8을 깨뜨린다(회귀 테스트로 확인, 로마 숫자 heading 표본에서 재현). §3.1 patch 요청(미해결 이슈 참조).
2. 하위 경로 선택: `format=md` → MD, `format=txt` + CSV 힌트(미디어 타입/확장자) + `csv.mode≠off` → CSV, 그 외 → TXT.
3. TXT: 문단 분할(`auto`/`blank_line`/`line`, 마커 런 줄 단위 분리) → heading 패턴 P1(법령, 압축 배정)·P2(십진, run 규칙)·P3(로마자)·P4(괄호)·P6(강조기호), lookahead 조건(d)·선행 빈 줄 조건(e) → 개조식 목록(마커 사다리 `outline_report`/`law_article`, 들여쓰기 우선, 기호는 직전 번호 항목 자식) → 선택적 구분자 표(`delimited`) → 트리 조립(heading/paragraph는 최근접 얕은 heading의 자식, list_item은 최근접 얕은 list_item, 없으면 heading) → `metadata.title`/`genre`.
4. MD: YAML 프론트매터 추출(`---…---`) → `MarkdownIt("gfm-like")`(linkify 비활성) 파싱 → `SyntaxTreeNode` 순회로 heading/paragraph/list_item/table/fence/code_block/blockquote(`/quote` 경로) 매핑 → 인라인 평문 추출(strong/em/s/code_inline/link 평탄화, softbreak/hardbreak→`\n`) → 프론트매터 없으면 유일한 첫 `h1` → `metadata.title`.
5. CSV: 표준 라이브러리 `csv.Sniffer`(TSV 힌트면 구분자 `\t` 고정) → 격자 구성(부족 셀 `""`, 초과 셀 마지막 셀에 병합) → 헤더 판정(`auto`/`first_row`/`none`) → `rows_per_block` 초과 시 `/part[n]` 분할(헤더 반복) → `max_cols` 초과 시 `parse.unsupported_variant`.
6. 봉투 조립: `Producer`·`ParserFingerprint`·`LineageRefs`·`text_length`·`block_count`·`source_encoding`. 디코딩 리포트를 `artifacts[]{kind=vendor_json}`로 저장(`ctx.artifacts.put_derived`).

## 테스트(파일·케이스) — `tests/adapters/parse/test_text_markdown.py`

- cp949 공문 픽스처(`notice_cp949.txt`): 인코딩 판정=cp949, heading(P4 접두형)+list_item run(종결부호 규칙)+기호 중첩(들여쓰기 우선)+말미 문단, 트리·`element_path`·`block_id` 결정성.
- 법령 인라인 표본: P1 압축 배정(장·조만 → 1·2), 조건(d) 예외(P1은 lookahead 미적용, 연속 조가 모두 heading), `①` 목록(law_article 사다리), genre 자동 추론.
- heading 패턴 표: P2 run 규칙(숫자 개요 연속 → heading, 종결부호 있으면 list_item), P3·P6 양성/음성.
- Markdown 픽스처(`overview_frontmatter.md`): 프론트매터→`metadata`, heading 레벨, 중첩 목록, GFM 표 셀 provenance, fence 언어, blockquote `/quote` 경로.
- CSV 픽스처(`status.csv`): 헤더 자동 감지, 셀 그대로 보존, `rows_per_block` 분할·헤더 반복(작은 값으로 강제), `max_cols` 초과 → `parse.unsupported_variant`.
- 인코딩 폴백: 깨진 바이트 → `utf_8_replace` 저하, `replace_max_ratio` 초과 → `parse.conversion_failed`.
- 트리 불변식 일괄 검증(hwpx 테스트와 동형): `block_id` 유일성·재계산 일치, `element_path` 유일성, `parent_block_id` 선행 등장, `ordinal` 형제 연속성, `provenance.page/bbox = null`.

## 완료 기준

- 위 테스트 전량 통과, `uv run ruff check src/rag_platform/adapters/parse/text_charset_markdown_it.py` 통과.
- import-linter `adapters-no-storage` 위반 없음(수동 확인: storage/security 미임포트).

## 검증 계층

1층(여기서 검증) — `uv run pytest -q tests/adapters/parse/test_text_markdown.py`. Docker·모델·GPU·외부 네트워크 불필요.
DEFERRED 없음(이 WP 범위 안에서는 3층 분리 대상 없음; 축소된 항목은 별도 후속 WP로 미해결 이슈에 기록).

결과: 통과 23 / xfail 0 / DEFERRED 0
