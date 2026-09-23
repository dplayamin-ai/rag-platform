"""`parser.hwpx_python_hwpx` 파서 스테이지 — `SourceDocument`(format=hwpx) 원본 바이트를 `ParsedDocument`로 만든다.

설계 근거: 04-pipelines/04 §1(`profile_option=hwpx_standard`)·§3.1(스테이지 골격)·§3.7(BinData)·§3.16(암호화)·§6,
바이블 §4.1(5멤버 스테이지 프로토콜)·§5.4 `ParsedDocument`·§6.2(지문 해시), ADR-0002·ADR-0007.
구성: `HwpxPythonHwpxParser` — 스테이지 5멤버(`plugin_id`·`config_schema`·`capabilities()`·`fingerprint()`·`run()`)와
테스트·HWP 5.0 변환 경로용 `parse_bytes(data, inp, ctx)`. 변환 본체는 `owpml_adapter`(순수)이고 이 파일은
BinData·표 HTML·파서 리포트 저장과 봉투 조립만 한다.
불변식: 원본 바이트는 스토리지에서 직접 읽지 않고 셸이 주는 `ctx.source_bytes()` 포트로만 받는다
(04 미해결 이슈 18 제안 이름). `ctx.artifacts.put_derived`만 쓰며(쓰기 전용, 테넌트 바운드) 시계는 `ctx.now()`만
쓴다. 암호화 판정은 `detect`의 `container_flags`를 따른다. python-hwpx·lxml 내부 예외는 모두
`parse.conversion_failed`로 바꾼다(§6).
검증 계층: 1층(여기서 검증) — `tests/adapters/parse/test_hwpx.py`(가짜 `StageContext`·인메모리 아티팩트 포트).
"""

from __future__ import annotations

import inspect
import json
from datetime import UTC
from importlib.metadata import version as package_version
from typing import TYPE_CHECKING, Any

from rag_platform.adapters.parse.owpml_adapter import (
    PLUGIN_ID,
    HeaderIndex,
    HwpxParserConfig,
    OwpmlPackage,
    build_blocks,
    prescan,
    read_metadata,
)
from rag_platform.contracts import common_types as ct
from rag_platform.contracts.parsed_document import DerivedArtifact, LineageRefs, ParsedDocument, ParserFingerprint
from rag_platform.contracts.parsed_document.ParsedDocument.artifacts import Kind as ArtifactKind
from rag_platform.sdk.hashing import hash_of
from rag_platform.sdk.stage import StageError

if TYPE_CHECKING:
    from datetime import datetime

    from rag_platform.contracts.source_document import SourceDocument

__all__ = ["HwpxParserConfig", "HwpxPythonHwpxParser"]

PLUGIN_VERSION = "0.1.0"
PROFILE_OPTION = "hwpx_standard"
SCHEMA_VERSION = "1.0.0"
_LIBRARY = "python-hwpx"
_BCP47_DEFAULT = "ko"
_CONVERSION_FAILED = "parse.conversion_failed"
_DOCUMENT_ENCRYPTED = "parse.document_encrypted"


# `Any`: `put_derived` 반환형은 셸 구현마다 다르다(계약 모델 또는 dict) — 어댑터 경계에서 `ArtifactRef`로 정규화.
def _to_artifact_ref(value: Any) -> ct.ArtifactRef:
    if isinstance(value, ct.ArtifactRef):
        return value
    if hasattr(value, "model_dump"):
        return ct.ArtifactRef.model_validate(value.model_dump(mode="json"))
    return ct.ArtifactRef.model_validate(value)


def _rfc3339_ms(moment: datetime) -> str:
    utc = moment.astimezone(UTC)
    return utc.strftime("%Y-%m-%dT%H:%M:%S.") + f"{utc.microsecond // 1000:03d}Z"


class HwpxPythonHwpxParser:
    """HWPX 인프로세스 파서(A 등급, `in_process`). HWP 5.0 → HWPX 변환본도 `source=converted`로 같은 코드를 쓴다."""

    plugin_id = PLUGIN_ID
    config_schema = HwpxParserConfig
    requires_lineage: tuple[str, ...] = ()

    def __init__(self, config: HwpxParserConfig | None = None) -> None:
        """설정을 고정한다(설정은 `config_hash` → `fingerprint` → `stage_key` 입력)."""
        self.config = config or HwpxParserConfig()

    def config_hash(self) -> str:
        """`H("config", canonical_json(config))` — 정렬 키·구분자 고정 JSON(바이블 §6.2 근사)."""
        canonical = json.dumps(
            self.config.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
        return hash_of("config", canonical)

    def capabilities(self) -> ct.Capabilities:
        """`isolation_modes=[in_process]`, `input_formats=[hwpx]`, 재개 미지원(04 §3.1 골격)."""
        return ct.Capabilities(
            isolation_modes=[ct.IsolationMode.in_process],
            supports_resumable=False,
            contracts_compat=ct.ContractsCompat(">=1.0,<2.0"),
            input_formats=["hwpx"],
            requires_gpu=False,
        )

    def fingerprint(self) -> str:
        """`H("producer", plugin_id, plugin_version, config_hash, "", "")`(인프로세스: image digest·모델 없음)."""
        return hash_of("producer", self.plugin_id, PLUGIN_VERSION, self.config_hash(), "", "")

    async def run(self, inp: SourceDocument, ctx: Any) -> ParsedDocument:
        """셸이 제공하는 원본 바이트 포트(`ctx.source_bytes()`, 동기·비동기 모두 허용)로 바이트를 받아 파싱한다."""
        port = getattr(ctx, "source_bytes", None)
        if port is None:
            raise StageError(
                _CONVERSION_FAILED,
                stage="parse",
                plugin_id=self.plugin_id,
                detail="StageContext has no source_bytes port (04-pipelines/04 open issue 18)",
            )
        data = port()
        if inspect.isawaitable(data):
            data = await data
        return await self.parse_bytes(bytes(data), inp, ctx)

    async def parse_bytes(
        self,
        data: bytes,
        inp: SourceDocument,
        ctx: Any,
        *,
        block_source: ct.BlockSource = ct.BlockSource.text_layer,
    ) -> ParsedDocument:
        """HWPX 바이트 → `ParsedDocument`. 저장은 `ctx.artifacts.put_derived`로만 한다."""
        if inp.container_flags.encrypted:
            raise StageError(
                _DOCUMENT_ENCRYPTED,
                stage="parse",
                plugin_id=self.plugin_id,
                detail="container_flags.encrypted=true; in-process path has no decryption (04 §3.16)",
            )
        pkg = OwpmlPackage.open(data)
        genre_hint = inp.metadata.genre
        doc_version = inp.doc_version.root
        try:
            plan = prescan(pkg, HeaderIndex.from_xml(pkg.header), self.config, genre_hint=genre_hint)
            figure_refs = await self._store_binaries(pkg, plan.binary_ids, ctx)
            result = build_blocks(
                pkg, plan, doc_version=doc_version, cfg=self.config, figure_refs=figure_refs, source=block_source
            )
            metadata, opf_language = read_metadata(pkg, result, plan)
        except StageError:
            raise
        except Exception as exc:  # §6: 어댑터 내부 예외(python-hwpx·lxml)는 종류와 무관하게 conversion_failed
            raise StageError(
                _CONVERSION_FAILED,
                stage="parse",
                plugin_id=self.plugin_id,
                detail=f"OWPML adapter error: {type(exc).__name__}",
            ) from exc

        artifacts = list(result.artifacts)
        blocks_by_id = {b.block_id.root: b for b in result.blocks}
        for table_id, html in sorted(result.table_html.items()):
            ref = _to_artifact_ref(
                await ctx.artifacts.put_derived(
                    html.encode("utf-8"), kind="table_html", ext="html", media_type="text/html"
                )
            )
            table = blocks_by_id[table_id].table
            if table is not None:
                table.html_ref = ref
            artifacts.append(DerivedArtifact(kind=ArtifactKind.table_html, ref=ref, block_id=ct.Hex32(table_id)))
        report = {
            "plugin_id": self.plugin_id,
            "library": f"{_LIBRARY}=={package_version(_LIBRARY)}",
            "version_xml": dict(pkg.package.version_info.attributes),
            "section_count": len(pkg.sections),
            **result.report,
        }
        report_ref = _to_artifact_ref(
            await ctx.artifacts.put_derived(
                json.dumps(report, ensure_ascii=False, sort_keys=True).encode("utf-8"),
                kind="vendor_json",
                ext="json",
                media_type="application/json",
            )
        )
        artifacts.append(DerivedArtifact(kind=ArtifactKind.vendor_json, ref=report_ref))

        language = opf_language or (inp.metadata.language_hint.root if inp.metadata.language_hint else _BCP47_DEFAULT)
        return ParsedDocument(
            schema_version=SCHEMA_VERSION,
            schema_type="ParsedDocument",
            tenant_id=inp.tenant_id,
            collection_id=inp.collection_id,
            producer=ct.Producer(
                plugin_id=self.plugin_id,
                plugin_version=PLUGIN_VERSION,
                config_hash=self.config_hash(),
                image_digest=None,
            ),
            quality=ct.Quality.degraded if result.degraded else ct.Quality.full,
            warnings=result.warnings,
            created_at=_rfc3339_ms(ctx.now()),
            lineage_refs=LineageRefs(source=inp.artifact),
            document_id=inp.document_id,
            doc_version=inp.doc_version,
            source_ref=inp.artifact,
            parser_fingerprint=ParserFingerprint(
                parser_id=self.plugin_id,
                parser_version=f"{_LIBRARY}=={package_version(_LIBRARY)}",
                sidecar_image_digest=None,
                profile_option=PROFILE_OPTION,
            ),
            parser_chain=[ct.PluginId(self.plugin_id)],
            source_kind=ct.SourceKind.flow,
            page_count=None,
            language=language,
            metadata=metadata,
            blocks=result.blocks,
            artifacts=artifacts,
            annotations=result.annotations or None,
            fields=result.fields or None,
            links=result.links or None,
            text_length=sum(len(b.text) for b in result.blocks),
            block_count=len(result.blocks),
        )

    async def _store_binaries(
        self, pkg: OwpmlPackage, binary_ids: tuple[str, ...], ctx: Any
    ) -> dict[str, ct.ArtifactRef]:
        """참조된 BinData를 id 오름차순으로 한 번씩 저장(콘텐츠 주소화 — 같은 그림 재사용 시 저장 1회, §3.7)."""
        refs: dict[str, ct.ArtifactRef] = {}
        for item_id in binary_ids:
            entry = pkg.binary(item_id)
            if entry is None:
                continue
            payload, ext, media_type = entry
            if len(payload) > self.config.max_bindata_bytes:
                continue
            refs[item_id] = _to_artifact_ref(
                await ctx.artifacts.put_derived(payload, kind="figure_crop", ext=ext, media_type=media_type)
            )
        return refs
