"""검색 hot path — 인프로세스로 실행되며 PostgreSQL에 의존하지 않는다(L2 계층; 바이블 §12, ADR-0034).

설계 근거: 바이블 §12(모듈 맵), ADR-0034(hot path는 PostgreSQL 독립).
구성: 계획된 하위 모듈 — `planner`, `filters`(D-09 빌더: security, strategy, user), `channels`,
`fusion`, `hydrate`, `rerank`; 하위 패키지 `postprocess`, `pack`.
불변식: 이 계층은 `ledger`·`storage`(PostgreSQL)에 직접 의존하지 않는다(ADR-0034); hot path
성능을 위해 `sdk` 포트를 통해서만 외부 자원에 접근한다.
검증 계층: 1층(여기서 검증) — 각 하위 모듈 구현 시 개별 단위 테스트로 검증.
"""

from __future__ import annotations
