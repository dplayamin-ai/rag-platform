"""평가 하네스(shell 계층; 바이블 §12 `eval`).

설계 근거: 바이블 §12(모듈 맵).
구성: 계획된 하위 모듈 — `harness`, `runner`(`LocalRunner` 재사용), `trec`, `metrics_ranx`,
`judge_ragas`, `span_hit`, `gates`, `datasets/`.
불변식: 프로덕션 진입점(`api`/`mcp`/`cli`)은 `eval` 하네스를 의존성으로 가져오지 않는다.
검증 계층: 1층(여기서 검증) — 각 하위 모듈 구현 시 개별 단위 테스트로 검증.
"""

from __future__ import annotations
