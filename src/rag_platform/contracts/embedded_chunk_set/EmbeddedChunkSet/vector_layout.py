"""GENERATED — 수정 금지. 재생성: `uv run python tools/contracts_gen.py`

역할: `schemas/*.schema.json`의 계약 스키마 하나를 그대로 옮긴 Pydantic v2 모델(계층 L0) — 파이프라인 단계 간에 주고받는 데이터의 타입을 정의한다.
설계 근거: 바이블 §5.1(계약이 정본), §6.4(kebab 스키마 이름 ↔ snake_case 모듈명), §12(레이어 지도).
구성: 클래스명은 스키마의 `title`(또는 `$defs`의 각 항목)과 동일하며, 필드는 스키마의 `properties`/`required`를 그대로 반영한다.
불변식: `tools/contracts_gen.py`만 이 파일을 쓴다 — 손으로 고친 내용은 다음 재생성 때 사라진다.
검증 계층: 1층(여기서 검증) — tests/contracts, tools/validate-contracts.mjs.
"""

from __future__ import annotations

from enum import StrEnum


class Format(StrEnum):
    """
    vectors_ref 컨테이너 형식 인라인 열거({Type}.{path} 등재 규칙, 바이블 §5.7). VectorLayout.format 전용
    """

    npz = "npz"
    parquet = "parquet"


class Dtype(StrEnum):
    """
    vectors_ref 행렬 원소 자료형 인라인 열거({Type}.{path} 등재 규칙, 바이블 §5.7). VectorLayout.dense.dtype·late_interaction.dtype이 공유. 기본 float32. 여러 계약이 쓰게 되면 §5.7 VectorDtype 등재(minor) 후 common-types 승격(00 U-14, 미해결 이슈 2)
    """

    float32 = "float32"
    float16 = "float16"
    bfloat16 = "bfloat16"
    int8 = "int8"
