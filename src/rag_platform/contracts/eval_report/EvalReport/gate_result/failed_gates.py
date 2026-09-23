"""GENERATED — 수정 금지. 재생성: `uv run python tools/contracts_gen.py`

역할: `schemas/*.schema.json`의 계약 스키마 하나를 그대로 옮긴 Pydantic v2 모델(계층 L0) — 파이프라인 단계 간에 주고받는 데이터의 타입을 정의한다.
설계 근거: 바이블 §5.1(계약이 정본), §6.4(kebab 스키마 이름 ↔ snake_case 모듈명), §12(레이어 지도).
구성: 클래스명은 스키마의 `title`(또는 `$defs`의 각 항목)과 동일하며, 필드는 스키마의 `properties`/`required`를 그대로 반영한다.
불변식: `tools/contracts_gen.py`만 이 파일을 쓴다 — 손으로 고친 내용은 다음 재생성 때 사라진다.
검증 계층: 1층(여기서 검증) — tests/contracts, tools/validate-contracts.mjs.
"""

from __future__ import annotations

from enum import StrEnum


class Condition(StrEnum):
    """
    실패한 게이트 조건 = 프로파일 게이트 객체의 키 이름(바이블 §7.3 eval.gates.* 와 §7.4 gate 객체). 15 EvalGate{min, max, max_regression, p, warn_below}·GateSpec{grid, min_delta, min_delta_pt, min_qrels, max_cost_per_doc_usd} 판정 키와 1:1(EF-15). 인라인 열거 {Type}.{path} 등재 규칙(§5.7). warned_gates 항목도 같은 열거를 쓴다
    """

    min = "min"
    max = "max"
    max_regression = "max_regression"
    p = "p"
    warn_below = "warn_below"
    min_delta = "min_delta"
    min_delta_pt = "min_delta_pt"
    min_qrels = "min_qrels"
    max_cost_per_doc_usd = "max_cost_per_doc_usd"
    grid = "grid"


class Severity(StrEnum):
    """
    fail 은 passed 를 false 로 만들고, warn(warn_below 등)은 warned_gates 에만 기록된다
    """

    fail = "fail"
    warn = "warn"
