"""pydantic-settings 기반 런타임 설정(shell 계층; 바이블 §6.6, §12 `settings`).

설계 근거: 바이블 §6.6(설정 규약), §12(모듈 맵).
구성: 환경변수는 `RAG_` 접두사와 `__` 중첩 구분자를 쓴다(예: `RAG_PG__DSN`).
불변식: `security`·`profiles`와 같은 계층에 있다 — 상위 계층(`api`/`mcp`/`cli`)만 이를 조립한다.
검증 계층: 1층(여기서 검증) — 설정 모델 구현 시 개별 단위 테스트로 검증.
"""

from __future__ import annotations
