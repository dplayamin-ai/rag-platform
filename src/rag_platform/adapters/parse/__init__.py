"""`ParsedDocument`를 만드는 파싱 어댑터 모음(바이블 §12 `adapters/parse`).

설계 근거: 바이블 §12(모듈 맵), 10-development/03 §2.4(어댑터는 `sdk`·`contracts`만 의존).
구성: 구현됨 — `hwpx_python_hwpx`(`owpml_adapter`). 계획 — `router`(`ParseRouterStage`: 라우팅·폴백
체인), `format_detector`, `hwpx_hwpxlib_sidecar`(암호화 HWPX), `hwp5_java_sidecar`, `hwp5_unhwp`,
`hwp5_hwp_hwpx_parser`, `pdf_docling_standard`(`docling_to_parsed`), `pdf_fast_pdftext`,
`docx_docling_docx2python`, `office_lo_sidecar`, `html_trafilatura_docling`, `text_charset_markdown_it`.
불변식: `storage`·`security`를 import하지 않는다; 벤더 타입은 어댑터 밖으로 새지 않는다.
검증 계층: 1층(여기서 검증) — `tests/adapters/parse/test_hwpx.py`.
"""

from __future__ import annotations
