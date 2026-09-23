---
title: "WP-105 parse-pdf-fast-pypdfium2"
status: implemented
task: F1-05
---

# WP-105 — `parser.pdf_fast_pdftext`(빠른 경로, `pdf_fast_cpu`)

## 목표

`04-pipelines/05-parser-pdf.md` §4(빠른 경로 `pdf_fast_cpu`)·§7.2(heading 레벨 추론)·§7.3(읽기 순서·
2단 컬럼)·§7.7(provenance·좌표계)·§11(품질 게이트)이 정의하는 PDF 디지털 빠른 경로 파서 플러그인
`parser.pdf_fast_pdftext`(`profile_option=pdf_fast_cpu`)를 구현한다. `SourceDocument{format=pdf}`
바이트를 받아 `ParsedDocument`를 만든다. 범위는 이 작업 지시의 "사양 요지"로 좁힌다:

- pypdfium2로 페이지별 문자 bbox·폰트 크기를 직접 추출(아래 "패키지 결정" 참조), 줄(line)로 묶고
  다시 문단/heading 블록으로 병합한다.
- 폰트 크기 클러스터링(k≤4) + 한국어/숫자 번호 패턴(§7.2 규칙 4의 두 정본 계열: `제N편>제N장>제N절>
  제N조`, `N.>N.N>N.N.N`)으로 heading 레벨을 추론한다. `가.`/`(N)`/`①`류 보조 마커는 직전 패턴
  레벨+1로 근사한다(아래 "의도적 축소" 참조).
- 페이지마다 2단 컬럼을 감지해(§7.3 의사코드) 왼→오 읽기 순서로 재배열하고, 컬럼을 가로지르는
  블록(폭 > 페이지폭×0.6)은 y 위치에 따라 두 컬럼 사이에 끼운다.
- `Provenance.bbox`는 좌상단 원점·PDF 포인트, 소수 둘째 자리 반올림(§7.7). `element_path =
  /page[p]/block[b]`(0-based), 페이지 나눔은 `/page[p]/break`.
- 텍스트 밀도가 낮은 페이지(`chars < 20`이고 `image_area_ratio > 0.05`, §3.1·§3.2 임계값)는 이 파서가
  OCR을 하지 못하므로(`needs_model`) 블록을 만들지 않고 `page_status[].status=skipped` +
  `Warning(parse.page_skipped)`로 표시하며 문서 `quality=degraded`가 된다("ocr_required" 신호는 계약에
  전용 필드가 없어 이 두 값의 조합으로 표현 — open_issues 참조). `chars<20`이고 이미지도 거의 없으면
  `empty`(§3.2)로 보고 `quality`에 영향 없음.

**패키지 결정(확인 후 결정, 검증됨):** 04-pipelines/05 §1.2·§13은 `pdftext==0.7.1`(PyPI) 사용을
전제하지만, `pdftext>=0.7.1`은 `pypdfium2==5.10.1`을 정확히 고정 요구한다. 이 프로젝트는
`pypdfium2>=5.13.0`(다른 어댑터가 이미 의존)으로 고정돼 있어 `uv add pdftext`를 실행하면
`No solution found ... pypdfium2>=5.13.0 ... unsatisfiable`로 즉시 실패한다(실제 실행해 확인, 되돌림).
`pdftext` 자체는 모델 가중치에 의존하지 않지만(요청 사양의 "모델 의존이면 쓰지 않음" 조건과는 무관하게)
버전 고정 충돌로 설치 불가하므로 쓰지 않기로 결정한다. 대신 이미 프로젝트에 고정된 `pypdfium2`의 raw
ctypes API(`FPDFText_GetCharBox`·`FPDFText_GetFontSize`·`FPDFText_GetFontWeight`)로 pdftext와 동등한
문자 bbox·폰트 크기 추출을 직접 구현한다. `parser_fingerprint.parser_version`은 실제 사용 라이브러리를
반영해 `"pypdfium2=={version}"`로 쓴다(문서의 `"pdftext==0.7.1"` 표기와 다름 — open_issues 참조).

**의도적 축소(이번 WP 범위 밖 — open_issues 참조):** 표(`TableData`)·그림(`figure`)·목록(`list_item`)·
머리말/꼬리말(`page_header`/`page_footer`) 블록, outline(북마크) 매칭 heading 보정(§7.2 규칙 1),
`invisible_ratio`/`pua_ratio`/`control_ratio`/`no_tounicode_ratio` 기반 `garbled`/`pre_ocr` 페이지
분류(§3.1·§3.2 전체), 암호 PDF 복호화(`credentials_ref`), shard·재개(`ResumeCursor`)는 "사양 요지"에
없거나 표 전체(§3~§9)를 구현하려면 이 지시가 허용한 범위를 넘는다. 이런 요소가 있는 페이지의 본문은
`paragraph`로만 남는다(§4.1 표의 기본값과 일치).

## 파일

- `src/rag_platform/adapters/parse/pdf_fast_pdftext.py` (신규)
- `tests/adapters/parse/test_pdf_fast.py` (신규)
- `tests/fixtures/pdf_fast/pdf_builder.py` (신규 픽스처 헬퍼 — reportlab 없이 순수 Python으로 최소
  PDF 바이트를 만든다: Catalog/Pages/Page/Type1 Helvetica 폰트/콘텐츠 스트림 + 선택적 원시 RGB
  이미지 XObject)

## 시그니처

```python
class PdfFastParserConfig(BaseModel):  # frozen, extra="forbid"
    min_page_chars: int = 20                    # §3.1 chars 임계값
    min_image_area_ratio: float = 0.05           # §3.1 image_area_ratio 임계값(empty vs 저밀도)
    heading_size_ratio: float = 1.15             # §7.2 규칙 3
    heading_max_len: int = 120
    max_heading_clusters: int = 4                # §7.2 규칙 3 k≤4
    heading_page_ratio_gate: float = 0.4          # §7.2 규칙 6 / §11
    heading_doc_ratio_gate: float = 0.25
    column_min_gap_ratio: float = 0.05           # §7.3
    column_min_coverage: float = 0.3
    cross_column_width_ratio: float = 0.6

class PdfFastPdftextParser:
    plugin_id = "parser.pdf_fast_pdftext"
    config_schema = PdfFastParserConfig
    def config_hash(self) -> str: ...
    def capabilities(self) -> ct.Capabilities: ...
    def fingerprint(self) -> str: ...
    async def run(self, inp: SourceDocument, ctx: Any) -> ParsedDocument: ...
    async def parse_bytes(self, data: bytes, inp: SourceDocument, ctx: Any) -> ParsedDocument: ...

# 순수 헬퍼(단위 테스트 대상, PDF 불필요)
def _cluster_font_sizes(sizes: list[float], *, max_clusters: int) -> dict[float, int]: ...
def _pattern_heading_level(text: str, last_level: list[int]) -> tuple[int, str] | None: ...
def _detect_columns(blocks, page_width: float, *, min_gap_ratio: float, min_coverage: float) -> list[tuple[float, float]]: ...
def _merge_reading_order(columns: list[list[Any]], cross_blocks: list[Any]) -> list[Any]: ...
```

## 입출력 계약 발췌(철자 정본)

- `ParsedDocument.source_kind ∈ {born_digital, mixed, scanned}`(§3.3 간이 규칙: 축소판 — `pre_ocr`·
  `garbled` 미판정), `page_count = len(pdf)`(non-null, `ge=1`).
- `Block.provenance.bbox = [x0,y0,x1,y1]`(좌상단 원점, PDF pt, 소수 둘째 자리 반올림; `page_break`는
  `null`), `page`는 1-based, `element_path`는 `/page[p]/block[b]`(p·b 0-based)와 `/page[p]/break`
  (바이블 §5.4, 04-pipelines/05 §7.7 표).
- `Block.block_id = H("block", doc_version, element_path)[:32]`(`rag_platform.sdk.hashing.block_id`).
- `BlockType`: 이 WP는 `heading`·`paragraph`·`page_break` 3종만 만든다(전체 열거 14종 중 부분집합,
  §4.1 표와 정합 — 나머지는 위 "의도적 축소" 참조).
- `PageStatusEntry{page, status, ocr_confidence}` — 저밀도 페이지만 `status=PageStatus.skipped`,
  `ocr_confidence=None`(§11 "페이지 실패" 행 확장 적용).
- `Warning{code, message, page}` — 저밀도 페이지는 `code=ErrorCodeCatalog.parse_page_skipped`(카탈로그
  기존 코드 재사용; 전용 "OCR 필요" 코드는 카탈로그에 없음 — open_issues).
- `parser_fingerprint{parser_id="parser.pdf_fast_pdftext", parser_version="pypdfium2==<ver>",
  sidecar_image_digest=null, profile_option="pdf_fast_cpu"}`, `parser_chain=[PluginId(plugin_id)]`.
- 오류 코드는 §5.7 카탈로그만: `parse.document_encrypted`(암호 + `credentials_ref` 없음),
  `parse.corrupt_container`(pypdfium2 열기 실패).

## 불변식·금지

- `blocks`는 문서 순서 평탄 리스트, 계층은 `parent_block_id`(heading 스택 최상단)·`ordinal`(0-based,
  부모별 연속, `page_break`는 항상 최상위 형제).
- `element_path`는 문서 내 유일(P-2). `char_start=0, char_end=len(text)`(블록 전체 구간, 코드포인트).
- 순수성: 부수효과는 `ctx.artifacts.put_derived`(이 WP는 사용 안 함, 자리만 남김)·`ctx.now()`만.
  네트워크 접근 없음.
- 어댑터는 `rag_platform.storage`/`rag_platform.security`를 임포트하지 않는다(import-linter
  `adapters-no-storage`). 계약 생성물(`src/rag_platform/contracts/**`)은 손편집 금지.
- `pdftext`(PyPI) 패키지는 의존성에 추가하지 않는다(위 "패키지 결정" 참조 — `pyproject.toml`/
  `uv.lock` 미변경).
- 모델 가중치 다운로드 없음. OCR·레이아웃 모델 경로는 만들지 않는다(`needs_model`).

## 단계

1. `PdfFastPdftextParser.run`: `ctx.source_bytes()` 포트(동기·비동기 모두 허용)로 원본 바이트 획득 →
   `parse_bytes` 위임(hwpx 어댑터와 동형 패턴).
2. `parse_bytes`: `inp.container_flags.encrypted`이고 `credentials_ref` 없음 → `parse.document_encrypted`.
   `pypdfium2.PdfDocument(data)` 열기 실패(`PdfiumError`) → `parse.corrupt_container`.
3. 페이지 루프: `page.get_textpage()`로 문자별 `(text, charbox, font_size)` 추출(`FPDFText_GetCharBox`/
   `FPDFText_GetFontSize`, 실패한 개별 문자는 방어적으로 0 크기 처리) → `\r\n`/`\n`/`\r` 경계로 줄(line)
   분리 → 인접 줄을 폰트 크기 동일성 + 수직 간격(≤ 1×줄높이)으로 문단 후보 블록으로 병합. 문자 수
   `< min_page_chars`이고 이미지 영역비 `≤ min_image_area_ratio` → `empty`(블록 없음, 상태 영향 없음);
   `< min_page_chars`이고 이미지 영역비 `>` 임계값 → 저밀도(블록 없음, `page_status=skipped` +
   경고, `quality=degraded`).
4. 전체 문서에 걸쳐 heading 후보(크기 ≥ 본문 중앙값×1.15 또는 굵게, 길이 ≤120, `.`로 끝나지 않음)의
   크기를 클러스터링(k≤4, 내림차순 level 1..4)하고, 번호 패턴(§7.2 규칙 4)이 있으면 패턴 레벨이
   우선한다. heading 비율 게이트(페이지 `>0.4` 또는 문서 `>0.25`)를 넘으면 폰트 전용 승격을 되돌린다
   (패턴 매칭 승격은 유지). 정합 단계에서 `level ≤ 6`과 "부모 없는 heading은 직전 heading level+1로
   당김"을 적용한다.
5. 페이지별로 heading·paragraph 블록에 2단 컬럼 감지(§7.3)를 적용해 왼→오 순서로 재배열(가로지르는
   블록은 y 순으로 사이에 삽입)한 뒤, 2페이지부터 페이지 시작에 `page_break` 블록을 앞에 붙인다.
6. 최종 순서로 `element_path`·`block_id`·`parent_block_id`(heading 스택)·`ordinal`·`provenance`(bbox
   좌표 변환 `[left, H-top, right, H-bottom]`, 소수 둘째 자리)를 부여하고 `ParsedDocument` 봉투를
   조립한다(`source_kind`는 페이지 밀도 분류 비율로 §3.3 간이 규칙 적용).

## 테스트(파일·케이스) — `tests/adapters/parse/test_pdf_fast.py`

- 순수 헬퍼 단위 테스트(PDF 불필요): `_cluster_font_sizes`(k≤4 클러스터링, 내림차순 level),
  `_pattern_heading_level`(제N편/장/절/조, N./N.N/N.N.N, 가./(N)/① 보조 마커 +1 근사, 우선순위),
  `_detect_columns`(2단 판정 성공·실패 양쪽 — 간격 부족·커버리지 부족으로 단일 컬럼 폴백),
  `_merge_reading_order`(가로지르는 블록이 왼→오 사이에 끼는 순서).
- `tests/fixtures/pdf_fast/pdf_builder.py`로 만든 최소 PDF 통합 테스트: (a) 제목(18pt) + 본문(11pt,
  2줄 한 문단 + 다음 문단) 단일 페이지 — heading 레벨·`furniture=false`·`char_start/end`·
  `element_path` 검증; (b) 3페이지 문서 — 2·3페이지 시작에 `page_break` 블록, `page` 1-based 검증;
  (c) 큰 이미지 XObject + 텍스트 없음 페이지 — `page_status=skipped`+`parse.page_skipped` 경고+
  `quality=degraded`; (d) 텍스트도 이미지도 없는 페이지 — `empty`로 블록 없음, `quality=full` 유지;
  (e) 2단 컬럼(왼쪽 x=72, 오른쪽 x=320, y 인터리브 배치) — 왼쪽 전부 → 오른쪽 전부 순서 검증;
  (f) 암호화 플래그 + `credentials_ref` 없음 → `StageError(parse.document_encrypted)`; (g) 손상 바이트
  → `StageError(parse.corrupt_container)`; (h) 결정성 — 같은 바이트 재파싱 → 동일
  `model_dump(mode="json")`.
- 트리 불변식(hwpx 테스트와 동형): `block_id` 유일성·재계산 일치, `element_path` 유일성,
  `parent_block_id` 선행 등장, `ordinal` 형제 연속성, `page_break` 외 전 블록 `bbox` non-null.

## 완료 기준

- 위 테스트 전량 통과, `uv run ruff check src/rag_platform/adapters/parse/pdf_fast_pdftext.py` 통과.
- import-linter `adapters-no-storage` 위반 없음(수동 확인: storage/security 미임포트).
- `pyproject.toml`/`uv.lock` 미변경(패키지 결정 참조).

## 검증 계층

1층(여기서 검증) — `uv run pytest -q tests/adapters/parse/test_pdf_fast.py`. Docker·모델·GPU·외부
네트워크 불필요(순수 Python PDF 픽스처, pypdfium2는 렌더 없이 텍스트 레이어만 읽음). 실제 스캔
문서 OCR·Docling 레이아웃 경로(`parser.pdf_docling_standard`)·표/그림/목록/머리말 블록·outline
heading 보정·`garbled`/`pre_ocr` 페이지 분류·재개(`ResumeCursor`)는 `needs_model`/후속 WP로
미룬다(DEFERRED: 위 "의도적 축소" 항목을 별도 WP에서 Docling+RapidOCR 사이드카 환경으로 구현).

결과: 통과 29 / xfail 0 / DEFERRED 0
