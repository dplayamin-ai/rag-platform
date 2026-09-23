"""GENERATED — do not edit; run `uv run python tools/contracts_gen.py` to regenerate.

Source of truth: schemas/*.schema.json (bible §5.1, §6.4, §12)."""

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
