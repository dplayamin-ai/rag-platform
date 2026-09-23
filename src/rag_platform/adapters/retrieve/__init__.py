"""`CandidateSet`을 만드는 검색기(retriever) 어댑터 모음(바이블 §12 `adapters/retrieve`).

설계 근거: 바이블 §12(모듈 맵), 10-development/03 §2.4(어댑터는 `sdk`·`contracts`만 의존).
구성: 계획된 하위 모듈 — `qdrant_dense`, `qdrant_sparse`, `qdrant_sparse_bm25`, `opensearch_bm25`.
불변식: `storage`·`security`를 import하지 않는다; 벤더 타입은 어댑터 밖으로 새지 않는다.
검증 계층: 1층(여기서 검증) — 각 하위 모듈 구현 시 개별 단위 테스트로 검증.
"""

from __future__ import annotations
