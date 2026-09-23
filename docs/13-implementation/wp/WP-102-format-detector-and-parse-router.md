---
title: "WP-102 format-detector-and-parse-router"
status: implemented
task: F1-02
---

# WP-102 — `parser.format_detector` + `parser.router`(포맷 판별·파싱 라우터)

## 목표

`04-pipelines/03-parsing-router-and-format-detection.md`가 정의하는 두 결정 — **판별**(`detect`
서브스테이지: 이 바이트가 무엇인가)과 **라우팅**(`parser.router`: 누가 파싱하는가) — 을 이 WP
지시(F1-02 사양 요지)로 좁힌 범위에서 구현한다.

- 판별: 매직 바이트 → 컨테이너 내부 검사(ZIP 중앙 디렉터리·`mimetype`/`[Content_Types].xml` /
  OLE2 CFB `FileHeader`·`WordDocument`·`EncryptedPackage`+`EncryptionInfo`) → 선언 콘텐츠 타입 →
  확장자 순 고정 우선순위(§2.1), 텍스트 계열 세부 판별(json/html/md/txt, §2.4), 신뢰도 표(§2.5).
- 라우팅: 포맷별 후보 체인(hwpx→`parser.hwpx_python_hwpx`, pdf→`parser.pdf_fast_pdftext`,
  html→`parser.html_trafilatura`, txt/md/json→`parser.text_charset_markdown_it`) + 폴백(§6.1) +
  품질 신호(빈 산출 = 텍스트 밀도 0, §6.3) 기반 재라우팅 트리거 + `parser_chain[]` 기록(§7.2) +
  `quality` 승격(§6.4).
- `docx`는 `needs_model` 자리다: 후보 `parser.docx_docling_docx2python`(Docling)은 이 WP가
  등록하지 않는다 — `StageBuilder.build_stage`가 `KeyError`를 던지면 §4.1 3단계("미설치 후보
  건너뛴다")로 처리돼 후보 0개 → `parse.unsupported_format`이 된다(모델 가중치 다운로드 금지).

**의도적 축소(설계 문서 대비, open_issues 참조):** PDF `source_kind`(born_digital/scanned/mixed)
프로브·`PdfRoute`·페이지 단위 OCR·`page_route`(§4.2·§4.3·§4.4)는 이번 WP 범위 밖이다 — `pdf` 포맷은
단일 후보(`pdf_fast_pdftext`)로 단순화했다(OCR·GPU 금지 환경과 일치). `SplitRoute`(§4.7, JSON 배열
분할)도 범위 밖이며 `json`은 `txt`와 같은 후보로 단순화했다. 암호화·배포용 정책 분기(§4.6)는 `detect`가
`container_flags`만 채우고 실제 정책 판정(자격 증명 조회 등)은 각 포맷 어댑터(F1 배치의 다른 WP)의 몫으로
남긴다. 격리 모드 실행(`execute_isolated`/`SidecarStage`, §5.1)은 구현하지 않는다 — 후보는 항상
`await stage.run(...)`로 직접 호출한다(Docker 없음 환경과 일치). 이 문서가 제안한 `parse.detect` 프로파일
키(§9 미해결 이슈 15)와 프로파일 `parse.router` 스키마 자체(15 문서 소유)는 다루지 않는다 — 라우팅 표는
`ParseRouterStage` 생성자 인자(`DEFAULT_ROUTE_TABLE` 기본값)로만 주입한다.

## 파일

- `src/rag_platform/adapters/parse/format_detector.py`(신규) — `detect()` 순수 함수 + `FormatDetectorStage`
- `src/rag_platform/adapters/parse/router.py`(신규) — `ParseRouterStage` + `DEFAULT_ROUTE_TABLE`
- `tests/adapters/parse/test_router.py`(신규)

## 시그니처

```python
# format_detector.py
@dataclass(frozen=True)
class DetectionResult:
    media_type: str
    format: ct.SourceFormat
    format_confidence: float
    container_flags: ContainerFlags
    detect_report: DetectReport

def detect(data: bytes, *, hint_media_type: str | None = None, hint_extension: str | None = None) -> DetectionResult: ...

class FormatDetectorConfig(BaseModel): ...  # extra="forbid", frozen — 옵션 없음(v1)

class FormatDetectorStage:
    plugin_id = "parser.format_detector"
    config_schema = FormatDetectorConfig
    def capabilities(self) -> ct.Capabilities: ...
    def fingerprint(self) -> str: ...
    async def run(self, inp: SourceDocument, ctx: Any) -> SourceDocument: ...
    def detect_source(self, data: bytes, inp: SourceDocument, ctx: Any) -> SourceDocument: ...

# router.py
RouteEntry = tuple[str, ...] | str
DEFAULT_ROUTE_TABLE: dict[ct.SourceFormat, RouteEntry]

class StageBuilder(Protocol):  # PluginRegistry.build_stage와 구조적으로만 호환
    def build_stage(self, plugin_id: str, config: Mapping[str, Any], services: Any = None) -> Any: ...

class ParseRouterStage:
    plugin_id = "parser.router"
    config_schema = ParseRouterConfig
    def __init__(self, builder: StageBuilder, route_table=None, *, config=None) -> None: ...
    def capabilities(self) -> ct.Capabilities: ...
    def fingerprint(self) -> str: ...
    async def run(self, inp: SourceDocument, ctx: Any) -> ParsedDocument: ...
```

## 입출력 계약 발췌(철자 정본)

- `SourceDocument.format: common_types.SourceFormat`(13값: `hwpx, hwp5, hwp3, pdf, docx, doc, rtf,
  odt, html, txt, md, json, unknown`), `.format_confidence: float`(0~1), `.container_flags:
  ContainerFlags{encrypted, distribution, compressed, hwp_version}`, `.media_type:
  common_types.MediaType`, `.detect_report: DetectReport{signals, hint_media_type, hint_agrees,
  candidates}`(모두 `source_document.py`).
- `ParsedDocument.parser_chain: list[PluginId]`(min_length=1, 마지막=산출 파서),
  `.quality: common_types.Quality`(`full`/`degraded`), `.text_length`, `.blocks[].type:
  common_types.BlockType`(`table`/`figure` 판정에 사용).
- `StageError.code`는 §5.7 철자만: `parse.unsupported_format`·`parse.corrupt_container`(둘 다
  `detect`가 종결), `parse.unsupported_variant`(라우터 종결 코드 항목, hwp3), `parse.conversion_failed`
  (폴백·체인 소진·빈 산출·예산 부족), `profile.invalid`(라우팅 표에 없는 포맷 키 — 방어적 분기, `DEFAULT_ROUTE_TABLE`은
  13값 전부를 채워 정상 경로에서는 도달하지 않는다).

## 불변식·금지

- `detect()`는 `format=unknown`이면 `parse.unsupported_format`, 컨테이너 손상이면
  `parse.corrupt_container`를 던진다 — 정상 반환된 `format`은 언제나 `unknown` 제외 12값 중 하나다.
- 판별 신뢰도는 §2.5 표대로: 매직+내부검사 일치 1.0(암호화 OOXML만 0.7), 텍스트 계열 json/html/
  md-신호/txt는 0.9/0.8/0.6/0.6(힌트 일치 시 +0.1, 상한 1.0), 힌트만으로 판정한 markdown은 0.5
  고정(가산 없음).
- 라우터 후보 배열 순서는 유일한 우선순위 — 재배열 금지, 건너뛰기만 허용(§4.1). 폴백 대상은
  `parse.sidecar_unavailable`·`parse.conversion_failed`뿐이고 그 외 코드·`contract.violation`은
  체인을 즉시 중단한다(§6.1).
- `quality=degraded`는 "이전 후보가 실패한 뒤 성공"(폴백 발생)일 때만 승격한다. 빈 산출(§6.3)이
  체인의 **마지막** 후보에서 나오면 `quality=full`로 강제 채택한다(빈 문서는 유효 출력).
- `format_detector.py`·`router.py` 모두 포맷별 벤더 어댑터를 임포트하지 않는다 — 후보는
  `StageBuilder.build_stage(plugin_id, ...)`로만 만든다(`adapters`↔`plugins`는 import-linter
  `layers` 계약상 같은 층의 독립 패키지).
- OLE2 CFB 판독은 이 파일이 직접 구현한다(신규 패키지 금지). `FileHeader` 비트 위치는 04-pipelines/03
  §2.3이 "확인 필요(as of 2026-09)"로 표시한 값 그대로 구현했다 — 실물 HWP 5.0 표본 대조는 이 WP 범위
  밖(04 HWPX/HWP WP가 표본 검증).
- 계약 생성물(`src/rag_platform/contracts/**`)은 손편집 금지.

## 단계

1. `detect()`: 매직 바이트(PDF/ZIP/OLE/RTF/HWP3) → 없으면 텍스트 계열(NUL 비율 0 판정 후
   json→html→markdown(신호)→markdown(힌트)→txt) → 어느 것도 아니면 `parse.unsupported_format`.
   ZIP은 `zipfile`(중앙 디렉터리)로 `mimetype`/`content.hpf`+`version.xml`/`[Content_Types].xml`+
   `word/document.xml` 항목만 개별로 풀어 hwpx/docx/odt를 가른다(ZIP 폭탄·1MiB 판정 항목 상한 적용).
   OLE2 CFB는 헤더→FAT→디렉터리(평탄 스캔)→MiniFAT/미니스트림 순으로 직접 파싱해 `FileHeader`/
   `WordDocument`/`EncryptedPackage`+`EncryptionInfo` 내용만 읽는다.
2. `FormatDetectorStage.detect_source()`: `ctx.source_bytes()`로 바이트를 받아 `detect()` 결과를
   입력 `SourceDocument`에 병합(`format`·`format_confidence`·`container_flags`·`media_type`·
   `detect_report`·`producer`·`created_at` 재기입, 봉투·정책 필드는 입력 복사).
3. `ParseRouterStage.run()`: 위 결과로 `router[format]` 조회 → 문자열(종결 코드)이면 즉시 실패 →
   배열이면 `_select_viable`(§4.1 3단계, `KeyError`만으로 필터) → 필터 후 0개면
   `parse.unsupported_format` → 순차 실행(잔여 시간 예산 확인, §5.2) → `StageError` 폴백 분류(§6.1)
   → 빈 산출 시 다음 후보(마지막이면 accept, §6.3) → `_finalize`(`parser_chain[]` 교체, `quality`
   승격, §6.4·§7.2).

## 테스트(파일·케이스) — `tests/adapters/parse/test_router.py`

- `detect()` 매직 바이트: PDF(+`/Encrypt` 트레일러), ZIP(`mimetype=application/hwp+zip`인 hwpx,
  `content.hpf`+`version.xml`뿐인 hwpx, docx, odt, 미상 zip → `parse.unsupported_format`), RTF,
  HWP 3.0 시그니처(→ `parse.unsupported_variant`는 라우터 단에서 검증), 빈 ZIP·손상 ZIP(BadZipFile)
  → `parse.corrupt_container`.
- OLE2 CFB(이 WP가 직접 구성한 최소 유효 컴파운드 파일, MiniFAT/미니스트림 경로 포함): `FileHeader`
  시그니처+버전+속성 비트(hwp5, `ViewText` 플래그 불일치 신호 포함), `WordDocument`(doc),
  `EncryptedPackage`+`EncryptionInfo`(암호화 docx, confidence 0.7), 시그니처 불일치 → `unknown`.
  손상 CFB(잘린 헤더·순환 FAT 체인) → `parse.corrupt_container`.
- 텍스트 계열: JSON 파싱 성공(0.9), HTML 루트 신호(0.8), Markdown ATX/펜스/프론트매터 신호(0.6),
  힌트만의 markdown(0.5, 가산 없음), 평문 txt(0.6), 힌트 일치 가산(+0.1, 상한 1.0), `hint_agrees`
  True/False/None.
- `ParseRouterStage`: 1차 후보 성공(quality 그대로, `parser_chain=[그 후보]`); 1차
  `parse.conversion_failed` → 2차 성공(quality=degraded, `parser_chain` 2개 기록); 1차
  `parse.document_encrypted`(비재시도) → 체인 즉시 중단, 예외 그대로 전파; `contract.violation` →
  체인 중단; 체인 전부 소진 → `parse.conversion_failed`(`cause` 연결); 빈 산출 후보(마지막 아님) →
  다음 후보로 폴백; 빈 산출이 마지막 후보 → `quality=full`로 채택; 미등록 후보(docx, `KeyError`) →
  `parse.unsupported_format`; hwp3(종결 코드 라우팅) → `parse.unsupported_variant`; `remaining_ms`가
  예산 미만 → `parse.conversion_failed`.

## 완료 기준

- 위 테스트 전량 통과, `uv run ruff check src/rag_platform/adapters/parse/format_detector.py
  src/rag_platform/adapters/parse/router.py` 통과.
- import-linter `adapters-no-storage`·`layers` 위반 없음(수동 확인: `rag_platform.plugins`·
  `rag_platform.storage`·`rag_platform.security` 미임포트).

## 검증 계층

1층(여기서 검증) — `uv run pytest -q tests/adapters/parse/test_router.py`. Docker·모델·GPU·외부
네트워크 불필요. DEFERRED 없음(축소 항목은 위 open_issues로 후속 WP에 넘긴다).

결과: 통과 43 / xfail 0 / DEFERRED 0
