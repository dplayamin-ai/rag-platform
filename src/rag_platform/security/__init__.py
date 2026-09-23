"""보안 서비스 모음(shell 계층; 바이블 §10, §12 `security`).

설계 근거: 바이블 §10(보안), §12(모듈 맵).
구성: 계획된 하위 모듈 — `principal_resolver`, `authz_cedar`, `security_context`, `rate_limit`,
`acl_recheck`(`aclrev`), `egress_policy`, `backend_token`(요청별 테넌트 JWT), `key_provider`,
`audit`.
불변식: 바이블 §12는 호출자를 `api`·`retrieval`·`adapters/index`로 제한한다; 그보다 아래 계층은
이 능력을 `sdk` 포트를 통해서만 받는다.
검증 계층: 1층(여기서 검증) — 각 하위 모듈 구현 시 개별 단위 테스트로 검증.
"""

from __future__ import annotations
