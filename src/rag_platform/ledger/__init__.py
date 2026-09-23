"""PostgreSQL 잡·인덱스 원장(shell 계층; 바이블 §13.1, §12 `ledger`).

설계 근거: 바이블 §13.1(원장 스키마), §12(모듈 맵).
구성 예정: `models`, `repo`, `migrations/`, `reconcile`, `consistency_check`, `usage`.
불변식: 모든 테이블은 `tenant_id`와 row level security `FORCE`를 가진다.
검증 계층: 2층 needs_docker — 실제 PostgreSQL은 Docker/Linux 환경에서 검증(`tools/verify/run-deferred.sh`).
"""

from __future__ import annotations
