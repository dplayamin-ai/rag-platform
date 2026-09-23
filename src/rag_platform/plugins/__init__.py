"""플러그인 탐색 패키지 진입점(계층 L2, 바이블 §12 `plugins`) — 코드 없이 하위 모듈을 위한 자리다.

역할: `rag_platform.{extension_point}` 그룹(바이블 §6.7)의 엔트리 포인트 레지스트리, `PluginMeta`
검증, `license_gate`(D-02, ADR-0001), `capabilities_check`를 감싸는 패키지.
설계 근거: 바이블 §12(레이어 지도), §6.7(엔트리 포인트 그룹 이름 규약).
구성: 실제 구현은 `registry.py`에 있다 — `PluginRegistry`, `validate_plugin_meta`, `check_license`,
`check_capabilities`, `entry_point_group`.
불변식: 레지스트리는 단계 클래스를 엔트리 포인트로 동적으로만 찾는다 — 어댑터 모듈을 정적으로
import하지 않는다.
검증 계층: 1층(하위 모듈 테스트) — tests/unit/test_plugins_registry.py.
"""

from __future__ import annotations
