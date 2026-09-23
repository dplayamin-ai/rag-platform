"""MCP 서버 표면(진입점 계층; 바이블 §12 `mcp`; ADR-0025).

설계 근거: 바이블 §12(모듈 맵), ADR-0025(MCP 우선 소비).
구성: 계획된 모듈 — `McpToolAdapter`, 도구 `search`/`get_document`/`list_collections`,
`cursor_store`.
불변식: 프로덕션 코어 로직을 재구현하지 않는다 — `api`가 쓰는 것과 같은 서비스 계층을 호출한다.
검증 계층: 1층(여기서 검증) — 각 도구 구현 시 개별 통합 테스트로 검증.
"""

from __future__ import annotations
