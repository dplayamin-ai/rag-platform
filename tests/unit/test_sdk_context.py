"""Unit tests for `rag_platform.sdk.context` (bible §11.1 `PipelineContext`, §4.1 `StageContext`)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from rag_platform.sdk.context import DerivedArtifacts, LocalContext, PipelineContext, SecretsRef
from rag_platform.storage.artifact_store import InMemoryArtifactStore


class _FakeTokenCounter:
    tokenizer_id = "fake"

    def count(self, text: str) -> int:
        return len(text)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _make_context(store: InMemoryArtifactStore, **overrides: object) -> LocalContext:
    defaults: dict[str, object] = {
        "tenant_id": "t1",
        "collection_id": "c1",
        "profile_hash": "ph",
        "trace_id": "tr1",
        "store": store,
        "clock": _utc_now,
    }
    defaults.update(overrides)
    return LocalContext(**defaults)


def test_secrets_ref_resolves_without_exposing_raw_values() -> None:
    secrets = SecretsRef(resolver=lambda ref: f"resolved:{ref}")
    assert secrets.resolve("vault://tenant/api-key") == "resolved:vault://tenant/api-key"


def test_local_context_now_uses_injected_clock() -> None:
    fixed = datetime(2026, 9, 23, tzinfo=UTC)
    store = InMemoryArtifactStore()
    ctx = _make_context(store, clock=lambda: fixed)
    assert ctx.now() == fixed


async def test_local_context_sleep_and_emit_do_not_raise() -> None:
    store = InMemoryArtifactStore()
    ctx = _make_context(store)
    await ctx.sleep(timedelta(seconds=0))
    await ctx.emit({"type": "ingest.document.fetched"})  # local mode: no outbox, just a log call


def test_build_stage_context_binds_tenant_scope_and_lineage() -> None:
    store = InMemoryArtifactStore()
    ctx = _make_context(store)
    stage_ctx = ctx.build_stage_context(
        stage_token_counter=_FakeTokenCounter(), document_id="d1", job_id="j1", lineage={"SourceDocument": object()}
    )
    assert stage_ctx.tenant_id == "t1"
    assert stage_ctx.collection_id == "c1"
    assert stage_ctx.document_id == "d1"
    assert stage_ctx.job_id == "j1"
    assert stage_ctx.trace_id == "tr1"
    assert stage_ctx.profile_hash == "ph"
    assert "SourceDocument" in stage_ctx.lineage
    assert stage_ctx.cancelled is False
    assert stage_ctx.resume_details is None


def test_stage_context_heartbeat_is_a_no_op_and_remaining_ms_reports_budget() -> None:
    store = InMemoryArtifactStore()
    ctx = _make_context(store, budget_ms=800)
    stage_ctx = ctx.build_stage_context(stage_token_counter=_FakeTokenCounter())
    stage_ctx.heartbeat({"page": 3})  # must not raise (bible §11.1: LocalRunner is non-durable)
    assert stage_ctx.remaining_ms() == 800


async def test_tenant_bound_artifacts_put_source_binds_tenant_id() -> None:
    store = InMemoryArtifactStore()
    ctx = _make_context(store)
    stage_ctx = ctx.build_stage_context(stage_token_counter=_FakeTokenCounter())
    assert isinstance(stage_ctx.artifacts, DerivedArtifacts)
    ref = await stage_ctx.artifacts.put_source(b"raw bytes", media_type="application/pdf")
    assert ref.uri.startswith("mem://tenants/t1/sources/")


async def test_tenant_bound_artifacts_put_derived_binds_kind_and_ext() -> None:
    store = InMemoryArtifactStore()
    ctx = _make_context(store)
    stage_ctx = ctx.build_stage_context(stage_token_counter=_FakeTokenCounter())
    ref = await stage_ctx.artifacts.put_derived(b"<html/>", kind="page_image", ext="html", media_type="text/html")
    assert "/derived/page_image/" in ref.uri


def test_pipeline_context_protocol_is_runtime_checkable() -> None:
    class _FakePipelineContext:
        async def run(self, stage, inp_ref, out_type, policy):
            return inp_ref

        async def emit(self, event) -> None:
            return

        def now(self):
            return datetime.now(UTC)

        async def sleep(self, d) -> None:
            return

    assert isinstance(_FakePipelineContext(), PipelineContext)


@pytest.mark.parametrize("missing", ["run", "emit", "now", "sleep"])
def test_pipeline_context_protocol_rejects_missing_member(missing: str) -> None:
    members = {"run": None, "emit": None, "now": lambda self: None, "sleep": None}
    body = {name: (lambda self, *_a, **_kw: None) for name in members if name != missing}

    incomplete = type("Incomplete", (), body)
    assert not isinstance(incomplete(), PipelineContext)
