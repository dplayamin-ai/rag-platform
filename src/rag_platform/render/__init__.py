"""`ContextPack`을 `RenderedContext`로 바꾸는 렌더러 모음(L2 계층; 바이블 §9.3, §12 `render`).

설계 근거: 바이블 §9.3(렌더 계약), §12(모듈 맵).
구성: 계획된 하위 모듈 — `anthropic_search_result`, `anthropic_document`, `openai_messages`,
`gemini_messages`, `xml_documents`, `markdown`, `mcp_tool_result`, `plain_records`,
`dify_external_knowledge`, `citation_map`.
불변식: 각 렌더러는 `ContextPack.items[].cite_id`를 보존해 인용 왕복(citation round-trip)이 깨지지
않게 한다(§9.3).
검증 계층: 1층(여기서 검증) — `tests/unit/testing/test_renderer_citation_roundtrip.py`.
"""

from __future__ import annotations
