---
title: 설계 브리프 (Architect Brief)
status: active
owner: architecture
version: 1.2.2
last_updated: 2026-09-23
audience: 모든 문서 작성자·리뷰어·구현자 (사람과 에이전트)
---

# RAG Platform 설계 브리프

> 이 문서는 **모든 산출물의 앵커**다. 다른 문서와 충돌하면 이 문서와 `02-architecture/00-design-bible.md`(설계 바이블)가 우선한다.
> 우선순위: 설계 브리프 > 설계 바이블 > ADR > 개별 설계 문서.

## 1. 한 문장 정의

**RAG Platform**은 수집된 문서(HWPX·HWP·PDF·DOC/DOCX·TXT·HTML 등)의 **위치(URI)와 메타데이터를 API로 받아**, 오픈소스 최선의 기술로 **파싱 → 정규화 → 의미 기반 청킹 → 보강(enrichment) → 임베딩 → 하이브리드 인덱싱**을 수행하고, **리트리벌 API**로 LLM이 즉시 참고해 최고의 답을 낼 수 있는 **Top-K 컨텍스트 팩(Context Pack)** 을 돌려주는 오픈소스(Apache-2.0) 플랫폼이다.

## 2. 원 요구사항 (사용자 원문 → 해석)

| # | 원문 | 해석 및 설계 함의 |
|---|------|------------------|
| R1 | 수집된 HWPX, PDF, DOC, TXT, HTML 등의 주소와 메타 정보를 API로 전달받아서 | **Pull 모델 수집**. 플랫폼은 크롤러가 아니다. `IngestRequest`(URI + metadata + 정책)를 받아 비동기 잡으로 처리. URI 스킴: `s3://`, `gs://`, `az://`, `file://`, `http(s)://`, `smb://`(플러그인). 한국 공공/기업 문서 특성상 **HWPX/HWP 1급 지원** 필수. |
| R2 | 파싱하고 의미적인 부분을 고려하여 청킹하여 임베딩하는 라이브러리와 오픈소스를 최대한 사용하고 | **Not-Invented-Here 금지**. 파서(Docling, Unstructured, PyMuPDF, python-hwpx 등), 청커(Docling HybridChunker, Chonkie, LlamaIndex 등), 임베딩(BGE-M3, multilingual-e5, Qwen3-Embedding, KURE 등)은 검증된 오픈소스를 어댑터로 감싼다. 우리가 소유하는 것은 **표준 계약(contract)과 오케스트레이션**이다. |
| R3 | 리트리벌 API를 통해 TOP-K를 최대한 잘 뽑아주는 RAG 플랫폼 | 검색 품질이 제1 지표. **하이브리드(dense + sparse + lexical) → 융합 → 리랭킹 → 후처리**를 기본 파이프라인으로. 평가 하네스(nDCG@k, Recall@k, MRR, 컨텍스트 정밀도)를 1급 시민으로. |
| R4 | 각 파이프라인을 최대한 우아하고 모든 기술을 사용하도록 설계 | "모든 기술"은 **모두 기본 켬**이 아니라 **모두 플러그인으로 수용 가능한 확장 지점**을 의미한다. 기본 프로파일은 검증된 조합, 고급 기법(GraphRAG, RAPTOR, ColBERT, LLM 리랭커, 컨텍스트 압축 등)은 프로파일/플러그인으로 선택. 우아함 = 단일 책임 스테이지, 순수 함수형 계약, 관측 가능성, 멱등성. |
| R5 | 각 단계의 인풋과 아웃풋을 표준화하여 규약을 만들고 | 모든 스테이지 경계마다 **버전드 JSON Schema(2020-12) + Pydantic v2 모델**. 스테이지는 `Stage[In, Out]` 순수 변환. 산출물(artifact)은 오브젝트 스토리지에 콘텐츠 주소화(content-addressed)로 저장, 재처리·캐싱·감사 가능. |
| R6 | 최종적으로 TOP-K는 LLM이 참고하면 최고의 효과를 낼 수 있어야 한다 | 출력은 단순 청크 배열이 아니라 **Context Pack**: 토큰 예산 내 정렬(lost-in-the-middle 대응), 중복 제거, 부모 확장(small-to-big), 출처·인용 ID, 표/그림 텍스트화, 신뢰도 점수, 프롬프트 템플릿 힌트, Anthropic `document` 블록/`citations` 등 **LLM 네이티브 포맷으로 직렬화 가능**. MCP 서버로 에이전트가 직접 호출 가능. |

## 3. 설계 원칙 (Design Principles)

1. **Contracts First** — 스테이지 간 계약(스키마)이 코드보다 먼저다. 계약이 바뀌면 `schema_version`이 바뀐다.
2. **Adapters over Forks** — 오픈소스는 어댑터로 감싼다. 포크하지 않는다. 벤더 모델(DoclingDocument 등)은 우리의 표준 모델로 변환된다.
3. **Pure Stages, Durable Orchestration** — 스테이지는 입력→출력 순수 변환. 상태·재시도·타임아웃은 오케스트레이터가 책임진다.
4. **Idempotent & Content-Addressed** — 같은 입력은 같은 출력. 모든 산출물은 해시로 주소화되어 재사용된다.
5. **Hybrid by Default, Pluggable Everywhere** — 기본 프로파일은 하이브리드 검색 + 리랭킹. 모든 스테이지는 플러그인 교체 가능.
6. **Korean-First, Multilingual-Ready** — HWPX/HWP, 한국어 토크나이징(Nori/Kiwi), 한국어 임베딩 벤치마크를 1급으로 다루되 다국어 모델을 기본 채택.
7. **Evaluation-Driven** — 모든 기본값은 골든셋 평가로 정당화된다. 평가 하네스는 코어 컴포넌트.
8. **Observable & Explainable** — OpenTelemetry(GenAI semconv) 트레이스, 각 후보의 점수 분해(dense/sparse/lexical/rerank), 왜 이 청크가 뽑혔는지 설명 가능.
9. **Multi-Tenant & Secure by Design** — tenant/collection/ACL이 모든 계약과 인덱스 필터에 존재. PII 처리 훅.
10. **LLM-Native Output** — 최종 출력은 사람이 아니라 LLM이 소비한다. 토큰 예산·순서·인용 가능성을 최적화한다.

## 4. 확정 결정 (Architect-Fixed Decisions)

아래는 브리프 수준에서 확정한다. 변경하려면 ADR로 뒤집어야 한다.

| ID | 결정 | 근거 |
|----|------|------|
| D-01 | 구현 언어 **Python 3.12/3.13**(파서 워커 이미지는 3.12/3.13 고정, 3.14는 호환성 검증 후 채택), 계약 모델 **Pydantic v2**, API **FastAPI**, 패키지 관리 **uv**(`uv lock --check` CI), 린트 **ruff**, 타입 **mypy(strict)**, 계층 규칙 **import-linter** (개정 v1.1, 근거: ADR-0035) | RAG 생태계(Docling, Unstructured, LlamaIndex, sentence-transformers 등)가 Python 중심; Unstructured `<3.14`·RapidOCR `≤3.13` 상한 |
| D-02 | 라이선스 **Apache-2.0**. 의존성은 **라이선스 등급표 A/B/C/D/X**로 판정한다: A(Apache/MIT/BSD/MPL-2.0 파일 단위 카피레프트) 자유, B(LGPL) 동적 링크·선택 extra만(정적 링크 휠 기본 설치 금지), C(GPL/AGPL/SSPL/ELv2/BUSL 서버·라이브러리) 별도 컨테이너 + 네트워크 API만·코어 이미지 미포함·별도 저장소 고지·Helm opt-in, D(모델 제한 라이선스·지역 제한·매출 임계·귀속 의무) 기본 프로파일 금지 + `model_license_ack` 필수, X(사용 비허가) 금지. 플러그인·모델 메타데이터에 `license`·`license_grade`·`territory` 필수, CI 라이선스 게이트(pip-licenses + liccheck + SBOM + `models.lock`) (개정 v1.1, 근거: ADR-0001) | 오픈소스 플랫폼의 채택성; LGPL·BSL/SSPL·GPL 서버·모델 라이선스·지역 제한(HunyuanOCR) 규칙 공백 해소 |
| D-03 | 문서 기본 언어 **한국어**(기술 용어·식별자는 영문). 코드·스키마 필드·API는 **영문 snake_case** | 사용자 및 1차 대상 시장 |
| D-04 | **표준 문서 모델(ParsedDocument)은 자체 소유**. DoclingDocument·Unstructured Elements 등은 어댑터로 변환. 구조(계층 섹션·단락·표·그림·목록·각주·메타)와 **출처(provenance)** 를 필수 보존하되, `element_path`와 `char_start/char_end`(원문 유니코드 코드포인트 오프셋)는 **필수**, `page`/`bbox`는 **nullable**(HWP/HWPX·DOCX·HTML·MD 등 흐름 포맷은 null; bbox는 `[x0, y0, x1, y1]` 좌상단 원점·PDF 포인트) (개정 v1.1, 근거: ADR-0002) | 벤더 독립성, HWPX 등 벤더 미지원 포맷 통합; 흐름 포맷에는 페이지·bbox가 존재하지 않음 |
| D-05 | 스테이지 경계: `IngestRequest → SourceDocument → ParsedDocument → NormalizedDocument → ChunkSet → EnrichedChunkSet → EmbeddedChunkSet → IndexCommit` / `QueryRequest → QueryPlan → CandidateSet → RankedSet → ContextPack`. 모든 경계는 JSON Schema 2020-12로 게시 | R5 |
| D-06 | 발급형 ID(`request_id`, `document_id`, `job_id`, `commit_id`, `query_id`, `plan_id`, `pack_id` 등 `*_id`)는 **ULID**(시간 정렬). **콘텐츠 파생 키는 예외로 BLAKE3 hex를 그대로 쓴다**: 결합식 `H(label, *parts) = blake3_hex(label ‖ 0x1F ‖ 0x1F로 결합한 parts)`(바이블 §6.2), `block_id = H("block", doc_version, element_path)[:32]`, `chunk_id = H("chunk", doc_version, chunker_config_hash, level, span)`, `stage_key`(잡 스코프 `tenant_id/collection_id/document_id` 포함), `doc_version`, `*_hash`. **물리 인덱스 키는 스코프·세대 합성** `record_id = H("record", tenant_id, collection_id, document_id, index_generation, chunk_id)`이며 Qdrant 포인트 ID는 `uuid5(NAMESPACE_RAG_CHUNK, record_id)`, OpenSearch `_id = record_id`(콘텐츠 주소 `chunk_id`는 payload 필드로 유지). 콘텐츠 해시는 **BLAKE3**(소문자 hex). 시간은 **RFC 3339 UTC**. 언어 코드는 **BCP 47** (개정 v1.2, 근거: ADR-0004, ADR-0037) | 정렬성·성능·표준성; 결정적(콘텐츠 주소화) 청크 ID는 시간 정렬 ULID로 표현할 수 없음; `chunk_id`에는 테넌트·컬렉션·문서 스코프가 없어 동일 바이트 문서를 두 테넌트(또는 두 컬렉션)가 수집하면 같은 포인트를 덮어쓰고, 청킹 전 단계가 같은 재색인은 이전 세대를 덮어써 세대 공존·롤백이 깨짐 |
| D-07 | 기본 검색 파이프라인: **dense + sparse(learned) + lexical(BM25, 한국어 형태소)** 3-way 하이브리드 → **플랫폼 측 `fuser` RRF(k=60, 채널 가중 1:1:1, 변형 질의 0.5)** 기본, 컬렉션 골든셋 ≥200 qrels 확보 시 min-max convex combination으로 프로파일 전환(점수 분해 보존을 위해 서버 융합은 경량 프로파일의 단일 컬렉션 질의만) → `hydrate`(상위 후보 payload 1회 배치 조회) → **크로스인코더 리랭킹**(top-100→20) → 후처리 **고정 순서** `relevance_gate → dedup → mmr → parent_expand → dedup → sentence_window(옵션) → compress(옵션)` → 토큰 예산 패킹(`pack` 스테이지) 내부 고정 순서 `acl_recheck → budget_cut → reorder(litm_alternating) → citation_align` (개정 v1.2, 근거: ADR-0013) | R3, R6; "중복 제거 → 부모 확장 → MMR" 순서는 확장 후 다양성 판단이 둔화되고 부모 중복이 재발함; `reorder`·`citation_align`이 패킹의 `k_max`·토큰 예산 절단 앞에 오면 절단 뒤 렌더 위치(K 의존)가 무효가 되고 `cite_id`가 이중 부여됨 |
| D-08 | 수집은 **비동기 잡**. `POST /v1/ingest`는 `Idempotency-Key` 필수(draft-07 의미론: 재전송 200/409/422), 동기 응답은 `202 {job_id, status_url, events_url}`. 잡 상태 정본은 PostgreSQL `jobs`(Temporal은 실행 엔진), 상태 전이·도메인 이벤트는 CloudEvents 1.0.2 봉투로 트랜잭셔널 아웃박스에 기록 후 웹훅·SSE로 릴레이(v1 브로커 없음), 오케스트레이터 불가 시 503 + `Retry-After`와 조정 스케줄 (개정 v1.1, 근거: ADR-0017) | R1; 읽기 모델·멱등성·조정(reconcile) 절차 명시 |
| D-09 | **멀티테넌시 1급**: `tenant_id`, `collection_id`, `acl` 필드는 모든 인덱스 레코드에 존재하고 리트리벌 시 필터 강제 | 원칙 9 |
| D-10 | **플러그인 시스템**: Python entry points 기반 레지스트리. 확장 지점 = `fetcher`, `parser`, `normalizer`, `chunker`, `enricher`, `embedder`, `index_backend`, `query_transformer`, `retriever`, `fuser`, `reranker`, `postprocessor`, `packer`, `evaluator` | R4 |
| D-11 | **관측성**: OpenTelemetry Python SDK(트레이스·메트릭·로그), GenAI semantic conventions는 **특정 저장소 커밋에 고정**하고 속성 상수는 OTel Weaver로 생성(`gen_ai.*` + OpenInference `retrieval.*` + 자체 `rag.*`), Prometheus 메트릭(`rag_<stage>_<name>_<unit>`), 콘텐츠 캡처 기본 끔·`tenant_id`는 해시. Grafana·Tempo·Loki(AGPL)·Langfuse·Arize Phoenix(ELv2)는 **OTLP 대상·분리 컨테이너로만**(pip/코드 의존 금지), AGPL 불가 환경 대안(OpenSearch Observability + Perses, VictoriaMetrics/Logs + Jaeger) 문서화 (개정 v1.1, 근거: ADR-0022) | 원칙 8; semconv Development 단계(속성 개명 위험)와 관측 스택 라이선스 경계 |
| D-12 | **평가 하네스 코어 포함**: 골든셋 포맷 **TREC qrels/run + `answer_spans` JSONL**(문서 ID + 정답 문자 구간, 재청킹에 불변), 오프라인 메트릭(ranx/ir_measures, nDCG **선형 이득** 고정, Holm 보정), LLM-judge(RAGAS collections + DeepEval 병기), A/B 프로파일 비교 + 인터리빙·쌍대 비교, 한국어 벤치마크. 하네스는 프로덕션과 동일한 인프로세스 스테이지를 실행하고 모든 품질 기본값은 프로파일 `gate`로 정당화 (개정 v1.1, 근거: ADR-0023) | 원칙 7; 문서 단위 qrels만으로는 청킹 전략 비교(O-09)가 불가 |
| D-13 | **MCP(Model Context Protocol) 서버** 제공(`mcp>=2,<3`, Streamable HTTP, FastAPI `/mcp` 마운트, 외부 OIDC AS + RFC 9728 PRM): `search`, `get_document`, `list_collections` 도구. 스펙 2026-07-28이 세션을 제거했으므로 "더 보기"는 `cursor` 입력/`next_cursor` 출력(Valkey 핸들, 테넌트 바인딩)으로 구현하고 결과는 `structuredContent`(슬림 ContextPack) + 20k 토큰 상한. `search_batch`·`expand`는 v1.1 후보 (개정 v1.1, 근거: ADR-0025) | R6; 세션 상태 기반 페이지네이션 설계 불가 |
| D-14 | 저장소: **PostgreSQL**(메타·잡·원장·아웃박스·레지스트리·Temporal 영속화(별도 DB)), **S3 호환 오브젝트 스토리지**(원본·산출물 BLAKE3 콘텐츠 주소화; 로컬은 **RustFS 또는 SeaweedFS**(둘 다 Apache-2.0, ADR 실측 후 택1; MinIO는 2026-04 아카이브·AGPL 소스 전용 전환으로 제외), 개발은 `file://`), **Valkey**(BSD-3, Redis 프로토콜 호환; 캐시·레이트리밋·멱등 키·MCP 커서·질의 임베딩 캐시; Redis 8은 호환 옵션), 벡터/렉시컬 인덱스는 D-15에 따름 (개정 v1.1, 근거: ADR-0011) | 검증된 표준; Redis 8.0+ RSALv2/SSPLv1/AGPLv3 삼중 라이선스, MinIO 유지보수 종료 |
| D-15 | 벡터 인덱스 **기본 Qdrant**(named vectors `dense`·`sparse_learned`·선택 `late_interaction`, payload 사전 필터, `is_tenant` 파티셔닝), 렉시컬 인덱스 **기본 OpenSearch(analysis-nori; 색인 `decompound_mode=mixed`/질의 `discard`, 컬렉션 사용자 사전 파이프라인 필수, DLS 이중 방어)**; 둘 다 `IndexBackend` 인터페이스 + `capabilities()` 선언 뒤에 두어 Milvus/Weaviate/pgvector+pg_textsearch/Vespa/Apache Solr/LanceDB로 교체 가능(Elasticsearch는 공식 이미지 라이선스상 어댑터 호환만). **경량 프로파일**은 Qdrant 단독: Qdrant는 BM25를 계산하지 않으므로 플랫폼이 한국어 형태소 분석기로 토큰화하고 BM25 TF 포화값(k1=1.2, b=0.75)을 계산한 `sparse_bm25` 벡터를 `modifier: idf`(테넌트별 IDF)로 적재하며, 한국어 키워드 필터는 형태소 `lexical_terms` keyword payload를 쓴다(플랫폼 측 `korean_analyzer` 필수) (개정 v1.1, 근거: ADR-0012, ADR-0021) | 하이브리드 품질 + 한국어 렉시컬; Qdrant 서버는 BM25 미계산·한국어 형태소 분석 없음 |
| D-16 | 기본 임베딩 **BGE-M3**(dense 1024d + sparse 단일 패스; 유지 근거는 "3-in-1 단일 패스 + 생태계 + 드롭인 한국어 파인튠"), 서빙은 **vLLM pooling(BGE-M3 3-in-1) + TEI(dense 전용 모델·리랭커) + 인프로세스(개발·lite)**(Infinity는 sparse 미지원·릴리스 정체로 제외; 같은 공간 내 서빙 교체는 코사인 ≥0.9999 동등성 게이트). 리랭커 기본 **bge-reranker-v2-m3**. late interaction은 별도 `late_interaction` 슬롯(기본 끔, KURE-v2 128d 후보; BGE-M3 colbert 1024d는 인덱스 저장 불가). 교체 후보는 A/B 등급만(multilingual-e5, Qwen3-Embedding/Reranker, KURE-v1, PIXIE, snowflake-arctic-embed-ko 등; jina 계열은 CC-BY-NC/Qwen Research로 제외, BYO 모델은 `model_license_ack`). `ko-quality` 교체 게이트 nDCG@10 +2p (개정 v1.1, 근거: ADR-0009, ADR-0010) | 다국어·한국어 성능, 오픈 라이선스; TEI/Infinity로는 BGE-M3 sparse를 생산할 수 없어 원 결정이 실현 불가 |
| D-17 | 오케스트레이션 **Temporal**(내구성 워크플로우: 재시도·타임아웃·하트비트·사가·스케줄; 영속화·가시성 PostgreSQL). 파이프라인 정의는 오케스트레이터 중립 `PipelineContext`에만 의존하고(`temporalio` 임포트 금지 린트) 경계 페이로드는 `ArtifactRef`만. 개발·CI·평가 하네스는 **비내구 `LocalRunner`**(같은 파이프라인 정의를 다른 셸로 실행), 경량 프로덕션은 Temporal 단일 바이너리 + PostgreSQL. 리트리벌 경로는 오케스트레이터를 거치지 않는다 (개정 v1.1, 근거: ADR-0003) | 장시간 OCR·대량 배치의 신뢰성; `@workflow.defn` 직접 재사용은 로컬 실행 불가·내구성 미명시 |
| D-18 | 파서 기본: **HWPX → python-hwpx(+자체 OWPML 어댑터)**, **HWP 5.0 → Apache-2.0 Java 사이드카(hwplib + hwp2hwpx + hwpxlib) → HWPX → 동일 OWPML 어댑터**, 폴백 unhwp(헬퍼 프로세스, x64) → hwp-hwpx-parser(순수 Python) → LibreOffice + H2Orestart(GPLv3, 격리 컨테이너 `lo-sidecar`, opt-in); pyhwp는 AGPL 선택 플러그인; 배포용 문서는 테넌트 옵트인 시 Tika `HwpV5Parser` 텍스트 전용(`quality=degraded`), 암호화 문서는 `credentials_ref` 없으면 `parse.document_encrypted`. **PDF → Docling(레이아웃·표) + pypdfium2/pdftext(고속 텍스트; PyMuPDF는 AGPL이라 인프로세스 제외, 옵트인 사이드카만) + OCR(기본 RapidOCR PP-OCRv5 korean mobile ONNX, GPU 프로파일 PaddleOCR PP-OCRv5 server, 폴백 Tesseract 5 `kor+eng`·`kor_vert`; Surya 옵트인, EasyOCR·HunyuanOCR 제외)**, **DOCX → Docling `MsWordDocumentBackend` + docx2python(각주·미주 병합 필수)**, **DOC/RTF/ODT → LibreOffice headless(`lo-sidecar`) → DOCX → Docling**, **HTML → Trafilatura(`xml`) → Docling HTML(순서 고정)**, **TXT/MD → charset-normalizer + ftfy + markdown-it-py**. 어댑터 계약은 불변 (개정 v1.1, 근거: ADR-0006, ADR-0007, ADR-0008) | R1, R2; PyMuPDF AGPL 인프로세스 링크, pyhwp AGPL·2020년 이후 무릴리스, H2Orestart GPLv3(MIT 표기 오류), OCR 우선순위 부재, Docling·python-docx 각주 미처리 |
| D-19 | 청킹 기본: **ParsedDocument 네이티브 `StructureAwareChunker`**(Docling HybridChunker 알고리즘 재현: 요소 단위 → 초과 분할(문장 → semchunk) → 동일 heading 병합 → 부모 생성; Docling 어댑터는 `[docling-chunker]` extra 2차 + CI 동등성) + **토큰 예산 병합**(자식 512 / 부모 2048 / 병합 하한 64, 임베딩 모델 토크나이저 기준) + **부모-자식(small-to-big; 부모는 반환 단위만, 임베딩 안 함)** + **표 행 그룹 청킹(256 토큰, 헤더 행 반복)** + **문맥 보강 = 결정적 `context_prefix`(문서 제목·heading 경로·캡션, 기본 켬, 본문과 분리 저장) + LLM 접두어·문서/섹션 요약(O-05 정책, 기본 끔)**. 의미 분할(semantic splitter)·late chunking(mean pooling 장문 모델 강제 검증)·proposition은 프로파일 옵션 (개정 v1.1, 근거: ADR-0020, ADR-0016) | R2, R6; Docling 청커는 DoclingDocument 전용(HWP/HWPX 백엔드 없음), "문맥 보강 기본"이 LLM 요약으로 읽히면 O-05와 충돌 |
| D-20 | Context Pack은 **LLM 공급자 중립 표준 JSON** + **렌더러**(Anthropic Messages **`search_result`(1차)/`document`(2차) + `citations`** 블록, OpenAI 호환 메시지, Gemini 메시지, 공급자 중립 XML `<documents>` + `[dN]` 마커, Markdown, MCP `structuredContent`, 외부 앱용 `plain_records`/`dify_external_knowledge`). `cite_id`는 관련도순 불변(렌더 위치와 분리), 렌더 순서는 `litm_alternating` 기본, 토큰 예산은 대상 LLM 토크나이저로 재계산, 인용은 `output_config.format`(구조화 출력)과 병용 불가하므로 레퍼런스 `answer`는 인용 켠 텍스트 응답 1차 (개정 v1.1, 근거: ADR-0024) | R6; Anthropic RAG 전용 GA 경로는 `search_result` 블록 |

## 5. 개방 결정 (설계 경쟁·연구로 확정할 항목)

다음은 07-tech-landscape 연구와 02-architecture 설계 경쟁 결과로 확정하고 ADR로 기록한다.

- O-01 융합 기본값: RRF vs 가중 정규화(min-max/z-score) vs DBSF — 한국어 골든셋 기준
- O-02 sparse 표현: BGE-M3 sparse vs SPLADE-v3 vs OpenSearch neural sparse
- O-03 GraphRAG/LightRAG·RAPTOR를 코어 옵션 모듈로 둘지, 외부 플러그인으로 둘지
- O-04 late interaction(ColBERT/ColPali)을 리랭커 단계에 두는지, 인덱스 단계에 두는지
- O-05 LLM 기반 보강(요약·가상 질문 생성)의 기본 켬/끔과 비용 정책
- O-06 이벤트 버스: Temporal 시그널만으로 충분한지, NATS/Kafka를 추가하는지
- O-07 HWP 5.0(바이너리) 지원 범위와 LibreOffice 변환 의존 여부
- O-08 스캔 PDF OCR 엔진 기본값(PaddleOCR vs Tesseract vs RapidOCR vs Surya) — 한국어 정확도·라이선스·GPU 요구
- O-09 청크 크기·오버랩 기본값(토큰 기준) 및 한국어 토크나이저(모델 토크나이저 vs cl100k)
- O-10 gRPC 제공 여부(REST 우선)

→ 해결: 설계 바이블 결정 레지스터 참조 ([02-architecture/00-design-bible.md](../02-architecture/00-design-bible.md) §3.2, O-01~O-10 → ADR-0013·0014·0015·0010·0016·0017·0007·0008·0019·0018)

비고(v1.2.2): 바이블 1.3.0이 새 개방 결정 두 건에 번호를 배정했다(상태 `open`, 해결은 ADR-0039 이후). **O-11** `profile_hash`만 바뀐 컬렉션 프로파일 변경(두 물리 해시 불변)의 green 물리 이름과 재색인 모드 B, **O-12** blue/green 채움 중 `documents` 원장 포인터와 정합성 검사 기준. 문서에서는 `**미정(O-11):**`·`**미정(O-12):**`로 표기한다.

## 6. 시스템 경계 (Scope)

**포함**: 수집 API, 파서군, 정규화, 청킹, 보강, 임베딩, 인덱싱, 리트리벌 API, 컨텍스트 패킹, MCP 서버, 관리 API, 평가 하네스, 관측성, 배포 매니페스트, 플러그인 SDK, 클라이언트 SDK(Python/TypeScript).

**제외(Non-goals, 단 훅은 제공)**: 웹 크롤러/커넥터(원천 수집), 최종 답변 생성 UI(챗봇), 모델 파인튜닝 파이프라인, 사용자 인증 서버(OIDC 연동만), 문서 편집. 선택적 `answer` 엔드포인트는 **레퍼런스 구현**으로만 제공(Claude 기반, 인용 포함).

## 7. 품질 목표 (Non-functional Targets, 초안)

| 항목 | 목표 |
|------|------|
| 리트리벌 p95 지연 | 하이브리드+리랭크 Top-10, 100만 청크 기준 **< 800ms** (리랭커 GPU), **< 1.5s** (CPU) |
| 수집 처리량 | 텍스트 PDF 100페이지 **< 30s**, 스캔 PDF 100페이지 **< 5min** (GPU OCR), 워커 수평 확장 |
| 검색 품질 | 내부 한국어 골든셋 nDCG@10 ≥ 0.80, Recall@20 ≥ 0.92 (베이스라인 dense-only 대비 +15%p 이상) |
| 가용성 | 리트리벌 API 99.9%, 수집은 at-least-once + 멱등 |
| 재현성 | 동일 `IngestRequest` + 동일 프로파일 → 동일 `IndexCommit` 해시 |
| 보안 | 테넌트 격리, ACL 필터 강제, 아웃바운드 egress 통제(SSRF 방어)·웹훅 서명, 전송 TLS, 저장 암호화, 감사 로그 |

## 8. 산출물 맵 (Document Map)

모든 문서는 `docs/` 아래, 파일명은 `NN-kebab-case.md`. 각 문서는 아래 **문서 규약**을 따른다.

```
docs/
  README.md                         # 읽기 순서·문서 지도
  00-vision/      00-design-brief(본 문서), 01-vision-and-goals, 02-design-principles, 03-glossary, 04-scope-and-non-goals
  01-requirements/ 01-functional-requirements, 02-non-functional-requirements, 03-personas-and-use-cases, 04-user-stories-and-acceptance-criteria
  02-architecture/ 00-design-bible, 01-system-overview, 02-component-architecture, 03-data-flow-and-document-lifecycle,
                   04-storage-architecture, 05-plugin-architecture, 06-orchestration-and-workflows,
                   07-multi-tenancy-and-security-architecture, 08-deployment-architecture, 09-failure-modes-and-resilience
  03-contracts/    00-contract-overview, 01-ingest-request, 02-source-document, 03-parsed-document, 04-normalized-document,
                   05-chunk-set, 06-enriched-chunk-set, 07-embedded-chunk-set-and-index-record, 08-index-commit,
                   09-query-request-and-query-plan, 10-candidate-set-and-ranked-set, 11-context-pack,
                   12-jobs-events-and-status, 13-error-model, 14-schema-versioning-and-compatibility,
                   15-collection-profile-and-policy-contracts, 16-eval-feedback-and-sidecar-contracts
  04-pipelines/    01-pipeline-framework, 02-fetching-and-source-resolution, 03-parsing-router-and-format-detection,
                   04-parser-hwpx-and-hwp, 05-parser-pdf, 06-parser-doc-and-docx, 07-parser-html, 08-parser-txt-md-and-others,
                   09-normalization-and-cleaning, 10-chunking-strategies, 11-enrichment, 12-embedding, 13-indexing,
                   14-query-understanding, 15-hybrid-search-and-fusion, 16-reranking, 17-post-processing-and-context-packing,
                   18-advanced-retrieval-graph-raptor-agentic, 19-update-delete-and-reindexing
  05-api/          01-api-design-guidelines, 02-ingestion-api, 03-retrieval-api, 04-management-api, 05-mcp-server,
                   06-client-sdks, 07-webhooks-and-events, openapi.yaml(OpenAPI 3.1 정본)
  06-adr/          README(인덱스·작성 절차), 0001-… (MADR 형식; 바이블 §3.3 번호·slug)
  07-tech-landscape/ 00-summary-and-selection-matrix, 01-… 14-… (연구 결과; 13-korean-nlp-tokenization-and-language-resources,
                   14-advanced-rag-graph-raptor-agentic-multimodal 포함)
  08-evaluation/   01-evaluation-strategy, 02-retrieval-metrics-and-harness, 03-golden-dataset-construction,
                   04-llm-judge-and-generation-quality, 05-benchmark-plan-and-baselines, 06-online-feedback-loop
  09-operations/   01-deployment-guide, 02-configuration-reference, 03-observability, 04-scaling-and-performance,
                   05-security-and-compliance, 06-runbooks, 07-backup-and-disaster-recovery, 08-upgrade-and-migration
  10-development/  01-repository-structure, 02-development-environment, 03-coding-standards, 04-testing-strategy,
                   05-ci-cd, 06-plugin-development-guide, 07-contributing, 08-release-process
  11-roadmap/      01-milestones, 02-epics-and-backlog, 03-risks-and-mitigations
  12-appendix/     00-progress-report, 01-phase3-completeness-review, 02-phase4-5-plan, 03-bible-amendment-triage-input,
                   04-phase3-document-ledger, 05-phase6-implementation-kit-plan, 06-traceability-matrix(기계 생성),
                   07-bible-amendment-triage-decisions, 08-propagation-directives,
                   design-proposals/ (설계 경쟁 제안서 A·B·C, 역사 기록),
                   sources/ (업스트림 참고 자료 사본 — 문서 규약 적용 제외)
schemas/           JSON Schema 2020-12 파일 35개 (설계 바이블 §5.1 인벤토리 35종의 스키마 파일과 `common-types`; 각 파일은 03-contracts 문서 하나가 소유),
                   README.md(스키마 색인, 5단계 작성 예정)
```

문서 맵 개정: v1.2.1(2026-09-22) — `03-contracts/15`·`16`(바이블 §5.1의 운영 계약 `CollectionSpec`·`Profile`·`PluginMeta`·`Capabilities`·`StagePolicy`·`TieringPolicy`·`EgressPolicy` / `EvalDataset`·`EvalRun`·`EvalReport`·`FeedbackEvent`·`UserDictEntry`·`ConvertRequest`·`ConvertResponse`)와 `12-appendix/` 등재. v1.2.2(2026-09-23) — 실제 파일과 일치(바이블 1.3.0 AM-03): `07-tech-landscape/` 00~14(13 한국어 NLP, 14 고급 RAG), `12-appendix/` 02~08(4·5단계 계획, 트리아지 입력·결정, 문서 원장, 6단계 구현 키트 계획, 추적 매트릭스, 전파 지시서), `06-adr/README`, `05-api/openapi.yaml`, `schemas/` 35개 파일과 `schemas/README.md`(예정). §4 확정 결정은 바뀌지 않았다(바이블 1.3.0은 가산 개정만, D-xx 개정 없음). §5에 O-11·O-12 비고 추가.

## 9. 문서 작성 규약 (Documentation Conventions)

1. **Frontmatter 필수**: `title`, `status`(draft|review|active|deprecated), `owner`, `version`, `last_updated`, `depends_on`(참조 문서 경로 배열), `schema_version`(계약 문서만).
2. **언어**: 한국어 본문. 기술 용어는 처음 등장 시 `한국어(English)` 병기, 이후 영문 또는 널리 쓰이는 한국어. 식별자·필드·API·코드는 영문.
3. **구조**: `# 제목` → `## 목적` → `## 범위` → 본문 → `## 결정 사항 요약` → `## 미해결 이슈` → `## 참조`. 계약 문서는 추가로 `## 스키마`, `## 예시`, `## 불변식(Invariants)`, `## 버전 이력`.
4. **다이어그램**: Mermaid 사용(`flowchart`, `sequenceDiagram`, `classDiagram`, `stateDiagram-v2`, `erDiagram`, C4는 `C4Context`/`C4Container`). ASCII 아트 금지.
5. **스키마 표기**: 필드 표는 `필드 | 타입 | 필수 | 설명 | 예시`. 타입 표기는 JSON Schema 용어(`string`, `integer`, `number`, `boolean`, `array<T>`, `object`, `enum[...]`, `string(ulid)`, `string(date-time)`). 코드 예시는 Pydantic v2 + JSON 예시 둘 다.
6. **상호참조**: 상대 경로 링크 `[제목](../03-contracts/03-parsed-document.md)`. 존재하지 않는 문서를 링크하지 않는다(문서 맵에 있는 경로만).
7. **결정 표기**: 결정은 `**결정:**` 볼드로 시작하고 관련 ADR을 링크. 미정은 `**미정(O-xx):**`.
8. **수치**: 성능·크기 목표는 표로. 근거 없는 수치 금지(출처 또는 "초안 목표" 명시).
9. **명명**: 스키마 타입은 `PascalCase`(예: `ParsedDocument`), 필드는 `snake_case`, 열거값은 `snake_case` 문자열, 이벤트 이름은 `domain.entity.action`(예: `ingest.document.parsed`), 메트릭은 `rag_<stage>_<name>_<unit>`.
10. **금지**: 이모지, 과장("세계 최고" 등은 비전 문서에서만), 근거 없는 벤치마크 숫자, 존재하지 않는 라이브러리 API. 확실하지 않으면 "확인 필요"로 표시.
11. **길이**: 각 설계 문서 250~900행. 계약 문서는 스키마 전체 포함. ADR은 60~200행.

## 10. 핵심 용어 (초안, 03-glossary에서 확장)

| 용어 | 정의 |
|------|------|
| Source Document | URI로 식별되는 원본 파일 + 수집 메타데이터 |
| ParsedDocument | 포맷 독립 표준 문서 모델: 계층 블록 트리 + 출처(provenance) |
| Block | 문서 구성 단위(heading, paragraph, list_item, table, figure, caption, footnote, code, formula, page_break…) |
| Chunk | 검색 단위. 하나 이상의 Block 조각 + 부모 경로 + 토큰 수 |
| Enrichment | 청크에 부착되는 파생 정보(문맥 요약, 키워드, 가상 질문, 엔티티, 언어) |
| Index Record | 인덱스 백엔드에 저장되는 최종 레코드(벡터들 + 페이로드) |
| Index Commit | 한 문서 버전의 인덱싱 결과 단위(원자적 교체·롤백 단위) |
| Profile | 파이프라인 구성 프리셋(파서·청커·임베더·검색 전략의 조합, 버전드) |
| Query Plan | 질의 이해 결과(재작성 질의들, 필터, 검색 전략, 예산) |
| Candidate | 개별 리트리버가 반환한 청크 + 점수 |
| Ranked Result | 융합·리랭킹 후 청크 + 점수 분해 |
| Context Pack | LLM에게 전달할 최종 패키지(정렬된 청크, 인용 ID, 토큰 통계, 렌더 힌트) |
| Collection | 테넌트 내 인덱스 논리 단위(프로파일 고정) |

## 11. 작성자(에이전트)에게

- 이 브리프와 설계 바이블을 먼저 읽고, 자기 문서의 `depends_on` 문서를 읽은 뒤 작성한다.
- 다른 문서의 필드명·타입·열거값을 **그대로** 사용한다. 새 필드가 필요하면 자기 문서의 `## 미해결 이슈`에 제안으로 남기고, 임의로 계약을 바꾸지 않는다.
- 오픈소스 API·버전·라이선스는 확실할 때만 단정한다. 불확실하면 "확인 필요(as of 2026-09)"로 표기한다.
- 우아함은 장식이 아니라 **경계의 명확성**이다. 각 스테이지가 무엇을 받고 무엇을 내는지, 실패하면 어떻게 되는지를 먼저 쓴다.
