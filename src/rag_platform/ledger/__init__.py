"""PostgreSQL 잡·인덱스 원장(shell 계층; 바이블 §13.1, §12 `ledger`).

구성 예정: `models`, `repo`, `migrations/`, `reconcile`, `consistency_check`, `usage`. 모든
테이블은 `tenant_id`와 row level security `FORCE`를 가진다.
"""

from __future__ import annotations
