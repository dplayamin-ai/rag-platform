"""트랜잭션 아웃박스 릴레이(바이블 §12 `orchestration/outbox`).

설계 근거: 바이블 §12(모듈 맵), §11(오케스트레이션의 아웃박스 패턴).
구성 예정: `relay_core`(순수 함수 3종), `temporal_relay`, `procrastinate_relay`, `webhook_signer`.
불변식: 아웃박스 레코드 전송은 최소 1회(at-least-once) — 소비자는 멱등하게 처리해야 한다.
검증 계층: 2층 needs_docker — 실제 릴레이는 PostgreSQL/Valkey가 있는 Docker/Linux 환경에서 검증.
"""

from __future__ import annotations
