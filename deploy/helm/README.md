# deploy/helm/

Helm charts (bible §12, docs/02-architecture/08-deployment-architecture.md §4):
`rag-platform/` (production chart with per-profile values) and `rag-platform-data/` (development
and staging umbrella for the data tier).

`rag-platform/profiles/*.yaml` is a generated copy of `src/rag_platform/profiles/builtin/*.yaml`
(10-development/01 §6). GPL/AGPL images from `rag-platform-gpl-sidecars` are referenced only
through `optIn.*` values, all `false` by default (ADR-0001).

Not runnable on the Windows VDI (no Docker or Kubernetes); chart tests are deferred.
