"""텔레메트리(계층 L1; 바이블 §6.5, §12 `telemetry`).

설계 근거: 바이블 §6.5(텔레메트리 규약), §12(모듈 맵), ADR-0022(Weaver 스키마).
구성: 계획된 하위 모듈 — `otel`(Weaver로 생성한 `gen_ai.*`·`rag.*` 상수, ADR-0022), `metrics`,
`redaction`.
불변식: span attribute 문자열 리터럴은 이 패키지 밖에서 직접 쓰지 않는다 — 항상 이 패키지의 상수를
참조한다.
검증 계층: 1층(여기서 검증) — 각 하위 모듈 구현 시 개별 단위 테스트로 검증.
"""

from __future__ import annotations
