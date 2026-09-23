"""GENERATED — do not edit; run `uv run python tools/contracts_gen.py` to regenerate.

Source of truth: schemas/*.schema.json (bible §5.1, §6.4, §12)."""

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
