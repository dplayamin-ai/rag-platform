# deploy/compose/

Development compose stacks (bible §12, docs/02-architecture/08-deployment-architecture.md):
`compose.lite.yaml`, `compose.lite-durable.yaml`, `compose.observability.yaml`, `.env.example`.

Not runnable on the Windows VDI (no Docker). Tests that need these services are marked
`needs_docker` and listed in the deferred verification ledger.
