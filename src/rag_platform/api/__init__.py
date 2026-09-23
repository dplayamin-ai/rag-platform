"""FastAPI 기반 REST API 표면 `/v1`(진입점 계층; 바이블 §14, §12 `api`; ADR-0018).

설계 근거: 바이블 §14(API 표면), §12(모듈 맵), ADR-0018.
구성: 계획된 라우터 — `ingest`, `query`, `render`, `answer`, `jobs`, `documents`, `collections`,
`profiles`, `tenants`, `api_keys`, `plugins`, `schemas`, `version`, `audit_events`, `eval`,
`feedback`, `subscriptions`, `events`(SSE); 더해 `problems`(RFC 9457), `idempotency`.
불변식: API 전용 뷰 DTO의 단일 출처(바이블 §5.1) — 계약 모델을 그대로 응답으로 내보내지 않는다.
검증 계층: 1층(여기서 검증) — 라우터 구현 시 `TestClient` 기반 통합 테스트로 검증.
"""

from __future__ import annotations
