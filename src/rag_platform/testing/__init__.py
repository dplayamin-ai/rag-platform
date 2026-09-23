"""배포판에 포함되는 conformance kit(계층 스택 밖; 바이블 §12 `testing`).

구성 예정: `contract_roundtrip`, `idempotency`, `security_invariants`,
`renderer_citation_roundtrip`, `litm_order`, `fuser_equivalence`, 가짜 `StageContext`/
`RuntimeServices`. 프로덕션 진입점(`api`, `orchestration`)은 이 패키지를 임포트할 수 없다
(10-development/01 §4.2).
"""

from __future__ import annotations
