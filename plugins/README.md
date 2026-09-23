# plugins/

Separately distributed A/B-grade plugins, one directory per distribution `rag-plugin-{name}`
(import `rag_plugin_{name}`), each a uv workspace member (root `pyproject.toml`
`[tool.uv.workspace] members = ["plugins/rag-plugin-*"]`).

- Layout per plugin: `pyproject.toml`, `src/rag_plugin_{name}/`, `tests/`, `README.md`.
- Plugins import only `rag_platform.contracts` and the plugin SDK surface `rag_platform.sdk`.
- GPL/AGPL (C-grade) plugins never live here; they belong to `rag-platform-gpl-sidecars` (ADR-0001).

See docs/10-development/01-repository-structure.md §3.3 and docs/10-development/06-plugin-development-guide.md.
