"""배포판에 포함되는 conformance kit(계층 스택 밖; 바이블 §12 `testing`).

설계 근거: 바이블 §12(모듈 맵, `testing`은 계층 스택 밖), 10-development/01 §4.2(적합성 키트),
ADR-0032(코어와 외부 플러그인이 같은 키트를 실행).
구성 예정: `contract_roundtrip`, `idempotency`, `security_invariants`,
`renderer_citation_roundtrip`, `litm_order`, `fuser_equivalence`, 가짜 `StageContext`/
`RuntimeServices`; 하위 패키지 `doubles`.
불변식: 프로덕션 진입점(`api`, `mcp`, `orchestration`)은 이 패키지를 임포트할 수 없다
(10-development/01 §4.2, import-linter `testing-not-in-production`).
검증 계층: 1층(여기서 검증) — `uv run lint-imports`(계약), `tests/unit/testing/`.
"""

from __future__ import annotations
