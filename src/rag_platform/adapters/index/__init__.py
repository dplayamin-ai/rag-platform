"""`IndexRecord` 배치를 적재하는 인덱스 백엔드 어댑터 모음(바이블 §12 `adapters/index`).

설계 근거: 바이블 §12(모듈 맵), §11.4(`IndexCommit` 세대 사가), 10-development/03 §2.4(어댑터는
`sdk`·`contracts`만 의존).
구성: 구현됨 — `qdrant/`(`filters`, `point_id`, `bm25_sparse`, `backend`). 계획 — `opensearch/`
(`nori_settings`, `dls`), `saga`(`IndexCommit` 생성 사가), `age_graph_store`.
불변식: `storage`·`security`를 import하지 않는다; 벤더 타입은 어댑터 밖으로 새지 않는다.
검증 계층: 1층(여기서 검증) — `tests/adapters/index/test_qdrant_local.py`.
"""

from __future__ import annotations
