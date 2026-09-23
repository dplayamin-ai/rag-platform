"""`rag` CLI 하위 명령 구현 — `ingest`/`query`/`serve`/`profile validate`(바이블 §12 `cli`, F5-03).

역할: 전체 플랫폼을 단일 프로세스에서 인프로세스로 잇는 "lite-dev" 실행기. `ingest`는 F1~F3 실 어댑터
(fetch·parse·normalize·chunk·enrich·embed·index)를 `LocalRunner`로 엮어 `IndexCommit`까지 만들고,
`query`는 F4 실 모듈(planner·channels·fusion·hydrate·postprocess·pack·render)을 `pipelines.query.
run_query`의 6-Protocol에 배선해 `ContextPack`을 만든다 — 두 파이프라인 정의 자체의 문서화된 배선
공백("이 배선은 F5의 몫", `pipelines/ingest.py`·`pipelines/query.py` 참고)을 이 파일이 메운다.
설계 근거: 바이블 §11.6(5분 기동 절차)·§12(cli 명령·계층), §7.1(lite 컴포넌트 표);
`docs/13-implementation/wp/WP-503-cli-and-full-e2e.md`.
구성: `ingest_paths`/`run_query_lite` — 공개 진입점(테스트·`main` 공용); `_Registry` — 컬렉션/문서
ID를 상태 디렉터리에 영속화; `_LitePipelineContext` — 수집 측 `PipelineContext`; `_call_*` — 질의
측 6-Protocol 어댑터; `build_arg_parser`/`main` — argparse CLI.
불변식·주의: 모델 가중치 다운로드 없음(`InprocessFakeEmbedder`). `cli`는 최상위 계층이라 `api`/`mcp`를
import하지 않는다(import-linter `layers`, 같은 층 형제 금지) — `serve api|mcp`는 서브프로세스로
띄운다. 물리 Qdrant 별칭은 플래너 규약 `col_{collection_id}_vec`로 고정해 수집·질의가 같은 컬렉션을
가리키게 한다.
검증 계층: 1층(여기서 검증) — `tests/e2e/test_full_e2e.py`. `serve`의 실 서버 기동과
`deploy/compose/compose.lite.yaml`은 `# DEFERRED: needs_docker`(run-deferred.sh).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from pydantic import AnyUrl
from ulid import ULID

from rag_platform.adapters.chunk.structure_aware import StructureAwareChunkerConfig, StructureAwareChunkerStage
from rag_platform.adapters.embed.inprocess_fake import InprocessFakeEmbedder
from rag_platform.adapters.enrich.derived_meta import DerivedMetaEnricher
from rag_platform.adapters.enrich.deterministic_prefix import DeterministicPrefixEnricher
from rag_platform.adapters.enrich.korean_keywords import KoreanKeywordsEnricher
from rag_platform.adapters.fetch.fsspec_httpx import FetchConfig, FsspecHttpxFetcher
from rag_platform.adapters.index.qdrant.backend import CollectionLayout, QdrantIndexBackend
from rag_platform.adapters.index.qdrant.bm25_sparse import WhitespaceTokenizer, document_vector
from rag_platform.adapters.index.qdrant.hydrate import QdrantHydrateBackend
from rag_platform.adapters.normalize.stage import NormalizerChainConfig, NormalizerChainStage
from rag_platform.adapters.parse.html_trafilatura_docling import HtmlParserConfig, HtmlTrafilaturaDoclingParser
from rag_platform.adapters.parse.hwpx_python_hwpx import HwpxParserConfig, HwpxPythonHwpxParser
from rag_platform.adapters.parse.pdf_fast_pdftext import PdfFastParserConfig, PdfFastPdftextParser
from rag_platform.adapters.parse.router import ParseRouterStage
from rag_platform.adapters.parse.text_charset_markdown_it import TextCharsetMarkdownItParser, TextParserConfig
from rag_platform.adapters.retrieve.qdrant_dense import QdrantDenseRetriever
from rag_platform.adapters.retrieve.qdrant_sparse_bm25 import QdrantSparseBm25Retriever
from rag_platform.contracts import common_types as ct
from rag_platform.contracts.chunk_set import ChunkSet, NormalizedRef
from rag_platform.contracts.cloud_event_envelope import CloudEventEnvelope
from rag_platform.contracts.context_pack import ContextPack, RenderHints, TokenizerSpec
from rag_platform.contracts.context_pack.ContextPack.budget.tokenizer import Provider as TokenizerProvider
from rag_platform.contracts.embedded_chunk_set import EmbeddedChunkSet
from rag_platform.contracts.enriched_chunk_set import EnrichedChunkSet
from rag_platform.contracts.index_commit import IndexCommit
from rag_platform.contracts.index_record import IndexRecord
from rag_platform.contracts.ingest_request import IngestRequest
from rag_platform.contracts.normalized_document import NormalizedDocument, ParsedRef
from rag_platform.contracts.parsed_document import ParsedDocument
from rag_platform.contracts.query_request import QueryRequest
from rag_platform.contracts.ranked_set import PostprocessReport, PostprocessStepReport, RankedSet
from rag_platform.contracts.source_document import SourceDocument
from rag_platform.orchestration.local.runner import LocalRunner, StageSpec
from rag_platform.pipelines import ingest as ingest_pipeline, query as query_pipeline
from rag_platform.profiles.loader import load_profile
from rag_platform.profiles.validate import ProfileInvalidError, validate_loading_rules, validate_schema
from rag_platform.render import anthropic_search_result, markdown
from rag_platform.retrieval import channels, fusion, hydrate as hydrate_stage, planner
from rag_platform.retrieval.pack import packer
from rag_platform.retrieval.pack.budget_cut import BudgetCutConfig
from rag_platform.retrieval.postprocess import dedup as dedup_stage, relevance_gate
from rag_platform.sdk.channel_run import QueryVectors, Retriever
from rag_platform.sdk.hashing import blake3_hex, hash_of, point_id_for_record, record_id
from rag_platform.sdk.policy import StagePolicy
from rag_platform.storage.artifact_store import ArtifactRef as StoreRef, FileArtifactStore

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Mapping, MutableMapping, Sequence

    from rag_platform.contracts.candidate_set import CandidateSet
    from rag_platform.contracts.query_plan import QueryPlan

__all__ = [
    "build_arg_parser",
    "build_backend",
    "build_embedder",
    "build_query_deps",
    "ingest_paths",
    "main",
    "resolve_collection",
    "run_query_lite",
    "security_context_for",
]

# ---------------------------------------------------------------------------------------------
# 상수 — lite 프로파일 고정값(바이블 §7.2 표)과 이 WP의 개발 편의 규약.
# ---------------------------------------------------------------------------------------------
_PROFILE_ALIASES: dict[str, str] = {"lite-dev": "lite"}  # open_issues: 진짜 `lite-dev.yaml`은 없음
_DEFAULT_STATE_DIR = Path(".rag")
_SUPPORTED_EXTENSIONS = frozenset({".txt", ".md", ".markdown", ".json", ".html", ".htm", ".hwpx", ".pdf"})
_TOKENIZER_ID = "hf:BAAI/bge-m3"
_EMBED_DIM = 16
_LITE_TAU = 0.20  # relevance_gate.tau
_LITE_COSINE_THRESHOLD = 0.95
_LITE_MINHASH = {"num_perm": 128, "seed": 42, "threshold": 0.8}
_LITE_PACK_K_MAX = 10
_LITE_PACK_MAX_CONTEXT_TOKENS = 12_000
_LITE_PACK_RESERVED_ANSWER_TOKENS = 2_000
_LITE_CONFIDENCE_HIGH = 0.7
_LITE_CONFIDENCE_MEDIUM = 0.4
# lite.yaml 정본 채널 `timeout_ms`(250)는 서버 Qdrant를 겨냥한 값이다 — 이 WP의 온디스크 로컬
# 모드는 매 질의마다 `QdrantClient(path=...)`를 새로 열어 저장소를 다시 불러오므로(§4.3
# "결과 캐시 금지"와 별개로, 이 셸이 매 호출마다 새 백엔드 인스턴스를 만드는 개발 편의 때문에)
# 콜드 스타트 지연이 250ms를 넘기면 `retrieve.unavailable`로 잘못 실패할 수 있다(open_issues) —
# CLI 전용 `PlannerDefaults`로만 완화한다(lite.yaml 자체는 손대지 않는다).
_CLI_CHANNEL_TIMEOUT_MS = 5_000
_WIN_DRIVE_URI_RE = re.compile(r"^file:///([A-Za-z]:)")

_MEDIA_TYPE_OF: dict[str, str] = {
    "SourceDocument": "application/vnd.rag.source-document+json",
    "ParsedDocument": "application/vnd.rag.parsed-document+json",
    "NormalizedDocument": "application/vnd.rag.normalized-document+json",
    "ChunkSet": "application/vnd.rag.chunk-set+json",
    "EnrichedChunkSet": "application/vnd.rag.enriched-chunk-set+json",
    "EmbeddedChunkSet": "application/vnd.rag.embedded-chunk-set+json",
}


def resolve_profile_id(profile: str) -> str:
    """CLI `--profile` 값을 실제 `profiles/builtin/*.yaml` id로 푼다(`lite-dev` → `lite`, open_issues)."""
    return _PROFILE_ALIASES.get(profile, profile)


def physical_alias_for(collection_id: str) -> str:
    """플래너 채널 별칭 규약과 맞춘 물리 Qdrant 컬렉션 이름(`retrieval.planner._build_channels`)."""
    return f"col_{collection_id}_vec"


# ---------------------------------------------------------------------------------------------
# 상태 디렉터리 레지스트리 — 별도 CLI 실행 간 tenant_id/collection_id/document_id를 영속화한다.
# ---------------------------------------------------------------------------------------------


@dataclass
class _Registry:
    """`<state_dir>/collections.json` — 컬렉션 이름 → (tenant_id, collection_id, 문서 ID) 매핑."""

    path: Path
    data: dict[str, Any] = field(default_factory=lambda: {"collections": {}})

    @classmethod
    def load(cls, path: Path) -> _Registry:
        """존재하면 읽고, 없으면 빈 레지스트리를 새로 만든다."""
        if path.is_file():
            return cls(path=path, data=json.loads(path.read_text(encoding="utf-8")))
        return cls(path=path)

    def save(self) -> None:
        """레지스트리를 디스크에 기록한다(상위 디렉터리 생성 포함)."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=2, ensure_ascii=False), encoding="utf-8")

    def collection(self, name: str, *, profile_id: str, create: bool) -> dict[str, Any]:
        """컬렉션 항목을 찾거나(`create=True`) 새로 발급한다."""
        entry = self.data["collections"].get(name)
        if entry is not None:
            return cast("dict[str, Any]", entry)
        if not create:
            msg = f"unknown collection {name!r}; run `rag ingest --collection {name} ...` first"
            raise KeyError(msg)
        entry = {"tenant_id": str(ULID()), "collection_id": str(ULID()), "profile_id": profile_id, "documents": {}}
        self.data["collections"][name] = entry
        return entry

    def document_id_for(self, entry: dict[str, Any], source_path: str) -> str:
        """경로별 `document_id`를 재사용하거나(재수집 멱등) 새로 발급한다."""
        document_id = entry["documents"].get(source_path)
        if document_id is None:
            document_id = str(ULID())
            entry["documents"][source_path] = document_id
        return cast("str", document_id)


# ---------------------------------------------------------------------------------------------
# 공용 소품 — 저장소 참조 변환, 시계, 토큰 카운터.
# ---------------------------------------------------------------------------------------------


def _root_value(value: Any) -> Any:
    """Pydantic `RootModel`(`Uri`/`Hex64`/`Ulid`/...)을 평범한 값으로 벗긴다."""
    return value.root if hasattr(value, "root") else value


def _normalize_file_uri(uri: str) -> str:
    """Windows `file:///C:/...`(3슬래시)를 `FileArtifactStore`가 읽는 `file://C:/...`로 되돌린다."""
    return _WIN_DRIVE_URI_RE.sub(r"file://\1", uri)


def _to_store_ref(ref: Any) -> StoreRef:
    """계약 `ArtifactRef`(어떤 모양이든)를 `storage`의 평범한 dataclass ref로 바꾼다."""
    return StoreRef(
        uri=_normalize_file_uri(str(_root_value(ref.uri))),
        blake3=str(_root_value(ref.blake3)),
        media_type=str(_root_value(ref.media_type)),
        size_bytes=ref.size_bytes,
    )


def _as_contract_ref(ref: StoreRef) -> ct.ArtifactRef:
    """`storage.ArtifactRef`를 계약 `common_types.ArtifactRef`로 감싼다(`DerivedArtifacts` 반환 모양)."""
    return ct.ArtifactRef(
        uri=ct.Uri(AnyUrl(ref.uri)),
        blake3=ct.Hex64(ref.blake3),
        media_type=ct.MediaType(ref.media_type),
        size_bytes=ref.size_bytes,
        schema_type=ct.SchemaTypeName(ref.schema_type) if ref.schema_type is not None else None,
        schema_version=ct.Semver(ref.schema_version) if ref.schema_version is not None else None,
        stage_key=ct.Hex64(ref.stage_key) if ref.stage_key is not None else None,
    )


def _ref_dict(ref: StoreRef, schema_type: str) -> dict[str, Any]:
    """`{source,parsed,...}` lineage_refs 항목 하나를 정확한 리터럴 모양으로 만든다."""
    return {
        "uri": ref.uri,
        "blake3": ref.blake3,
        "media_type": _MEDIA_TYPE_OF[schema_type],
        "schema_type": schema_type,
        "schema_version": "1.0.0",
        "size_bytes": ref.size_bytes,
        "stage_key": ref.stage_key,
    }


def _fixup_lineage_media_types(lineage_refs: dict[str, Any]) -> dict[str, Any]:
    """상류 `lineage_refs`의 `media_type`/`schema_type`을 `EnrichedChunkSet` 등이 요구하는 리터럴로 재기입."""
    key_to_schema_type = {
        "source": "SourceDocument",
        "parsed": "ParsedDocument",
        "normalized": "NormalizedDocument",
        "chunk_set": "ChunkSet",
        "enriched": "EnrichedChunkSet",
        "embedded": "EmbeddedChunkSet",
    }
    fixed: dict[str, Any] = {}
    for key, value in lineage_refs.items():
        schema_type = key_to_schema_type.get(key)
        if value is None or schema_type is None:
            continue
        fixed[key] = {
            "uri": value["uri"],
            "blake3": value["blake3"],
            "media_type": _MEDIA_TYPE_OF[schema_type],
            "schema_type": schema_type,
            "schema_version": "1.0.0",
            "size_bytes": value["size_bytes"],
            "stage_key": value.get("stage_key"),
        }
    return fixed


class _Clock:
    """`ctx.now()`만 필요로 하는 호출부(질의 측 협력자)를 위한 최소 시계."""

    def now(self) -> datetime:
        """벽시계 UTC(셸 계층은 `datetime.now(UTC)` 직접 호출이 허용된다, 03 sec. 10.1)."""
        return datetime.now(UTC)


class _ApproxTokenCounter:
    """`sdk.ports.TokenCounter` 최소 구현 — 문자 기반 근사(모델 다운로드 없음)."""

    tokenizer_id = _TOKENIZER_ID

    def count(self, text: str) -> int:
        """문자 3개당 토큰 1개로 근사한다(실 토크나이저 미다운로드, lite 개발 기본값)."""
        return max(1, len(text) // 3)


class _Artifacts:
    """`sdk.context.DerivedArtifacts` 포트 — 테넌트 바운드 `FileArtifactStore` 래퍼."""

    def __init__(self, store: FileArtifactStore, tenant_id: str) -> None:
        """저장소와 테넌트를 고정한다."""
        self._store = store
        self._tenant_id = tenant_id

    async def put_source(self, data: bytes, *, media_type: str) -> ct.ArtifactRef:
        """원본 바이트를 저장한다."""
        ref = await self._store.put_source(data, tenant_id=self._tenant_id, media_type=media_type)
        return _as_contract_ref(ref)

    async def put_derived(self, data: bytes, *, kind: str, ext: str, media_type: str) -> ct.ArtifactRef:
        """파생 바이트를 저장한다."""
        ref = await self._store.put_derived(data, tenant_id=self._tenant_id, kind=kind, ext=ext, media_type=media_type)
        return _as_contract_ref(ref)


class _StageCtx:
    """`StageContext` 최소 구현(바이블 §4.1) — 키워드 인자로 스테이지별 부가 필드를 얹는다."""

    def __init__(self, *, clock: _Clock, **kwargs: Any) -> None:
        """공통 필드를 기본값으로 채우고 `kwargs`로 스테이지별 부가 필드를 덮어쓴다."""
        self._clock = clock
        self.heartbeats: list[dict[str, Any]] = []
        self.lineage: dict[str, Any] = {}
        self.plan = None
        self.resume_details = None
        self.cancelled = False
        for key, value in kwargs.items():
            setattr(self, key, value)

    def now(self) -> datetime:
        """주입된 시계를 그대로 돌려준다."""
        return self._clock.now()

    def heartbeat(self, details: dict[str, Any]) -> None:
        """`ResumeCursor` 세부값을 기록한다(이 셸은 재개하지 않는다)."""
        self.heartbeats.append(dict(details))

    def remaining_ms(self) -> int | None:
        """예산 무제한(`None`) — 이 셸은 라우터 후보 예산 체크에 걸리지 않는다."""
        return None


class _ParserBuilder:
    """`parser.router`의 `StageBuilder` 포트 — 등록된 후보만 만들고, 나머지는 `KeyError`(§4.1 3단계)."""

    def __init__(self, factories: dict[str, Callable[[], Any]]) -> None:
        """`plugin_id → 0인자 팩토리` 매핑을 고정한다."""
        self._factories = factories

    def build_stage(self, plugin_id: str, config: Mapping[str, Any], services: Any = None) -> Any:
        """등록된 `plugin_id`의 스테이지를 만든다. 미등록이면 `KeyError`."""
        del config, services
        if plugin_id not in self._factories:
            raise KeyError(plugin_id)
        return self._factories[plugin_id]()


@dataclass
class _AdapterStage:
    """실 `Stage[In, Out]`(또는 손으로 엮은 콜러블) 하나를 `LocalRunner`의 `Stage[bytes, bytes]`로 감싼다."""

    plugin_id: str
    in_type: type[Any]
    fp: str
    call: Callable[[Any, Any], Awaitable[Any]]
    config_schema: type = object
    requires_lineage: tuple[str, ...] = ()

    def capabilities(self) -> Any:
        """`LocalRunner`는 호출하지 않는다 — `Stage` 5멤버 모양을 채우기만 한다."""
        return None

    def fingerprint(self) -> str:
        """감싼 실 스테이지 자신의 지문을 그대로 돌려준다."""
        return self.fp

    async def run(self, inp: bytes, ctx: Any) -> bytes:
        """`in_type`으로 역직렬화 → 실 스테이지 실행 → JSON 바이트로 재직렬화."""
        model_in = self.in_type.model_validate_json(inp)
        model_out = await self.call(model_in, ctx)
        return cast("bytes", model_out.model_dump_json().encode("utf-8"))


class _LiteProfile:
    """`pipelines.ingest.PipelineProfile` 구현 — 모든 스테이지 켬, `recount`는 끔(임베더 토크나이저 일치)."""

    _policy = StagePolicy(
        task_queue="ingest-cpu", start_to_close=timedelta(minutes=5), heartbeat=None, max_attempts=3, resumable=False
    )

    def has_stage(self, stage: str) -> bool:
        """`recount`만 끈다 — 페이크 임베더 토크나이저가 청커와 이미 일치한다."""
        return stage != "recount"

    def stage_policy(self, _stage: str) -> StagePolicy:
        """모든 스테이지에 같은 관대한 정책을 돌려준다(재시도가 실제로 발동할 일이 없다)."""
        return self._policy


def _dense_space_id(dim: int) -> str:
    """`embedding_space_ids.dense` 값(페이크 임베더 + 차원으로 결정)."""
    return hash_of("space", "embedder.inprocess_fake", "dense", str(dim))


def _sparse_space_id(analyzer_id: str) -> str:
    """`embedding_space_ids.sparse_bm25` 값(분석기 ID로 결정)."""
    return hash_of("space", "sparse_bm25", analyzer_id)


def _enrichment_dict(bucket: MutableMapping[str, Any], chunk: ct.Chunk) -> dict[str, Any]:
    """결정적 보강기가 채우지 않는 플랫폼 합성 필드를 기본값으로 채운다."""
    return {
        "embed_text": bucket.get("embed_text", chunk.text),
        "index_text": bucket.get("index_text", chunk.lexical_text),
        "strip_offsets": bucket.get("strip_offsets", {"text_start_in_embed": 0, "text_start_in_index": 0}),
        "keywords": bucket.get("keywords", []),
        "entities": [],
        "dates": bucket.get("dates"),
        "law_refs": bucket.get("law_refs"),
        "risk_flags": [],
        "risk_score": 0.0,
        "pii_entity_counts": {},
        "status": "complete",
    }


def _build_enriched_payload(
    *, chunk_set: ChunkSet, self_ref: StoreRef, enricher_fp: str, enrichments: dict[str, Any]
) -> dict[str, Any]:
    """`EnrichedChunkSet` 봉투를 이미 계산된 `enrichments`로 조립한다."""
    chunk_set_dump = chunk_set.model_dump(mode="json")
    return {
        "schema_version": "1.0.0",
        "schema_type": "EnrichedChunkSet",
        "tenant_id": chunk_set_dump["tenant_id"],
        "collection_id": chunk_set_dump["collection_id"],
        "producer": {
            "plugin_id": "enricher.cli_lite",
            "plugin_version": "0.1.0",
            "config_hash": hash_of("config", "cli_lite"),
            "image_digest": None,
            "model_ids": [],
        },
        "quality": chunk_set_dump["quality"],
        "warnings": [],
        "created_at": _rfc3339_ms(datetime.now(UTC)),
        "lineage_refs": {
            **_fixup_lineage_media_types(chunk_set_dump["lineage_refs"]),
            "chunk_set": _ref_dict(self_ref, "ChunkSet"),
        },
        "chunk_set_id": chunk_set_dump["chunk_set_id"],
        "document_id": chunk_set_dump["document_id"],
        "doc_version": chunk_set_dump["doc_version"],
        "chunk_set_ref": _ref_dict(self_ref, "ChunkSet"),
        "enricher_fingerprint": enricher_fp,
        "policy_hash": hash_of("policy", "cli_lite"),
        "status": "complete",
        "budget_used": {
            "provider": None,
            "model_id": None,
            "llm_tokens_in": 0,
            "llm_tokens_out": 0,
            "cost_usd": 0,
            "calls": 0,
            "budget_remaining_tokens": 0,
        },
        "enrichments": enrichments,
        "stats": {
            "chunks_enriched": len(enrichments),
            "llm_cache_hits": 0,
            "entities_total": 0,
            "chunks_partial": 0,
        },
    }


def _build_embedded_payload(
    *,
    enriched: EnrichedChunkSet,
    self_ref: StoreRef,
    embedder: InprocessFakeEmbedder,
    vectors: dict[str, Any],
    vectors_ref: ct.ArtifactRef,
    dense_space: str,
    sparse_space: str,
) -> dict[str, Any]:
    """`EmbeddedChunkSet` 봉투를 이미 계산된 `vectors`로 조립한다."""
    enriched_dump = enriched.model_dump(mode="json")
    embedding_profile_hash = hash_of("spaces", f"dense={dense_space}", f"sparse_bm25={sparse_space}")
    return {
        "schema_version": "1.0.0",
        "schema_type": "EmbeddedChunkSet",
        "tenant_id": enriched_dump["tenant_id"],
        "collection_id": enriched_dump["collection_id"],
        "producer": {
            "plugin_id": embedder.plugin_id,
            "plugin_version": "0.1.0",
            "config_hash": hash_of("config", "cli_lite"),
            "image_digest": None,
            "model_ids": [],
        },
        "quality": enriched_dump["quality"],
        "warnings": [],
        "created_at": _rfc3339_ms(datetime.now(UTC)),
        "lineage_refs": {
            **_fixup_lineage_media_types(enriched_dump["lineage_refs"]),
            "enriched": _ref_dict(self_ref, "EnrichedChunkSet"),
        },
        "chunk_set_id": enriched_dump["chunk_set_id"],
        "document_id": enriched_dump["document_id"],
        "doc_version": enriched_dump["doc_version"],
        "enriched_ref": _ref_dict(self_ref, "EnrichedChunkSet"),
        "embedding_space_ids": {"dense": dense_space, "sparse_bm25": sparse_space},
        "embedding_profile_hash": embedding_profile_hash,
        "embedder_fingerprint": hash_of(
            "embedder", embedder.plugin_id, "0.1.0", hash_of("config", "cli_lite"), "", embedding_profile_hash
        ),
        "mode": "document",
        "pooling": "cls",
        "vectors_ref": {
            "uri": _root_value(vectors_ref.uri),
            "blake3": _root_value(vectors_ref.blake3),
            "media_type": "application/json",
            "size_bytes": vectors_ref.size_bytes,
        },
        "vectors": vectors,
        "cache_hits": 0,
        "stats": {
            "vectors_total": len(vectors),
            "bytes_dense": len(vectors) * embedder.dim * 4,
            "bytes_sparse": 0,
            "bytes_late_interaction": 0,
        },
    }


def _build_index_record(
    *,
    chunk: ct.Chunk,
    enrichment: Any,
    dense_vector: list[float],
    sparse_bm25: dict[str, Any],
    source_dump: dict[str, Any],
    chunk_set_dump: dict[str, Any],
    embedded_dump: dict[str, Any],
    scope: tuple[str, str, str],
    commit_id: str,
    generation: int,
    title: str,
) -> IndexRecord:
    """실 상류 `Chunk`/`SourceDocument` 필드로부터 leaf/level-2 `IndexRecord` 하나를 만든다."""
    tenant_id, collection_id, document_id = scope
    chunk_dump = chunk.model_dump(mode="json")
    chunk_id = chunk_dump["chunk_id"]
    acl = source_dump["acl"]
    metadata = source_dump.get("metadata") or {}
    text = chunk_dump["text"]
    rid = record_id(tenant_id, collection_id, document_id, generation, chunk_id)
    payload = {
        "record_id": rid,
        "point_id": str(point_id_for_record(rid)),
        "chunk_id": chunk_id,
        "tenant_id": tenant_id,
        "collection_id": collection_id,
        "document_id": document_id,
        "doc_version": chunk_set_dump["doc_version"],
        "commit_id": commit_id,
        "index_generation": generation,
        "is_current": False,
        "item_kind": chunk_dump["item_kind"],
        "level": chunk_dump["level"],
        "parent_chunk_id": chunk_dump.get("parent_chunk_id"),
        "ordinal": chunk_dump["ordinal"],
        "vectors": {"dense": list(dense_vector), "sparse_bm25": sparse_bm25},
        "index_text": enrichment.index_text,
        "lexical_terms": sorted({keyword.term for keyword in enrichment.keywords}),
        "text": text[:8192],
        "text_preview": text[:200],
        "text_truncated": False,
        "context_prefix": chunk_dump["context_prefix"]["deterministic"] or "",
        "block_refs": chunk_dump["block_refs"],
        "sentence_spans": chunk_dump["sentence_spans"],
        "title": title[:512],
        "heading_path": chunk_dump["heading_path"],
        "numbering_path": chunk_dump.get("numbering_path") or [],
        "source_uri": source_dump["source_uri"],
        "external_id": source_dump.get("external_id"),
        "doc_date": metadata.get("doc_date"),
        "doc_type": metadata.get("doc_type"),
        "department": metadata.get("department"),
        "tags": metadata.get("tags"),
        "lang": chunk_dump["lang"],
        "genre": chunk_set_dump["genre_route"],
        "page_start": None,
        "page_end": None,
        "text_source": chunk_dump["text_source"],
        "ocr_confidence_min": chunk_dump.get("ocr_confidence_min"),
        "acl_allow": acl["allow_principals"],
        "acl_deny": acl.get("deny_principals") or [],
        "acl_visibility": acl.get("visibility", "tenant"),
        "acl_classification": acl.get("classification", "internal"),
        "acl_embargo_until": acl.get("embargo_until"),
        "acl_expires_at": acl.get("expires_at"),
        "acl_hash": source_dump["acl_hash"],
        "content_hash": chunk_dump["content_hash"],
        "token_count_primary": chunk_dump["token_counts"].get(chunk_set_dump["primary_tokenizer_id"], 0),
        "risk_score": enrichment.risk_score,
        "pii_policy_applied": chunk_set_dump["pii_policy_applied"],
        "embedding_space_ids": embedded_dump["embedding_space_ids"],
        "embedding_profile_hash": embedded_dump["embedding_profile_hash"],
        "analyzer_id": chunk_set_dump["analyzer_id"],
        "dictionary_hash": chunk_set_dump["dictionary_hash"],
        "chunk_set_blake3": embedded_dump["lineage_refs"]["chunk_set"]["blake3"],
        "updated_at": _rfc3339_ms(datetime.now(UTC)),
    }
    return IndexRecord.model_validate(payload)


def _build_index_commit_payload(
    *,
    embedded_dump: dict[str, Any],
    chunk_set_dump: dict[str, Any],
    self_ref: StoreRef,
    scope: tuple[str, str, str],
    job_id: str,
    commit_id: str,
    generation: int,
    records: list[IndexRecord],
    backend: QdrantIndexBackend,
    physical: str,
    fingerprints: tuple[str, str, str],
    profile_id: str,
) -> dict[str, Any]:
    """이미 커밋된 레코드 배치를 둘러싼 `IndexCommit` 봉투를 조립한다."""
    tenant_id, collection_id, document_id = scope
    parser_fp, normalizer_fp, enricher_fp = fingerprints
    commit_hash = hash_of("commit", commit_id, str(generation), *(record.record_id.root for record in records))
    embedded_lineage = {
        **_fixup_lineage_media_types(embedded_dump["lineage_refs"]),
        "embedded": _ref_dict(self_ref, "EmbeddedChunkSet"),
    }
    now = _rfc3339_ms(datetime.now(UTC))
    return {
        "schema_version": "1.0.0",
        "schema_type": "IndexCommit",
        "tenant_id": tenant_id,
        "collection_id": collection_id,
        "producer": {
            "plugin_id": backend.plugin_id,
            "plugin_version": "0.1.0",
            "config_hash": hash_of("config", "cli_lite"),
            "image_digest": None,
            "model_ids": [],
        },
        "quality": embedded_dump["quality"],
        "warnings": [],
        "created_at": now,
        "lineage_refs": embedded_lineage,
        "commit_id": commit_id,
        "document_id": document_id,
        "doc_version": chunk_set_dump["doc_version"],
        "job_id": job_id,
        "kind": "upsert",
        "previous_commit_id": None,
        "supersedes_commit_ids": [],
        "status": "committed",
        "index_generation": generation,
        "profile_id": profile_id,
        "profile_hash": hash_of("profile", profile_id),
        "parser_fingerprint_hash": parser_fp,
        "normalizer_fingerprint": normalizer_fp,
        "chunker_config_hash": chunk_set_dump["chunker_config_hash"],
        "enricher_fingerprint": enricher_fp,
        "embedder_fingerprint": embedded_dump["embedder_fingerprint"],
        "embedding_space_ids": embedded_dump["embedding_space_ids"],
        "embedding_profile_hash": embedded_dump["embedding_profile_hash"],
        "analyzer_id": chunk_set_dump["analyzer_id"],
        "dictionary_hash": chunk_set_dump["dictionary_hash"],
        "record_count": len(records),
        "commit_hash": commit_hash,
        "backend_results": [
            {
                "backend_id": backend.plugin_id,
                "backend_version": backend.backend_version or "local",
                "physical_name": physical,
                "alias": physical,
                "upserted": len(records),
                "deleted": 0,
                "duration_ms": 1,
                "status": "ok",
            }
        ],
        "artifact_refs": embedded_lineage,
        "stats": {
            "bytes_dense": len(records) * _EMBED_DIM * 4,
            "bytes_sparse": 0,
            "bytes_lexical": 0,
            "bytes_late_interaction": 0,
            "leaf_count": len(records),
            "parent_count": max(0, len(chunk_set_dump["chunks"]) - len(records)),
            "llm_tokens": 0,
            "wall_seconds": 0.01,
        },
        "events_emitted": [],
        "started_at": now,
        "committed_at": now,
        "updated_at": now,
    }


def _rfc3339_ms(moment: datetime) -> str:
    """바이블 §6.3 정본 표기(밀리초, `Z` 접미)."""
    utc = moment.astimezone(UTC)
    return utc.strftime("%Y-%m-%dT%H:%M:%S.") + f"{utc.microsecond // 1000:03d}Z"


class _LitePipelineContext:
    """`pipelines.ingest.run`이 기대하는 `PipelineContext`(바이블 §11.1) — `LocalRunner` 스테이지 1개씩 실행.

    `orchestration`에 아직 없는 "실 어댑터 배선" 셸(`pipelines/ingest.py`의 문서화된 F5 공백)을
    F1~F3 실 모듈로 채운다 — hwpx·pdf·html·txt/md/json 파서, 결정적 정규화·구조 인식 청킹·보강,
    페이크 임베더, Qdrant 로컬 인덱스.
    """

    def __init__(
        self,
        *,
        store: FileArtifactStore,
        tenant_id: str,
        collection_id: str,
        document_id: str,
        job_id: str,
        backend: QdrantIndexBackend,
        physical: str,
        profile_id: str,
        allowed_roots: tuple[str, ...],
    ) -> None:
        """수집 1건에 필요한 모든 실 어댑터·상태를 만든다."""
        self.store = store
        self.tenant_id = tenant_id
        self.collection_id = collection_id
        self.document_id = document_id
        self.job_id = job_id
        self.backend = backend
        self.physical = physical
        self.profile_id = profile_id
        self._clock = _Clock()

        builder = _ParserBuilder(
            {
                "parser.hwpx_python_hwpx": lambda: HwpxPythonHwpxParser(HwpxParserConfig()),
                "parser.text_charset_markdown_it": lambda: TextCharsetMarkdownItParser(TextParserConfig()),
                "parser.html_trafilatura_docling": lambda: HtmlTrafilaturaDoclingParser(HtmlParserConfig()),
                "parser.pdf_fast_pdftext": lambda: PdfFastPdftextParser(PdfFastParserConfig()),
            }
        )
        self._router = ParseRouterStage(builder)
        self._normalizer = NormalizerChainStage(NormalizerChainConfig())
        self._chunker = StructureAwareChunkerStage(StructureAwareChunkerConfig())
        self._fetcher = FsspecHttpxFetcher(FetchConfig(file_allowed_roots=allowed_roots))
        self._enrichers = (DeterministicPrefixEnricher(), KoreanKeywordsEnricher(), DerivedMetaEnricher())
        self._embedder = InprocessFakeEmbedder(embedding_space_id="fake:cli-lite", dim=_EMBED_DIM)
        self._tokenizer = WhitespaceTokenizer()
        self.backend.ensure_collection(
            physical, CollectionLayout(dense_dim=_EMBED_DIM, sparse_bm25=True, sparse_learned=False)
        )

        self._source: SourceDocument | None = None
        self._chunk_set: ChunkSet | None = None
        self._enriched: EnrichedChunkSet | None = None
        self._dense_vectors: dict[str, list[float]] = {}
        self._index_generation = 0
        self.last_index_commit: IndexCommit | None = None

        enrich_fp = hash_of("producer", "enricher.cli_lite")
        self._stage_of: dict[str, _AdapterStage] = {
            "fetch": _AdapterStage(
                self._fetcher.plugin_id, IngestRequest, self._fetcher.fingerprint(), self._call_fetch
            ),
            "parse": _AdapterStage(
                self._router.plugin_id, SourceDocument, self._router.fingerprint(), self._call_parse
            ),
            "normalize": _AdapterStage(
                self._normalizer.plugin_id, ParsedDocument, self._normalizer.fingerprint(), self._call_normalize
            ),
            "chunk": _AdapterStage(
                self._chunker.plugin_id, NormalizedDocument, self._chunker.fingerprint(), self._call_chunk
            ),
            "enrich": _AdapterStage("enricher.cli_lite", ChunkSet, enrich_fp, self._call_enrich),
            "embed": _AdapterStage(
                self._embedder.plugin_id,
                EnrichedChunkSet,
                hash_of("producer", self._embedder.plugin_id, "0.1.0", str(self._embedder.dim)),
                self._call_embed,
            ),
            "index": _AdapterStage(
                self.backend.plugin_id, EmbeddedChunkSet, hash_of("producer", self.backend.plugin_id), self._call_index
            ),
            "publish": _AdapterStage(
                "publish.local_ledger", IndexCommit, hash_of("producer", "publish.local_ledger"), self._call_publish
            ),
        }
        self.context = self  # `LocalRunner(context=...)`가 기대하는 `now()`/`sleep()` 협력자
        # `_LitePipelineContext`는 `sdk.context.LocalContext`의 구체 클래스는 아니지만
        # `LocalRunner`가 실제로 쓰는 표면(`tenant_id`/`collection_id`/`build_stage_context`/
        # `sleep`)을 전부 구현한다(의도적 구조적 축소, 위 `now`/`sleep`/`build_stage_context` 참고).
        self.runner = LocalRunner(context=self, store=store, token_counter=_ApproxTokenCounter())  # type: ignore[arg-type]

    # -- 스테이지 본체(실 어댑터 1개 또는 손으로 엮은 그룹을 감싼다) --------------------------

    async def _call_fetch(self, req: IngestRequest, ctx: Any) -> SourceDocument:
        """`fetch` — `file://` 원본을 가져온다."""
        source = await self._fetcher.run(req, ctx)
        self._source = source
        return source

    async def _call_parse(self, source: SourceDocument, ctx: Any) -> ParsedDocument:
        """`parse` — 포맷 판별 + 후보 체인(`ParseRouterStage`)."""

        async def _source_bytes() -> bytes:
            return await self.store.get_bytes(_to_store_ref(source.artifact))

        ctx.source_bytes = _source_bytes
        return await self._router.run(source, ctx)

    async def _call_normalize(self, parsed: ParsedDocument, ctx: Any) -> NormalizedDocument:
        """`normalize` — 정규화 체인."""
        return await self._normalizer.run(parsed, ctx)

    async def _call_chunk(self, normalized: NormalizedDocument, ctx: Any) -> ChunkSet:
        """`chunk` — 구조 인식 계층 청킹."""
        chunk_set = await self._chunker.run(normalized, ctx)
        self._chunk_set = chunk_set
        return chunk_set

    async def _call_enrich(self, chunk_set: ChunkSet, ctx: Any) -> EnrichedChunkSet:
        """`enrich` — 결정적 접두어·형태소 키워드·파생 메타를 합쳐 `EnrichedChunkSet`을 만든다."""
        acc: dict[str, MutableMapping[str, Any]] = {}
        for enricher in self._enrichers:
            await enricher.enrich(chunk_set.chunks, ctx, acc)

        leaf_levels = (ct.ChunkLevel.integer_0, ct.ChunkLevel.integer_2)
        indexable = [chunk for chunk in chunk_set.chunks if chunk.level in leaf_levels]
        enrichments = {
            chunk.chunk_id.root: _enrichment_dict(acc.get(chunk.chunk_id.root, {}), chunk) for chunk in indexable
        }
        payload = _build_enriched_payload(
            chunk_set=chunk_set, self_ref=ctx.self_ref, enricher_fp=self._stage_of["enrich"].fp, enrichments=enrichments
        )
        enriched = EnrichedChunkSet.model_validate(payload)
        self._enriched = enriched
        return enriched

    async def _call_embed(self, enriched: EnrichedChunkSet, ctx: Any) -> EmbeddedChunkSet:
        """`embed` — 페이크 dense + BM25 sparse."""
        chunk_ids = sorted(enriched.enrichments.keys())
        embed_texts = [enriched.enrichments[cid].embed_text for cid in chunk_ids]
        dense_vectors = self._embedder.embed_documents(embed_texts) if embed_texts else []
        analyzer_id = self._tokenizer.analyzer_id

        vectors: dict[str, Any] = {}
        for offset, cid in enumerate(chunk_ids):
            sparse = document_vector(self._tokenizer.tokenize(enriched.enrichments[cid].index_text))
            sparse_payload = (
                sparse.model_dump(mode="json") if sparse is not None else {"indices": [0], "values": [0.0001]}
            )
            vectors[cid] = {
                "dense": {"name": "dense", "dim": self._embedder.dim, "offset": offset},
                "sparse_bm25": {"name": "sparse_bm25", "vocab_id": analyzer_id, **sparse_payload},
                "embed_text_hash": blake3_hex(embed_texts[offset]),
                "truncated": False,
            }
        vectors_ref = await ctx.artifacts.put_derived(
            json.dumps({"chunk_ids": chunk_ids, "dense": dense_vectors}).encode("utf-8"),
            kind="vectors",
            ext="json",
            media_type="application/json",
        )
        payload = _build_embedded_payload(
            enriched=enriched,
            self_ref=ctx.self_ref,
            embedder=self._embedder,
            vectors=vectors,
            vectors_ref=vectors_ref,
            dense_space=_dense_space_id(self._embedder.dim),
            sparse_space=_sparse_space_id(analyzer_id),
        )
        embedded = EmbeddedChunkSet.model_validate(payload)
        self._dense_vectors = dict(zip(chunk_ids, dense_vectors, strict=True))
        return embedded

    async def _call_index(self, embedded: EmbeddedChunkSet, ctx: Any) -> IndexCommit:
        """`index` — Qdrant 로컬 업서트 + `IndexCommit`."""
        if self._source is None or self._chunk_set is None or self._enriched is None:
            msg = "index stage needs the source/chunk_set/enriched state a prior stage call sets"
            raise RuntimeError(msg)
        source_dump = self._source.model_dump(mode="json")
        chunk_set_dump = self._chunk_set.model_dump(mode="json")
        embedded_dump = embedded.model_dump(mode="json")
        by_chunk_id = {chunk.chunk_id.root: chunk for chunk in self._chunk_set.chunks}
        metadata = source_dump.get("metadata") or {}
        title = metadata.get("title") or source_dump["source_uri"].rsplit("/", 1)[-1]
        scope = (self.tenant_id, self.collection_id, self.document_id)

        self._index_generation += 1
        generation = self._index_generation
        commit_id = str(ULID())
        records = [
            _build_index_record(
                chunk=by_chunk_id[chunk_id],
                enrichment=self._enriched.enrichments[chunk_id],
                dense_vector=self._dense_vectors[chunk_id],
                sparse_bm25={
                    "indices": vector_bundle["sparse_bm25"]["indices"],
                    "values": vector_bundle["sparse_bm25"]["values"],
                },
                source_dump=source_dump,
                chunk_set_dump=chunk_set_dump,
                embedded_dump=embedded_dump,
                scope=scope,
                commit_id=commit_id,
                generation=generation,
                title=title,
            )
            for chunk_id, vector_bundle in embedded_dump["vectors"].items()
        ]
        self.backend.upsert(self.physical, records, commit_id=commit_id, index_generation=generation)
        self.backend.set_current(
            self.physical,
            tenant_id=self.tenant_id,
            collection_id=self.collection_id,
            document_id=self.document_id,
            index_generation=generation,
        )
        payload = _build_index_commit_payload(
            embedded_dump=embedded_dump,
            chunk_set_dump=chunk_set_dump,
            self_ref=ctx.self_ref,
            scope=scope,
            job_id=self.job_id,
            commit_id=commit_id,
            generation=generation,
            records=records,
            backend=self.backend,
            physical=self.physical,
            fingerprints=(self._router.fingerprint(), self._normalizer.fingerprint(), self._stage_of["enrich"].fp),
            profile_id=self.profile_id,
        )
        commit = IndexCommit.model_validate(payload)
        self.last_index_commit = commit
        return commit

    async def _call_publish(self, commit: IndexCommit, _ctx: Any) -> CloudEventEnvelope:
        """`publish` — `ingest.document.indexed` 이벤트(로컬 모드는 outbox 없음, 로그만)."""
        commit_dump = commit.model_dump(mode="json")
        payload = {
            "specversion": "1.0",
            "id": str(ULID()),
            "source": "urn:rag:cli",
            "type": "ingest.document.indexed",
            "time": _rfc3339_ms(datetime.now(UTC)),
            "subject": f"tenant/{self.tenant_id}/document/{self.document_id}",
            "datacontenttype": "application/json",
            "tenantid": self.tenant_id,
            "data": {
                "job_id": self.job_id,
                "document_id": self.document_id,
                "collection_id": self.collection_id,
                "stage": "index",
                "doc_version": commit_dump["doc_version"],
                "quality": commit_dump["quality"],
                "commit_id": commit_dump["commit_id"],
                "index_generation": commit_dump["index_generation"],
                "commit_hash": commit_dump["commit_hash"],
                "record_count": commit_dump["record_count"],
                "job_state": "succeeded",
            },
        }
        return CloudEventEnvelope.model_validate(payload)

    # -- `PipelineContext`(바이블 §11.1) ------------------------------------------------------

    def _extra_for(self, stage: str, inp_ref: StoreRef) -> dict[str, Any]:
        """바이블 §4.1 임시 관례: `ctx.parsed_ref`/`ctx.normalized_ref`/`ctx.self_ref`."""
        if stage == "normalize":
            return {
                "parsed_ref": ParsedRef(
                    uri=ct.Uri(AnyUrl(inp_ref.uri)),
                    blake3=inp_ref.blake3,
                    media_type=inp_ref.media_type,
                    schema_type="ParsedDocument",
                    schema_version="1.0.0",
                    size_bytes=inp_ref.size_bytes,
                )
            }
        if stage == "chunk":
            return {
                "normalized_ref": NormalizedRef(
                    uri=ct.Uri(AnyUrl(inp_ref.uri)),
                    blake3=inp_ref.blake3,
                    media_type=inp_ref.media_type,
                    schema_type="NormalizedDocument",
                    schema_version="1.0.0",
                    size_bytes=inp_ref.size_bytes,
                )
            }
        if stage in ("enrich", "embed", "index", "publish"):
            return {"self_ref": inp_ref}
        return {}

    async def _rehydrate_state(self, stage: str, ref: StoreRef) -> None:
        """`stage_key` 캐시 히트(ADR-0037)로 `Stage.run`을 건너뛴 뒤에도 인스턴스 상태를 되살린다."""
        if stage not in ("fetch", "chunk", "enrich", "embed"):
            return
        out_bytes = await self.store.get_bytes(ref)
        if stage == "fetch":
            self._source = SourceDocument.model_validate_json(out_bytes)
        elif stage == "chunk":
            self._chunk_set = ChunkSet.model_validate_json(out_bytes)
        elif stage == "enrich":
            self._enriched = EnrichedChunkSet.model_validate_json(out_bytes)
        else:
            embedded = EmbeddedChunkSet.model_validate_json(out_bytes)
            vectors_blob = json.loads(await self.store.get_bytes(_to_store_ref(embedded.vectors_ref)))
            self._dense_vectors = dict(zip(vectors_blob["chunk_ids"], vectors_blob["dense"], strict=True))

    def build_stage_context(
        self, *, stage_token_counter: Any, document_id: str | None = None, job_id: str | None = None
    ) -> _StageCtx:
        """`LocalRunner`가 스테이지 1개 실행 직전에 부르는 `StageContext` 팩토리."""
        return _StageCtx(
            clock=self._clock,
            tenant_id=self.tenant_id,
            collection_id=self.collection_id,
            document_id=document_id,
            job_id=job_id,
            trace_id="cli-lite",
            profile_hash=hash_of("profile", self.profile_id),
            token_counter=stage_token_counter,
            analyzer=None,
            artifacts=_Artifacts(self.store, self.tenant_id),
            **getattr(self, "extra", {}),
        )

    async def run(self, stage: str, inp_ref: Any, out_type: type[Any], policy: StagePolicy) -> Any:
        """`PipelineContext.run` — 스테이지 1개를 길이 1짜리 `LocalRunner.run([...])`으로 실행한다."""
        spec = StageSpec(name=stage, stage=self._stage_of[stage], policy=policy, schema_type=out_type.__name__)
        input_bytes = await self.store.get_bytes(inp_ref)
        self.extra = self._extra_for(stage, inp_ref)
        result = await self.runner.run([spec], input_bytes, document_id=self.document_id, job_id=self.job_id)
        if result.status != "succeeded":
            errors = result.errors
            if errors:
                raise errors[0]
            msg = f"stage {stage!r} ended in status {result.status!r}"
            raise RuntimeError(msg)
        assert result.ref is not None  # noqa: S101 - succeeded run always sets a ref (LocalRunner invariant)
        await self._rehydrate_state(stage, result.ref)
        return result.ref

    async def emit(self, _event: Any) -> None:
        """로컬 모드는 outbox 릴레이가 없다(바이블 §11.1) — no-op."""
        return

    def now(self) -> datetime:
        """`LocalRunner`/`PipelineContext`가 공유하는 시계."""
        return self._clock.now()

    async def sleep(self, _duration: Any) -> None:
        """이 셸의 스테이지는 `RETRYABLE`을 던지지 않는다 — no-op."""
        return


async def _make_req_ref(store: FileArtifactStore, *, tenant_id: str, collection_id: str, source_uri: str) -> StoreRef:
    """`IngestRequest`를 만들어 저장하고 그 참조를 돌려준다(수집 체인의 첫 입력)."""
    req = IngestRequest.model_validate(
        {
            "schema_version": "1.0.0",
            "request_id": str(ULID()),
            "collection_id": collection_id,
            "source_uri": source_uri,
            "acl": {"allow_principals": ["tenant:*"], "visibility": "tenant"},
            "requested_at": _rfc3339_ms(datetime.now(UTC)),
        }
    )
    return await store.put_artifact(
        req.model_dump_json().encode("utf-8"),
        tenant_id=tenant_id,
        schema_type="IngestRequest",
        media_type="application/vnd.rag.ingest-request+json",
    )


async def ingest_paths(
    paths: Sequence[Path],
    *,
    collection: str,
    profile: str = "lite-dev",
    state_dir: Path = _DEFAULT_STATE_DIR,
) -> list[dict[str, Any]]:
    """`rag ingest`의 공개 진입점 — 각 경로를 lite 프로파일로 끝까지(fetch→...→publish) 수집한다.

    Returns:
        경로별 `{path, document_id, commit_id, record_count, status}` 요약(입력 순서).
    """
    profile_id = resolve_profile_id(profile)
    registry = _Registry.load(state_dir / "collections.json")
    entry = registry.collection(collection, profile_id=profile_id, create=True)
    tenant_id, collection_id = entry["tenant_id"], entry["collection_id"]

    store = FileArtifactStore(state_dir / "artifacts")
    backend = QdrantIndexBackend.local(str(state_dir / "qdrant"))
    physical = physical_alias_for(collection_id)
    allowed_roots = tuple({str(p.resolve().parent) for p in paths})

    summaries: list[dict[str, Any]] = []
    try:
        for path in paths:
            resolved = path.resolve()
            document_id = registry.document_id_for(entry, str(resolved))
            job_id = str(ULID())
            req_ref = await _make_req_ref(
                store, tenant_id=tenant_id, collection_id=collection_id, source_uri=resolved.as_uri()
            )
            pipeline = _LitePipelineContext(
                store=store,
                tenant_id=tenant_id,
                collection_id=collection_id,
                document_id=document_id,
                job_id=job_id,
                backend=backend,
                physical=physical,
                profile_id=profile_id,
                allowed_roots=allowed_roots,
            )
            await ingest_pipeline.run(pipeline, req_ref, _LiteProfile())
            commit = pipeline.last_index_commit
            summaries.append(
                {
                    "path": str(resolved),
                    "document_id": document_id,
                    "commit_id": str(commit.commit_id.root) if commit else None,
                    "record_count": commit.record_count if commit else 0,
                    "status": commit.status.value if commit else "unknown",
                }
            )
    finally:
        # 온디스크 로컬 Qdrant는 파일 잠금을 쓴다(`portalocker`) — `_LitePipelineContext`가 자기
        # 참조 순환(`self.context = self`)을 만들어 refcount만으로는 즉시 해제되지 않으므로, 다음
        # `rag query`/`build_backend` 호출이 "already accessed" 오류 없이 열 수 있도록 명시적으로
        # 닫는다(같은 프로세스 안에서 ingest → query를 잇는 이 WP의 개발 모드에 필요).
        backend.client.close()
    registry.save()
    return summaries


# ---------------------------------------------------------------------------------------------
# 질의 측 배선 — `pipelines.query.QueryPipelineDeps`의 6-Protocol을 F4 실 모듈로 채운다.
# ---------------------------------------------------------------------------------------------


def _query_vectors_for(plan: QueryPlan, embedder: InprocessFakeEmbedder) -> dict[str, QueryVectors]:
    """단일 변형(원 질의, 바이블 §4.3 규칙 경로)의 dense 질의 벡터 맵을 만든다."""
    variant = plan.rewritten_queries[0]
    variant_id = _root_value(variant.variant_id)
    dense = tuple(embedder.embed_query(plan.normalized_query))
    return {variant_id: QueryVectors(dense=dense)}


def _make_retrieve(backend: QdrantIndexBackend, embedder: InprocessFakeEmbedder) -> query_pipeline.ChannelRetriever:
    """`ChannelRetriever` 어댑터 — dense/lexical 두 채널 모두 로컬 Qdrant 백엔드로 나간다."""
    retrievers: dict[str, Retriever] = {
        "retriever.qdrant_dense": QdrantDenseRetriever(backend=backend),
        "retriever.qdrant_sparse_bm25": QdrantSparseBm25Retriever(backend=backend, tokenizer=WhitespaceTokenizer()),
    }
    clock = _Clock()

    async def _retrieve(plan: QueryPlan, security: ct.SecurityContext) -> CandidateSet:
        del security  # `ChannelRetriever` 프로토콜 매개변수 이름 고정 — lite 리트리버는 미사용.
        query_vectors = _query_vectors_for(plan, embedder)
        # `_Clock`은 두 리트리버가 실제로 쓰는 `ctx.now()`만 채운다(`StageContext`의 나머지 멤버는
        # 이 lite 셸의 질의 경로가 필요로 하지 않는다) — 전체 프로토콜 대신 부분집합만 구현한 의도적
        # 구조적 축소.
        return await channels.retrieve_once(plan, query_vectors, clock, retrievers=retrievers)  # type: ignore[arg-type]

    return _retrieve


def _make_hydrate(backend: QdrantIndexBackend) -> query_pipeline.Hydrator:
    """`Hydrator` 어댑터 — 보안 재필터 포함 Qdrant 배치 조회."""
    backend_port = QdrantHydrateBackend(backend=backend)

    async def _hydrate(ranked: RankedSet, plan: QueryPlan, security: ct.SecurityContext) -> RankedSet:
        del security  # `Hydrator` 프로토콜 매개변수 이름 고정 — 보안 재필터는 Qdrant 조회 내부에서 적용.
        return await hydrate_stage.hydrate(ranked, plan, backend_port, now=datetime.now(UTC))

    return _hydrate


def _postprocess(ranked: RankedSet, plan: QueryPlan) -> RankedSet:
    """`Postprocessor` 어댑터 — lite는 `relevance_gate → dedup`만 켠다(mmr·parent_expand는 §7.2 "끔")."""
    del plan  # `Postprocessor` 프로토콜 매개변수 이름 고정(구조적 타입 검사) — lite는 미사용.
    gate = relevance_gate.apply(ranked.results, tau=_LITE_TAU)
    deduped = dedup_stage.apply(
        gate.results,
        cosine_threshold=_LITE_COSINE_THRESHOLD,
        minhash_threshold=_LITE_MINHASH["threshold"],
        num_perm=int(_LITE_MINHASH["num_perm"]),
        seed=int(_LITE_MINHASH["seed"]),
    )
    steps = [
        PostprocessStepReport(
            step=ct.PostprocessStep.relevance_gate, removed=len(gate.omitted), added=gate.added, took_ms=0
        ),
        PostprocessStepReport(step=ct.PostprocessStep.dedup, removed=deduped.removed, added=deduped.added, took_ms=0),
    ]
    omitted = [*(ranked.omitted or ()), *gate.omitted, *deduped.omitted]
    gate_passed = gate.gate.passed if gate.gate else None
    stats = ranked.stats.model_copy(update={"n_out": len(deduped.results), "gate_passed": gate_passed})
    return ranked.model_copy(
        update={
            "stage": ct.RankedStage.postprocessed,
            "results": deduped.results,
            "omitted": omitted,
            "relevance_gate": gate.gate,
            "postprocess_report": PostprocessReport(steps=steps),
            "stats": stats,
        }
    )


def _pack_config(
    plan: QueryPlan, security: ct.SecurityContext, *, token_counter: _ApproxTokenCounter
) -> packer.PackConfig:
    """Lite 프로파일 고정값(바이블 §7.2)으로 `PackConfig`를 만든다."""
    return packer.PackConfig(
        security=security,
        token_counter=token_counter,
        budget_cut=BudgetCutConfig(
            k_max=_LITE_PACK_K_MAX,
            max_context_tokens=_LITE_PACK_MAX_CONTEXT_TOKENS,
            reserved_answer_tokens=_LITE_PACK_RESERVED_ANSWER_TOKENS,
        ),
        ordering_strategy=ct.OrderingStrategy.litm_alternating,
        tokenizer=TokenizerSpec(
            provider=TokenizerProvider.anthropic, model="claude-placeholder", name="anthropic:claude-placeholder"
        ),
        count_method=ct.CountMethod.approximate,
        render_hints=RenderHints(
            preferred_renderer=ct.Renderer.markdown,
            citation_style=ct.CitationStyle.bracket_id,
            instructions_template_id="rag-answer-ko@1",
            table_format_preference=[ct.TableFormat.markdown, ct.TableFormat.json],
            language="ko",
            expose_confidence=True,
            data_marking=ct.DataMarking.none,
        ),
        profile_id=str(_root_value(plan.profile_id)),
        profile_hash=str(_root_value(plan.profile_hash)),
        trace_id=blake3_hex(str(_root_value(plan.plan_id)))[:32],
        producer=ct.Producer(
            plugin_id="packer.cli_lite",
            plugin_version="0.1.0",
            config_hash=hash_of("config", "cli_lite"),
            image_digest=None,
        ),
        pack_id=str(ULID()),
        confidence_high=_LITE_CONFIDENCE_HIGH,
        confidence_medium=_LITE_CONFIDENCE_MEDIUM,
    )


def _make_pack(token_counter: _ApproxTokenCounter) -> query_pipeline.Packer:
    """`Packer` 어댑터 — `pack` 내부 acl_recheck→budget_cut→reorder→citation_align은 `packer.pack`이 수행."""

    def _pack(ranked: RankedSet, plan: QueryPlan, security: ct.SecurityContext) -> ContextPack:
        cfg = _pack_config(plan, security, token_counter=token_counter)
        return packer.pack(ranked, cfg, now=datetime.now(UTC))

    return _pack


def security_context_for(*, tenant_id: str, collection_id: str) -> ct.SecurityContext:
    """단일 테넌트 CLI 개발 모드의 서버 주입 `SecurityContext`(ADR-0027 — 요청 본문 값은 무시)."""
    return ct.SecurityContext(
        tenant_id=tenant_id,
        principals=[ct.PrincipalString("tenant:*")],
        collection_ids=[ct.Ulid(collection_id)],
        as_of=_rfc3339_ms(datetime.now(UTC)),
        classification_max=ct.Classification.confidential,
        policy_version="1",
        auth_method=ct.AuthMethod.api_key,
        visible_set=[ct.Visibility.public, ct.Visibility.tenant],
    )


def _cli_planner_defaults() -> planner.PlannerDefaults:
    """`PlannerDefaults`를 그대로 두되 채널 `timeout_ms`만 CLI 온디스크 콜드 스타트용으로 늘린다."""
    base = planner.PlannerDefaults()
    channels = tuple(
        planner.ChannelDefault(cd.channel, cd.retriever_id, cd.backend_id, cd.top_k, _CLI_CHANNEL_TIMEOUT_MS)
        for cd in base.channels
    )
    return replace(base, channels=channels)


def build_query_deps(backend: QdrantIndexBackend, embedder: InprocessFakeEmbedder) -> query_pipeline.QueryPipelineDeps:
    """`QueryPipelineDeps`(6-Protocol)를 F4 실 모듈로 채운다 — `rag query`와 MCP `search` 어댑터가 공유."""
    token_counter = _ApproxTokenCounter()
    planner_defaults = _cli_planner_defaults()
    return query_pipeline.QueryPipelineDeps(
        plan=lambda request, security: planner.plan(request, security, defaults=planner_defaults),
        retrieve=_make_retrieve(backend, embedder),
        fuse=lambda candidates, plan: fusion.fuse(candidates, plan, now=datetime.now(UTC)),
        hydrate=_make_hydrate(backend),
        postprocess=_postprocess,
        pack=_make_pack(token_counter),
        renderers={
            ct.Renderer.markdown: markdown.render,
            ct.Renderer.anthropic_search_result: anthropic_search_result.render,
        },
    )


def resolve_collection(collection: str, *, state_dir: Path = _DEFAULT_STATE_DIR) -> tuple[str, str]:
    """레지스트리에서 `(tenant_id, collection_id)`를 찾는다(질의 측 재사용, MCP 어댑터 포함)."""
    registry = _Registry.load(state_dir / "collections.json")
    entry = registry.collection(collection, profile_id="lite", create=False)
    return entry["tenant_id"], entry["collection_id"]


def build_backend(state_dir: Path = _DEFAULT_STATE_DIR) -> QdrantIndexBackend:
    """`rag ingest`가 쓴 것과 같은 온디스크 Qdrant 로컬 인스턴스를 연다(MCP 어댑터 재사용)."""
    return QdrantIndexBackend.local(str(state_dir / "qdrant"))


def build_embedder() -> InprocessFakeEmbedder:
    """CLI 전체가 공유하는 단일 페이크 임베딩 공간(MCP 어댑터가 같은 벡터를 내도록 재사용)."""
    return InprocessFakeEmbedder(embedding_space_id="fake:cli-lite", dim=_EMBED_DIM)


async def run_query_lite(
    query_text: str,
    *,
    collection: str,
    state_dir: Path = _DEFAULT_STATE_DIR,
    render: bool = True,
) -> query_pipeline.QueryPipelineResult:
    """`rag query`의 공개 진입점 — `plan→retrieve→fuse/hydrate→postprocess→pack→render`(바이블 §4.3)."""
    tenant_id, collection_id = resolve_collection(collection, state_dir=state_dir)
    backend = build_backend(state_dir)
    embedder = build_embedder()
    security = security_context_for(tenant_id=tenant_id, collection_id=collection_id)
    request = QueryRequest(
        schema_version="1.0.0",
        query_id=str(ULID()),
        query=query_text,
        collection_ids=[ct.Ulid(collection_id)],
        requested_at=_rfc3339_ms(datetime.now(UTC)),
    )
    deps = build_query_deps(backend, embedder)
    try:
        return await query_pipeline.run_query(request, security, deps, render=render)
    finally:
        # `ingest_paths`와 같은 이유(파일 잠금) — 뒤이은 다른 `build_backend` 호출(MCP 어댑터 등)이
        # 같은 프로세스 안에서 막히지 않도록 닫는다.
        backend.client.close()


# ---------------------------------------------------------------------------------------------
# CLI — argparse 하위 명령(바이블 §12 `cli` 명령 목록의 이 WP 범위: ingest/query/serve/profile validate).
# ---------------------------------------------------------------------------------------------


def _discover_paths(raw_paths: Sequence[str]) -> list[Path]:
    """파일은 그대로, 디렉터리는 지원 확장자만 재귀 수집한다(정렬로 결정적 순서 보장)."""
    resolved: list[Path] = []
    for raw in raw_paths:
        candidate = Path(raw)
        if candidate.is_dir():
            resolved.extend(sorted(p for p in candidate.rglob("*") if p.suffix.lower() in _SUPPORTED_EXTENSIONS))
        else:
            resolved.append(candidate)
    return resolved


def _cmd_ingest(args: argparse.Namespace) -> int:
    """`rag ingest <paths...> --profile lite-dev --collection NAME`."""
    paths = _discover_paths(args.paths)
    if not paths:
        sys.stderr.write("rag ingest: no input files found\n")
        return 2
    summaries = asyncio.run(
        ingest_paths(paths, collection=args.collection, profile=args.profile, state_dir=Path(args.state_dir))
    )
    sys.stdout.write(json.dumps(summaries, indent=2, ensure_ascii=False) + "\n")
    return 0 if all(s["status"] == "committed" for s in summaries) else 1


def _cmd_query(args: argparse.Namespace) -> int:
    """`rag query "<질의>" --collection NAME [--format text|json]`."""
    try:
        result = asyncio.run(
            run_query_lite(args.query, collection=args.collection, state_dir=Path(args.state_dir), render=True)
        )
    except KeyError as exc:
        sys.stderr.write(f"rag query: {exc}\n")
        return 2
    if args.format == "json":
        payload = {
            "context_pack": result.context_pack.model_dump(mode="json"),
            "rendered": result.rendered.model_dump(mode="json") if result.rendered else None,
        }
        sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    else:
        pack = result.context_pack
        sys.stdout.write(f"items={len(pack.items)} sufficiency={pack.sufficiency.status.value}\n")
        if result.rendered is not None:
            sys.stdout.write(str(result.rendered.provider_payload) + "\n")
    return 0


def _cmd_serve(args: argparse.Namespace) -> int:
    """`rag serve api|mcp` — uvicorn/`mcp` stdio 진입점을 서브프로세스로 띄운다(장수명 프로세스).

    `cli`는 `api`/`mcp`와 같은 층의 독립 형제라 인프로세스 import가 금지된다(import-linter
    `layers`) — 그래서 서브프로세스 실행이 이 명령의 유일하게 계약을 지키는 구현이다.
    """
    if args.target == "api":
        argv = [
            sys.executable,
            "-m",
            "uvicorn",
            "rag_platform.api.app:app",
            "--host",
            args.host,
            "--port",
            str(args.port),
        ]
    else:
        argv = [sys.executable, "-m", "rag_platform.mcp.server"]
    try:
        completed = subprocess.run(argv, check=False)  # noqa: S603 - fixed argv, no shell, trusted interpreter
    except FileNotFoundError as exc:
        sys.stderr.write(f"rag serve {args.target}: {exc} (open_issues: uvicorn/mcp entry point missing)\n")
        return 127
    return completed.returncode


def _cmd_profile_validate(args: argparse.Namespace) -> int:
    """`rag profile validate <profile_id>` — 스키마 + 로딩 규칙(바이블 §7.4)."""
    profile_id = resolve_profile_id(args.profile_id)
    resolved = load_profile(profile_id)
    try:
        validate_schema(resolved.data)
        validate_loading_rules(resolved.data)
    except ProfileInvalidError as exc:
        sys.stderr.write(f"profile.invalid: {'; '.join(exc.issues)}\n")
        return 1
    except Exception as exc:  # noqa: BLE001 - jsonschema.ValidationError and friends surface as-is to the operator
        sys.stderr.write(f"profile.invalid: {exc}\n")
        return 1
    sys.stdout.write(f"{args.profile_id} -> {profile_id}: valid (profile_hash={resolved.profile_hash})\n")
    return 0


def build_arg_parser() -> argparse.ArgumentParser:
    """`rag` 하위 명령 파서를 만든다(바이블 §12 cli 명령 목록의 이 WP 범위)."""
    parser = argparse.ArgumentParser(prog="rag", description="RAG platform CLI (lite-dev in-process runtime)")
    sub = parser.add_subparsers(dest="command", required=True)

    ingest_parser = sub.add_parser("ingest", help="ingest paths into a local lite collection")
    ingest_parser.add_argument("paths", nargs="+", help="files or directories to ingest")
    ingest_parser.add_argument("--profile", default="lite-dev")
    ingest_parser.add_argument("--collection", required=True)
    ingest_parser.add_argument("--state-dir", default=str(_DEFAULT_STATE_DIR))
    ingest_parser.set_defaults(handler=_cmd_ingest)

    query_parser = sub.add_parser("query", help="run a query against a local lite collection")
    query_parser.add_argument("query", help="query text")
    query_parser.add_argument("--collection", required=True)
    query_parser.add_argument("--state-dir", default=str(_DEFAULT_STATE_DIR))
    query_parser.add_argument("--format", choices=("text", "json"), default="text")
    query_parser.set_defaults(handler=_cmd_query)

    serve_parser = sub.add_parser("serve", help="launch the api or mcp server process")
    serve_parser.add_argument("target", choices=("api", "mcp"))
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8000)
    serve_parser.set_defaults(handler=_cmd_serve)

    profile_parser = sub.add_parser("profile", help="profile-related commands")
    profile_sub = profile_parser.add_subparsers(dest="profile_command", required=True)
    profile_validate = profile_sub.add_parser("validate", help="validate a resolved profile")
    profile_validate.add_argument("profile_id")
    profile_validate.set_defaults(handler=_cmd_profile_validate)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """`rag` 진입점 — 하위 명령을 파싱해 실행한다."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    handler: Callable[[argparse.Namespace], int] = args.handler
    return handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
