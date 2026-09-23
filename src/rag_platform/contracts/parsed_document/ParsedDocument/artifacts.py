"""GENERATED — do not edit; run `uv run python tools/contracts_gen.py` to regenerate.

Source of truth: schemas/*.schema.json (bible §5.1, §6.4, §12)."""

from __future__ import annotations

from enum import StrEnum


class Kind(StrEnum):
    page_image = "page_image"
    figure_crop = "figure_crop"
    table_html = "table_html"
    vendor_json = "vendor_json"
    derived_source = "derived_source"
