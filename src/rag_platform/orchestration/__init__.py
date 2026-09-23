"""실행 셸(shell 계층; 바이블 §11, §12 `orchestration`).

구성 예정: `context`(`StagePolicy` 적용, `run_stage`)와 `dispatcher`(문서별 직렬화, 테넌트
동시성); 하위 패키지 `local`, `temporal`, `outbox`.
"""

from __future__ import annotations
