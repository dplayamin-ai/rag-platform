"""내장 프로파일 YAML 파일 `base`, `lite`, `standard`, `premium`, `korean-gov`(바이블 §7.1).

설계 근거: 바이블 §7.1(내장 프로파일 목록과 각 계층 기본값).
구성: 프로파일별 YAML 정의 파일 — 다른 프로파일은 `base`에서 `extends`로 파생한다.
불변식: 이 디렉터리의 YAML은 `profiles.schema`로 검증을 통과해야 한다.
검증 계층: 1층(여기서 검증) — `tests/unit/test_profiles_loader.py`.
"""

from __future__ import annotations
