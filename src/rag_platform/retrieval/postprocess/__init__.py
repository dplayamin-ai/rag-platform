"""`RankedSet`에 적용하는 후처리 단계 모음(바이블 §8.2, §12 `retrieval/postprocess`).

설계 근거: 바이블 §8.2(후처리 단계 순서), §12(모듈 맵).
구성: 계획된 하위 모듈 — `relevance_gate`, `dedup`, `mmr`, `parent_expand`, `sentence_window`,
`compress`.
불변식: 각 단계는 입력 `RankedSet`의 `score_breakdown`을 보존하거나, 바꿀 경우 사유를 남긴다(§8.2).
검증 계층: 1층(여기서 검증) — 각 하위 모듈 구현 시 개별 단위 테스트로 검증.
"""

from __future__ import annotations
