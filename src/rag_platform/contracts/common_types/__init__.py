"""GENERATED — do not edit; run `uv run python tools/contracts_gen.py` to regenerate.

Source of truth: schemas/*.schema.json (bible §5.1, §6.4, §12)."""

from __future__ import annotations

from enum import IntEnum, StrEnum
from typing import Any, Literal

from pydantic import AnyUrl, BaseModel, ConfigDict, Field, RootModel, constr

from . import TableCell as TableCell_1
from .Block import figure as figure_1, footnote as footnote_1
from .TableData import quality as quality_1


class CommonTypes(RootModel[Any]):
    root: Any = Field(
        ...,
        description="RAG Platform 공용 타입·공용 문서/청크/결과 타입·열거 정본. 설계 바이블 §5.3(공용 타입), §5.4·§5.5(Block, NormalizedBlock, Chunk, Enrichment, VectorBundle, RankedResult, ContextItem), §5.7(열거), §6(명명)을 그대로 옮긴 $defs 모음이다. 다른 계약 스키마는 이 파일의 $defs를 $ref로 참조하고 재정의하지 않는다. 소유 문서: docs/03-contracts/00-contract-overview.md",
        title="CommonTypes",
    )


class Ulid(RootModel[str]):
    root: str = Field(
        ...,
        description="발급형 ID. 26자 Crockford base32 대문자(바이블 §6.1).",
        pattern="^[0-9A-HJKMNP-TV-Z]{26}$",
    )


class Hex64(RootModel[str]):
    root: str = Field(
        ...,
        description="BLAKE3 소문자 hex 64자. 콘텐츠 파생 키·해시(바이블 §6.1).",
        pattern="^[0-9a-f]{64}$",
    )


class Hex32(RootModel[str]):
    root: str = Field(
        ...,
        description="BLAKE3 hex 32자 절단. block_id 전용(바이블 §6.2).",
        pattern="^[0-9a-f]{32}$",
    )


class Uuid(RootModel[str]):
    root: str = Field(
        ...,
        description="UUID 소문자(Qdrant point_id, Temporal workflow_run_id).",
        pattern="^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    )


class Semver(RootModel[str]):
    root: str = Field(
        ...,
        description="Semantic Versioning 2.0.0 문자열(schema_version, plugin_version).",
        pattern="^(0|[1-9]\\d*)\\.(0|[1-9]\\d*)\\.(0|[1-9]\\d*)(?:-((?:0|[1-9]\\d*|\\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\\.(?:0|[1-9]\\d*|\\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\\+([0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*))?$",
    )


class Bcp47(RootModel[str]):
    root: str = Field(
        ...,
        description="BCP 47 언어 태그. 기본 서브태그 소문자(ko, en, ko-KR; 바이블 §6.3).",
        pattern="^[a-z]{2,3}(-[A-Za-z0-9]{2,8})*$",
    )


class DateTime(RootModel[str]):
    root: str = Field(
        ...,
        description="RFC 3339 UTC, Z 접미. 정본 표기는 밀리초 정밀도(2026-09-22T09:00:00.000Z; 바이블 §6.3).",
        pattern="^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d{1,9})?Z$",
    )


class Date(RootModel[str]):
    root: str = Field(
        ...,
        description="날짜만(YYYY-MM-DD). 필드명 *_date.",
        pattern="^\\d{4}-\\d{2}-\\d{2}$",
    )


class Duration1(RootModel[str]):
    model_config = ConfigDict(
        regex_engine="python-re",
    )
    root: str = Field(
        ...,
        description="ISO 8601 기간(PT5M).",
        pattern="^P(?!$)(\\d+Y)?(\\d+M)?(\\d+W)?(\\d+D)?(T(?=\\d)(\\d+H)?(\\d+M)?(\\d+(\\.\\d+)?S)?)?$",
    )


class Duration2(RootModel[str]):
    root: str = Field(
        ...,
        description="바이블 §4.4·§5.3 표기(5m, 30s, 24h). 로더가 ISO 8601로 정규화한다.",
        pattern="^\\d+(ms|s|m|h|d)$",
    )


class Duration(RootModel[Duration1 | Duration2]):
    root: Duration1 | Duration2 = Field(
        ...,
        description="기간. ISO 8601 또는 바이블 축약 표기(00-contract-overview 미해결 이슈 참조).",
    )


class Uri(RootModel[AnyUrl]):
    root: AnyUrl = Field(..., description="절대 URI(s3://, file://, https://, urn:...).")


class Cidr(RootModel[str]):
    root: str = Field(
        ...,
        description="IPv4 또는 IPv6 CIDR 표기(EgressPolicy.deny_cidrs).",
        pattern="^(([0-9]{1,3}\\.){3}[0-9]{1,3}/[0-9]{1,2}|[0-9A-Fa-f:.]+/[0-9]{1,3})$",
    )


class PrincipalString(RootModel[str]):
    root: str = Field(
        ...,
        description="주체 문자열 user:{subject} | group:{group_id} | service:{client_id} | tenant:*(바이블 §6.1, §10.1). Principal 객체와 구분한다.",
        max_length=512,
        pattern="^(user:\\S+|group:\\S+|service:\\S+|tenant:\\*)$",
    )


class PluginId(RootModel[str]):
    root: str = Field(
        ...,
        description="{extension_point}.{implementation}(바이블 §6.1). 예 parser.hwpx_python_hwpx",
        pattern="^[a-z][a-z0-9_]*\\.[a-z][a-z0-9_]*$",
    )


class TokenizerId(RootModel[str]):
    root: str = Field(
        ...,
        description="hf:{repo} | tiktoken:{encoding} | anthropic:{model} | gemini:{model}(바이블 §6.1).",
        pattern="^(hf|tiktoken|anthropic|gemini):\\S+$",
    )


class ModelId(RootModel[str]):
    root: str = Field(
        ...,
        description="{repo}@{revision}(바이블 §6.1).",
        pattern="^[^@\\s]+@[^@\\s]+$",
    )


class ImageDigest(RootModel[str]):
    root: str = Field(
        ...,
        description="OCI 이미지 digest(Producer.image_digest).",
        pattern="^sha256:[0-9a-f]{64}$",
    )


class ErrorCode(RootModel[str]):
    root: str = Field(
        ...,
        description="{stage}.{reason} 형식(바이블 §5.7 접두 규약)의 원시 패턴. 계약의 코드 필드(Warning.code·StageError.code·ProblemDetails.code)는 이 패턴이 아니라 ErrorCodeCatalog를 $ref한다(00 I-14; 카탈로그 밖 코드는 ADR로 추가).",
        max_length=64,
        pattern="^(fetch|parse|normalize|chunk|enrich|embed|index|publish|plan|retrieve|fuse|hydrate|rerank|postprocess|pack|render|auth|api|profile|plugin|contract|outbox)\\.[a-z][a-z0-9_]*$",
    )


class ErrorTypeUrn(RootModel[AnyUrl]):
    root: AnyUrl = Field(..., description="RFC 9457 type = urn:rag:error:{code}(바이블 §4.1).")


class SchemaId(RootModel[AnyUrl]):
    root: AnyUrl = Field(..., description="urn:rag:schema:{kebab-name}:{major}(바이블 §6.4).")


class SchemaTypeName(RootModel[str]):
    root: str = Field(
        ...,
        description="PascalCase 계약 타입명(ParsedDocument).",
        pattern="^[A-Z][A-Za-z0-9]*$",
    )


class MediaType(RootModel[str]):
    root: str = Field(
        ...,
        description="IANA 미디어 타입 또는 자체 application/vnd.rag.{kebab-name}+json(바이블 §6.4).",
        pattern="^[a-z]+/[A-Za-z0-9!#$&^_.+-]+$",
    )


class CiteId(RootModel[str]):
    root: str = Field(
        ...,
        description="d{rank}, 1-based 관련도순(바이블 §6.1).",
        pattern="^d[1-9][0-9]*$",
    )


class ChunkSpan(RootModel[str]):
    root: str = Field(
        ...,
        description="{first_block_id}:{char_start}-{last_block_id}:{char_end}(바이블 §6.2).",
        pattern="^[0-9a-f]{32}:[0-9]+-[0-9a-f]{32}:[0-9]+$",
    )


class BlockType(StrEnum):
    heading = "heading"
    paragraph = "paragraph"
    list_item = "list_item"
    table = "table"
    figure = "figure"
    caption = "caption"
    footnote = "footnote"
    code = "code"
    formula = "formula"
    page_break = "page_break"
    page_header = "page_header"
    page_footer = "page_footer"
    toc = "toc"
    form_field = "form_field"


class BlockContainer(StrEnum):
    body = "body"
    text_box = "text_box"
    table_cell = "table_cell"
    footnote_body = "footnote_body"
    page_header = "page_header"
    page_footer = "page_footer"


class BlockSource(StrEnum):
    text_layer = "text_layer"
    ocr = "ocr"
    vlm = "vlm"
    converted = "converted"


class SourceFormat(StrEnum):
    hwpx = "hwpx"
    hwp5 = "hwp5"
    hwp3 = "hwp3"
    pdf = "pdf"
    docx = "docx"
    doc = "doc"
    rtf = "rtf"
    odt = "odt"
    html = "html"
    txt = "txt"
    md = "md"
    json = "json"
    unknown = "unknown"


class SourceKind(StrEnum):
    born_digital = "born_digital"
    scanned = "scanned"
    mixed = "mixed"
    pre_ocr = "pre_ocr"
    flow = "flow"


class Genre(StrEnum):
    law_article = "law_article"
    outline_report = "outline_report"
    narrative = "narrative"
    web_article = "web_article"
    form = "form"
    manual = "manual"
    unknown = "unknown"


class Quality(StrEnum):
    full = "full"
    degraded = "degraded"


class PageStatus(StrEnum):
    ok = "ok"
    timeout = "timeout"
    ocr_failed = "ocr_failed"
    skipped = "skipped"


class FurnitureReason(StrEnum):
    repeated_header = "repeated_header"
    nav = "nav"
    boilerplate = "boilerplate"


class TableRole(StrEnum):
    data = "data"
    toc = "toc"
    form = "form"
    layout = "layout"


class ItemKind(StrEnum):
    text = "text"
    list_group = "list_group"
    code = "code"
    table = "table"
    table_part = "table_part"
    figure = "figure"
    parent = "parent"
    summary = "summary"
    community_report = "community_report"
    entity = "entity"
    page_image = "page_image"


class ChunkLevel(IntEnum):
    """
    0 리프, 1 부모 섹션, 2 문서·코퍼스 상위 파생(summary, community_report, entity).
    """

    integer_0 = 0
    integer_1 = 1
    integer_2 = 2


class TableSerialization(StrEnum):
    html = "html"
    markdown = "markdown"
    triplet = "triplet"
    row_json = "row_json"


class TableFormat(StrEnum):
    html = "html"
    markdown = "markdown"
    json = "json"


class PiiPolicy(StrEnum):
    mask = "mask"
    tokenize = "tokenize"
    exclude = "exclude"
    keep = "keep"
    reject = "reject"


class PiiTokenizeMode(StrEnum):
    hash = "hash"
    encrypt = "encrypt"


class DedupPolicy(StrEnum):
    skip_if_same_hash = "skip_if_same_hash"
    reindex_always = "reindex_always"


class SplitHint(StrEnum):
    none = "none"
    json_array = "json_array"
    zip_members = "zip_members"


class Visibility(StrEnum):
    public = "public"
    tenant = "tenant"
    restricted = "restricted"


class Classification(StrEnum):
    """
    나열 순 = 등급 순(public < internal < confidential < secret).
    """

    public = "public"
    internal = "internal"
    confidential = "confidential"
    secret = "secret"


class AuthMethod(StrEnum):
    oidc = "oidc"
    api_key = "api_key"
    mtls = "mtls"


class TenantStatus(StrEnum):
    """
    바이블 §5.7 1.3.0(AM-38). disabled 테넌트에 대한 요청은 auth.forbidden(403).
    """

    active = "active"
    disabled = "disabled"


class VectorName(StrEnum):
    dense = "dense"
    sparse_learned = "sparse_learned"
    sparse_bm25 = "sparse_bm25"
    late_interaction = "late_interaction"
    page_multivector = "page_multivector"
    pooled_page_multivector = "pooled_page_multivector"
    page_dense = "page_dense"


class Pooling(StrEnum):
    cls = "cls"
    mean = "mean"
    late = "late"


class EmbeddingMode(StrEnum):
    document = "document"
    query = "query"


class KeywordSource(StrEnum):
    analyzer_nng = "analyzer_nng"
    analyzer_nnp = "analyzer_nnp"
    sparse_top = "sparse_top"
    user_dict = "user_dict"


class EntityExtractor(StrEnum):
    gliner2 = "gliner2"
    spacy_ko = "spacy_ko"
    llm = "llm"
    dictionary = "dictionary"


class EnrichStatus(StrEnum):
    complete = "complete"
    partial = "partial"


class Channel(StrEnum):
    dense = "dense"
    sparse = "sparse"
    lexical = "lexical"
    graph = "graph"
    tree = "tree"
    visual = "visual"
    late_interaction = "late_interaction"


class ScoreKind(StrEnum):
    """
    점수 원장 열 = Channel ∪ {fused, rerank}.
    """

    dense = "dense"
    sparse = "sparse"
    lexical = "lexical"
    graph = "graph"
    tree = "tree"
    visual = "visual"
    late_interaction = "late_interaction"
    fused = "fused"
    rerank = "rerank"


class BoostKind(StrEnum):
    entity = "entity"
    recency = "recency"
    item_kind_penalty = "item_kind_penalty"
    user_dictionary = "user_dictionary"


class FusionMethod(StrEnum):
    rrf = "rrf"
    convex_minmax = "convex_minmax"
    convex_zscore = "convex_zscore"
    dbsf = "dbsf"
    combmnz = "combmnz"


class RerankBackend(StrEnum):
    tei = "tei"
    vllm = "vllm"
    sglang = "sglang"
    llamacpp = "llamacpp"
    in_process = "in_process"
    qdrant_maxsim = "qdrant_maxsim"


class RerankResponseSchema(StrEnum):
    tei = "tei"
    cohere = "cohere"


class ScoreNormalization(StrEnum):
    sigmoid = "sigmoid"
    minmax = "minmax"
    identity = "identity"


class Route(StrEnum):
    no_retrieval = "no_retrieval"
    single = "single"
    multi = "multi"


class Complexity(StrEnum):
    no_retrieval = "no_retrieval"
    single_step = "single_step"
    multi_step = "multi_step"


class Strategy(StrEnum):
    hybrid = "hybrid"
    graph_local = "graph_local"
    graph_global = "graph_global"
    tree_collapsed = "tree_collapsed"
    visual_pages = "visual_pages"
    iterative = "iterative"


class QueryRole(StrEnum):
    original = "original"
    rewrite = "rewrite"
    abstraction = "abstraction"
    hypothetical = "hypothetical"
    sub_query = "sub_query"


class ChannelRunStatus(StrEnum):
    ok = "ok"
    timeout = "timeout"
    error = "error"
    disabled = "disabled"


class RankedStage(StrEnum):
    fused = "fused"
    reranked = "reranked"
    postprocessed = "postprocessed"


class PostprocessStep(StrEnum):
    """
    고정 순서 relevance_gate → dedup → mmr → parent_expand → dedup → sentence_window → compress(dedup은 두 번 등장).
    """

    relevance_gate = "relevance_gate"
    dedup = "dedup"
    mmr = "mmr"
    parent_expand = "parent_expand"
    sentence_window = "sentence_window"
    compress = "compress"


class PackStep(StrEnum):
    """
    pack 내부 고정 순서.
    """

    acl_recheck = "acl_recheck"
    budget_cut = "budget_cut"
    reorder = "reorder"
    citation_align = "citation_align"


class ExplainCode(StrEnum):
    lexical_only_hit = "lexical_only_hit"
    dense_only_hit = "dense_only_hit"
    sparse_only_hit = "sparse_only_hit"
    multi_channel_hit = "multi_channel_hit"
    rerank_skipped = "rerank_skipped"
    parent_of_n_hits = "parent_of_n_hits"
    mmr_demoted = "mmr_demoted"
    below_gate = "below_gate"
    deduped = "deduped"
    window_added = "window_added"
    boost_entity = "boost_entity"
    boost_recency = "boost_recency"
    late_interaction_pass = "late_interaction_pass"
    hydrate_missing = "hydrate_missing"
    acl_revoked_hint = "acl_revoked_hint"


class OrderingStrategy(StrEnum):
    litm_alternating = "litm_alternating"
    relevance_desc = "relevance_desc"
    document_order = "document_order"


class ConfidenceTier(StrEnum):
    high = "high"
    medium = "medium"
    low = "low"


class CountMethod(StrEnum):
    exact_api = "exact_api"
    exact_local = "exact_local"
    approximate = "approximate"


class OverflowPolicy(StrEnum):
    downgrade_tables = "downgrade_tables"
    truncate = "truncate"
    compress = "compress"


class OmitReason(StrEnum):
    below_threshold = "below_threshold"
    duplicate = "duplicate"
    budget_exceeded = "budget_exceeded"
    acl_denied = "acl_denied"
    parent_merged = "parent_merged"
    item_kind_excluded = "item_kind_excluded"
    risk_flagged = "risk_flagged"
    hydrate_missing = "hydrate_missing"


class SufficiencyStatus(StrEnum):
    not_needed = "not_needed"
    sufficient = "sufficient"
    insufficient = "insufficient"
    unknown = "unknown"


class SufficiencyMethod(StrEnum):
    rule = "rule"
    llm_judge = "llm_judge"


class ConflictKind(StrEnum):
    version = "version"
    source = "source"
    date = "date"


class TextFormat(StrEnum):
    markdown = "markdown"
    plain = "plain"
    html = "html"


class CitationStyle(StrEnum):
    native = "native"
    bracket_id = "bracket_id"


class DataMarking(StrEnum):
    none = "none"
    delimit = "delimit"
    datamark = "datamark"


class AclCheckSource(StrEnum):
    payload = "payload"
    revocation_hint = "revocation_hint"


class Renderer(StrEnum):
    anthropic_search_result = "anthropic_search_result"
    anthropic_document = "anthropic_document"
    openai_messages = "openai_messages"
    gemini_messages = "gemini_messages"
    xml_documents = "xml_documents"
    markdown = "markdown"
    mcp_tool_result = "mcp_tool_result"
    plain_records = "plain_records"
    dify_external_knowledge = "dify_external_knowledge"


class ResponseFormat(StrEnum):
    concise = "concise"
    detailed = "detailed"
    pack_only = "pack_only"


class RetrievalVariant(StrEnum):
    default = "default"
    quality = "quality"
    fast = "fast"


class RetrievalMode(StrEnum):
    hybrid = "hybrid"
    dense = "dense"
    sparse = "sparse"
    lexical = "lexical"


class CommitStatus(StrEnum):
    pending = "pending"
    vector_written = "vector_written"
    lexical_written = "lexical_written"
    flipping_lexical = "flipping_lexical"
    flipping_vector = "flipping_vector"
    committed = "committed"
    rolling_back = "rolling_back"
    rolled_back = "rolled_back"
    failed = "failed"


class CommitKind(StrEnum):
    upsert = "upsert"
    delete = "delete"


class JobState(StrEnum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    partial = "partial"
    failed = "failed"
    cancelling = "cancelling"
    cancelled = "cancelled"


class JobKind(StrEnum):
    """
    바이블 §5.7 1.3.0: delete_collection 추가(AM-37) — 부모가 문서 페이지를 순회해 자식 delete_document 잡을 팬아웃한다(collection.delete.v1).
    """

    ingest_document = "ingest_document"
    reprocess_document = "reprocess_document"
    delete_document = "delete_document"
    delete_collection = "delete_collection"
    acl_update = "acl_update"
    reindex_collection = "reindex_collection"
    build_graph = "build_graph"
    evaluate = "evaluate"
    consistency_check = "consistency_check"
    tier_promotion = "tier_promotion"


class IsolationMode(StrEnum):
    in_process = "in_process"
    helper_process = "helper_process"
    sidecar = "sidecar"


class TenantIsolationTier(StrEnum):
    payload_filter = "payload_filter"
    shard_key = "shard_key"
    index_per_tenant = "index_per_tenant"


class LicenseGrade(StrEnum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    X = "X"


class Linkage(StrEnum):
    pure_python = "pure_python"
    dynamic = "dynamic"
    static_bundled = "static_bundled"


class IndexPerTenantMode(StrEnum):
    opt_in = "opt_in"
    auto = "auto"
    disabled = "disabled"


class ExtensionPoint(StrEnum):
    fetcher = "fetcher"
    parser = "parser"
    normalizer = "normalizer"
    chunker = "chunker"
    enricher = "enricher"
    embedder = "embedder"
    index_backend = "index_backend"
    query_transformer = "query_transformer"
    retriever = "retriever"
    fuser = "fuser"
    reranker = "reranker"
    postprocessor = "postprocessor"
    packer = "packer"
    evaluator = "evaluator"


class ProfileTier(StrEnum):
    lite = "lite"
    standard = "standard"
    premium = "premium"
    korean_gov = "korean-gov"


class DegradedComponent(StrEnum):
    """
    바이블 §5.3 DegradedEntry 행의 목록. channel.*는 Channel 값으로 전개.
    """

    planner_llm = "planner_llm"
    channel_dense = "channel.dense"
    channel_sparse = "channel.sparse"
    channel_lexical = "channel.lexical"
    channel_graph = "channel.graph"
    channel_tree = "channel.tree"
    channel_visual = "channel.visual"
    channel_late_interaction = "channel.late_interaction"
    fusion = "fusion"
    hydrate = "hydrate"
    rerank = "rerank"
    late_interaction_rerank = "late_interaction_rerank"
    parent_expand = "parent_expand"
    sentence_window = "sentence_window"
    compress = "compress"
    token_count = "token_count"
    acl_recheck = "acl_recheck"
    self_query_filter = "self_query_filter"
    multi_query = "multi_query"
    query_embedding = "query_embedding"


class DegradedReason(StrEnum):
    timeout = "timeout"
    unavailable = "unavailable"
    capability_unsupported = "capability_unsupported"
    analyzer_mismatch = "analyzer_mismatch"
    profile_mismatch = "profile_mismatch"
    latency_budget = "latency_budget"
    llm_failed = "llm_failed"
    filter_relaxed = "filter_relaxed"
    approximate_count = "approximate_count"
    skipped_by_policy = "skipped_by_policy"
    partial_result = "partial_result"


class JudgmentLevel(StrEnum):
    binary = "binary"
    graded = "graded"


class LabelProvenance(StrEnum):
    human = "human"
    umbrela = "umbrela"
    synthetic = "synthetic"


class EvalRunStatus(StrEnum):
    running = "running"
    completed = "completed"
    failed = "failed"


class DictSource(StrEnum):
    manual = "manual"
    imported = "imported"
    mined = "mined"


class FeedbackKind(StrEnum):
    cited = "cited"
    rated = "rated"
    corrected = "corrected"


class FilterOp(StrEnum):
    eq = "eq"
    ne = "ne"
    in_ = "in"
    not_in = "not_in"
    gt = "gt"
    gte = "gte"
    lt = "lt"
    lte = "lte"
    exists = "exists"
    prefix = "prefix"
    contains_any = "contains_any"
    contains_all = "contains_all"


class FilterableField(StrEnum):
    """
    사용자·self-query 필터 가능 필드 화이트리스트(바이블 §5.7). tenant_id, collection_id, acl_*, is_current, index_generation, level, commit_id, record_id는 금지 → plan.filter_field_forbidden.
    """

    document_id = "document_id"
    doc_version = "doc_version"
    external_id = "external_id"
    doc_date = "doc_date"
    doc_type = "doc_type"
    department = "department"
    tags = "tags"
    lang = "lang"
    genre = "genre"
    item_kind = "item_kind"
    heading_path = "heading_path"
    entity_ids = "entity_ids"
    page_start = "page_start"
    page_end = "page_end"
    page = "page"


class FilterableField3(RootModel[str]):
    root: str = Field(
        ...,
        description="컬렉션 filterable_fields에 선언된 키만(플래너가 검증).",
        pattern="^custom\\.[a-z0-9_]+$",
    )


class FilterableField1(RootModel[FilterableField | FilterableField3]):
    root: FilterableField | FilterableField3 = Field(
        ...,
        description="사용자·self-query 필터 가능 필드 화이트리스트(바이블 §5.7). tenant_id, collection_id, acl_*, is_current, index_generation, level, commit_id, record_id는 금지 → plan.filter_field_forbidden.",
    )


class EventType(StrEnum):
    """
    바이블 §5.7 이벤트 이름 카탈로그(domain.entity.action). CloudEventEnvelope.type. 1.3.0: tenant.policies.changed 추가(AM-38, 25종).
    """

    ingest_document_fetched = "ingest.document.fetched"
    ingest_document_parsed = "ingest.document.parsed"
    ingest_document_normalized = "ingest.document.normalized"
    ingest_document_chunked = "ingest.document.chunked"
    ingest_document_enriched = "ingest.document.enriched"
    ingest_document_embedded = "ingest.document.embedded"
    ingest_document_indexed = "ingest.document.indexed"
    ingest_document_retried = "ingest.document.retried"
    ingest_document_failed = "ingest.document.failed"
    ingest_document_deleted = "ingest.document.deleted"
    job_state_changed = "job.state.changed"
    index_commit_published = "index.commit.published"
    index_commit_rolled_back = "index.commit.rolled_back"
    index_consistency_mismatch = "index.consistency.mismatch"
    acl_document_updated = "acl.document.updated"
    collection_profile_changed = "collection.profile.changed"
    collection_reindex_completed = "collection.reindex.completed"
    audit_query_executed = "audit.query.executed"
    audit_document_accessed = "audit.document.accessed"
    audit_acl_changed = "audit.acl.changed"
    audit_admin_action = "audit.admin.action"
    feedback_query_cited = "feedback.query.cited"
    feedback_query_rated = "feedback.query.rated"
    eval_run_completed = "eval.run.completed"
    tenant_policies_changed = "tenant.policies.changed"


class ErrorCodeCatalog(StrEnum):
    """
    바이블 §5.7 오류 코드 카탈로그 전체(경고·폴백 코드 포함). 재시도 가능 여부는 카탈로그가 결정한다. 1.3.0: AM-36 16종 추가(84종) — 재시도 no: parse.block_limit_exceeded, parse.container_limit_exceeded, contract.schema_type_mismatch, contract.upcast_failed, render.template_unsupported, api.not_found(404), api.quota_exceeded; 나머지 신규 코드는 경고(재시도 —).
    """

    fetch_access_denied = "fetch.access_denied"
    fetch_not_found = "fetch.not_found"
    fetch_too_large = "fetch.too_large"
    fetch_scheme_unsupported = "fetch.scheme_unsupported"
    fetch_egress_denied = "fetch.egress_denied"
    fetch_timeout = "fetch.timeout"
    fetch_upstream_error = "fetch.upstream_error"
    parse_unsupported_format = "parse.unsupported_format"
    parse_unsupported_variant = "parse.unsupported_variant"
    parse_corrupt_container = "parse.corrupt_container"
    parse_document_encrypted = "parse.document_encrypted"
    parse_distribution_document = "parse.distribution_document"
    parse_sidecar_unavailable = "parse.sidecar_unavailable"
    parse_conversion_failed = "parse.conversion_failed"
    parse_page_timeout = "parse.page_timeout"
    parse_page_ocr_failed = "parse.page_ocr_failed"
    parse_page_skipped = "parse.page_skipped"
    parse_block_oversized = "parse.block_oversized"
    parse_block_limit_exceeded = "parse.block_limit_exceeded"
    parse_element_path_synthesized = "parse.element_path_synthesized"
    parse_table_structure_fallback = "parse.table_structure_fallback"
    parse_footnote_unanchored = "parse.footnote_unanchored"
    parse_container_limit_exceeded = "parse.container_limit_exceeded"
    parse_extractor_fallback = "parse.extractor_fallback"
    normalize_nfd_residual = "normalize.nfd_residual"
    normalize_pii_policy_violation = "normalize.pii_policy_violation"
    normalize_pii_detector_unavailable = "normalize.pii_detector_unavailable"
    normalize_segmenter_fallback = "normalize.segmenter_fallback"
    chunk_tokenizer_missing = "chunk.tokenizer_missing"
    chunk_count_exceeded = "chunk.count_exceeded"
    chunk_block_oversized = "chunk.block_oversized"
    enrich_content_policy_violation = "enrich.content_policy_violation"
    enrich_llm_policy_denied = "enrich.llm_policy_denied"
    enrich_budget_exceeded = "enrich.budget_exceeded"
    enrich_extractor_timeout = "enrich.extractor_timeout"
    enrich_llm_unavailable = "enrich.llm_unavailable"
    embed_space_mismatch = "embed.space_mismatch"
    embed_tokenizer_missing = "embed.tokenizer_missing"
    embed_server_unavailable = "embed.server_unavailable"
    embed_token_overflow = "embed.token_overflow"
    index_security_fields_missing = "index.security_fields_missing"
    index_generation_conflict = "index.generation_conflict"
    index_backend_unavailable = "index.backend_unavailable"
    index_partial_commit = "index.partial_commit"
    plan_security_context_missing = "plan.security_context_missing"
    plan_filter_field_forbidden = "plan.filter_field_forbidden"
    plan_collection_forbidden = "plan.collection_forbidden"
    plan_llm_failed = "plan.llm_failed"
    retrieve_security_context_missing = "retrieve.security_context_missing"
    fuse_k_missing = "fuse.k_missing"
    retrieve_channel_timeout = "retrieve.channel_timeout"
    retrieve_backend_error = "retrieve.backend_error"
    retrieve_unavailable = "retrieve.unavailable"
    hydrate_backend_error = "hydrate.backend_error"
    rerank_schema_mismatch = "rerank.schema_mismatch"
    pack_tokenizer_mismatch = "pack.tokenizer_mismatch"
    render_mixed_blocks = "render.mixed_blocks"
    render_citations_with_structured_output = "render.citations_with_structured_output"
    render_empty_pack = "render.empty_pack"
    rerank_timeout = "rerank.timeout"
    postprocess_parent_text_miss = "postprocess.parent_text_miss"
    pack_count_api_failed = "pack.count_api_failed"
    pack_budget_overflow = "pack.budget_overflow"
    pack_conflict_unlabeled = "pack.conflict_unlabeled"
    pack_acl_hint_unavailable = "pack.acl_hint_unavailable"
    auth_unauthenticated = "auth.unauthenticated"
    auth_forbidden = "auth.forbidden"
    auth_too_many_principals = "auth.too_many_principals"
    api_idempotency_conflict = "api.idempotency_conflict"
    api_idempotency_payload_mismatch = "api.idempotency_payload_mismatch"
    api_rate_limited = "api.rate_limited"
    api_not_found = "api.not_found"
    api_quota_exceeded = "api.quota_exceeded"
    contract_violation = "contract.violation"
    contract_schema_type_mismatch = "contract.schema_type_mismatch"
    contract_upcast_failed = "contract.upcast_failed"
    contract_acl_deny_all = "contract.acl_deny_all"
    profile_invalid = "profile.invalid"
    profile_gate_pending = "profile.gate_pending"
    plugin_license_denied = "plugin.license_denied"
    plugin_capability_unsupported = "plugin.capability_unsupported"
    render_template_unsupported = "render.template_unsupported"
    outbox_egress_denied = "outbox.egress_denied"
    outbox_relay_failed = "outbox.relay_failed"


class ArtifactRef(BaseModel):
    """
    오브젝트 스토리지 산출물 참조. 오케스트레이터 경계를 넘는 유일한 페이로드(바이블 §4.1, §5.3).
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    uri: Uri = Field(..., description="s3:// 또는 file:// URI(오브젝트 키 규약 §13.3)")
    blake3: Hex64 = Field(..., description="산출물 바이트의 BLAKE3 콘텐츠 해시")
    media_type: MediaType = Field(..., description="application/vnd.rag.{kebab-name}+json 또는 원본 MIME")
    schema_type: SchemaTypeName | None = Field(
        None,
        description="계약 산출물이면 PascalCase 타입명. 봉투 schema_type과 일치해야 로드",
    )
    schema_version: Semver | None = Field(None, description="계약 산출물이면 계약 버전")
    size_bytes: int = Field(..., description="바이트 크기(인라인 금지 검증·계량)", ge=0)
    stage_key: Hex64 | None = Field(None, description="생산 스테이지 멱등성 키(계보 자기 서술)")


class Producer(BaseModel):
    """
    재현성 지문. fingerprint = H("producer", plugin_id, plugin_version, config_hash, image_digest or "", ",".join(model_ids))(바이블 §6.2).
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    plugin_id: PluginId
    plugin_version: Semver = Field(..., description="패키지 버전")
    config_hash: Hex64 = Field(..., description='H("config", canonical_json(config))')
    image_digest: ImageDigest | None = Field(..., description="사이드카·서빙 이미지 digest. 인프로세스는 null")
    model_ids: list[ModelId] | None = Field(None, description="{model_id}@{revision} 목록")


class Provenance(BaseModel):
    """
    원문 좌표(ADR-0002). char_*는 원문 Block.text 기준 0-based 유니코드 코드포인트, 끝 미포함.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    element_path: str = Field(
        ...,
        description="원본 요소 경로(OWPML 경로·Docling self_ref·HTML XPath·pdftext 블록 경로). 문서 내 유일",
        min_length=1,
    )
    char_start: int = Field(..., ge=0)
    char_end: int = Field(..., ge=0)
    page: int | None = Field(..., description="1-based. 흐름 포맷(HWP/HWPX·DOCX·HTML·MD)은 null", ge=1)
    bbox: list[float] | None = Field(
        ...,
        description="[x0, y0, x1, y1] 좌상단 원점·PDF 포인트(1/72 in). 흐름 포맷은 null",
        max_length=4,
        min_length=4,
    )
    section_index: int | None = Field(None, description="HWPX 구역(secPr) 인덱스", ge=0)


class Acl(BaseModel):
    """
    문서 단위 ACL(모든 레벨 레코드가 상속, 바이블 §10.1). 거부가 허용보다 우선.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    allow_principals: list[PrincipalString] = Field(..., max_length=1024)
    deny_principals: list[PrincipalString] | None = Field(None, max_length=1024)
    visibility: Visibility = Field(..., description="기본 tenant")
    classification: Classification | None = Field(None, description="기본 internal. 팩 classification_max로 전파")
    embargo_until: DateTime | None = Field(None, description="이 시각 전 검색 불가")
    expires_at: DateTime | None = Field(None, description="이 시각 후 검색 불가")
    source_acl_hash: Hex64 | None = Field(None, description="원천 ACL 변경 감지")


class SecurityContext(BaseModel):
    """
    서버 주입·읽기 전용. 클라이언트 입력 없음(ADR-0027, 바이블 §5.3).
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    tenant_id: Ulid
    principals: list[PrincipalString] = Field(
        ...,
        description="사용자 + 확장 그룹 + tenant:*. 초과 auth.too_many_principals",
        max_length=1024,
        min_length=1,
    )
    collection_ids: list[Ulid] = Field(..., description="Cedar allowed_collections ∩ 요청 컬렉션")
    as_of: DateTime = Field(..., description="서버 now(). embargo/expiry 판정 시각")
    classification_max: Classification = Field(
        ..., description="주체가 볼 수 있는 최고 등급(테넌트 정책 기본 internal)"
    )
    policy_version: str = Field(..., description="Cedar 정책 버전", min_length=1)
    auth_method: AuthMethod
    visible_set: list[Visibility] = Field(
        ...,
        description="기본 [public, tenant]; api_key이고 service: 주체만이면 [public]",
        min_length=1,
    )


class Principal(BaseModel):
    """
    PrincipalResolver 출력(바이블 §8.1 1단계). SecurityContext.principals의 원천.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    subject: str = Field(..., description="OIDC sub 또는 이메일, API 키 client_id", min_length=1)
    groups: list[str]
    tenant_id: Ulid
    roles: list[str]
    auth_method: AuthMethod
    api_key_id: str | None = None


class TokenCounts(RootModel[int]):
    root: int = Field(..., ge=0)


class TokenCounts1(RootModel[dict[constr(pattern=r"^(hf|tiktoken|anthropic|gemini):\S+$"), TokenCounts]]):
    root: dict[constr(pattern=r"^(hf|tiktoken|anthropic|gemini):\S+$"), TokenCounts] = Field(
        ...,
        description='{tokenizer_id: integer}. 예 {"hf:BAAI/bge-m3": 387, "tiktoken:o200k_base": 455}',
        min_length=1,
    )


class Warning(BaseModel):
    """
    품질 삼중항 2. 콘텐츠 미포함.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    code: ErrorCodeCatalog = Field(
        ...,
        description="§5.7 카탈로그에 등재된 코드(재시도 열 '—' 경고·폴백 코드 또는 partial 코드). 카탈로그 밖 코드는 스키마가 거부한다(00 I-14)",
    )
    message: str = Field(..., description="콘텐츠 미포함")
    block_id: Hex32 | None = None
    chunk_id: Hex64 | None = None
    page: int | None = Field(None, ge=1)


class DegradedEntry(BaseModel):
    """
    품질 삼중항 3(질의 측). 콘텐츠 미포함.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    component: DegradedComponent
    reason: DegradedReason
    detail: str | None = None


class ErrorLocation(BaseModel):
    """
    StageError.location. 오류 위치 식별자만 담고 ACL·주체·콘텐츠는 담지 않는다(13-error-model §2.2 제안 하위 타입).
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    pointer: str | None = Field(
        None,
        description="RFC 6901 JSON Pointer(요청 본문 또는 산출물 내 위치)",
        max_length=256,
    )
    page: int | None = Field(None, description="1-based 페이지(흐름 포맷은 생략)", ge=1)
    block_id: Hex32 | None = None
    chunk_id: Hex64 | None = None
    channel: Channel | None = Field(None, description="질의 측 채널(retrieve·hydrate 오류)")
    collection_id: Ulid | None = None
    document_id: Ulid | None = None


class CloudEventEnvelope(BaseModel):
    """
    CloudEvents 1.0.2 봉투(ADR-0017). data는 ID·해시·상태만, 콘텍스트 본문 금지.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    specversion: Literal["1.0"]
    id: Ulid = Field(..., description="event_id(소비자 멱등 키)")
    source: AnyUrl = Field(..., description="urn:rag:{component}")
    type: EventType
    time: DateTime
    subject: str = Field(
        ...,
        description="tenant/{tenant_id}/{entity}/{id}",
        pattern="^tenant/[0-9A-HJKMNP-TV-Z]{26}/[a-z_]+/[^/\\s]+$",
    )
    datacontenttype: Literal["application/json"]
    dataschema: SchemaId | None = None
    tenantid: Ulid = Field(..., description="CloudEvents 확장 속성(릴레이 테넌트 스코프)")
    data: dict[str, Any] = Field(..., description="ID·해시·상태만. 콘텍스트 본문 금지(E12)")


class ChannelScore(BaseModel):
    """
    채널 원점수·채널 내 순위·융합 기여분·적중 질의 변형.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    score: float = Field(..., description="채널 원점수(cosine / dot / BM25 / MaxSim)")
    rank: int = Field(..., description="채널 내 1-based 순위", ge=1)
    contribution: float = Field(..., description="융합 기여분(RRF: w/(k+rank))")
    variant_ids: list[Ulid] = Field(..., description="적중 질의 변형(rewritten_queries[].variant_id)")


class Boost(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    kind: BoostKind
    delta: float


class ScoreBreakdown(BaseModel):
    """
    점수 원장(K3, ADR-0030). 불변식 Σ contribution(non-null 채널) = fused.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    dense: ChannelScore | None
    sparse: ChannelScore | None
    lexical: ChannelScore | None
    graph: ChannelScore | None
    tree: ChannelScore | None
    visual: ChannelScore | None
    late_interaction: ChannelScore | None
    fused: float
    fused_rank: int = Field(..., ge=1)
    rerank_raw: float | None
    rerank_normalized: float | None
    normalization: ScoreNormalization
    boosts: list[Boost] | None = None


class FilterNode4(BaseModel):
    """
    사용자·self-query 필터 DSL. 논리 결합(and/or/not) 또는 리프(field, op, value) 택1. 깊이 ≤ 3, 절 ≤ 32(플래너 검증).
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    field: FilterableField1
    op: FilterOp
    value: Any | None = Field(
        None,
        description="op별 값. in/not_in/contains_*는 배열, exists는 boolean, 그 외 스칼라",
    )


class Span(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    chunk_id: Hex64
    char_start: int = Field(..., ge=0)
    char_end: int = Field(..., ge=0)


class Entity(BaseModel):
    """
    보강 엔티티(기본 GLiNER2).
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    name: str = Field(..., min_length=1)
    type: str = Field(..., min_length=1)
    canonical_id: str | None = None
    confidence: float = Field(..., ge=0.0, le=1.0)
    span: Span | None = None
    extractor: EntityExtractor


class Relation(BaseModel):
    """
    그래프 플러그인 슬롯(ADR-0015).
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    subject_id: str = Field(..., min_length=1)
    predicate: str = Field(..., min_length=1)
    object_id: str = Field(..., min_length=1)
    weight: float
    evidence_chunk_ids: list[Hex64]


class BlockRef(BaseModel):
    """
    단일 좌표계(K1). char_*는 Chunk.text(display) 기준, original_char_*는 원문 Block.text 기준(offset_map 사상). Chunk·IndexRecord·RankedResult의 block_refs가 같은 구조.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    block_id: Hex32
    element_path: str = Field(..., description="Block.provenance.element_path 복사", min_length=1)
    char_start: int = Field(..., ge=0)
    char_end: int = Field(..., ge=0)
    original_char_start: int = Field(..., ge=0)
    original_char_end: int = Field(..., ge=0)
    page: int | None = Field(..., ge=1)
    bbox: list[float] | None = Field(..., max_length=4, min_length=4)
    section_index: int | None = Field(None, ge=0)


class IndexBackendCapabilities(BaseModel):
    """
    Capabilities.extra(index_backend 전용). 프로파일 로딩 검증·채널 구성의 근거.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    supports_server_bm25: bool
    korean_analyzer: bool
    supports_server_fusion: list[FusionMethod]
    tenant_isolation: list[TenantIsolationTier] = Field(..., min_length=1)
    supports_alias_swap: bool
    supports_multivector: bool
    max_vector_dim: int | None = Field(..., ge=1)
    max_multivector_elements: int | None = Field(..., ge=1)
    supports_payload_only_points: bool | None


class Backoff(BaseModel):
    """
    기본 {1s, 5m, 2.0}
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    initial: Duration
    max: Duration
    coefficient: float = Field(..., ge=1.0)


class StagePolicy(BaseModel):
    """
    스테이지 실행 정책(바이블 §4.4 표의 한 행).
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    task_queue: str = Field(..., pattern="^[a-z][a-z0-9-]*$")
    start_to_close: Duration
    heartbeat: Duration | None
    max_attempts: int = Field(..., ge=1)
    backoff: Backoff | None = Field(None, description="기본 {1s, 5m, 2.0}")
    non_retryable_error_codes: list[ErrorCodeCatalog]
    resumable: bool
    isolation: IsolationMode | None = None


class TieringPolicy(BaseModel):
    """
    테넌트 격리 등급 승격 정책(E15, ADR-0028). 기본 {1000000, null, opt_in, 24h}.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    shard_key_threshold_chunks: int = Field(..., ge=1)
    threshold_qps: float | None = Field(None, ge=0.0)
    index_per_tenant: IndexPerTenantMode
    promotion_window: Duration | None = None


class AllowedScheme(RootModel[str]):
    root: str = Field(..., pattern="^[a-z][a-z0-9+.-]*$")


class AllowedPort(RootModel[int]):
    root: int = Field(..., ge=1, le=65535)


class EgressPolicy(BaseModel):
    """
    아웃바운드 egress 정책(E16, ADR-0038). 프로파일 정책 AND 테넌트 정책.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    allowed_schemes: list[AllowedScheme] = Field(..., description="기본 [https, s3, gs, az]", min_length=1)
    allowed_hosts: list[str] | None = None
    deny_cidrs: list[Cidr] = Field(..., description="사설·루프백·링크로컬·클라우드 메타데이터 CIDR")
    max_redirects: int = Field(..., description="기본 3, 리다이렉트마다 재검사", ge=0)
    resolve_pin: bool = Field(..., description="DNS 해석 IP 검사 후 고정 연결")
    max_bytes: int | None = Field(None, ge=1)
    connect_timeout_ms: int | None = Field(None, ge=1)
    allowed_ports: list[AllowedPort] | None = None
    strip_query_keys: list[str] | None = Field(
        None,
        description="N(바이블 §5.3 1.3.0, AM-30). 서명 쿼리 파라미터 키(로그·감사 이벤트 기록 전 제거). 정본 목록은 04-pipelines/02 §3.6",
    )


class LineageRefs(BaseModel):
    """
    봉투 lineage_refs(바이블 §5.2). 상류 산출물 참조, 자기 자신 제외. IndexCommit.artifact_refs와 같은 키.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    source: ArtifactRef | None = None
    parsed: ArtifactRef | None = None
    normalized: ArtifactRef | None = None
    chunk_set: ArtifactRef | None = None
    enriched: ArtifactRef | None = None
    embedded: ArtifactRef | None = None


class TableCell(BaseModel):
    """
    표 앵커 셀(병합 셀은 앵커 1개). 0-based 좌표, span ≥ 1.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    row: int = Field(..., ge=0)
    col: int = Field(..., ge=0)
    row_span: int = Field(..., ge=1)
    col_span: int = Field(..., ge=1)
    text: str = Field(..., description="셀 내 문단 병합. 중첩 표는 [table:{block_id}] 플레이스홀더")
    is_header: bool
    header_kind: TableCell_1.HeaderKind
    provenance: Provenance | None = None
    nested_table_block_id: str | None = None


class HeaderRowIndice(RootModel[int]):
    root: int = Field(..., ge=0)


class Quality1(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    merged_cells_preserved: bool
    structure_source: quality_1.StructureSource
    structure_confidence: float | None = Field(None, ge=0.0, le=1.0)


class TableData(BaseModel):
    """
    셀 격자 무손실(HTML rowspan/colspan 재생성 가능).
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    n_rows: int = Field(..., ge=0)
    n_cols: int = Field(..., ge=0)
    cells: list[TableCell]
    header_row_indices: list[HeaderRowIndice]
    header_inferred: bool
    role: TableRole
    quality: Quality1
    html_ref: ArtifactRef | None = None


class Figure(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    artifact: ArtifactRef
    kind: figure_1.Kind
    alt_text: str | None = None
    caption_generated: bool | None = None
    caption_model: str | None = None


class Formula(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    script: str = Field(..., description="한컴 수식 script 원문(필수)")
    latex: str | None = None


class Footnote(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    kind: footnote_1.Kind
    anchor_block_id: str | None = None
    anchor_char_offset: int | None = Field(None, ge=0)
    marker: str | None = None


class Code(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    language: str | None = None


class PageBreak(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    page_no: int | None = Field(None, ge=1)
    section_index: int | None = Field(None, ge=0)


class Block(BaseModel):
    """
    ParsedDocument.blocks[] 요소. 문서 순서 평탄 리스트, 계층은 parent_block_id.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    block_id: Hex32 = Field(..., description='H("block", doc_version, element_path)[:32]')
    type: BlockType
    parent_block_id: Hex32 | None
    ordinal: int = Field(..., ge=0)
    text: str = Field(..., description='원문(NFC 미적용; 표·그림은 "" 가능)')
    level: int | None = Field(None, description="heading 0..6(0 = 문서 제목), list_item 깊이", ge=0)
    numbering_label: str | None = None
    heading_inferred: bool | None = None
    ordered: bool | None = None
    furniture: bool = Field(..., description="머리말·꼬리말·nav 등 본문 아님(기본 청킹 제외)")
    container: BlockContainer
    lang: Bcp47 | None = None
    source: BlockSource
    confidence: float | None = Field(None, ge=0.0, le=1.0)
    provenance: Provenance
    caption_of: str | None = None
    caption_block_ids: list[Hex32] | None = None
    table: TableData | None = None
    figure: Figure | None = None
    formula: Formula | None = None
    footnote: Footnote | None = None
    code: Code | None = None
    page_break: PageBreak | None = None


class OffsetMapItemItem(RootModel[int]):
    root: int = Field(..., ge=0)


class OffsetMapItem(RootModel[list[OffsetMapItemItem]]):
    root: list[OffsetMapItemItem] = Field(..., min_length=3)


class SubSpanItem(RootModel[int]):
    root: int = Field(..., ge=0)


class SubSpan(RootModel[list[SubSpanItem]]):
    root: list[SubSpanItem] = Field(..., min_length=2)


class SentenceSpan(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    start: int = Field(..., ge=0)
    end: int = Field(..., ge=0)
    sub_spans: list[SubSpan]


class NormalizedBlock(BaseModel):
    """
    NormalizedDocument.blocks[] 요소. 원 Block과 block_id로 1:1. display_text NFC / lexical_text NFKC.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    block_id: Hex32
    display_text: str = Field(..., description="NFC(제어·PUA·zero-width 제거; 표시·인용 원문)")
    lexical_text: str = Field(
        ...,
        description="NFKC(기호 통일, 한자 독음, 띄어쓰기 교정 opt-in; BM25·키워드 입력)",
    )
    offset_map: list[OffsetMapItem] = Field(..., description="[display_start, original_start, length] 구간 사상")
    sentence_spans: list[SentenceSpan] = Field(..., description="display 기준")
    lang: Bcp47
    boilerplate: bool
    furniture_reason: FurnitureReason | None = None
    text_source: BlockSource
    confidence: float | None = Field(..., ge=0.0, le=1.0)


class SentenceSpan1Item(RootModel[int]):
    root: int = Field(..., ge=0)


class SentenceSpan1(RootModel[list[SentenceSpan1Item]]):
    root: list[SentenceSpan1Item] = Field(..., min_length=2)


class RowRangeItem(RootModel[int]):
    root: int = Field(..., ge=0)


class ColRangeItem(RootModel[int]):
    root: int = Field(..., ge=0)


class TableRef(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    table_block_id: Hex32
    header_row_indices: list[HeaderRowIndice]
    row_range: list[RowRangeItem] = Field(..., max_length=2, min_length=2)
    col_range: list[ColRangeItem] = Field(..., max_length=2, min_length=2)
    serialization: TableSerialization
    html_ref: ArtifactRef | None


class Window(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    before_chunk_ids: list[Hex64]
    after_chunk_ids: list[Hex64]


class ContextPrefix(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    deterministic: str = Field(..., description='"{title} › {heading_path 조인} › {caption?}" 50~100토큰')
    generated: str | None = Field(..., description="LLM 문맥(O-05, 기본 null)")
    generated_by: ModelId | None


class Chunk(BaseModel):
    """
    ChunkSet.chunks[] 요소. chunk_id = H("chunk", doc_version, chunker_config_hash, str(level), span)(ADR-0004). 3-텍스트 규칙: text는 접두어 미포함(ADR-0029). item_kind ↔ level 대응(바이블 §5.7 ChunkLevel; parent ⇔ 1, summary·community_report·entity ⇔ 2, 그 외 ⇔ 0; 05 C-5)은 allOf의 if/then 4개로 강제하며 IndexRecord와 같은 규칙이다.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    chunk_id: Hex64
    span: ChunkSpan
    item_kind: ItemKind
    level: ChunkLevel
    parent_chunk_id: Hex64 | None
    child_chunk_ids: list[Hex64] | None = None
    ordinal: int = Field(..., ge=0)
    text: str = Field(..., description="display_text 조각, 접두어 미포함")
    lexical_text: str = Field(..., description="lexical_text 조각(BM25·sparse 입력 원료)")
    heading_path: list[str]
    numbering_path: list[str] | None = None
    block_refs: list[BlockRef] = Field(
        ...,
        description="level 0·1은 1개 이상이며 오프셋 합집합이 text를 재구성한다. level 2(summary·community_report·entity)는 text가 파생물이라 재구성 불변식이 적용되지 않는다(00 미해결 이슈 U-11)",
    )
    sentence_spans: list[SentenceSpan1]
    token_counts: TokenCounts1
    lang: Bcp47
    table_ref: TableRef | None = None
    window: Window | None = None
    context_prefix: ContextPrefix
    tree_level: int | None = Field(None, ge=0)
    page_image_ref: ArtifactRef | None = None
    text_source: BlockSource = Field(
        ...,
        description="포함 블록 source의 최저 신뢰 등급(text_layer > converted > vlm > ocr)",
    )
    ocr_confidence_min: float | None = Field(..., ge=0.0, le=1.0)
    content_hash: Hex64 = Field(..., description="blake3_hex(utf8(text))")


class StripOffsets(BaseModel):
    """
    strip() 대칭 보장
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    text_start_in_embed: int = Field(..., ge=0)
    text_start_in_index: int = Field(..., ge=0)


class Keyword(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    term: str = Field(..., min_length=1)
    weight: float = Field(..., description="source별 가중(06 §5), ≥ 0(06 E-12)", ge=0.0)
    source: KeywordSource


class PiiEntityCounts(RootModel[int]):
    root: int = Field(..., ge=0)


class Enrichment(BaseModel):
    """
    EnrichedChunkSet.enrichments[chunk_id]. embed_text = deterministic + "\\n" + (generated + "\\n")? + text; index_text = prefix(lexical) + "\\n" + lexical_text.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    embed_text: str = Field(..., description="dense·sparse 입력")
    index_text: str = Field(..., description="BM25 입력")
    strip_offsets: StripOffsets = Field(..., description="strip() 대칭 보장")
    keywords: list[Keyword]
    entities: list[Entity]
    relations: list[Relation] | None = None
    dates: list[Date] | None = None
    law_refs: list[str] | None = None
    figure_caption: str | None = None
    figure_table_markdown: str | None = None
    hypothetical_questions: list[str] | None = Field(None, description="켜면 index_text에만 부착")
    summary: str | None = None
    risk_flags: list[str]
    risk_score: float = Field(..., ge=0.0, le=1.0)
    pii_entity_counts: dict[str, PiiEntityCounts]
    status: EnrichStatus


class Dense(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    name: Literal["dense"]
    dim: int = Field(..., ge=1)
    offset: int = Field(..., ge=0)


class Indice(RootModel[int]):
    root: int = Field(..., ge=0)


class SparseLearned(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    name: Literal["sparse_learned"]
    vocab_id: str = Field(..., min_length=1)
    indices: list[Indice]
    values: list[float]


class SparseBm25(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    name: Literal["sparse_bm25"]
    vocab_id: str = Field(..., description="= analyzer_id", min_length=1)
    indices: list[Indice]
    values: list[float]


class LateInteraction(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    name: Literal["late_interaction"]
    dim: int = Field(..., ge=1)
    count: int = Field(..., ge=1)
    offset: int = Field(..., ge=0)


class VectorBundle1(BaseModel):
    """
    EmbeddedChunkSet.vectors[chunk_id]. 벡터 본문은 vectors_ref 안 오프셋. sparse_learned(standard) 또는 sparse_bm25(lite) 중 하나 이상.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    dense: Dense
    sparse_learned: SparseLearned
    sparse_bm25: SparseBm25 | None = None
    late_interaction: LateInteraction | None = None
    page_multivector: dict[str, Any] | None = Field(None, description="visual-pages(07 문서)")
    pooled_page_multivector: dict[str, Any] | None = Field(None, description="visual-pages(07 문서)")
    page_dense: dict[str, Any] | None = Field(None, description="visual-pages(07 문서)")
    embed_text_hash: Hex64 = Field(..., description="캐시 키 재계산")
    truncated: bool = Field(..., description="토큰 초과 절단 여부")


class SparseLearned1(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    name: Literal["sparse_learned"]
    vocab_id: str = Field(..., min_length=1)
    indices: list[Indice]
    values: list[float]


class SparseBm251(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    name: Literal["sparse_bm25"]
    vocab_id: str = Field(..., description="= analyzer_id", min_length=1)
    indices: list[Indice]
    values: list[float]


class VectorBundle2(BaseModel):
    """
    EmbeddedChunkSet.vectors[chunk_id]. 벡터 본문은 vectors_ref 안 오프셋. sparse_learned(standard) 또는 sparse_bm25(lite) 중 하나 이상.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    dense: Dense
    sparse_learned: SparseLearned1 | None = None
    sparse_bm25: SparseBm251
    late_interaction: LateInteraction | None = None
    page_multivector: dict[str, Any] | None = Field(None, description="visual-pages(07 문서)")
    pooled_page_multivector: dict[str, Any] | None = Field(None, description="visual-pages(07 문서)")
    page_dense: dict[str, Any] | None = Field(None, description="visual-pages(07 문서)")
    embed_text_hash: Hex64 = Field(..., description="캐시 키 재계산")
    truncated: bool = Field(..., description="토큰 초과 절단 여부")


class VectorBundle(RootModel[VectorBundle1 | VectorBundle2]):
    root: VectorBundle1 | VectorBundle2 = Field(
        ...,
        description="EmbeddedChunkSet.vectors[chunk_id]. 벡터 본문은 vectors_ref 안 오프셋. sparse_learned(standard) 또는 sparse_bm25(lite) 중 하나 이상.",
    )


class Acl1(BaseModel):
    """
    IndexRecord.acl_* 역평탄화; pack.acl_recheck 입력
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    allow: list[PrincipalString]
    deny: list[PrincipalString]
    visibility: Visibility
    classification: Classification
    embargo_until: DateTime | None
    expires_at: DateTime | None
    acl_hash: Hex64


class SentenceSpan2Item(RootModel[int]):
    root: int = Field(..., ge=0)


class SentenceSpan2(RootModel[list[SentenceSpan2Item]]):
    root: list[SentenceSpan2Item] = Field(..., min_length=2)


class RankedResult(BaseModel):
    """
    RankedSet.results[] 요소. hydrated=true 조건 필수(text 등)는 RankedSet 스키마의 if/then이 강제한다.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    record_id: Hex64 | None = Field(..., description="부모 확장 항목(item_kind=parent)은 null")
    chunk_id: Hex64
    collection_id: Ulid
    document_id: Ulid
    doc_version: Hex64
    item_kind: ItemKind
    level: ChunkLevel
    parent_chunk_id: Hex64 | None
    final_rank: int = Field(..., ge=1)
    final_score: float = Field(..., ge=0.0, le=1.0)
    fused_score: float
    fused_rank: int = Field(..., ge=1)
    rerank_raw_score: float | None = None
    rerank_normalized_score: float | None = None
    rerank_rank: int | None = Field(None, ge=1)
    score_breakdown: ScoreBreakdown
    channels_hit: list[Channel]
    variant_ids: list[Ulid]
    text: str | None = None
    context_prefix: str | None = None
    heading_path: list[str] | None = None
    numbering_path: list[str] | None = None
    title: str | None = None
    source_uri: Uri | None = None
    external_id: str | None = None
    doc_date: Date | None = None
    doc_type: str | None = None
    page_start: int | None = Field(None, ge=1)
    page_end: int | None = Field(None, ge=1)
    lang: Bcp47 | None = None
    text_source: BlockSource | None = None
    ocr_confidence_min: float | None = Field(None, ge=0.0, le=1.0)
    chunk_set_blake3: Hex64 | None = None
    token_count_primary: int | None = Field(
        None,
        description="N(바이블 §5.5 1.3.0, AM-33). hydrate 시 채움 — 대상 토크나이저 기준 text 토큰 수(Chunk.token_counts.primary 복사)",
        ge=0,
    )
    ordinal: int | None = Field(
        None,
        description="N(바이블 §5.5 1.3.0, AM-33). hydrate 시 채움 — Chunk.ordinal 복사(같은 부모 아래 형제 순서, 0-based)",
        ge=0,
    )
    text_truncated: bool | None = Field(
        None,
        description="N(바이블 §5.5 1.3.0, AM-33). hydrate 시 채움 — text가 IndexRecord payload 절단본(embed.token_overflow)이면 true",
    )
    pii_policy_applied: PiiPolicy | None = Field(
        None,
        description="N(바이블 §5.5 1.3.0, AM-33). hydrate 시 채움 — 원천은 IndexRecord.payload.pii_policy_applied 경로",
    )
    acl: Acl1 | None = Field(None, description="IndexRecord.acl_* 역평탄화; pack.acl_recheck 입력")
    block_refs: list[BlockRef] | None = None
    sentence_spans: list[SentenceSpan2] | None = None
    table_ref: dict[str, Any] | None = Field(None, description="Chunk.table_ref 복사(pack이 tables[]로 구체화)")
    html_ref: ArtifactRef | None = None
    expanded_from: list[Hex64] | None = None
    duplicates_of: Hex64 | None = None
    window_chunk_ids: list[Hex64] | None = None
    explain: list[ExplainCode]


class Header(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    title: str
    section_path: list[str]
    numbering_path: list[str]
    source_uri: Uri
    external_id: str | None = None
    doc_date: Date | None = None
    doc_type: str | None = None
    page_start: int | None = Field(None, ge=1)
    page_end: int | None = Field(None, ge=1)
    lang: Bcp47
    doc_version_label: str | None = None


class Segment(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    index: int = Field(..., ge=0)
    text: str
    char_start: int = Field(..., ge=0)
    char_end: int = Field(..., ge=0)
    block_id: Hex32


class Table(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    table_id: str = Field(..., min_length=1)
    html: str | None = None
    markdown: str | None = None
    json_records: list[dict[str, Any]] | None = None
    caption: str | None = None
    format_used: TableFormat
    downgraded: bool


class Figure1(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    figure_id: str = Field(..., min_length=1)
    caption: str | None = None
    alt_text: str | None = None
    image_ref: ArtifactRef | None = None


class Parent(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    parent_chunk_id: Hex64
    expanded: bool
    parent_text_included: bool
    child_chunk_ids: list[Hex64]


class ConflictsWithItem(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    cite_id: CiteId
    kind: ConflictKind
    note: str | None = None


class Acl2(BaseModel):
    """
    반환 직전 재검증 증적(E9)
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    classification: Classification
    checked: Literal[True]
    checked_at: DateTime = Field(..., description="= SecurityContext.as_of")
    source: AclCheckSource


class ContextItem(BaseModel):
    """
    ContextPack.items[] 요소. cite_id는 관련도순 불변, position은 렌더 위치. provenance는 block_refs에서 결정적으로 생성.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    cite_id: CiteId
    rank: int = Field(..., description="관련도 순위(1-based, 최종 항목 기준)", ge=1)
    position: int = Field(..., description="렌더 위치(0-based)", ge=0)
    record_id: Hex64 | None
    chunk_id: Hex64
    collection_id: Ulid
    document_id: Ulid
    doc_version: Hex64
    parent_chunk_id: Hex64 | None = None
    item_kind: ItemKind
    level: ChunkLevel
    confidence_tier: ConfidenceTier
    header: Header
    text: str = Field(
        ...,
        description="원문(접두어 제외). level=0 항목 ≤ 8,192 UTF-8 바이트, 부모 확장 항목 ≤ 32,768",
    )
    text_format: TextFormat
    text_source: BlockSource
    ocr_confidence_min: float | None = Field(..., ge=0.0, le=1.0)
    segments: list[Segment] = Field(..., description="인용 최소 단위(문장·표 행), text 기준 오프셋")
    context_prefix: str | None = None
    tables: list[Table] | None = None
    figures: list[Figure1] | None = None
    parent: Parent | None = None
    duplicates_of: Hex64 | None = None
    conflicts_with: list[ConflictsWithItem] | None = None
    provenance: list[Provenance] = Field(
        ...,
        description="block_refs[]에서 결정적 생성: char_* = original_char_*. level 0·1은 1개 이상(00 미해결 이슈 U-11)",
    )
    acl: Acl2 = Field(..., description="반환 직전 재검증 증적(E9)")
    scores: ScoreBreakdown | None = Field(None, description="explain=true만")
    token_count: int = Field(..., description="budget.tokenizer 기준", ge=0)


class SecurityFilter(BaseModel):
    """
    보안 불변식(바이블 §10.2 (a), §5.1 1.3.0 공용 타입 승격 AM-35). 제거·완화 불가. 값은 security_context에서 복사.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    tenant_id: Ulid
    collection_ids: list[Ulid] = Field(..., max_length=20, min_length=1)
    principals: list[PrincipalString] = Field(..., max_length=1024, min_length=1)
    visible_set: list[Visibility] = Field(..., max_length=3, min_length=1)
    as_of: DateTime
    is_current: Literal[True]
    classification_max: Classification


class StrategyFilter(BaseModel):
    """
    전략 필터(바이블 §10.2 (b), §5.1 1.3.0 공용 타입 승격 AM-35). strategy별 고정값(최상위 allOf가 const로 고정). 사용자 완화 불가.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    level_in: list[ChunkLevel] = Field(..., max_length=3, min_length=1)
    item_kinds: list[ItemKind] = Field(..., max_length=11, min_length=1)


class ChannelRunId(RootModel[str]):
    root: str = Field(
        ...,
        description='"{channel}:{collection_id}:{variant_id}"(바이블 §6.1, §5.1 1.3.0 공용 타입 승격 AM-35). 채널 부분은 형태만 검사(Channel 열거 재기술 금지); 채널 값 = ChannelRun.channel 일치는 Pydantic이 검사한다.',
        pattern="^[a-z_]+:[0-9A-HJKMNP-TV-Z]{26}:[0-9A-HJKMNP-TV-Z]{26}$",
    )


class EmbeddingSpaceIds1(BaseModel):
    """
    바이블 §5.4 embedding_space_ids {dense, sparse_learned?, sparse_bm25?, late_interaction?}(§5.1 1.3.0 공용 타입 승격 AM-35). 키는 VectorName, 값은 H("space", model_id, revision, str(dim), str(normalized), prompt_hash, quantization, vocab_id or "")(§6.2). sparse_learned(standard) 또는 sparse_bm25(lite) 중 하나 이상. 모델·revision·차원·정규화·프롬프트·양자화·어휘 중 하나라도 바뀌면 다른 공간 = 재색인. visual-pages page_* 변형은 07 미해결 이슈 3 확정 후 minor로 추가(현재 미포함)
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    dense: Hex64
    sparse_learned: Hex64 = Field(..., description="vocab_id 예 xlm-roberta-250k(BGE-M3 sparse)")
    sparse_bm25: Hex64 | None = Field(None, description="lite. vocab_id = analyzer_id")
    late_interaction: Hex64 | None = Field(None, description="선택 슬롯(기본 끔, ADR-0010)")


class EmbeddingSpaceIds2(BaseModel):
    """
    바이블 §5.4 embedding_space_ids {dense, sparse_learned?, sparse_bm25?, late_interaction?}(§5.1 1.3.0 공용 타입 승격 AM-35). 키는 VectorName, 값은 H("space", model_id, revision, str(dim), str(normalized), prompt_hash, quantization, vocab_id or "")(§6.2). sparse_learned(standard) 또는 sparse_bm25(lite) 중 하나 이상. 모델·revision·차원·정규화·프롬프트·양자화·어휘 중 하나라도 바뀌면 다른 공간 = 재색인. visual-pages page_* 변형은 07 미해결 이슈 3 확정 후 minor로 추가(현재 미포함)
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    dense: Hex64
    sparse_learned: Hex64 | None = Field(None, description="vocab_id 예 xlm-roberta-250k(BGE-M3 sparse)")
    sparse_bm25: Hex64 = Field(..., description="lite. vocab_id = analyzer_id")
    late_interaction: Hex64 | None = Field(None, description="선택 슬롯(기본 끔, ADR-0010)")


class EmbeddingSpaceIds(RootModel[EmbeddingSpaceIds1 | EmbeddingSpaceIds2]):
    root: EmbeddingSpaceIds1 | EmbeddingSpaceIds2 = Field(
        ...,
        description='바이블 §5.4 embedding_space_ids {dense, sparse_learned?, sparse_bm25?, late_interaction?}(§5.1 1.3.0 공용 타입 승격 AM-35). 키는 VectorName, 값은 H("space", model_id, revision, str(dim), str(normalized), prompt_hash, quantization, vocab_id or "")(§6.2). sparse_learned(standard) 또는 sparse_bm25(lite) 중 하나 이상. 모델·revision·차원·정규화·프롬프트·양자화·어휘 중 하나라도 바뀌면 다른 공간 = 재색인. visual-pages page_* 변형은 07 미해결 이슈 3 확정 후 minor로 추가(현재 미포함)',
    )


class TableRef1(BaseModel):
    """
    Chunk.table_ref 구조(§5.1 1.3.0 공용 타입 승격 AM-35). row_range·col_range는 [start, end) 0-based.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    table_block_id: Hex32
    header_row_indices: list[HeaderRowIndice]
    row_range: list[RowRangeItem] = Field(..., description="[start, end) 0-based 정수 구간", max_length=2, min_length=2)
    col_range: list[ColRangeItem] = Field(..., description="[start, end) 0-based 정수 구간", max_length=2, min_length=2)
    serialization: TableSerialization
    html_ref: ArtifactRef | None


class ProfileId(RootModel[str]):
    root: str = Field(
        ...,
        description="프로파일 ID kebab-case(바이블 §6.1, §5.1 1.3.0 공용 타입 승격 AM-35). 예 standard, korean-gov",
        max_length=64,
        pattern="^[a-z][a-z0-9]*(-[a-z0-9]+)*$",
    )


class AnalyzerId(RootModel[str]):
    root: str = Field(
        ...,
        description="{engine}:{version}:{dictionary}(바이블 §6.1, §5.1 1.3.0 공용 타입 승격 AM-35). 예 mecab-ko:1.3.7:ko-dic-2.1.1, kiwi:0.24.0:cong",
        max_length=128,
        pattern="^[a-z][a-z0-9-]*:[^:\\s]+:[^\\s]+$",
    )


class KebabName(RootModel[str]):
    root: str = Field(
        ...,
        description="스키마 파일 이름·미디어 타입 접미의 kebab-name(§5.1 1.3.0 공용 타입 승격 AM-35).",
        pattern="^[a-z0-9]+(-[a-z0-9]+)*$",
    )


class ContractsCompat(RootModel[str]):
    root: str = Field(
        ...,
        description='수용 계약 schema_version 범위(">=1.0,<2.0", §5.1 1.3.0 공용 타입 승격 AM-35). 문법·평가는 14 §4.3: 쉼표로 이은 비교절, 각 절은 (>=|<=|==|<|>)MAJOR.MINOR(선행 0 금지), patch 불참, ~= 없음. M-2(contracts_compat == capabilities.contracts_compat)로 capabilities.contracts_compat에도 같은 문법이 강제된다.',
        max_length=64,
        pattern="^(>=|<=|==|<|>)(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)(,(>=|<=|==|<|>)(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*))*$",
    )


class StageError(BaseModel):
    """
    스테이지 오류. RFC 9457 type = urn:rag:error:{code} 1:1(바이블 §4.1). 재시도 여부는 카탈로그가 결정. message·occurred_at·attempt·location·cause는 바이블 §5.3 미등재 선택 필드(13-error-model 제안, 00 미해결 이슈 U-12).
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    code: ErrorCodeCatalog = Field(..., description="§5.7 카탈로그 등재 코드(00 I-14). type = urn:rag:error:{code}")
    type: ErrorTypeUrn
    retryable: bool
    stage: str = Field(
        ...,
        description="발생 스테이지(fetch, detect, parse, normalize, chunk, recount, enrich, embed, index, publish, plan, retrieve, fuse, hydrate, rerank, postprocess, pack, render) 또는 비파이프라인 지점(api, loader, relay)",
        max_length=32,
        pattern="^[a-z][a-z0-9_]*$",
    )
    plugin_id: str | None = Field(
        None,
        description="{extension_point}.{implementation}(바이블 §6.1). 예 parser.hwpx_python_hwpx",
        max_length=128,
        pattern="^[a-z][a-z0-9_]*\\.[a-z][a-z0-9_]*$",
    )
    detail: str | None = Field(
        None,
        description="인스턴스별 진단 문구(영문, 기계 지향). 콘텐츠 미포함",
        max_length=1024,
    )
    artifact_ref: ArtifactRef | None = Field(None, description="실패 시점 입력")
    message: str | None = Field(
        None,
        description="코드별 고정 영문 문구(카탈로그 title_en). 지역화는 ProblemDetails.title에서만",
        max_length=256,
    )
    occurred_at: DateTime | None = Field(None, description="발생 시각")
    attempt: int | None = Field(
        None,
        description="실패한 시도 번호(1-based; StagePolicy.max_attempts 대비)",
        ge=1,
    )
    location: ErrorLocation | None = Field(None, description="오류 위치(요청 필드·페이지·블록·청크·채널·스코프 ID)")
    cause: StageError | None = Field(
        None,
        description="원인 오류(폴백 체인·보상에서 감싼 하위 오류). 중첩 깊이 3 이하(Pydantic 검증)",
    )


class ProblemDetails(BaseModel):
    """
    RFC 9457 Problem Details + 확장 멤버(code, retryable, trace_id, errors). retry_after·request_id는 바이블 §5.3 미등재 선택 필드(13-error-model 제안, 00 미해결 이슈 U-12).
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    type: ErrorTypeUrn
    title: str = Field(
        ...,
        description="코드별 고정 제목. Accept-Language로 지역화되는 유일한 필드",
        max_length=256,
        min_length=1,
    )
    status: int = Field(..., description="HTTP 상태(13-error-model HTTP 매핑 표)", ge=400, le=599)
    detail: str | None = Field(None, description="인스턴스별 진단 문구(영문). 콘텐츠 미포함", max_length=2048)
    instance: str | None = Field(
        None,
        description="발생 요청 경로 또는 관련 자원(/v1/jobs/{job_id}). RFC 9457 §3.1.5 URI-reference(상대 참조 허용)",
        max_length=512,
        min_length=1,
    )
    code: ErrorCodeCatalog = Field(..., description="= StageError.code(§5.7 카탈로그 등재 코드, 00 I-14)")
    retryable: bool = Field(..., description="카탈로그 값. errors[]가 있으면 errors[].retryable의 OR")
    trace_id: str = Field(
        ...,
        description="W3C Trace Context trace-id(소문자 hex 32)",
        pattern="^[0-9a-f]{32}$",
    )
    errors: list[StageError] | None = Field(
        None,
        description="다중 오류(요청 검증·채널 실패). 16개 초과분은 detail에 개수만 남긴다",
        max_length=16,
        min_length=1,
    )
    retry_after: int | None = Field(
        None,
        description="Retry-After 헤더 값(초)의 본문 사본. status 429·503에서만",
        ge=0,
    )
    request_id: Ulid | None = Field(None, description="요청 ID(바이블 §6.1)")


class Capabilities(BaseModel):
    """
    모든 Stage 공통 capabilities() 선언(ADR-0032).
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    isolation_modes: list[IsolationMode] = Field(..., min_length=1)
    supports_resumable: bool = Field(..., description="heartbeat_details 재개 지원")
    contracts_compat: ContractsCompat = Field(
        ...,
        description='계약 호환 범위(">=1.0,<2.0"). M-2: PluginMeta.contracts_compat 와 같아야 한다',
    )
    input_formats: list[str] | None = None
    model_ids: list[ModelId] | None = None
    requires_gpu: bool | None = None
    extra: dict[str, Any] | None = Field(
        None,
        description="확장 지점 전용 필드. index_backend는 IndexBackendCapabilities",
    )


class FilterNode1(BaseModel):
    """
    사용자·self-query 필터 DSL. 논리 결합(and/or/not) 또는 리프(field, op, value) 택1. 깊이 ≤ 3, 절 ≤ 32(플래너 검증).
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    and_: list[FilterNode] = Field(..., alias="and", max_length=32, min_length=1)


class FilterNode2(BaseModel):
    """
    사용자·self-query 필터 DSL. 논리 결합(and/or/not) 또는 리프(field, op, value) 택1. 깊이 ≤ 3, 절 ≤ 32(플래너 검증).
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    or_: list[FilterNode] = Field(..., alias="or", max_length=32, min_length=1)


class FilterNode3(BaseModel):
    """
    사용자·self-query 필터 DSL. 논리 결합(and/or/not) 또는 리프(field, op, value) 택1. 깊이 ≤ 3, 절 ≤ 32(플래너 검증).
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    not_: FilterNode = Field(..., alias="not")


class FilterNode(RootModel[FilterNode1 | FilterNode2 | FilterNode3 | FilterNode4]):
    root: FilterNode1 | FilterNode2 | FilterNode3 | FilterNode4 = Field(
        ...,
        description="사용자·self-query 필터 DSL. 논리 결합(and/or/not) 또는 리프(field, op, value) 택1. 깊이 ≤ 3, 절 ≤ 32(플래너 검증).",
    )


StageError.model_rebuild()
FilterNode1.model_rebuild()
FilterNode2.model_rebuild()
FilterNode3.model_rebuild()
