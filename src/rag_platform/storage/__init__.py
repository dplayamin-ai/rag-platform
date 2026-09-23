"""아티팩트·캐시 저장 패키지 진입점(셸 레이어, 바이블 §13.3·§12 `storage`) — 코드 없이 자리만 잡는다.

역할: 오브젝트 스토어(`artifact_store`)와 캐시(`valkey`), 오브젝트 키 규약(`keys`)을 모아 두는
패키지.
설계 근거: 바이블 §13.3(오브젝트 키 규약), §12(레이어 지도, `storage`는 셸 레이어).
구성: `artifact_store.py` — `ArtifactStore`/`FileArtifactStore`/`InMemoryArtifactStore`; `keys.py` —
순수 키 생성 함수; `valkey.py` — `KeyValueCache` 프로토콜.
불변식: 실제 클래스·함수는 하위 모듈에 있다 — 이 파일 자체는 아무 것도 정의하지 않는다.
검증 계층: 1층(하위 모듈 테스트) — tests/unit/test_storage_*.py.
"""

from __future__ import annotations
