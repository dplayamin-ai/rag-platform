"""`[temporal]` extra 뒤에 위치하는 Temporal 바인딩(바이블 §11.1, §11.2; ADR-0003).

설계 근거: 바이블 §11.1(실행기 종류), §11.2(Temporal 워크플로), ADR-0003.
구성 예정: `workflows`, `activities`(범용 래퍼 `stage.{stage_name}` 1종), `worker`, `converters`,
`tracing`, `schedules`.
불변식: `[temporal]` extra 없이는 import되지 않는다 — 코어 경로가 `temporalio`에 의존해서는 안 된다.
검증 계층: 2층 needs_docker — 실제 Temporal 서버는 Docker/Linux 환경에서 검증.
"""

from __future__ import annotations
