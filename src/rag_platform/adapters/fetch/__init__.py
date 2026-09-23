"""`SourceDocument`를 만드는 fetch 어댑터 모음(바이블 §12 `adapters/fetch`).

설계 근거: 바이블 §12(모듈 맵), 10-development/03 §2.4(어댑터는 `sdk`·`contracts`만 의존).
구성: 계획된 하위 모듈 — `fsspec_httpx`.
불변식: `storage`·`security`를 import하지 않는다; 벤더 타입은 어댑터 밖으로 새지 않는다.
검증 계층: 1층(여기서 검증) — 하위 모듈 구현 시 개별 단위 테스트로 검증.
"""

from __future__ import annotations
