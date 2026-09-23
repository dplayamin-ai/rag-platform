"""프로파일 로딩과 검증(shell 계층; 바이블 §7, §12 `profiles`).

설계 근거: 바이블 §7(프로파일), §12(모듈 맵).
구성 예정: `loader`(`extends` 해석), `schema`, `validate`, `profile_hash`; 내장 프로파일은
`builtin/`에 있다.
불변식: `profile_hash`는 결정적이며 프로파일 내용이 바뀌면 반드시 바뀐다(§7 캐시 무효화 근거).
검증 계층: 1층(여기서 검증) — `tests/unit/test_profiles_loader.py`, `tests/unit/test_profiles_validate.py`.
"""

from __future__ import annotations
