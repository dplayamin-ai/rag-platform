"""비내구 인프로세스 실행기 `LocalRunner`(바이블 §11.1, §11.6; 모듈 `runner`; ADR-0003).

설계 근거: 바이블 §11.1(실행기 종류), §11.6(비내구 실행기의 재시도·타임아웃 정책), ADR-0003.
구성: `runner`(`LocalRunner` — 문서별 순차 실행, 프로세스 재시작에 취약).
불변식: 내구성 보장이 없다 — 프로세스가 죽으면 진행 중 작업은 유실된다(Temporal 실행기와 대비).
검증 계층: 1층(여기서 검증) — `tests/unit/test_sdk_*`, `tests/unit/conformance`.
"""

from __future__ import annotations
