---
title: "WP-104 parse-html-trafilatura"
status: active
owner: implementation
version: 1.0.0
last_updated: 2026-09-23
implementation_status: done
depends_on: ["../README.md", "../../12-appendix/10-implementation-design-gaps.md"]
task: F1-04
---
# WP-104 — `parser.html_trafilatura_docling` (HTML)

## 목표

`04-pipelines/07-parser-html.md`가 정의하는 HTML 파서 플러그인 `parser.html_trafilatura_docling`을
구현한다. `SourceDocument{format=html}` 바이트를 받아 `ParsedDocument`를 만든다. 범위는 이 작업 지시의
"사양 요지"로 좁힌다:

- Trafilatura(`output_format="xml"`) 본문 추출은 메타데이터(제목·저자·날짜·사이트명) 보조 원천과 본문
  충분성 신호로만 쓴다(스파이크로 확인: 짧은 표본에서 Trafilatura XML은 `<h2>`·`<table>` 구조를 보존하지
  않고 문단 하나로 합친다 — §11 확인 필요 항목과 일치). 블록 구조·`element_path`의 정본은 전처리된
  **원본 DOM**(lxml)이다 — 지시문 "DOM path provenance"와 일치.
- lxml 구조 파싱: `h1`~`h6`→`heading`(level), `p`/인라인·`br`만인 `div`→`paragraph`(`<br><br>`→`seg[n]`
  분할), `ul`/`ol`→`list_item`(중첩·번호 라벨), `table`(`rowspan`/`colspan`)→`TableData`(앵커 셀 격자),
  `img`→`figure`(data URI) 또는 alt 문단+링크, `pre`/`pre>code`→`code`(공백 보존, 언어 추론),
  `blockquote`→자식이 각각 `paragraph`(블록 자신은 투명).
- 메타: `title`(`og:title` > Trafilatura > `<title>` > 첫 `h1`), `og:site_name`, `article:published_time`
  → `metadata.created_at`/`web.published_at`(시간대 없으면 `default_timezone`), `html[lang]`/
  `content-language`/`og:locale` → `language`, `link[rel=canonical]`/`og:url` → `web.canonical_url`.
- 스크립트·스타일·폼 컨트롤·숨김 요소(`hidden`·`aria-hidden`·인라인 `display:none` 등) 제거,
  `nav`/`aside`/`header`/`footer`/랜드마크 role → `metadata.navigation_text` + 제거.
- Docling 구조 보조는 **`needs_model` 자리만**: `docling_table_backend_placeholder()`가
  `NotImplementedError`를 던지는 훅만 남기고 실제 연동은 하지 않는다(모델 가중치 다운로드 금지).
- 한국어 공공기관 게시판 형태 픽스처 2개(`board_notice_utf8.html`, `board_notice_cp949.html`).

**의도적 축소(§12 미해결 이슈에 준하는 국소 결정 — open_issues 참조):** 사이트 규칙(`site_rules`)의 CSS
선택자는 `cssselect` 미설치(이 작업에 허용된 신규 패키지 목록에 없음)로 XPath로 대체했다. 폴백 사다리
(`readability-lxml`·`html2txt`·`docling_direct` 별도 모드), MHTML·프레임 처리, JS 렌더링 감지,
첨부파일 분류(`attachments[]`), 중첩 표, JSON-LD 메타데이터, `favor_recall`/`favor_precision` 모드별
휴리스틱은 이번 WP 범위 밖이다 — "사양 요지"에 없고 표(§5.5·§9.4·§11.1·§6.5·§8) 전체를 구현하려면 이
지시가 허용한 범위를 넘는다.

## 파일

- `src/rag_platform/adapters/parse/html_trafilatura_docling.py` (신규)
- `tests/adapters/parse/test_html.py` (신규)
- `tests/fixtures/parse_html/board_notice_utf8.html`, `board_notice_cp949.html` (신규 픽스처, 한국어
  공공기관 게시판 형태 — `table.board_view` 메타 표 + `<br><br>` 본문 + 첨부 목록 + `nav`/`footer`)

## 시그니처

```python
class HtmlSiteRule(BaseModel):  # frozen, extra="forbid" — XPath 대체(§4.5 대체 표기, 위 축소 참조)
    rule_id: str
    hosts: list[str]
    main_selectors: list[str]   # XPath
    remove_selectors: list[str] # XPath
    default_timezone: str = "Asia/Seoul"

class HtmlParserConfig(BaseModel):  # frozen, extra="forbid" — ingest.parse.options.html 부분집합
    mode: Literal["standard", "docs_site", "news"] = "standard"
    include_links: bool = True
    include_images: bool = True
    remove_hidden: bool = True
    min_main_text_chars: int = 200
    default_timezone: str = "Asia/Seoul"
    site_rules: list[HtmlSiteRule] = []
    use_docling_table_backend: bool = False  # needs_model 자리 — 켜면 StageError(parse.conversion_failed)

class HtmlTrafilaturaDoclingParser:
    plugin_id = "parser.html_trafilatura_docling"
    config_schema = HtmlParserConfig
    def capabilities(self) -> ct.Capabilities: ...
    def fingerprint(self) -> str: ...
    async def run(self, inp: SourceDocument, ctx: Any) -> ParsedDocument: ...
    async def parse_bytes(self, data: bytes, inp: SourceDocument, ctx: Any) -> ParsedDocument: ...

def docling_table_backend_placeholder(table_html: str) -> None: ...  # raises NotImplementedError
```

## 입출력 계약 발췌(철자 정본)

- `ParsedDocument.source_kind = SourceKind.flow`, `page_count = None`, `Block.provenance.page/bbox = null`,
  `section_index = null`(바이블 §5.4, 07 §10).
- `Block.block_id = H("block", doc_version, element_path)[:32]`(`rag_platform.sdk.hashing.block_id`).
- `element_path`: DOM 경로, 0-based **같은 이름 형제** 순서, 루트(`html`)부터(07 §6.2·§10 DOM 모드 열).
  `<br><br>` 분할은 `/seg[n]`, 표 셀은 `/cell[r][c]`(앵커 좌표), 캡션은 `/caption[0]`(07 §10).
- `BlockType`: `heading, paragraph, list_item, table, figure, caption, code`(바이블 §5.7 14값 중 사용분).
- `parser_fingerprint.parser_version = "trafilatura=={ver};lxml=={ver}"`(복수 패키지 `;` 연결, 바이블 §5.4
  미해결 10 채택), `profile_option = "html_" + mode`.
- `TableData.quality.structure_source = StructureSource.native`(원본 `rowspan`/`colspan`에서 직접 격자를
  세우므로 Docling 재결합 손실이 없다 — 07 §6.5 `native` 정의와 일치, Docling 미사용은 위 축소 참조).
- `DocumentMetadata.web`(`WebMetadata`): `canonical_url`, `site_name`, `published_at`, `author`.
- 오류 코드는 §5.7 카탈로그만: `parse.conversion_failed`(lxml 파싱 실패, 본문 블록 0개 — 07 §13 `detail`
  `empty_main_content`).

## 불변식·금지

- `blocks`는 문서 순서 평탄 리스트, 계층은 `parent_block_id`·`ordinal`(0-based, 부모별 연속). 비-heading
  블록의 부모는 heading 스택 최상단(07 §6.4), 중첩 `list_item`의 부모는 바깥 `li`, `caption`의 부모는
  대상 `table`/`figure`.
- `element_path`는 문서 내 유일(P-2). `Block.text`는 원문(NFC 미적용; NBSP·전각 문자 보존, ASCII 공백만
  접음), `numbering_label`은 `text`에서 분리(07 §6.3).
- `furniture`는 항상 `false`(본문 영역 안 블록만 생성 — 랜드마크는 블록화하지 않고 `navigation_text`로만
  보존, 07 §7.1).
- 순수성: 네트워크·파일시스템 접근 없음(원격 이미지·첨부파일을 가져오지 않는다, 07 §9.2·§9.3). 부수효과는
  `ctx.artifacts.put_derived`·`ctx.now()`만.
- 어댑터는 `rag_platform.storage`/`rag_platform.security`를 임포트하지 않는다(import-linter
  `adapters-no-storage`). 계약 생성물(`src/rag_platform/contracts/**`)은 손편집 금지.
- `docling_table_backend_placeholder`는 항상 `NotImplementedError`를 던진다 — 모델 가중치 다운로드 금지
  환경에서 실제 연동을 흉내 내지 않는다.

## 단계

1. `_decode_html(data, http_charset)`: BOM → `<meta charset>`/`http-equiv` 프리스캔(첫 2048바이트) →
   `http_metadata.charset` → UTF-8. 라벨 정규화표(`euc-kr`·`ks_c_5601-1987` 등 → `cp949`)를 먼저 적용.
2. `lxml.html.fromstring(text, parser=HTMLParser(recover=True, remove_comments=True, remove_pis=True,
   no_network=True, huge_tree=False))`로 DOM 구성 → 메타데이터 추출(제거 전에 `<title>`·`og:*`·
   `article:*`·`link[rel=canonical]`·`html[lang]` 읽기) → 랜드마크(`nav`/`aside`/`header`/`footer`/역할)
   텍스트 수집 후 제거 → 스크립트·스타일·폼 컨트롤·`svg`·숨김 요소 제거 → 링크 절대화(`urljoin`).
3. 본문 영역 선택: `site_rules`(호스트 글롭 일치) 또는 기본 후보 XPath(`article`, `main`, `[role=main]`,
   `div.board_view div.cont`, `td.content`, `#content .view_cont`, `.bbs_content`, `div.cont`) 중 첫
   일치, 없으면 랜드마크 제거 후 `body` 전체(§5.5 `docling_direct`에 준하는 최종 폴백).
4. Trafilatura `bare_extraction(text, url=resolved_uri, output_format="xml", with_metadata=True,
   include_tables=True, include_links=True, include_images=<cfg>, include_comments=False,
   include_formatting=False, favor_recall=..., favor_precision=...)`를 예외 흡수 호출 — 제목·저자·날짜·
   사이트명 보조 원천, 실패해도 DOM 경로만으로 계속 진행(§11 확인 필요 1·11과 일치하는 국소 결정).
5. DOM 순회로 블록 생성(heading 스택으로 계층 복원, `h1..h6`/`p`/인라인전용 `div`/`ul,ol>li`/`table`/
   `img`/`pre`/`blockquote`/`figcaption`을 각각 매핑, 그 외 컨테이너는 투명 재귀) → 표는 격자 점유 계산
   으로 `rowspan`/`colspan` 앵커 셀을 세우고 실패 시 `merged_cells_preserved=false`+`quality=degraded`.
6. 봉투 조립: `Producer`·`ParserFingerprint`·`LineageRefs`·`text_length`·`block_count`·`source_encoding`.
   전처리된 본문 서브트리(`derived_source`, `text/html`), 표별 `table_html`, 추출 보고(`vendor_json`)를
   `ctx.artifacts.put_derived`로 저장. 블록이 0개면 `parse.conversion_failed`(`detail=empty_main_content`).

## 테스트(파일·케이스) — `tests/adapters/parse/test_html.py`

- UTF-8/CP949 게시판 픽스처 쌍: 인코딩 판정(`utf-8`/`cp949`), 메타 표 → `table` 블록(`role`·헤더 판정),
  `<br><br>` 본문 → `seg[n]` 분할, 개조식 글머리 보존, 첨부 목록 → `list_item`+`links[]`, `nav`/`footer`
  제거 → `metadata.navigation_text`.
- 메타데이터: `og:title`/`article:published_time`(시간대 없음 → `Asia/Seoul` 해석)/`link[rel=canonical]`
  /`html[lang]` 매핑, 사이트명 접미 없이도 제목 그대로.
- 표 구조: 병합 셀(`rowspan`/`colspan`) 격자 무결성(앵커 셀이 격자를 겹침 없이 채움), `html_ref` 저장.
- 이미지: `data:` URI → `figure` 블록 + `figure_crop` 아티팩트, 원격 `alt` 있는 이미지 → 문단+링크, `alt`
  없는 원격 이미지 → 블록 없음.
- 코드·인용: `pre>code[class=language-*]` → `code` 블록(언어 추론, 공백 보존), `blockquote` 자식 각각
  `paragraph`.
- 트리 불변식 일괄 검증(hwpx 테스트와 동형): `block_id` 유일성·재계산 일치, `element_path` 유일성,
  `parent_block_id` 선행 등장, `ordinal` 형제 연속성, `provenance.page/bbox/section_index = null`,
  `furniture == false` 전수, 캡션 양방향 링크.
- 오류: 빈 `<body>` → `parse.conversion_failed`. Docling 자리 훅 → `NotImplementedError`.
- 결정성: 같은 바이트 재파싱 → 동일 `model_dump(mode="json")`.

## 완료 기준

- 위 테스트 전량 통과, `uv run ruff check src/rag_platform/adapters/parse/html_trafilatura_docling.py` 통과.
- import-linter `adapters-no-storage` 위반 없음(수동 확인: storage/security 미임포트).

## 검증 계층

1층(여기서 검증) — `uv run pytest -q tests/adapters/parse/test_html.py`. Docker·모델·GPU·외부 네트워크
불필요. `docling_table_backend_placeholder`의 `NotImplementedError` 자리는 실제 Docling 연동이 아니라
훅 존재만 확인하므로 1층에서 검증하고, 실제 모델 연동은 `needs_model`(DEFERRED: Docling
`HTMLDocumentBackend`+모델 사이드카 환경에서 §6.5 원본 표 재결합을 구현) 별도 후속 WP로 미룬다.

결과: 통과 22 / xfail 0 / DEFERRED 0
