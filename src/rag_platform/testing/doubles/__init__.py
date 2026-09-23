"""conformance kit 테스트 대역 모음(바이블 §12 `testing`, 계층 스택 밖).

각 대역은 대체하려는 프로덕션 계층의 프로토콜(`ledger.repo.Ledger`, `storage.valkey.KeyValueCache`,
`sdk.ports.Embedder`, `sdk.ports.IndexBackend`)을 구현해, 단위 테스트가 PostgreSQL·Valkey·TEI
서버·Qdrant 클러스터 없이 호출부를 검증하게 한다. 각 모듈은 실 구현이 `needs_docker`/
`needs_model`/`needs_network`로 검증되는 지점을 가리키는 `DEFERRED:` 표기를 담는다(phase-6
계획 §8 3단계 검증).

불변식·주의: 프로덕션 진입점(`api`, `mcp`, `orchestration`)은 이 패키지를 임포트할 수 없다
(import-linter `testing-not-in-production`, 10-development/01 §4.2).
"""

from __future__ import annotations
