"""`ContextPack`을 만드는 컨텍스트 패킹 모음(바이블 §9.1, §12 `retrieval/pack`).

설계 근거: 바이블 §9.1(컨텍스트 팩 조립 단계), §12(모듈 맵).
구성: 계획된 하위 모듈 — `packer`, `acl_recheck`, `budget_cut`, `reorder`, `citation_align`,
`sufficiency`, `conflicts`, `chunk_text_store`.
불변식: `budget_cut` 이후에도 `ContextPack.budget.used_tokens <= max_context_tokens`를 보장한다(§9.1).
검증 계층: 1층(여기서 검증) — 각 하위 모듈 구현 시 개별 단위 테스트로 검증.
"""

from __future__ import annotations
