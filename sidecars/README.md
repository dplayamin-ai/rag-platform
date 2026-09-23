# sidecars/

A-grade sidecar images, not uv workspace members and without any `rag_platform` dependency.
Conversion sidecars expose `POST /v1/convert` and `GET /healthz` (ADR-0033).

- `parser-workers/` (planned): Java 21, Maven — hwplib, hwp2hwpx, hwpxlib, Tika HwpV5Parser.
- `ocr-gpu/` (planned): PaddleOCR PP-OCRv5 server with its own `pyproject.toml` and `uv.lock`.

GPL/AGPL images (`lo-sidecar`, pyhwp, pymupdf) are kept in the separate repository
`rag-platform-gpl-sidecars`; only Helm `optIn.*` values reference them (bible §6.7, ADR-0001).
