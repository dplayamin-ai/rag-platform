"""LLM 클라이언트 어댑터와 토큰 카운터 모음(바이블 §12 `adapters/llm`).

설계 근거: 바이블 §12(모듈 맵), 10-development/03 §2.4(어댑터는 `sdk`·`contracts`만 의존).
구성: 계획된 하위 모듈 — `anthropic`, `openai_compat`, `gemini`, `token_counters`.
불변식: `storage`·`security`를 import하지 않는다; 벤더 타입은 어댑터 밖으로 새지 않는다.
검증 계층: 1층(여기서 검증) — 각 하위 모듈 구현 시 개별 단위 테스트로 검증.
"""

from __future__ import annotations
