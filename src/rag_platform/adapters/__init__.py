"""벤더 어댑터 모음 — 확장 지점(extension point)마다 하위 패키지 하나(계층 L2; 바이블 §12 `adapters`).

설계 근거: 바이블 §12(계층 지도), 10-development/03 §2.4("Adapters over Forks" — 포크 대신 어댑터), ADR-0035.
구성: 하위 패키지는 `chunk`/`enrich`/`fetch`/`index`/`llm`/`normalize`/`parse`/`query`/`rerank`/`retrieve` 등
확장 지점별로 나뉘며, 각 디렉터리는 최소 하나의 entry point를 등록한다.
불변식: 어댑터는 `sdk`·`contracts`에만 의존한다 — `storage`·`security`는 절대 import하지 않는다(ArtifactRef
적재는 shell의 몫이다); 벤더 고유 타입은 어댑터 모듈 밖으로 새지 않는다.
검증 계층: 1층(여기서 검증) — `uv run lint-imports`(계약 "adapters never import storage/security").
"""

from __future__ import annotations
