"""Parse adapters producing ``ParsedDocument`` (bible §12 ``adapters/parse``).

Planned modules: ``router`` (``ParseRouterStage``: routing and fallback chain), ``format_detector``,
``hwpx_python_hwpx`` (``owpml_adapter``), ``hwpx_hwpxlib_sidecar`` (encrypted HWPX),
``hwp5_java_sidecar``, ``hwp5_unhwp``, ``hwp5_hwp_hwpx_parser``, ``pdf_docling_standard``
(``docling_to_parsed``), ``pdf_fast_pdftext``, ``docx_docling_docx2python``, ``office_lo_sidecar``,
``html_trafilatura_docling`` and ``text_charset_markdown_it``.
"""

from __future__ import annotations
