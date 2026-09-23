"""플러그인·스테이지 커널 SDK 패키지 진입점(계층 L1, 바이블 §12 `sdk`) — 코드 없이 하위 모듈을 위한 자리다.

역할: 코어 어댑터와 외부 `rag-plugin-*` 배포판이 딛고 서는 안정적 표면을 소유한다.
설계 근거: 바이블 §12(레이어 지도 `contracts ← sdk ← plugins|...`), §6.2(`H()` 콘텐츠 키).
구성: 실제 클래스·함수는 하위 모듈에 있다 — `stage.Stage`/`StageError`, `context.StageContext`/
`PipelineContext`/`DerivedArtifacts`, `policy.StagePolicy`, `ports.TokenCounter`/`Embedder` 등.
불변식: 이 패키지는 `contracts`에만 의존한다(`storage`/`ledger`/`profiles`/`orchestration` import
금지). 저장소 루트의 클라이언트 SDK `sdk/`(10-development/01 §2.5)와는 다른 패키지다.
검증 계층: 1층(하위 모듈 테스트) — tests/unit/test_sdk_*.py.
"""

from __future__ import annotations
