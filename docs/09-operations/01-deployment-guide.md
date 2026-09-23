---
title: 배포 가이드
status: active
owner: architecture
version: 0.1.0
last_updated: 2026-09-23
depends_on:
  - ../00-vision/00-design-brief.md
  - ../02-architecture/00-design-bible.md
  - ../02-architecture/08-deployment-architecture.md
  - ../02-architecture/04-storage-architecture.md
  - ../02-architecture/02-component-architecture.md
  - ../02-architecture/06-orchestration-and-workflows.md
  - ../03-contracts/00-contract-overview.md
  - ../03-contracts/15-collection-profile-and-policy-contracts.md
  - ../07-tech-landscape/00-summary-and-selection-matrix.md
  - ../07-tech-landscape/08-orchestration-messaging-and-api-frameworks.md
  - ../07-tech-landscape/05-embedding-models-and-serving.md
  - ../07-tech-landscape/06-vector-and-lexical-index-backends.md
  - ../07-tech-landscape/02-document-parsing-pdf-layout-ocr.md
  - ../06-adr/0011-kv-and-object-storage-valkey-rustfs-seaweedfs.md
---

# 배포 가이드

## 목적

이 문서는 [배포 아키텍처](../02-architecture/08-deployment-architecture.md)가 확정한 배포 단위(compose 서비스, Helm 차트·values, 네임스페이스, 노드풀)를 **운영자가 순서대로 실행할 수 있는 절차**로 옮긴다. 아무것도 없는 서버(또는 클러스터)에서 시작해 첫 문서를 수집하고 첫 `ContextPack`을 받기까지의 명령·설정·검증을 다루며, 그 과정에서 무엇이 정본(설계 바이블(Design Bible))이고 무엇이 이 문서의 제안인지 구분한다.

이 문서는 새 계약 타입·필드·열거값·엔드포인트·이벤트를 정의하지 않는다. 컨테이너·큐·환경 변수·이미지·물리명은 바이블 §2.2~§2.3·§6.6~§6.7·§11.2·§13.4를, Helm values 키·네임스페이스·노드 라벨은 배포 아키텍처 §4.2·§5.2·§6.1을 그대로 쓴다. 바이블 §12 `cli/` 목록에 없는 CLI 하위 명령은 모두 `(제안)`으로 표기하고 "## 미해결 이슈"에 모았다.

## 범위

- **포함**: 사전 요구(하드웨어·OS·GPU 드라이버·컨테이너 런타임·외부 의존), `lite` docker compose 배포(파일 구조·서비스·환경 변수·볼륨·헬스체크·quickstart), `standard`/`premium` Kubernetes(Helm 설치 절차, values 예시, 네임스페이스·시크릿·스토리지클래스, Temporal 설치 옵션, Qdrant/OpenSearch 자체·관리형 연결, 모델 서빙 배치, 인그레스·TLS), 초기화(DB 마이그레이션, 테넌트·컬렉션 생성, 프로파일 검증), 모델 준비(다운로드·캐시·에어갭 미러), 검증 체크리스트와 smoke test 스크립트, 업그레이드 절차 링크, 흔한 문제.
- **제외**: 환경 변수 전체 목록과 기본값 → [설정 레퍼런스](02-configuration-reference.md); 관측 백엔드 구성 → [관측성](03-observability.md); 사이징 실측·튠 → [확장과 성능](04-scaling-and-performance.md); 인증·인가·mTLS·비밀 관리 상세 → [보안과 컴플라이언스](05-security-and-compliance.md); 장애 대응 → [런북](06-runbooks.md); 백업·복구 → [백업과 재해 복구](07-backup-and-disaster-recovery.md); 업그레이드 세부 → [업그레이드와 마이그레이션](08-upgrade-and-migration.md); 이미지 빌드·서명 파이프라인 → [CI/CD](../10-development/05-ci-cd.md).
- **수치**: 하드웨어·용량 값은 배포 아키텍처 §7의 "초안 목표"를 그대로 옮긴 것이며 실측 후 갱신된다. 외부 이미지 태그·버전은 선정 매트릭스 확인일(2026-09-18~22) 기준이고, 실제 배포에서는 Helm values의 digest 고정값이 정본이다(배포 아키텍처 P5).
- **전방 참조**: 위 `→` 문서들과 05-api/04는 브리프 §8 문서 맵 경로이며 작성 예정이다. 작성 전까지는 바이블 해당 절이 정본이다.

---

## 1. 배포 경로 선택

**결정:** 배포 경로는 프로파일(`ProfileTier`)이 결정한다. `lite`는 docker compose 단일 노드(`rag up --profile lite [--durable]`)이고, `standard`·`premium`·`korean-gov`는 Helm 차트 `rag-platform` + 외부 제공 데이터 계층이다. 두 경로는 같은 코어 이미지 `rag-platform`과 같은 프로파일 YAML을 쓰며, 다른 것은 실행 셸(`LocalRunner`/Temporal 단일 바이너리 vs Temporal 분리)과 컨테이너 수뿐이다. (근거: 바이블 §7.1·§11.1·§11.6, 배포 아키텍처 §2, [ADR-0003](../06-adr/0003-orchestrator-neutral-pipeline-and-non-durable-local-runner.md), [ADR-0012](../06-adr/0012-lite-profile-qdrant-only-client-bm25.md))

```mermaid
flowchart TD
    A["시작: 용도는?"] --> B{"개발·CI·PoC<br/>단일 노드, GPU 0"}
    B -->|예| C["lite 개발 모드<br/>rag up --profile lite<br/>컨테이너 4 (LocalRunner)"]
    B -->|아니오| D{"운영이지만 단일 노드로 충분<br/>청크 ≤ 100만, GPU 0"}
    D -->|예| E["lite 운영 모드<br/>rag up --profile lite --durable<br/>컨테이너 5~6 (Temporal 단일 바이너리)"]
    D -->|아니오| F{"GPU 노드풀 여럿·HA·LLM 보강 큐"}
    F -->|아니오| G["standard: Helm rag-platform<br/>values-standard.yaml"]
    F -->|예| H["premium: Helm rag-platform<br/>values-premium.yaml"]
    G --> I{"공공·규제(ISMS-P)·에어갭"}
    H --> I
    I -->|예| J["korean-gov 오버레이<br/>values-korean-gov.yaml + values-airgapped.yaml"]
    I -->|아니오| K["환경 오버레이<br/>values-env-{dev,staging,prod}.yaml"]
    J --> K
```

컨테이너 수는 배포 아키텍처 §2.1 확정값(개발 4 / 운영 `--durable` 5, `objectstore` 동거 시 6)이다. 바이블 §7.1 열 머리의 "컨테이너 5"는 운영 모드·`file://` 기준 값이며, "4(개발) / 5~6(운영)"으로 정밀화하는 patch는 배포 아키텍처 미해결 이슈 14로 이미 요청되어 있다.

| 항목 | `lite` | `standard` | `premium` | `korean-gov` |
|------|--------|------------|-----------|--------------|
| 도구 | `rag` CLI + docker compose v2 | `helm` 3 + `kubectl` + `rag` CLI | 동일 | 동일 + `skopeo`(미러) |
| 이 문서의 절 | §2, §3, §5, §6.2, §7 | §2, §4, §5, §6, §7 | §4.6 추가 | §4.9, §6.3 추가 |
| 데이터 계층 | compose가 함께 기동 | 운영자 제공(관리형 또는 `rag-platform-data` 번들은 개발·스테이징만) | 동일 | 동일 + OpenBao·감사 인덱스 |
| 첫 검색까지(초안 목표) | 5분(바이블 §11.6) | 반나절(데이터 계층·시크릿·미러 준비 포함) | 1일 | 2일 이상(미러 반입) |

---

## 2. 사전 요구

### 2.1 하드웨어·OS

| 대상 | 최소(초안 목표) | 권장(초안 목표) | 근거 |
|------|-----------------|-----------------|------|
| `lite` 개발 | 4 vCPU / 16GB / SSD 100GB | 8 vCPU / 32GB | 배포 아키텍처 §7.4(청크 10만 이하, 동시 잡 4) |
| `lite` 운영(`--durable`) | 8 vCPU / 32GB / NVMe 500GB | 16 vCPU / 64GB | §7.4(청크 100만 이하: Qdrant dense 6.1GB + payload 6GB, 검색 p95 1,500ms CPU) |
| `standard` 노드풀 `cpu-general` | 노드 3 × 4 vCPU / 16GB | 오토스케일 | `api` 2~8, `worker-io`·`relay`·`parser-workers`(JVM 힙 1.5GB) |
| `standard` 노드풀 `cpu-parse` | 노드 2 × 8 vCPU / 32GB | 오토스케일 상한 32 파드 | `worker-cpu` 4 vCPU / 12GB(Docling 프로세스당 약 2GB × 4) |
| `standard` 노드풀 `gpu-serving` | GPU 1장(MIG 지원) 또는 2장(전용) + 8 vCPU / 32GB | 2장 전용 | bge-m3·bge-reranker-v2-m3 각 fp16 약 1.1GB, 권장 VRAM 6~8GB(07-tech-landscape/05) |
| `premium` GPU 노드풀 | `gpu-embed`·`gpu-rerank`·`gpu-ocr`(T4/L4급) 각 ≥1, 선택 `gpu-llm`(24GB급) | 각 2장 | 배포 아키텍처 §6.3(`quality-max` 16GB+, Qwen3-VL-8B 24GB급) |
| 데이터 계층(`standard` M 규모) | PostgreSQL 4 vCPU / 16GB + 복제 1; Qdrant 3노드 × 48GB RAM; OpenSearch 3노드 힙 8GB; Valkey 3 × 2GB | 관리형 | §7.2·§7.3 |

- **OS·아키텍처**: Linux x86_64가 기준이다. arm64는 `lite` 개발에 한정한다 — HWP 5.0 1차 폴백 unhwp가 x64 전용이어서(바이블 §7.1, 리스크 #4) arm64에서는 hwp-hwpx-parser만 남는다.
- **커널·파일시스템**: Qdrant·OpenSearch 노드는 `vm.max_map_count`(OpenSearch 요구값 262144, 확인 필요 as of 2026-09)와 로컬 NVMe를 권장한다. 오브젝트 스토리지 버킷은 버저닝을 켠다([저장소 아키텍처](../02-architecture/04-storage-architecture.md) §3.3).
- **시각**: 모든 노드 NTP 동기화. `Idempotency-Key` 만료·`embargo_until` 판정·JWT `exp`가 RFC 3339 UTC 시각에 의존한다(배포 아키텍처 §9).

### 2.2 GPU 드라이버·CUDA

GPU는 서빙(`embedding-server`·`reranker-server`·선택 `sparse-encoder-server`·`llm-server`)과 사이드카 `ocr-gpu`에만 있다. 코어 이미지 `rag-platform`에는 CUDA가 없으므로 워커 노드에는 GPU가 필요 없다(배포 아키텍처 P7).

| 항목 | 요구 | 근거 |
|------|------|------|
| 장치 노출 | NVIDIA GPU Operator(k8s-device-plugin v0.20.0 계열); DRA(`ResourceClaim`)는 Kubernetes 1.32+(권고 1.34+)에서만 선택 경로 | 07-tech-landscape/08 |
| 드라이버·CUDA(TEI) | CUDA 12.2+ 호환 드라이버, GPU Compute Capability ≥ 7.5; TEI 이미지 태그는 CC별(`86`·`89`·`hopper`, T4는 `turing` — 태그 존재 확인 필요 as of 2026-09) | 07-tech-landscape/08 TEI 행 |
| 드라이버·CUDA(vLLM 0.29 pooling) | 이미지가 요구하는 CUDA 마이너 버전과 노드 드라이버 호환 매트릭스 확인 필요(as of 2026-09) | 배포 아키텍처 §3.1 |
| 드라이버·CUDA(`ocr-gpu`) | PaddlePaddle CUDA 베이스 이미지의 CUDA 버전과 노드 드라이버를 맞춘 digest를 values에 고정 | 배포 아키텍처 §3.3, 07-tech-landscape/02 "CUDA 결합" |
| MIG | `standard` GPU 1장 구성은 MIG 지원 GPU(A30/A100/H100 계열, 목록 확인 필요)만 운영 허용; L4·T4·A10은 2장 전용 | 배포 아키텍처 §6.2 |
| time-slicing | 개발·스테이징 한정(`serving.sharing: time_slicing` 명시 시 렌더) | 동일 |
| 노드 라벨·테인트 | `rag.io/node-pool=gpu-serving`(premium은 `gpu-embed`·`gpu-rerank`·`gpu-ocr`·`gpu-llm`) + 테인트 `nvidia.com/gpu=present:NoSchedule` | 배포 아키텍처 §6.1 |

설치 확인: GPU 노드에서 `nvidia-smi`로 드라이버·CUDA 버전이 보이고, `kubectl describe node <gpu-node>`의 `Allocatable`에 `nvidia.com/gpu`(또는 `nvidia.com/mig-*`)가 나타나야 한다.

### 2.3 컨테이너 런타임·CLI 도구

| 도구 | `lite` | `standard`+ | 비고 |
|------|:------:|:-----------:|------|
| Docker Engine + Compose v2(`docker compose`) | 필수 | — | `rag up`이 compose를 호출 |
| containerd + NVIDIA Container Toolkit | — | GPU 노드 필수 | GPU Operator가 설치 가능 |
| Kubernetes | — | 필수 | 버전 하한은 KEDA v2.20.2·GPU Operator v0.20.0·인그레스 컨트롤러의 공동 지원 범위로 정하며 확인 필요(as of 2026-09); DRA 경로는 1.32+ |
| `helm` 3, `kubectl` | — | 필수 | OCI 레지스트리 차트(`helm pull --verify`) |
| KEDA v2.20.2 | — | 필수 | 스케일러 `temporal`·`prometheus`·`postgresql` |
| cert-manager | — | 권장 | 인그레스 TLS·내부 CA |
| `uv` | 필수 | 권장 | `uv tool install rag-platform` → CLI `rag`(바이블 §11.6) |
| `skopeo`, `cosign`, `syft`/`trivy` | — | 에어갭·운영 | 이미지 복제·서명 검증·SBOM(배포 아키텍처 §3.5) |
| `curl`, `jq` | 권장 | 필수 | §7 smoke test |

### 2.4 외부 의존(데이터 계층·IdP·관측)

| 구성 요소 | 버전(매트릭스 확인일 기준) | `lite` | `standard`+ | 필수 기능 |
|-----------|---------------------------|:------:|:-----------:|-----------|
| PostgreSQL | Temporal 요구 12+; 원장은 RLS·시간 파티셔닝(`pg_partman` 선택) — 원장 최소 버전은 [설정 레퍼런스](02-configuration-reference.md) 확정 | compose | 관리형 또는 HA | DB `rag_ledger`, `temporal`, `temporal_visibility`(별도 인스턴스 권장), 역할 4종(§5.1) |
| Qdrant | 1.19 | compose | 3노드 사본 2 | named vectors, payload 인덱스 `is_tenant`, 테넌트 IDF(`sparse_bm25`, lite), gRPC 6334, alias, 스냅샷 |
| OpenSearch | 3.8 + `analysis-nori` | — | 3노드 사본 ≥1 | Nori, security 플러그인(JWT 인증·DLS), `repository-s3`, 인덱스 템플릿 |
| Valkey | 9 | compose | 3노드 또는 관리형 | Redis 7.2 명령 집합 호환([ADR-0011](../06-adr/0011-kv-and-object-storage-valkey-rustfs-seaweedfs.md)) |
| Temporal | Server 1.32 / `temporalio` 1.33 | `--durable` 시 단일 바이너리 | frontend/history/matching 분리 | PostgreSQL 영속화·가시성, 네임스페이스 `rag`(값), `numHistoryShards` 초기값 고정 |
| 오브젝트 스토리지 | RustFS 또는 SeaweedFS(택1 미정, ADR-0011) / 클라우드 S3 호환 | `file://` 기본 | S3 호환 필수 | 버저닝, SSE, 테넌트 접두 `tenants/{tenant_id}/` |
| OIDC IdP | Keycloak / Dex / 조직 IdP | 불필요(API 키) | 필수 | JWKS, 그룹 클레임, `audience` |
| OTel Collector 대상 | Prometheus·Tempo·Loki·Grafana·Langfuse(분리 컨테이너) | 선택(Jaeger + Prometheus) | 권장 | OTLP 4317 수신 |

### 2.5 포트

| 컨테이너 | 포트 | 프로토콜 | 노출 |
|----------|------|----------|------|
| `api`(`app`) | 8000 / 9090 | HTTP REST·SSE·`/mcp` / `/metrics` | 인그레스 / 스크레이프만 |
| PostgreSQL | 5432 | TCP | 내부 |
| Temporal frontend / UI(선택, 별도 컨테이너) | 7233 / 8080 | gRPC / HTTP | 내부(워커·api·relay) / 운영자 |
| Qdrant | 6333 / 6334 | REST / gRPC(`prefer_grpc=true`) | 내부 |
| OpenSearch | 9200 | HTTPS | 내부 |
| Valkey | 6379 | TCP | 내부 |
| 오브젝트 스토리지 | 9000(S3 API; SeaweedFS S3 게이트웨이 기본 8333은 9000으로 매핑) | HTTP(S) | 내부 |
| `embedding-server` / `reranker-server` | 8000 / 8080 | HTTP | 내부(`rag-serving`) |
| `parser-workers` / `ocr-gpu` / `lo-sidecar` | 8080 / 8000 / 8080 | HTTP `POST /v1/convert`, `GET /healthz` | 내부 |
| OTel Collector | 4317 | OTLP gRPC | 내부 |

---

## 3. `lite` 배포(docker compose)

### 3.1 파일 구조

`deploy/compose/`에는 네 파일이 있다(배포 아키텍처 §4.1): `compose.lite.yaml`(개발: `app`·`postgres`·`qdrant`·`valkey`, `LocalRunner`), `compose.lite-durable.yaml`(운영 오버레이: + `temporal`(단일 바이너리)·`temporal-setup`(1회, 제안 — 배포 아키텍처 §4.1 목록에는 없음), 선택 `objectstore`·`reranker`), `compose.observability.yaml`(선택: `otel-collector`·`jaeger`·`prometheus`), `.env.example`(`RAG_*` 변수 예시, 비밀은 파일 참조).

`rag up --profile lite`는 `compose.lite.yaml`을, `--durable`은 두 파일을 함께 적용한다(`docker compose -f compose.lite.yaml -f compose.lite-durable.yaml up -d`와 동치). 운영에서 `--durable` 없이 쓰는 것은 금지다 — `LocalRunner`는 비내구라 프로세스 종료 시 진행 중 잡이 `failed`가 된다(바이블 §11.1).

### 3.2 서비스 목록

| 서비스 | 이미지(digest 고정) | 개발 | 운영 | 볼륨 | 헬스체크 | 비고 |
|--------|---------------------|:----:|:----:|------|----------|------|
| `app` | `rag-platform` | 1 | 1 | `./.rag/artifacts:/data/artifacts`(`file://`), `./.rag/models:/models`, `./samples:/samples:ro` | `GET /readyz` | `rag serve api`; 개발은 `LocalRunner` 동거, 운영은 Temporal 워커(큐 `ingest`·`maintenance`) + Procrastinate 릴레이 동거(동거 플래그 이름은 미해결 이슈 1) |
| `postgres` | PostgreSQL | 1 | 1 | `pgdata` | `pg_isready` | DB `rag_ledger` + 운영 시 `temporal`·`temporal_visibility`, 스키마 `procrastinate` |
| `qdrant` | Qdrant 1.19 | 1 | 1 | `qdrant_storage` | TCP 6333 | named vectors `dense`·`sparse_bm25` |
| `valkey` | Valkey 9 | 1 | 1 | 없음(영속화 끔) | `valkey-cli ping` | 캐시·레이트리밋·멱등 조회 캐시 |
| `temporal-setup`(제안) | Temporal 1.32 | — | 1회 | — | 종료 코드 | `temporal-sql-tool` `setup-schema`/`update-schema`(두 DB) |
| `temporal` | Temporal 1.32 단일 바이너리 | — | 1 | — | `temporal operator cluster health`(CLI 포함 여부 확인 필요) | PostgreSQL 영속화, `numHistoryShards` 4(초안; 생성 후 변경 불가) |
| `objectstore` | RustFS 또는 SeaweedFS | — | 선택 | `objdata` | TCP 9000 | 기본은 `file://` 바인드 볼륨 |
| `reranker` | TEI `cpu-1.9` | 선택 | 선택 | `./.rag/models:/data` | TCP 8080 | gte-multilingual-reranker-base(30→10); 생략 시 `rerank.applied=false` |
| `otel-collector`, `jaeger`, `prometheus` | 업스트림 | 선택 | 선택 | — | — | `compose.observability.yaml` |

### 3.3 환경 변수(`.env.example`)

바이블 §6.6이 이름을 확정한 변수만 정본이고, `(제안)` 변수는 [컴포넌트 아키텍처](../02-architecture/02-component-architecture.md) §5.2 `Settings` 제안 필드다. 환경 변수로 프로파일 값을 덮어쓰는 경로는 없다(같은 문서 §5.1).

```bash
# --- 정본(바이블 §6.6) ---
RAG_PG__DSN=postgresql://rag_app:CHANGE_ME@postgres:5432/rag_ledger
RAG_OBJECT_STORE__URI=file:///data/artifacts            # 운영에서 objectstore 사용 시 s3://rag-lite
RAG_VALKEY__URL=redis://valkey:6379/0
# RAG_TEMPORAL__ADDRESS=temporal:7233                    # --durable 에서만 설정. 비우면 LocalRunner(개발)
# RAG_PROFILE__PATH=/config/profile.yaml                 # 비우면 builtin lite
RAG_OTEL__EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
RAG_OTEL__CONTENT_CAPTURE=none
RAG_SECRETS__PROVIDER=env

# --- 제안(컴포넌트 아키텍처 §5.2; 설정 레퍼런스 확정 대상) ---
RAG_PROFILE__ID=lite
RAG_OBJECT_STORE__ENDPOINT_URL=http://objectstore:9000  # s3:// 사용 시
RAG_SIDECAR__RERANKER_SERVER_URL=http://reranker:8080   # reranker 서비스를 띄운 경우만
RAG_SERVE__PORT=8000

# --- 모델 캐시(배포 아키텍처 §3.4) ---
HF_HOME=/models/hf
HF_HUB_OFFLINE=0                                        # 개발: 최초 다운로드 허용. 운영 미러 사용 시 1
```

비밀(`RAG_PG__DSN`의 비밀번호 등)은 `.env`에 직접 두지 말고 compose `secrets:` 또는 `RAG_SECRETS__PROVIDER=openbao`의 `credentials_ref`로 간접 참조한다(바이블 §6.6). 오타 방지: `RAG_` 접두 변수 중 모델이 모르는 이름은 기동 실패다(`check_unknown_env`, 컴포넌트 아키텍처 §5.2).

### 3.4 compose 스케치

`compose.lite.yaml`(개발):

```yaml
name: rag-lite
services:
  app:
    image: ghcr.io/example/rag-platform@sha256:<digest>
    command: ["serve", "api"]                      # ENTRYPOINT ["rag"]; RAG_TEMPORAL__ADDRESS 없음 → LocalRunner 동거
    env_file: .env
    ports: ["8000:8000", "9090:9090"]
    volumes:
      - ./.rag/artifacts:/data/artifacts           # RAG_OBJECT_STORE__URI=file:///data/artifacts
      - ./.rag/models:/models                       # bge-m3 ONNX int8, mecab-ko-dic, RapidOCR ONNX (최초 rag up 시 다운로드)
      - ./samples:/samples:ro
    depends_on:
      postgres: {condition: service_healthy}
      qdrant:   {condition: service_healthy}
      valkey:   {condition: service_healthy}
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/readyz').status == 200 else 1)"]
      interval: 15s
      timeout: 5s
      retries: 20
      start_period: 120s                            # 모델 최초 로드 대기
    restart: unless-stopped
  postgres:
    image: postgres@sha256:<digest>                 # 메이저 버전은 설정 레퍼런스 확정(Temporal 요구 12+)
    environment:
      POSTGRES_USER: postgres                       # 부트스트랩 슈퍼유저. rag_owner 는 NOLOGIN 이라 여기 쓸 수 없다(저장소 아키텍처 §2.4)
      POSTGRES_PASSWORD_FILE: /run/secrets/pg_superuser_password
      POSTGRES_DB: rag_ledger
    secrets: [pg_superuser_password]
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./init/postgres:/docker-entrypoint-initdb.d:ro   # 역할 rag_owner(NOLOGIN)·rag_app·rag_platform_admin·rag_maintenance 생성(§5.1); --durable 시 temporal 사용자·DB 2개
    healthcheck: {test: ["CMD-SHELL", "pg_isready -U postgres -d rag_ledger"], interval: 10s, timeout: 5s, retries: 10}
    restart: unless-stopped
  qdrant:
    image: qdrant/qdrant@sha256:<digest>            # 1.19
    ports: ["6333:6333", "6334:6334"]
    volumes: ["qdrant_storage:/qdrant/storage"]
    healthcheck: {test: ["CMD-SHELL", "bash -c ':> /dev/tcp/127.0.0.1/6333' || exit 1"], interval: 10s, timeout: 5s, retries: 10}
    restart: unless-stopped
  valkey:
    image: valkey/valkey@sha256:<digest>            # 9
    command: ["valkey-server", "--save", "", "--appendonly", "no", "--maxmemory-policy", "volatile-lru"]
    healthcheck: {test: ["CMD", "valkey-cli", "ping"], interval: 10s, timeout: 3s, retries: 10}
    restart: unless-stopped
secrets:
  pg_superuser_password: {file: ./.secrets/pg_superuser_password}
volumes: {pgdata: {}, qdrant_storage: {}}
```

`compose.lite-durable.yaml`(운영 오버레이):

```yaml
services:
  app:
    environment:
      RAG_TEMPORAL__ADDRESS: temporal:7233          # Temporal 워커(큐 ingest·maintenance) + Procrastinate 릴레이 동거
    depends_on:
      temporal: {condition: service_healthy}
  temporal-setup:                                   # 1회 실행(제안): temporal · temporal_visibility 두 DB(postgres init 스크립트가 생성)에 setup-schema → update-schema
    image: temporalio/server@sha256:<digest>        # 1.32
    entrypoint: ["/bin/sh", "-c"]
    command:                                        # `$$` 는 compose 변수 보간 이스케이프 — 셸에는 `$` 로 전달된다
      - |
        export SQL_PASSWORD="$$(cat /run/secrets/pg_temporal_password)"
        for db in temporal temporal_visibility; do
          temporal-sql-tool --plugin postgres12 --ep postgres -p 5432 -u temporal --db "$$db" setup-schema -v 0.0 || exit 1
          temporal-sql-tool --plugin postgres12 --ep postgres -p 5432 -u temporal --db "$$db" update-schema -d "./schema/postgresql/v12/$${db#temporal_}/versioned" || exit 1
        done
    secrets: [pg_temporal_password]                 # 플래그·SQL_PASSWORD·스키마 경로는 Temporal 1.32 문서 확인 필요(as of 2026-09)
    depends_on: {postgres: {condition: service_healthy}}
    restart: "no"
  temporal:
    image: temporalio/server@sha256:<digest>
    environment:
      DB: postgres12
      DB_PORT: "5432"
      POSTGRES_SEEDS: postgres
      POSTGRES_USER: temporal
      DBNAME: temporal
      VISIBILITY_DBNAME: temporal_visibility
      NUM_HISTORY_SHARDS: "4"                       # 단일 노드 초안; 생성 후 변경 불가
      SKIP_SCHEMA_SETUP: "true"                     # temporal-setup 이 수행
    ports: ["7233:7233"]
    depends_on: {temporal-setup: {condition: service_completed_successfully}}
    healthcheck: {test: ["CMD", "temporal", "operator", "cluster", "health", "--address", "127.0.0.1:7233"], interval: 15s, timeout: 5s, retries: 20}
    restart: unless-stopped
  objectstore:                                      # 선택: file:// 대신 S3 호환(RustFS 또는 SeaweedFS, ADR-0011 택1 후 이미지 확정)
    image: <rustfs-or-seaweedfs>@sha256:<digest>
    ports: ["9000:9000"]
    volumes: ["objdata:/data"]
    healthcheck: {test: ["CMD-SHELL", "bash -c ':> /dev/tcp/127.0.0.1/9000' || exit 1"], interval: 10s, timeout: 5s, retries: 10}
  reranker:                                         # 선택: TEI CPU
    image: ghcr.io/huggingface/text-embeddings-inference:cpu-1.9@sha256:<digest>
    command: ["--model-id", "/data/models/Alibaba-NLP/gte-multilingual-reranker-base/<sha>", "--port", "8080"]
    volumes: ["./.rag/models:/data/models:ro"]
    healthcheck: {test: ["CMD-SHELL", "bash -c ':> /dev/tcp/127.0.0.1/8080' || exit 1"], interval: 15s, timeout: 5s, retries: 20}
secrets:
  pg_temporal_password: {file: ./.secrets/pg_temporal_password}
volumes: {objdata: {}}
```

Temporal 컨테이너 환경 변수 이름(`DB`, `POSTGRES_SEEDS`, `SKIP_SCHEMA_SETUP` 등)은 업스트림 이미지 규약이며 1.32 이미지에서의 유효성은 확인 필요(as of 2026-09)다. 정본은 `rag up`이 렌더하는 파일이고 위 스케치는 그 구조를 보여준다.

### 3.5 Quickstart — 첫 수집·검색까지

바이블 §11.6 "개발 모드(5분 기동)"의 5단계를 명령 수준으로 풀었다. 3~4단계의 테넌트·API 키·컬렉션 부트스트랩은 바이블 §11.6에 없는 이 문서의 절차다(§5.2·§5.4). `rag up`은 compose 기동 뒤 마이그레이션(`rag ledger migrate`, 제안)·모델 최초 다운로드·`/readyz` 대기를 수행한다.

| 단계 | 명령 | 기대 결과 | 실패 시 |
|------|------|-----------|---------|
| 1 | `uv tool install rag-platform` | `rag --version` 출력 | uv 사설 인덱스 설정(에어갭, §6.3) |
| 2 | `rag up --profile lite`(운영: `--durable`) | 컨테이너 4(운영 5~6, §1) `healthy`; `GET :8000/readyz` 200; `./.rag/models`에 bge-m3 ONNX int8·mecab-ko-dic·RapidOCR ONNX | §9 "포트 충돌"·"모델 다운로드 실패" |
| 3 | `rag tenant create demo`(제안) → `TENANT_ID`; `rag api-key create --tenant $TENANT_ID --principal service:bootstrap`(제안) → `RAG_TOKEN` | ULID 테넌트, 키 1회 표시(원장 `api_keys.hash`만 저장) | 관리자 DSN 권한(`rag_platform_admin`) 확인 |
| 4 | 컬렉션 생성 — `curl -X POST :8000/v1/collections`(§5.4 JSON) | 201, `backends[0].alias = col_<id>_vec` | `profile.invalid`·`plugin.license_denied` → §5.3 |
| 5 | `rag ingest ./samples/*.hwpx --collection <collection_id> --wait` | 잡 `succeeded`, `index.commit.published` | `GET /v1/jobs/{job_id}` `last_error.code` |
| 6 | `rag query "정보공개 청구 절차" --collection <collection_id> --render markdown --explain` | `ContextPack.items` ≥ 1, `degraded = []`(리랭커 생략 시 `degraded[{rerank, skipped_by_policy}]`) | §9 "검색 0건" |
| 7 | `rag mcp serve` | `/mcp` 도구 `search`·`get_document`·`list_collections` | OIDC 없는 lite의 PRM 동작은 미해결 이슈 10 |

curl 등가(5·6단계): `Idempotency-Key`는 필수이고 `request_id`·`query_id`·`tenant_id`는 서버가 발급·주입하므로 본문에 넣지 않는다(바이블 §5.4·§5.5).

```bash
curl -sS -X POST "$RAG_URL/v1/ingest" \
  -H "Authorization: Bearer $RAG_TOKEN" -H "Content-Type: application/json" \
  -H "Idempotency-Key: quickstart-0001" \
  --data @ingest.json          # 아래 IngestRequest 예시
# → 202 {"job_id": "...", "status_url": ".../v1/jobs/...", "events_url": ".../v1/jobs/.../events"}
```

```json
{
  "schema_version": "1.0.0",
  "collection_id": "01JADQ3G5R7T9V2X4Z6B8D0F2H",
  "source_uri": "file:///samples/information-disclosure-guide.hwpx",
  "external_id": "samples/information-disclosure-guide",
  "metadata": {
    "title": "정보공개 청구 안내",
    "doc_type": "manual",
    "doc_date": "2026-03-01",
    "language_hint": "ko"
  },
  "acl": {
    "allow_principals": ["tenant:*"],
    "visibility": "tenant"
  },
  "requested_at": "2026-09-22T09:00:00.000Z"
}
```

```json
{
  "schema_version": "1.0.0",
  "query": "정보공개 청구 절차",
  "collection_ids": ["01JADQ3G5R7T9V2X4Z6B8D0F2H"],
  "top_k": 10,
  "renderer": "markdown",
  "explain": true,
  "requested_at": "2026-09-22T09:05:00.000Z"
}
```

`file://` 스킴은 개발 프로파일(`EgressPolicy.allowed_schemes`에 `file`·`http` 추가, 배포 아키텍처 §8)에서만 허용된다. 운영 `lite`에서는 `s3://`·`https://` 원천을 쓴다.

### 3.6 `lite` 운영 모드 제약

`--durable`은 Temporal 단일 바이너리를 추가해 수집을 내구 실행으로 바꾸지만 나머지 제약은 그대로다: OpenSearch 없음(렉시컬 채널은 Qdrant `sparse_bm25`, `channel=lexical`), 사이드카 없음(HWP 5.0은 unhwp → hwp-hwpx-parser, DOC은 `parse.unsupported_format`), GPU 없음, 큐 `ingest`·`maintenance`, `tenant_concurrent_jobs_max` 4, 검색 p95 목표 1,500ms, 인증은 API 키 + 정적 역할, `security.rate_limit.fail_mode`는 운영 `closed`(바이블 §7.1·§7.2). 업그레이드는 이미지 교체 + 재기동이며 수집만 수 분 중단되고 검색은 계속된다(배포 아키텍처 §10.4 lite).

---

## 4. `standard` / `premium` Kubernetes(Helm)

### 4.1 설치 순서

**결정:** Kubernetes 설치는 "네임스페이스·노드풀 → 데이터 계층 → 시크릿 → 모델 미러 → `helm install`(훅: models-verify → migrate → profile-validate → 릴리스 → schedules-apply) → 테넌트·컬렉션 → smoke test" 순서로 고정한다. 데이터 계층은 차트 의존성이 아니므로(배포 아키텍처 P3) 접속 정보가 시크릿으로 먼저 존재해야 `pre-install` 훅이 성공한다. (근거: 배포 아키텍처 §4.4, [ADR-0011](../06-adr/0011-kv-and-object-storage-valkey-rustfs-seaweedfs.md), [ADR-0031](../06-adr/0031-profile-schema-extends-and-quality-gates.md))

절 대응: (1) 네임스페이스·노드 라벨·테인트 §4.2 → (2) 데이터 계층·Temporal §4.4·§4.5 → (3) 시크릿·스토리지클래스 §4.3 → (4) 모델 미러 §6 → (5) `helm install` §4.8 → (6) 인그레스·TLS·DNS §4.7 → (7) 테넌트·컬렉션·사전 §5 → (8) smoke test·카나리 §7.

### 4.2 네임스페이스·노드풀

```bash
for ns in rag-platform rag-serving rag-optin rag-data rag-observability; do kubectl create namespace "$ns"; done
kubectl label nodes <cpu-node...>   rag.io/node-pool=cpu-general
kubectl label nodes <parse-node...> rag.io/node-pool=cpu-parse
kubectl taint nodes <parse-node...> rag.io/pool=cpu-parse:NoSchedule          # 선택
kubectl label nodes <gpu-node...>   rag.io/node-pool=gpu-serving              # premium: gpu-embed | gpu-rerank | gpu-ocr | gpu-llm
kubectl taint nodes <gpu-node...>   nvidia.com/gpu=present:NoSchedule
```

- 네임스페이스 5개는 배포 아키텍처 §5.2 확정값이다. 모든 네임스페이스에 기본 거부 NetworkPolicy가 차트(`network.networkPolicy.enabled: true`)로 배포되므로, CNI가 NetworkPolicy를 지원해야 한다. Egress Gateway가 없으면 `ipBlock.except` 규칙을 쓰는데 일부 CNI가 `except`를 지원하지 않는다 — Cilium 등 FQDN·CIDR 정책이 가능한 CNI를 권장하며 지원 목록은 미해결 이슈 8이다.
- `rag-optin`(GPL/AGPL 사이드카)은 egress 0이며 서비스 메시 주입 대상에서 제외한다(배포 아키텍처 §5.4).
- `rag-data`는 자체 호스팅 데이터 계층용이다. 관리형을 쓰면 비워 두고 `externals.*`에 외부 주소를 넣는다.

### 4.3 시크릿·스토리지클래스

| 시크릿(네임스페이스 `rag-platform`) | 키 | values 참조 | 주입 |
|-------------------------------------|----|-------------|------|
| `rag-pg` | `dsn`(`rag_app`), `dsn_owner`(마이그레이션 훅, 제안 — `rag_owner`는 `NOLOGIN`이므로 `rag_owner` 멤버십을 가진 로그인 역할의 DSN, §5.1), `dsn_maintenance`(릴레이·정합성 검사, 제안) | `externals.postgres.dsnSecretRef` | `RAG_PG__DSN` — 역할별 DSN 분리는 미해결 이슈 3 |
| `rag-s3` | `env`(S3 자격 증명 env 파일) | `externals.objectStore.credentialsSecretRef` | 오브젝트 스토리지 클라이언트 |
| `rag-valkey` | `url` | `externals.valkey.urlSecretRef` | `RAG_VALKEY__URL` |
| `rag-os-jwt` | `pem`(요청별 테넌트 JWT 서명 키, E8) | `externals.opensearch.jwtSigningKeySecretRef` | OpenSearch security 플러그인 JWT 인증 도메인과 동일 키 |
| `rag-qdrant` | `api-key` | `externals.qdrant.apiKeySecretRef` | Qdrant API 키 |
| `rag-temporal-tls`(선택) | `tls.crt`, `tls.key`, `ca.crt` | `externals.temporal.tlsSecretRef` | mTLS |
| `rag-tls` | `tls.crt`, `tls.key`(cert-manager 발급) | `ingress.tls.secretName` | 인그레스 TLS 종단 |
| `rag-regcred` | `.dockerconfigjson` | `global.image.pullSecrets[]` | 사설 레지스트리 |

External Secrets Operator를 쓰는 조직은 `config/externalsecret.yaml`(차트 템플릿)로 위 시크릿을 동기화하고 `secrets.provider: openbao|aws_kms`로 `credentials_ref` 간접 참조를 켠다(바이블 §6.6). 비밀 값은 로그·트레이스에 기록되지 않는다.

| 스토리지클래스 용도 | 접근 모드 | 크기(초안) | values |
|---------------------|-----------|-----------|--------|
| 모델 캐시(서빙·워커 init sync 대상) | `ReadWriteOnce` 노드 로컬(`local-nvme`) 또는 emptyDir | 20Gi | `models.cache.{storageClass, size, accessMode}` |
| 사전 적재 공유 모델 볼륨(선택) | `ReadOnlyMany` | 모델 합계 | 운영자가 미리 채운 경우만(init 컨테이너는 쓰지 않음, 배포 아키텍처 §3.4) |
| PostgreSQL·Qdrant·OpenSearch 데이터 | `ReadWriteOnce` NVMe | §2.1 사이징 | 자체 호스팅 시 `rag-platform-data` values |

### 4.4 데이터 계층: 자체 설치 vs 관리형

**결정:** 운영 차트는 데이터 계층을 설치하지 않으며, 자체 설치와 관리형 연결의 선택 기준은 아래 "필수 기능 체크리스트" 통과 여부다. 체크리스트를 통과하지 못하는 관리형 서비스(예: `analysis-nori`가 없는 OpenSearch, 테넌트 IDF·payload 파티셔닝이 없는 Qdrant 버전)는 연결 대상이 아니다. Qdrant 물리 컬렉션·OpenSearch 인덱스 템플릿·인덱스는 **운영자가 손으로 만들지 않는다** — 컬렉션 생성(§5.4) 시 `index_backend.*` 어댑터가 [저장소 아키텍처](../02-architecture/04-storage-architecture.md) §4.2·§5.1의 정본 JSON으로 생성한다. (근거: [ADR-0012](../06-adr/0012-lite-profile-qdrant-only-client-bm25.md), [ADR-0021](../06-adr/0021-korean-analyzer-kiwi-promotion-and-interim-mecab-kss.md), [ADR-0028](../06-adr/0028-tenant-isolation-tiering-policy.md))

| 구성 요소 | 자체 설치(개발·스테이징: `rag-platform-data` 번들 / 운영: 업스트림 차트·오퍼레이터) | 관리형 연결 | 필수 기능 체크리스트 |
|-----------|------|------|------|
| PostgreSQL | 업스트림 차트 또는 PostgreSQL 오퍼레이터(제품 선택은 [보안과 컴플라이언스](05-security-and-compliance.md)) | RDS·Cloud SQL 등 | 확장 `pgcrypto`(선택), RLS, 논리 복제(메이저 업그레이드), PITR; Temporal DB는 별도 인스턴스 권장(저장소 아키텍처 §2.6) |
| Qdrant | 공식 Helm 차트(StatefulSet 3노드; 차트 라이선스 확인 필요 as of 2026-09) — Qdrant 오퍼레이터는 상용 Private Cloud 구성요소일 수 있어 기본 매니페스트가 아니다(확인 필요) | Qdrant Cloud(API 키·TLS) | 1.19+, gRPC 6334, API 키, alias, 스냅샷의 S3 호환 저장소(확인 필요), `replication_factor: 2` |
| OpenSearch | OpenSearch Kubernetes Operator(Apache-2.0, 확인 필요) 또는 업스트림 Helm 차트; `analysis-nori`·`repository-s3` 플러그인을 이미지에 포함 | Amazon OpenSearch Service 등 — 3.8 제공 여부·Nori 플러그인·JWT 인증 도메인 지원 확인 필요(as of 2026-09) | 3.8 + `analysis-nori`, security 플러그인(JWT `roles_key`, DLS), `repository-s3`, 힙 ≤ 32GB, 데이터 노드 ≥3 |
| Valkey | 업스트림 차트(1 primary + 2 replica, Sentinel 또는 Cluster) | 관리형 Valkey/Redis 호환(Redis 8은 호환 옵션) | Redis 7.2 명령 집합, `maxmemory-policy volatile-lru`, 영속화 끔(`korean-gov` AOF 옵션) |
| 오브젝트 스토리지 | RustFS 또는 SeaweedFS(ADR-0011 택1 후 서브차트 고정) | S3·호환 서비스 | 버저닝, SSE-S3(`korean-gov` SSE-KMS), 멀티파트 정리, 접두 단위 정책 |

### 4.5 Temporal 설치 옵션

**결정:** `standard` 기본은 업스트림 Temporal Helm 차트를 `rag-data`에 자체 설치하고 영속화·가시성 DB를 원장과 **다른 PostgreSQL 인스턴스**에 두는 것이다. 조직에 Temporal 클러스터가 이미 있으면 전용 네임스페이스 `rag`를 만들어 재사용하고, 두 경우 모두 `externals.temporal.{address, namespace, tlsSecretRef}`만 바뀐다. `temporal server start-dev`는 개발 전용이며 어떤 운영 형상에도 쓰지 않는다. (근거: 바이블 §11.1, 배포 아키텍처 §2.2·§10.4, 07-tech-landscape/08 "셀프호스팅 의존성", [ADR-0003](../06-adr/0003-orchestrator-neutral-pipeline-and-non-durable-local-runner.md))

| 옵션 | 언제 | 절차 | values |
|------|------|------|--------|
| A. 기존 클러스터 재사용 | 조직 표준 Temporal 운영 중, 서버 1.32·SDK 1.33 호환 창 안 | `temporal operator namespace create --namespace rag --retention 7d`(보존 기간은 초안); mTLS 클라이언트 인증서를 `rag-temporal-tls`로; KEDA `temporal` 스케일러 접근 허용 | `externals.temporal: {address: <frontend>:7233, namespace: rag, tlsSecretRef: {name: rag-temporal-tls}}` |
| B. 자체 설치(기본) | 전용 클러스터 | (1) PostgreSQL에 DB `temporal`·`temporal_visibility`와 사용자 생성 → (2) `temporal-sql-tool setup-schema` → `update-schema`(두 DB, 서버 롤아웃 전) → (3) 업스트림 차트를 외부 PG 설정으로 설치(차트는 DB 서브차트를 설치하지 않음) — `server.config.numHistoryShards: 512`(초안; 부하 테스트 후 확정, 생성 후 변경 불가), frontend 2 / history 2 / matching 1(각 1~2 vCPU / 2~4GB, 초안) → (4) 네임스페이스 `rag` 생성 | `externals.temporal: {address: temporal-frontend.rag-data.svc:7233, namespace: rag}` |
| C. `lite` 단일 바이너리 | compose `--durable` | §3.4 | `RAG_TEMPORAL__ADDRESS=temporal:7233` |
| D. Temporal Cloud | 관리형 | mTLS 또는 API 키 인증, 네임스페이스 `<ns>.<account>`; KEDA 스케일러 인증 방식·2MB 페이로드 한계 동일 — 확인 필요(as of 2026-09) | `externals.temporal.address: <ns>.<account>.tmprl.cloud:7233` |

Temporal Web UI는 별도 컨테이너로 선택 배포한다. `relay` 파드도 Temporal frontend에 접속해야 하므로(전용 큐 `relay`, 배포 아키텍처 §2.2) NetworkPolicy가 `relay → 7233`을 허용하는지 확인한다.

### 4.6 모델 서빙 배치

서빙은 모델당 Deployment 1개다(배포 아키텍처 §6.3). GPU 파드는 `nodeSelector` + `tolerations` + `resources.limits.nvidia.com/gpu`(또는 MIG 리소스 이름)를 함께 선언하고, 가중치는 init 컨테이너 `rag models sync`가 볼륨에 내려받은 뒤 로컬 경로로 로드한다(§6.2).

```yaml
serving:
  embedding:
    engine: vllm_pooling                            # BGE-M3 3-in-1(ADR-0009). dense 전용 모델은 tei, 외부 서빙은 external
    model: {id: BAAI/bge-m3, revision: "<sha>"}
    image: vllm/vllm-openai
    digest: "sha256:<digest>"                       # 0.29 계열; CUDA 버전은 노드 드라이버에 맞춤
    replicas: 1
    gpu: {resourceName: nvidia.com/gpu, count: 1, memoryUtilization: 0.45}   # MIG: nvidia.com/mig-3g.40gb 등
    nodeSelector: {rag.io/node-pool: gpu-serving}   # tolerations(nvidia.com/gpu)·keda(1~2)는 차트 기본값
  reranker:
    engine: tei_gpu                                 # lite는 tei_cpu 또는 none
    model: {id: BAAI/bge-reranker-v2-m3, revision: "<sha>"}
    image: ghcr.io/huggingface/text-embeddings-inference
    tag: "89-1.9"                                   # 표시용. L4/L40 = 89, A10/A40 = 86, H100 = hopper, T4 = turing(확인 필요)
    digest: "sha256:<digest>"
    replicas: 1
    gpu: {resourceName: nvidia.com/gpu, count: 1}
    nodeSelector: {rag.io/node-pool: gpu-serving}
  sparse: {enabled: false}                          # ko-quality(PIXIE-Splade-v1.5)에서만 sparse-encoder-server
  sharing: dedicated                                # time_slicing 은 개발·스테이징만 렌더
```

- `vllm_pooling`의 기동 인자는 `vllm serve BAAI/bge-m3 --runner pooling`이며 BGE-M3 dense+sparse 단일 패스를 위한 `--hf-overrides`·IO 프로세서 플러그인 옵션은 07-tech-landscape/05 진입점 표기를 따르되 vLLM 0.29 문서로 확인 필요(as of 2026-09)다. 차트가 인자를 렌더하므로 운영자는 values만 만진다.
- 서빙 교체(같은 `embedding_space_id` 안에서 이미지·엔진만 변경)는 스테이징에서 코사인 ≥ 0.9999 동등성 게이트(D-16)를 통과한 뒤 `serving.additional[]`로 신 인스턴스를 띄우고 URL을 전환한다(배포 아키텍처 §6.3).
- `premium`은 `sidecars.ocrGpu.enabled: true`(`gpu-ocr` 노드풀), `workers.ingestGpuOcr`·`workers.ingestLlm` 활성, 선택 `serving.llm`(`gpu-llm`)을 더한다. LLM 보강은 여전히 기본 끔(컬렉션 옵트인, O-05)이다.

### 4.7 인그레스·TLS

**결정:** 진입점은 Ingress(NGINX 기준값) 또는 Gateway API `HTTPRoute` 하나이며 TLS는 엣지에서 종단한다. 인증·레이트리밋·멱등성은 인그레스가 아니라 `api`가 수행하므로 인그레스에는 그 기능을 켜지 않는다. (근거: 배포 아키텍처 §5.3, [ADR-0018](../06-adr/0018-api-rest-sse-mcp-no-grpc-rfc9457.md))

| 항목 | 값 | 이유 |
|------|----|------|
| TLS | cert-manager `ClusterIssuer`(공인 CA 또는 내부 CA) → `Certificate` → 시크릿 `rag-tls`; `ingress.tls.secretName: rag-tls` | 에어갭은 내부 CA(§6.3) |
| 요청 본문 상한 | 8MB(`nginx.ingress.kubernetes.io/proxy-body-size: 8m`) | `POST /v1/ingest/batch` 100 × 64KB, `POST /v1/render` 512KB |
| SSE·MCP 타임아웃 | `/v1/jobs/{job_id}/events`, `/v1/events`, `/mcp`: `proxy-read-timeout: "3600"`, `proxy-buffering: "off"`; 그 외 60s | 차트가 경로별 Ingress 두 개로 렌더 |
| HTTP 버전·헤더 | 클라이언트↔엣지 HTTP/2, 엣지↔`api` HTTP/1.1; `Idempotency-Key`, `Authorization`, `Last-Event-ID`, `traceparent` 전달, 응답 `RateLimit*` | uvicorn; 계약 헤더(바이블 §6.7) |
| 관리 표면 | `ingress.adminHost` + `ingress.adminAllowlist[]`(CIDR)로 `/v1/collections`, `/v1/profiles`, `/v1/tenants`, `/v1/subscriptions`, `/v1/eval`를 별도 호스트·IP 허용 목록으로 | 운영자 표면 최소 노출 |
| 검색 분리(선택) | `api.querySplit.enabled: true` → `/v1/query`, `/v1/render`, `/v1/answer`, `/mcp`, `/.well-known/oauth-protected-resource`가 `api-query`로 | 검색 p95 격리 |
| mTLS(`korean-gov`) | 서비스 메시 `mesh.enabled: true, mtlsMode: STRICT`; 메시 없으면 cert-manager 인증서로 서비스별 TLS | 배포 아키텍처 §5.4 |

DNS는 `ingress.host`(예 `rag.example.com`)와 선택 `adminHost`를 인그레스 컨트롤러 LB로 가리킨다. OIDC `issuer`·`audience`는 IdP 클라이언트 설정과 `externals.oidc`가 일치해야 하며, IdP JWKS URL은 `api` 네임스페이스의 외부 HTTPS egress 허용 목록(FQDN)에 포함된다(배포 아키텍처 §5.2).

### 4.8 Helm 설치 명령

```bash
helm pull oci://ghcr.io/<org>/charts/rag-platform --version <semver> --verify
helm install rag oci://ghcr.io/<org>/charts/rag-platform --version <semver> \
  --namespace rag-platform \
  -f values-standard.yaml -f values-env-prod.yaml \
  --set-file profile.inline=./profiles/standard-ko-hybrid.yaml \
  --atomic --timeout 30m
```

`--atomic`은 릴리스 실패 시 자동 롤백한다. 훅 Job은 `pre-install,pre-upgrade` 순서 `models-verify`(-30) → `migrate`(-20) → `profile-validate`(-10)로 실행되고 하나라도 실패하면 설치가 중단된다(배포 아키텍처 §4.4). 훅 로그는 `kubectl logs job/rag-models-verify -n rag-platform` 등으로 본다(훅 Job 이름은 릴리스 이름 접두).

설치 후 확인:

```bash
kubectl -n rag-platform get deploy,scaledobject,pdb,ingress
kubectl -n rag-platform rollout status deploy/rag-api
kubectl -n rag-serving  rollout status deploy/rag-embedding-server-bge-m3 deploy/rag-reranker-server-bge-reranker-v2-m3
```

### 4.9 values 예시(`standard` 최소, 운영 오버레이 포함)

```yaml
global:
  tier: standard
  image: {registry: ghcr.io/example, pullSecrets: [rag-regcred]}
  imageDigests:
    ragPlatform:     "sha256:<digest>"
    parserWorkers:   "sha256:<digest>"
    embeddingServer: "sha256:<digest>"
    rerankerServer:  "sha256:<digest>"
externals:
  postgres:   {dsnSecretRef: {name: rag-pg, key: dsn}}
  temporal:   {address: temporal-frontend.rag-data.svc:7233, namespace: rag}
  objectStore: {uri: s3://rag, endpointUrl: https://objectstore.rag-data.svc:9000, credentialsSecretRef: {name: rag-s3, key: env}}
  valkey:     {urlSecretRef: {name: rag-valkey, key: url}}
  qdrant:     {url: http://qdrant.rag-data.svc:6334, preferGrpc: true, apiKeySecretRef: {name: rag-qdrant, key: api-key}}
  opensearch: {url: https://opensearch.rag-data.svc:9200, jwtSigningKeySecretRef: {name: rag-os-jwt, key: pem}}
  oidc:       {issuer: https://idp.example.com/realms/rag, audience: rag-platform}
  otel:       {endpoint: http://otel-collector.rag-platform.svc:4317}
profile: {existingConfigMap: rag-profile}          # 또는 --set-file profile.inline
api:
  replicas: 2
  autoscaling: {enabled: true, minReplicas: 2, maxReplicas: 8, targetCPUUtilizationPercentage: 60}
  pdb: {minAvailable: 1}
workers:
  ingestIo:       {minReplicaCount: 1, maxReplicaCount: 4,  maxConcurrentActivities: 16, terminationGracePeriodSeconds: 60}
  ingestCpu:      {minReplicaCount: 1, maxReplicaCount: 32, processes: 4, maxConcurrentActivities: 1,
                   resources: {requests: {cpu: "4", memory: 12Gi}}, nodeSelector: {rag.io/node-pool: cpu-parse},
                   terminationGracePeriodSeconds: 120}
  ingestGpuEmbed: {minReplicaCount: 1, maxReplicaCount: 2, maxConcurrentActivities: 8}
  maintenance:    {minReplicaCount: 1, maxReplicaCount: 2, terminationGracePeriodSeconds: 300}
relay: {mode: temporal, replicas: 1, taskQueue: relay}
sidecars:
  parserWorkers: {enabled: true, replicas: 2}
  ocrGpu: {enabled: false}
optIn:
  loSidecar: {enabled: false}                       # GPL: enabled 시 acknowledgeLicense: true 필수
models: {mirrorUri: s3://rag/models, cache: {storageClass: local-nvme, size: 20Gi, accessMode: ReadWriteOnce}}
network: {networkPolicy: {enabled: true}, egressGateway: {enabled: true, cidr: 10.200.0.0/24}}
ingress:
  enabled: true
  className: nginx
  host: rag.example.com
  tls: {secretName: rag-tls}
  adminHost: rag-admin.example.com
  adminAllowlist: ["10.0.0.0/8"]
mesh: {enabled: false}
observability: {otelCollector: {mode: gateway, replicas: 2}, contentCapture: none, serviceMonitor: {enabled: true}}
```

`premium` 오버레이(`values-premium.yaml`)는 위에 `workers.ingestGpuOcr`·`workers.ingestLlm`(`maxConcurrentActivities: 4`), `sidecars.ocrGpu: {enabled: true, gpu: {resourceName: nvidia.com/gpu, count: 1}, nodeSelector: {rag.io/node-pool: gpu-ocr}}`, `api.replicas: 3`·`pdb.minAvailable: 2`, 서빙 `replicas: 2`, 노드풀 `gpu-embed`·`gpu-rerank` 셀렉터를 덮어쓴다. `korean-gov`는 `values-korean-gov.yaml`(`mesh.enabled: true`, OpenBao Transit, 감사 인덱스, Temporal 네임스페이스 등급별) + `values-airgapped.yaml`(§6.3)을 겹친다.

---

## 5. 초기화

### 5.1 원장 마이그레이션

| 항목 | 절차 |
|------|------|
| 실행 주체 | Helm 훅 Job `migrate`(`rag ledger migrate`, 제안 명령) 또는 `lite`의 `rag up`. 확장(expand) 단계만 적용하고 수축(contract)은 다음 릴리스 정리 단계에서 실행한다(배포 아키텍처 §10.5) |
| 역할 | 테이블 소유자는 `rag_owner`(`NOLOGIN`)이므로 마이그레이션은 `rag_owner` 멤버십을 가진 로그인 역할(제안: `rag_platform_admin`에 `GRANT rag_owner`)의 DSN `dsn_owner`로 접속해 시작 시 `SET ROLE rag_owner`를 수행한다(멤버십·DSN 확정은 미해결 이슈 3). 애플리케이션 `rag_app`(`NOBYPASSRLS`), 플랫폼 운영 `rag_platform_admin`, 백그라운드 `rag_maintenance` — [저장소 아키텍처](../02-architecture/04-storage-architecture.md) §2.4 |
| RLS | 모든 테넌트 스코프 테이블에 `ENABLE`+`FORCE ROW LEVEL SECURITY`와 정책이 마이그레이션 안에서 함께 적용된다. 정책 누락 = 마이그레이션 실패 |
| 파티션 | `job_events`·`audit_log` 월, `outbox` 일 단위 RANGE 파티션 선생성(`pg_partman` 또는 스케줄 잡) |
| 검증 | `psql -c "\d+ documents"`에서 `FORCE ROW LEVEL SECURITY`; `SET LOCAL app.tenant_id` 없는 트랜잭션에서 `SELECT count(*) FROM documents` = 0(fail-closed) |
| Temporal | `temporal-sql-tool update-schema`는 §4.5(서버 롤아웃 전, 두 DB 각각) |

### 5.2 테넌트·API 키 부트스트랩

바이블 §14 API 표면에는 테넌트 **생성** 엔드포인트가 없고(`PATCH /v1/tenants/{tenant_id}/policies`·`GET .../usage`만), `tenants` 쓰기는 `rag_platform_admin` 역할의 횡단 모드다(저장소 아키텍처 §2.4). 따라서 최초 테넌트는 CLI로 만든다(제안 명령, 미해결 이슈 1·2).

```bash
rag tenant create --name demo --tier standard \
  --policy llm_enrichment_allowed=false --policy allow_distribution_documents=false \
  --policy classification_max=internal                       # → tenant_id (ULID)
rag api-key create --tenant <tenant_id> --principal service:bootstrap --roles admin --expires-in 30d   # 키는 1회만 표시
```

- `tenants.policies`의 키는 바이블 §13.1 그대로 `llm_enrichment_allowed`, `allow_distribution_documents`, `classification_max`, `egress_policy`다. `egress_policy`(`EgressPolicy`)는 프로파일 `runtime.egress`와 AND로 결합되며 `deny_cidrs`를 축소할 수 없다(바이블 §7.4 (12)).
- `standard` 이상은 OIDC가 기본이다. IdP 그룹 → Cedar 역할(`reader`·`admin` 등)과 `allowed_collections` 매핑은 [보안과 컴플라이언스](05-security-and-compliance.md)가 소유하며, API 키는 서비스 계정(`service:{client_id}`)·부트스트랩 용도로만 남긴다(E1).
- 스테이징·운영에는 **카나리 침투 테넌트**를 하나 더 만들어 §7의 교차 테넌트 검사를 주기적으로 돌린다(배포 아키텍처 §8).

### 5.3 프로파일 검증

프로파일 YAML은 컬렉션에 속하고 `profile_hash`가 모든 커밋·플랜·팩에 기록되므로, 스테이징과 운영의 프로파일은 바이트 동일해야 한다(배포 아키텍처 §8). 개발용 완화(`security.rate_limit.fail_mode: open`, `runtime.egress.allowed_schemes`에 `file`·`http`)는 `profile_id` 접미 `-dev` 별도 프로파일로만 둔다.

```bash
rag profile validate --file profiles/standard-ko-hybrid.yaml        # 바이블 §7.4 규칙 12개
rag profile diff lite standard                                       # 상속 해소 후 차이만
curl -sS -X POST "$RAG_URL/v1/profiles/validate" -H "Authorization: Bearer $RAG_TOKEN" \
  -H "Content-Type: application/yaml" --data-binary @profiles/standard-ko-hybrid.yaml
```

검증 실패는 `profile.invalid`(422) / `plugin.license_denied`(422) / `plugin.capability_unsupported`(422)이며 `ProblemDetails.errors[].location.pointer`가 해소된 프로파일의 JSON 포인터를 가리킨다([프로파일·정책 계약](../03-contracts/15-collection-profile-and-policy-contracts.md) §3.9). 배포에서 자주 걸리는 규칙: (1) `license_grade` C/D 플러그인은 `optIn` 명시 필요 — `optIn.loSidecar.enabled=false`인데 `parse.router.doc`이 `lo-sidecar`를 참조하면 `profile-validate` 훅 실패; (6) `parse.options.ocr`의 `version`·`model`·`lang` 필수; (9) `lite`는 플랫폼 측 `korean_analyzer` 필수; (10) `parse.router`가 `SourceFormat` 13값 전부를 키로 가져야 함; (11) `query.hydrate.top_n ≥ max(rerank.top_n_in, pack.k_max)`.

### 5.4 컬렉션 생성

`POST /v1/collections`는 `CollectionSpec`을 만들되 `collection_id`·`profile_hash`·`embedding_space_ids`·`embedding_profile_hash`·`analyzer_id`·`dictionary_hash`·`dictionary_ref`·`backends`·`stats`·`created_at`·`updated_at`은 서버가 계산·발급한다. 클라이언트가 보내는 부분집합의 정확한 스키마는 05-api/04 확정 대상(미해결 이슈 4)이며, 아래는 그 부분집합의 예시다.

```json
{
  "schema_version": "1.0.0",
  "name": "정보공개 안내 문서",
  "profile_id": "standard",
  "tenant_isolation_tier": "payload_filter",
  "policies": {
    "pii_policy": "mask",
    "pii_tokenize_mode": "hash",
    "llm_enrichment_allowed": false,
    "allow_distribution_documents": false,
    "enrichment_budget_tokens": 0,
    "corpus_multiplier_max": 1.5
  },
  "filterable_fields": ["custom.ministry_code", "custom.doc_number"],
  "license_policy": {"max_grade": "B", "territory": ["KR"]}
}
```

생성 시 어댑터가 수행하는 것과 운영자가 확인할 것:

| 백엔드 | 어댑터 동작 | 확인 |
|--------|-------------|------|
| Qdrant | 물리 컬렉션 `rag_vec_{embedding_profile_hash[:12]}`가 없으면 저장소 아키텍처 §4.2 JSON으로 생성(`dense` 1024d Cosine, `m=0`·`payload_m=16`, scalar int8; `standard`는 `sparse_learned`, `lite`는 `sparse_bm25 modifier=idf`), payload 인덱스 §4.4, alias `col_{collection_id}_vec` | `GET /collections/aliases`에 alias; `GET /collections/{physical}`의 `payload_schema`에 `tenant_id`(`is_tenant`) |
| OpenSearch(`standard`+) | 인덱스 템플릿 `rag_lex_*`(Nori `nori_index`=`mixed`, `nori_search`=`discard`) 적용, 물리 인덱스 `rag_lex_{lexical_profile_hash[:12]}`, alias `col_{collection_id}_lex`(filtered alias `collection_id`) | `GET _index_template/rag_lex`; `GET _cat/aliases/col_*_lex`; `GET rag_lex_*/_settings`에 `analysis.tokenizer.rag_nori_mixed` |
| PostgreSQL | `collections` 행(`profile_hash`·`backends jsonb`) + Valkey `collspec:{collection_id}` 캐시 | `GET /v1/collections/{collection_id}`의 `backends[].physical_name`·`alias` |

컬렉션 프로파일을 바꾸는 것은 업그레이드가 아니라 blue/green 재색인(`PATCH /v1/collections/{collection_id}` → `reindex.collection.v1`)이다(바이블 §11.2).

### 5.5 사용자 사전·스케줄·구독(선택)

- **사용자 사전**: `PUT /v1/collections/{collection_id}/dictionary`에 `UserDictEntry[]`. 변경은 `dictionary_hash` → `lexical_profile_hash`를 바꾸므로 렉시컬 재색인 제안 응답이 온다(바이블 §14). `korean-gov`는 컬렉션 사용자 사전이 필수다(바이블 §7.1).
- **스케줄**: `post-install` 훅 `schedules-apply`(`rag schedules apply`, 제안)가 `maintenance.consistency.v1`(시간 1회 샘플 + 일 1회 전체), `maintenance.cleanup.v1`(`cleanup_delay` 1h), `eval.run.v1`(야간), `tier.promotion.v1`을 `ScheduleOverlapPolicy.SKIP`으로 생성한다. 확인: `temporal schedule list --namespace rag`.
- **웹훅 구독**: `POST /v1/subscriptions {webhook_url, events[], secret_ref}` — 등록 시 `EgressPolicy` 검사(E16), 서명 헤더 `RAG-Signature`(HMAC-SHA256, 바이블 §6.2). 수신자는 5분 재생 창을 검증한다.

---

## 6. 모델 준비

### 6.1 `models.lock`과 미러

**결정:** 모든 모델·사전·OCR 가중치는 이미지에 굽지 않고 오브젝트 스토리지 미러 `models/{repo}/{revision}/… + LICENSE + models.lock`(바이블 §13.3)에서 공급한다. 미러 생성은 연결망의 운영자 1회 작업이고, 볼륨 적재는 파드별 init 컨테이너만 한다(Helm 훅은 검증만). 운영 프로파일은 `HF_HUB_OFFLINE=1`로 런타임 다운로드를 차단한다. (근거: D-02 `models.lock`, 배포 아키텍처 §3.4, [ADR-0001](../06-adr/0001-license-grade-table-and-d02-interpretation.md), [ADR-0008](../06-adr/0008-ocr-default-rapidocr-ppocrv5-korean.md))

| 단계 | 명령(§12 `cli/` 미등재 — 모두 제안, 미해결 이슈 1) | 실행 위치 | 검증 |
|------|------|-----------|------|
| 1 미러 생성 | `rag models mirror --lock models.lock --dest s3://rag/models` | 연결망(HF 접근 가능) | 항목별 sha256, `LICENSE` 파일 존재, pickle 계열 거부(safetensors 전용), D 등급은 `model_license_ack` 없으면 제외 |
| 2 미러 검증 | `rag models verify --lock models.lock --mirror s3://rag/models` | Helm 훅 `models-verify`(-30) 또는 수동 | 존재·sha256·`LICENSE`·등급 대조; 실패 시 설치 중단 |
| 3 볼륨 적재 | `rag models sync --lock /config/models.lock --dest /models` | 각 파드 init 컨테이너(그 파드의 `consumers` 항목만) | 누락 시 파드 readiness 실패로 조기 노출 |
| `lite` | `rag up`이 최초 기동 시 bge-m3 dense ONNX int8·mecab-ko-dic·RapidOCR PP-OCRv5 korean ONNX를 `./.rag/models`에 다운로드(바이블 §11.6) | 개발 노드 | `HF_HUB_OFFLINE=0`; 운영 `lite`는 미러에서 `rag models sync`로 사전 적재 후 `1` |

프로파일별 `models.lock` 항목(형식은 배포 아키텍처 §3.4 예시 — `id, revision, sha256, license, grade, territory, format, consumers`; 확정은 10-development/05):

| 항목 | 소비자 | 포맷 | 프로파일 | 크기(초안) |
|------|--------|------|----------|-----------|
| `BAAI/bge-m3` | `embedder.vllm_pooling_bge_m3`(safetensors) / `embedder.inprocess_sentence_transformers`(ONNX int8) | safetensors / onnx | standard+ / lite | fp16 약 1.1GB / int8 약 0.6GB(확인 필요) |
| `BAAI/bge-reranker-v2-m3` | `reranker.tei_cross_encoder` | safetensors | standard+ | 약 1.1GB |
| `Alibaba-NLP/gte-multilingual-reranker-base` | `reranker.tei_cross_encoder`(TEI CPU) | safetensors | lite(선택) | 확인 필요 |
| `docling-project/docling-models`(heron·TableFormer) | `parser.pdf_docling_standard` | safetensors | standard+ | 수백 MB; CDLA-Permissive-2.0 등급 A는 잠정 |
| RapidOCR PP-OCRv5 korean mobile(det·rec ONNX) | `parser.pdf_docling_standard` | onnx | 전체 | 수십 MB |
| `PaddlePaddle/korean_PP-OCRv5_mobile_rec` + server det + UVDoc·textline orientation | `sidecar.ocr_gpu` | paddle | premium | 확인 필요 |
| mecab-ko-dic, kss 리소스 | `normalizer.mecab_ko`, `normalizer.kss_punct` | 사전 | 전체 | 수백 MB |
| spaCy `ko_core_news_lg`, GLiNER2 | `normalizer.presidio_ko`, `enricher.gliner2_entities` | wheel / safetensors | standard+ | 확인 필요 |
| Tesseract `kor`·`kor_vert` traineddata | `pdf_airgapped` 폴백 | traineddata | korean-gov·에어갭 | 수십 MB |
| Kiwi 모델(`[kiwi]` extra 시) | `normalizer.kiwi` | 모델 | 선택 | kiwipiepy ≥0.24.0 Apache-2.0 wheel 공개 확인 필요(ADR-0021) |

### 6.2 캐시 볼륨

| 소비자 | 마운트 | 볼륨 | 환경 변수 |
|--------|--------|------|-----------|
| `embedding-server`·`reranker-server` | `/models` | 노드 로컬 PVC(RWO) 또는 emptyDir + init sync | 모델 경로를 로컬로 지정(HF 다운로드 없음) |
| `worker-cpu` | `/models` | emptyDir + init sync(기본) 또는 사전 적재 `ReadOnlyMany` PVC | `HF_HOME=/models/hf`, `HF_HUB_OFFLINE=1` |
| `ocr-gpu` | `/models` | emptyDir + init sync 또는 번들 이미지 `ocr-gpu:<ver>-bundled` | — |
| `app`(lite) | `/models` | 바인드 `./.rag/models` | `HF_HOME=/models/hf` |

emptyDir는 파드 재스케줄 시 다시 내려받으므로 서빙 0→1 목표(< 3분, 배포 아키텍처 §6.4)를 지키려면 노드 로컬 PVC를 권장한다. 이미지 digest가 바뀌어도 청크 임베딩 캐시 `H("embed", embedding_space_id, "document", embed_text)`는 봉투가 없어 그대로 적중하므로 재임베딩 비용은 없다(배포 아키텍처 §6.3).

### 6.3 에어갭 미러 절차

`values-airgapped.yaml` 오버레이 하나로 표현하며 `korean-gov`는 기본으로 켠다(배포 아키텍처 §9). 다섯 축을 연결망에서 준비해 매체로 반입한다.

| 축 | 연결망 작업 | 반입 후 | 검증 |
|----|-------------|---------|------|
| 이미지 | `rag release bundle --images > images.txt`(제안) → `skopeo copy --all docker://ghcr.io/<org>/rag-platform@sha256:<d> oci-archive:rag-platform.tar` (코어·사이드카·서빙·데이터 계층·KEDA·GPU Operator·인그레스·OTel Collector 전부) | `skopeo copy oci-archive:… docker://registry.internal/rag/rag-platform@sha256:<d>`; `global.image.registry: registry.internal/rag` — digest 불변 | `rag release verify`(제안): digest 존재·cosign 서명 |
| 모델·사전 | `rag models mirror --lock models.lock --dest ./mirror/models` | 내부 오브젝트 스토리지 `models/`에 적재; `models.mirrorUri` 갱신 | `rag models verify` |
| 패키지 | 이미지 반입으로 런타임 패키지 다운로드 없음; 플러그인 추가 시 uv 사설 인덱스 wheel 미러 | `UV_INDEX_URL` 내부 | `uv lock --check` |
| Helm 차트 | `helm pull oci://…/rag-platform`, `rag-platform-data`, 업스트림 의존 차트 | `helm push` → 내부 OCI 레지스트리 | `helm pull --verify` |
| 인증서·시각 | 내부 CA 발급자(cert-manager), NTP 서버 | `ingress.tls`, `externals.*` TLS | JWT `exp`·RFC 3339 판정 |

`values-airgapped.yaml`이 켜는 것: `global.airgapped: true`(→ `HF_HUB_OFFLINE=1`, 외부 egress 0), `pdf_airgapped` 라우팅 허용(Docling + Tesseract `kor+eng`, CPU), `ocr-gpu:<ver>-bundled`, AGPL 불가 관측 대안(OpenSearch Observability + Perses 또는 VictoriaMetrics/Logs + Jaeger). 금지: 런타임 `pip install`·HF 다운로드·spaCy `download`, `latest` 태그, 외부 `count_tokens` API(팩은 `approximate` + `calibration_ratio`, `degraded{token_count}`), 외부 LLM 보강(온프레미스 `llm-server`만). 외부 URL을 참조하는 플러그인 설정을 `profile.invalid`로 거부하는 규칙은 배포 아키텍처 미해결 이슈 6(바이블 §7.4 (13) 제안)이다.

---

## 7. 검증 체크리스트(smoke test)

### 7.1 체크리스트

| # | 항목 | 명령·관측 | 기대 | 프로파일 |
|---|------|-----------|------|----------|
| 1 | liveness·readiness | `GET /healthz`, `GET /readyz` | 200; readiness는 프로파일 캐시 + Qdrant 도달만 요구(OpenSearch·PG·Temporal 불가는 readiness에 영향 없음, 배포 아키텍처 §10.2) | 전체 |
| 2 | 메트릭 | `GET :9090/metrics` | `rag_query_latency_seconds` 등 정본 메트릭(바이블 §6.5); `tenant_id` 라벨 없음 | 전체 |
| 3 | 수집·멱등 | `POST /v1/ingest` 2회(같은 `Idempotency-Key`) | 202 → 200 같은 `job_id`; 다른 본문은 422 `api.idempotency_payload_mismatch` | 전체 |
| 4 | 잡 완료 | `GET /v1/jobs/{job_id}` / SSE `/events` | `state=succeeded`, `index.commit.published` | 전체 |
| 5 | 검색 | `POST /v1/query` | `context_pack.items` ≥ 1, `degraded=[]`(lite 리랭커 생략 시 `rerank` 항목만) | 전체 |
| 6 | egress 카나리(E16) | `source_uri: https://169.254.169.254/…` 수집 | 잡 `failed`, `last_error.code = fetch.egress_denied`; `rag_egress_denied_total{component="fetch"}` 증가 | 전체 |
| 7 | 교차 테넌트 카나리(E2) | 카나리 테넌트 토큰으로 타 테넌트 `collection_ids` 질의 | 403 `plan.collection_forbidden` | 전체 |
| 8 | 레이트리밋 fail-closed | Valkey 중단 후 질의 | 운영 `closed` → 429 `api.rate_limited`; 개발 `open` → 통과 | 운영 |
| 9 | 오케스트레이터 불가 | Temporal frontend 차단 후 `POST /v1/ingest` | 503 + `Retry-After`, 잡 `queued` 유지; 검색은 정상 | standard+ |
| 10 | 사이드카·서빙 | `GET parser-workers:8080/healthz`; `POST embedding-server:8000/pooling`(bge-m3); `POST reranker-server:8080/rerank` | `image_digest`가 `global.imageDigests.parserWorkers`와 일치; dense 1024d + sparse; 리랭크 점수; 서빙 파드 안 `nvidia-smi` GPU 인식 | standard+ |
| 11 | 인덱스 alias·DLS | Qdrant `GET /collections/aliases`, OpenSearch `GET _cat/aliases/col_*`; 테넌트 JWT 없이 OpenSearch 직접 질의 | `col_{collection_id}_vec`·`_lex` 존재, `rag_lex_*` 템플릿; JWT 없는 질의는 거부(security 플러그인) | standard+ |
| 12 | 아웃박스 지연 | `rag_outbox_lag_seconds` | ≤ SLO(lite 30s / standard 5s / korean-gov 2s) | 전체 |
| 13 | 스케줄 | `temporal schedule list` | `maintenance.consistency.v1`·`maintenance.cleanup.v1`·`eval.run.v1` | standard+ |
| 14 | 골든셋 게이트 | `rag eval run --dataset ko-public-v1 --collection <id>` | `EvalReport.gate_result.passed = true`(`ndcg@10 ≥ 0.80`, `recall@20 ≥ 0.92` standard; lite 0.70/0.85) | 스테이징 |

### 7.2 smoke test 스크립트

`deploy/scripts/smoke-test.sh`(경로는 제안, 미해결 이슈 12). §7.1 항목 1, 3~7을 자동화하고, 항목 2(메트릭)는 `RAG_METRICS_URL`이 설정된 경우(클러스터 내부)에만 수행한다. 항목 7(교차 테넌트)은 `RAG_FOREIGN_COLLECTION_ID`가 있을 때만 실행된다. 인증 헤더 형식은 05-api/01 확정 대상이며 여기서는 `Authorization: Bearer`를 가정한다.

```bash
#!/usr/bin/env bash
# 배포 직후 검증. 필요 도구: curl, jq. 종료 코드 0 = 통과.
set -euo pipefail
: "${RAG_URL:?예: https://rag.example.com}"
: "${RAG_TOKEN:?API 키 또는 OIDC 액세스 토큰}"
: "${RAG_COLLECTION_ID:?smoke 전용 컬렉션 ULID}"
: "${RAG_SAMPLE_URI:?수집할 샘플 문서 URI (s3://... 또는 https://...)}"
RAG_METRICS_URL="${RAG_METRICS_URL:-}"                          # 예: http://rag-api.rag-platform.svc:9090/metrics (클러스터 내부)
RAG_FOREIGN_COLLECTION_ID="${RAG_FOREIGN_COLLECTION_ID:-}"      # 다른 테넌트의 컬렉션 ULID(교차 테넌트 카나리, 선택)
ALLOW_DEGRADED="${ALLOW_DEGRADED:-0}"                           # lite(리랭커 생략)는 1
AUTH=(-H "Authorization: Bearer ${RAG_TOKEN}" -H "Content-Type: application/json")
NOW="$(date -u +%Y-%m-%dT%H:%M:%S.000Z)"
BODY_FILE="$(mktemp)"; trap 'rm -f "$BODY_FILE"' EXIT
pass() { printf 'PASS %s\n' "$1"; }
fail() { printf 'FAIL %s\n' "$1" >&2; exit 1; }
req()  { curl -sS -o "$BODY_FILE" -w '%{http_code}' "$@"; }

# 1. 상태
[ "$(req "${RAG_URL}/healthz")" = 200 ] && pass healthz || fail healthz
[ "$(req "${RAG_URL}/readyz")"  = 200 ] && pass readyz  || fail readyz

# 2. 수집(202) + 멱등 재전송(200, 같은 job_id)
IDEM="smoke-$(date +%s)-${RANDOM}"
BODY=$(jq -n --arg c "$RAG_COLLECTION_ID" --arg u "$RAG_SAMPLE_URI" --arg t "$NOW" \
  '{schema_version:"1.0.0", collection_id:$c, source_uri:$u, external_id:("smoke-"+$t),
    metadata:{title:"smoke test", language_hint:"ko"},
    acl:{allow_principals:["tenant:*"], visibility:"tenant"}, requested_at:$t}')
CODE=$(req -X POST "${RAG_URL}/v1/ingest" "${AUTH[@]}" -H "Idempotency-Key: ${IDEM}" -d "$BODY")
[ "$CODE" = 202 ] || fail "ingest expected 202, got ${CODE}: $(cat "$BODY_FILE")"
JOB_ID=$(jq -r .job_id "$BODY_FILE"); pass "ingest job_id=${JOB_ID}"
CODE=$(req -X POST "${RAG_URL}/v1/ingest" "${AUTH[@]}" -H "Idempotency-Key: ${IDEM}" -d "$BODY")
{ [ "$CODE" = 200 ] && [ "$(jq -r .job_id "$BODY_FILE")" = "$JOB_ID" ]; } && pass idempotency-replay || fail "idempotency-replay (${CODE})"

# 3. 잡 완료 대기(최대 10분)
STATE=queued
for _ in $(seq 1 120); do
  req "${RAG_URL}/v1/jobs/${JOB_ID}" "${AUTH[@]}" >/dev/null; STATE=$(jq -r .state "$BODY_FILE")
  case "$STATE" in succeeded) break ;; failed|cancelled|partial) fail "job ${STATE}: $(jq -c '.last_error' "$BODY_FILE")" ;; esac
  sleep 5
done
[ "$STATE" = succeeded ] && pass "job succeeded" || fail "job timeout (state=${STATE})"

# 4. 검색
QBODY=$(jq -n --arg c "$RAG_COLLECTION_ID" --arg t "$NOW" \
  '{schema_version:"1.0.0", query:"smoke test", collection_ids:[$c], top_k:5, renderer:"markdown", explain:true, requested_at:$t}')
CODE=$(req -X POST "${RAG_URL}/v1/query" "${AUTH[@]}" -d "$QBODY")
[ "$CODE" = 200 ] || fail "query expected 200, got ${CODE}: $(cat "$BODY_FILE")"
[ "$(jq '.context_pack.items | length' "$BODY_FILE")" -gt 0 ] && pass "query items>0" || fail "query returned no items"
DEG=$(jq -c '.context_pack.degraded' "$BODY_FILE")
if [ "$DEG" = "[]" ]; then pass "degraded empty"
elif [ "$ALLOW_DEGRADED" = 1 ]; then pass "degraded allowed: ${DEG}"
else fail "degraded: ${DEG}"; fi

# 5. egress 카나리(E16): 메타데이터 IP → fetch.egress_denied
EBODY=$(jq -n --arg c "$RAG_COLLECTION_ID" --arg t "$NOW" \
  '{schema_version:"1.0.0", collection_id:$c, source_uri:"https://169.254.169.254/latest/meta-data/",
    external_id:("egress-canary-"+$t), acl:{allow_principals:["tenant:*"], visibility:"tenant"}, requested_at:$t}')
CODE=$(req -X POST "${RAG_URL}/v1/ingest" "${AUTH[@]}" -H "Idempotency-Key: ${IDEM}-egress" -d "$EBODY")
[ "$CODE" = 202 ] || fail "egress canary submit expected 202, got ${CODE}"
EJOB=$(jq -r .job_id "$BODY_FILE")
for _ in $(seq 1 24); do
  req "${RAG_URL}/v1/jobs/${EJOB}" "${AUTH[@]}" >/dev/null; [ "$(jq -r .state "$BODY_FILE")" = failed ] && break; sleep 5
done
[ "$(jq -r '.last_error.code' "$BODY_FILE")" = "fetch.egress_denied" ] && pass "egress denied" \
  || fail "egress canary: $(jq -c '{state, last_error}' "$BODY_FILE")"

# 6. 교차 테넌트 카나리(E2): 타 테넌트 컬렉션 → 403 plan.collection_forbidden
if [ -n "$RAG_FOREIGN_COLLECTION_ID" ]; then
  FBODY=$(jq -n --arg c "$RAG_FOREIGN_COLLECTION_ID" --arg t "$NOW" \
    '{schema_version:"1.0.0", query:"smoke", collection_ids:[$c], requested_at:$t}')
  CODE=$(req -X POST "${RAG_URL}/v1/query" "${AUTH[@]}" -d "$FBODY")
  { [ "$CODE" = 403 ] && [ "$(jq -r .code "$BODY_FILE")" = "plan.collection_forbidden" ]; } \
    && pass "cross-tenant denied" || fail "cross-tenant canary (${CODE}: $(cat "$BODY_FILE"))"
fi

# 7. 메트릭(클러스터 내부에서만)
if [ -n "$RAG_METRICS_URL" ]; then
  curl -sS "$RAG_METRICS_URL" | grep -q '^rag_query_latency_seconds' && pass metrics || fail metrics
fi
echo "SMOKE OK"
```

Kubernetes에서는 이 스크립트를 `helm test` 훅 또는 CI Job으로 실행한다(`RAG_METRICS_URL`은 클러스터 내부 서비스 주소). 스크립트가 만든 smoke 문서는 `DELETE /v1/documents/{document_id}`로 정리하거나 smoke 전용 컬렉션을 주기적으로 재생성한다.

---

## 8. 업그레이드 절차(링크)

업그레이드 순서·드레인·롤백 규칙은 [배포 아키텍처](../02-architecture/08-deployment-architecture.md) §10이 확정했고, 명령 수준 절차는 [업그레이드와 마이그레이션](08-upgrade-and-migration.md)이 소유한다. 이 문서는 배포 직후 운영자가 알아야 할 요지만 적는다.

| 항목 | 요지 |
|------|------|
| 순서 | 원장 확장(`migrate` 훅) → Temporal 서버(마이너 순차) → 워커 롤링(큐별 드레인) → `api` 롤링(`maxSurge 1 / maxUnavailable 0`) → `relay` → 검증(`Replayer`·카나리·게이트) → 정리 릴리스(수축) |
| 명령 | `helm upgrade rag oci://…/rag-platform --version <new> -f … --atomic --timeout 30m`; 훅이 `models-verify`·`migrate`·`profile-validate`를 다시 실행 |
| 롤백 | 수축 전이면 `helm rollback rag <rev>`는 항상 안전. Temporal 서버 스키마는 다운그레이드 불가 → PITR 복원 절차 |
| 프로파일 | 프로파일 값 변경은 업그레이드가 아니라 `version` 증가 → `profile_hash` 변경 → 컬렉션 blue/green 재색인. 코어 릴리스 노트의 "profile_hash 변경·재색인 필요 컬렉션" 항목을 확인 |
| `lite` | `rag up --profile lite --durable`을 새 digest로 재실행(이미지 교체 + 마이그레이션 + 재기동); 수집만 수 분 중단 |

---

## 9. 흔한 문제

| 증상 | 원인 | 조치 |
|------|------|------|
| `rag up` 실패: `port is already allocated`(8000·5432·6333·6379·7233) | 호스트 포트 충돌 | `.env`의 `RAG_SERVE__PORT`(제안)·compose `ports` 호스트 측 변경; 내부 서비스 간 주소는 컨테이너 이름이라 영향 없음 |
| `app` 기동 실패: `RAG_VALKY__URL` 같은 미지 변수 | `check_unknown_env` fail-closed(컴포넌트 아키텍처 §5.2) | 변수명을 바이블 §6.6 철자로 수정 |
| `app` readiness 120초 초과 | 최초 모델 다운로드(bge-m3 ONNX·mecab-ko-dic) 지연 또는 `HF_HUB_OFFLINE=1`인데 미러 없음 | 로그 확인; 운영은 §6.1 사전 적재 후 `HF_HUB_OFFLINE=1` |
| `worker-cpu` OOMKilled | Docling 프로세스당 약 2GB × `processes` 초과, 스캔 PDF 비율 증가 | `workers.ingestCpu.resources.requests.memory`(12Gi 초안)·`processes` 조정; `maxConcurrentActivities: 1` 유지 |
| Qdrant 메모리 급증 | dense RAM ≈ 벡터 수 × 1024 × 4B × 1.5(양자화 전) | scalar int8 기본 확인(`always_ram`), 원본 `on_disk`; M 규모는 48GB × 2사본(배포 아키텍처 §7.2) |
| OpenSearch 노드 재시작 반복 | JVM 힙 > 32GB 또는 `vm.max_map_count` 미설정 | 힙 ≤ 32GB, 데이터 노드 추가; 커널 파라미터 |
| GPU 미인식: 서빙 파드 `Pending`(`Insufficient nvidia.com/gpu`) | GPU Operator·device plugin 미설치, 노드 라벨·테인트 불일치, MIG 리소스 이름 불일치; MIG 미지원 GPU(L4·T4·A10) 1장에 두 서빙 배치 | `kubectl describe node`의 `Allocatable`; `nodeSelector`·`tolerations`·`gpu.resourceName` 대조; MIG 전략(`single`/`mixed`) 확인; 1장 공유는 2장 전용 또는 MIG(스테이징만 `serving.sharing: time_slicing`) |
| 서빙 파드 CrashLoop: CUDA 오류 | 이미지 CUDA 버전과 노드 드라이버 불일치(TEI CUDA 12.2+, PaddlePaddle 이미지 결합) | 드라이버 호환 매트릭스에 맞는 이미지 digest로 `serving.*.digest`·`sidecars.ocrGpu` 교체 |
| `profile-validate` 훅 실패 `profile.invalid` | `parse.router`에 `SourceFormat` 13값 누락, `ocr.version/model/lang` 누락, `hydrate.top_n < max(rerank.top_n_in, pack.k_max)` | `ProblemDetails.errors[].location.pointer`의 키 수정 |
| 훅 실패 `plugin.license_denied` / DOC·RTF가 `parse.unsupported_format` | C 등급 이미지(`lo-sidecar`·AGPL 사이드카)를 `optIn.*.enabled`·`acknowledgeLicense: true` 없이 프로파일이 참조 / `lo-sidecar` 미설치 | `optIn.loSidecar.enabled: true`(GPL 고지 인지) 또는 라우터에서 제거 |
| HWP 5.0 실패율 증가 + `rag_parser_sidecar_unavailable_total` 증가 | `parser-workers` 다운 또는 NetworkPolicy가 `worker-cpu → parser-workers:8080` 차단 | 사이드카 `GET /healthz`; 정책 확인; 폴백 unhwp → hwp-hwpx-parser는 자동 |
| 검색 응답에 `degraded[{channel.lexical, unavailable}]` | OpenSearch 불가(readiness에는 영향 없음, 설계상 정상 저하) | OpenSearch 복구; `retrieve` "최소 1채널 성공" 규칙 |
| 검색 0건 | 잡 미완료(`is_current=false` 세대만 존재), ACL(`visibility`·`allow_principals`)로 필터, 다른 `collection_id` | `GET /v1/jobs`·`GET /v1/documents/{id}/commits`의 `status=committed`; `explain: true`로 필터 확인 |
| `POST /v1/ingest` 503 + `Retry-After` | Temporal frontend 불가 | Temporal 상태 확인; 잡은 `queued` 유지, 조정 스케줄이 재시작 |
| 모든 질의 429 `api.rate_limited` | Valkey 불가 + 운영 `fail_mode: closed`(정상 설계) | Valkey 복구; 개발만 `open` |
| PG 조회가 0행 | 트랜잭션에 `SET LOCAL app.tenant_id` 없음(RLS fail-closed) | 애플리케이션 경로는 `TenantTx`만 사용; 운영 조회는 `rag_platform_admin` + `app.cross_tenant=on` |
| 수집 잡 `fetch.egress_denied` | 원천이 사설망·메타데이터 IP·비허용 스킴(`http`, `file`) | 운영은 `https/s3/gs/az`만; 사설 원천은 Egress Gateway 뒤 공인 주소 또는 테넌트 `egress_policy` 확장(`deny_cidrs` 축소는 불가) |
| SSE가 60초마다 끊김 / 웹훅 미수신 | 인그레스 읽기 타임아웃 / `webhook_url`이 `EgressPolicy`에 거부·`relay` → Egress Gateway 정책 누락 | SSE·`/mcp` 경로 `proxy-read-timeout 3600`, `proxy-buffering off`, 클라이언트 `Last-Event-ID` 재접속 / `rag_egress_denied_total{component="relay"}` 확인, 수신자 공인 HTTPS 주소 |

---

## 결정 사항 요약

- **결정:** 배포 경로는 프로파일이 결정한다 — `lite`는 `rag up --profile lite [--durable]`(compose), `standard`·`premium`·`korean-gov`는 Helm `rag-platform` + 운영자 제공 데이터 계층. 같은 코어 이미지·같은 프로파일 YAML을 쓴다. ([ADR-0003](../06-adr/0003-orchestrator-neutral-pipeline-and-non-durable-local-runner.md), [ADR-0012](../06-adr/0012-lite-profile-qdrant-only-client-bm25.md))
- **결정:** Kubernetes 설치 순서는 네임스페이스·노드풀 → 데이터 계층 → 시크릿·스토리지클래스 → 모델 미러 → `helm install --atomic`(훅 `models-verify` → `migrate` → `profile-validate` → 릴리스 → `schedules-apply`) → 테넌트·컬렉션 → smoke test로 고정한다. ([ADR-0011](../06-adr/0011-kv-and-object-storage-valkey-rustfs-seaweedfs.md), [ADR-0031](../06-adr/0031-profile-schema-extends-and-quality-gates.md))
- **결정:** Temporal은 `standard` 기본 자체 설치(업스트림 차트, 영속화·가시성 DB는 원장과 다른 PostgreSQL 인스턴스, 네임스페이스 `rag`, `numHistoryShards` 512 초안)이며 기존 클러스터 재사용은 전용 네임스페이스로 허용한다. `start-dev`는 개발 전용, `lite`는 단일 바이너리 + PostgreSQL이다. ([ADR-0003](../06-adr/0003-orchestrator-neutral-pipeline-and-non-durable-local-runner.md))
- **결정:** Qdrant·OpenSearch는 자체·관리형 모두 허용하되 필수 기능 체크리스트(Qdrant 1.19 named vectors·`is_tenant`·alias·gRPC; OpenSearch 3.8 `analysis-nori`·security JWT/DLS·`repository-s3`)를 통과해야 하고, 물리 컬렉션·인덱스 템플릿·alias는 운영자가 아니라 컬렉션 생성 시 어댑터가 정본 JSON으로 만든다. ([ADR-0012](../06-adr/0012-lite-profile-qdrant-only-client-bm25.md), [ADR-0021](../06-adr/0021-korean-analyzer-kiwi-promotion-and-interim-mecab-kss.md), [ADR-0028](../06-adr/0028-tenant-isolation-tiering-policy.md))
- **결정:** 모델·사전·OCR 가중치는 `models.lock` 기반 오브젝트 스토리지 미러에서 파드별 init 컨테이너가 적재하고(Helm 훅은 검증만), 운영은 `HF_HUB_OFFLINE=1`로 런타임 다운로드를 차단한다. 에어갭은 이미지·모델·패키지·차트·인증서 다섯 축의 미러 + `values-airgapped.yaml`이다. ([ADR-0001](../06-adr/0001-license-grade-table-and-d02-interpretation.md), [ADR-0008](../06-adr/0008-ocr-default-rapidocr-ppocrv5-korean.md))
- **결정:** 인그레스는 TLS 종단·경로 라우팅만 하고 인증·레이트리밋·멱등성은 `api`가 소유한다. SSE·`/mcp` 경로는 읽기 타임아웃 3,600s·버퍼링 끔, 본문 상한 8MB, 관리 표면은 `adminHost` + 허용 목록으로 분리한다. ([ADR-0018](../06-adr/0018-api-rest-sse-mcp-no-grpc-rfc9457.md))
- **결정:** 배포 검증은 §7.1 체크리스트와 `smoke-test.sh`를 릴리스 게이트로 삼으며, egress 카나리(`fetch.egress_denied`)와 교차 테넌트 카나리(`plan.collection_forbidden`)를 반드시 포함한다. `api` readiness는 프로파일 캐시 + Qdrant 도달만이며 OpenSearch·PG·Temporal 불가는 저하(`degraded`)·수집 503으로만 나타나야 한다. ([ADR-0038](../06-adr/0038-outbound-egress-policy-and-webhook-signing.md), [ADR-0027](../06-adr/0027-security-context-injection-and-acl-enforcement-points.md), [ADR-0034](../06-adr/0034-retrieval-hot-path-postgres-independence-and-hydrate.md))

## 미해결 이슈

1. **CLI 하위 명령 이름(제안).** `rag ledger migrate`, `rag models mirror|verify|sync`, `rag release bundle|verify`, `rag schedules apply`(배포 아키텍처 미해결 이슈 5)에 이 문서가 `rag tenant create`, `rag api-key create`, `lite` 단일 프로세스의 워커·릴레이 동거 플래그를 더했다. 바이블 §12 `cli/` 행 갱신(patch)과 [CI/CD](../10-development/05-ci-cd.md)·[릴리스 프로세스](../10-development/08-release-process.md) 확정 필요.
2. **테넌트 생성·부트스트랩 경로.** 바이블 §14에 테넌트 생성 엔드포인트가 없다. CLI 전용(`rag_platform_admin` 횡단 모드)으로 둘지 `POST /v1/tenants`를 추가할지 05-api/04에서 확정 후 바이블 §14 minor 개정 여부 결정. 운영 `lite`에서 `rag up`이 첫 테넌트·API 키까지 만들지, `standard`의 카나리 테넌트를 Helm `post-install` 훅으로 자동 생성할지는 [보안과 컴플라이언스](05-security-and-compliance.md)와 합의.
3. **역할별 PostgreSQL DSN.** `Settings`는 `RAG_PG__DSN` 하나인데 마이그레이션(`rag_owner` 소유자 권한)·애플리케이션(`rag_app`)·릴레이·정합성 검사(`rag_maintenance`)는 다른 역할이다. `rag_owner`는 `NOLOGIN`(저장소 아키텍처 §2.4)이므로 마이그레이션 DSN의 로그인 역할과 `rag_owner` 멤버십 부여(§5.1 제안: `rag_platform_admin` + `SET ROLE rag_owner`), 시크릿 키 `dsn_owner`·`dsn_maintenance`(제안), 프로세스별 주입 규칙을 [설정 레퍼런스](02-configuration-reference.md)·컴포넌트 아키텍처 §5.2에서 확정.
4. **컬렉션 생성 요청 본문.** `CollectionSpec` 중 클라이언트가 보내는 부분집합(§5.4 예시)의 스키마와 서버 계산 필드 목록은 05-api/04 확정 대상.
5. **관리형 OpenSearch 적합성.** 3.8 제공 시점, `analysis-nori`, JWT 인증 도메인·DLS, `repository-s3`의 관리형 서비스별 지원은 확인 필요(as of 2026-09). 미충족 시 자체 설치만 허용.
6. **Qdrant 배포 수단.** 공식 Helm 차트 라이선스와 Kubernetes 오퍼레이터(상용 Private Cloud 구성요소 여부), 스냅샷의 S3 호환 저장소 설정은 확인 필요(as of 2026-09).
7. **Temporal 컨테이너 규약.** `lite --durable`의 단일 바이너리 이미지 환경 변수(`DB`, `POSTGRES_SEEDS`, `SKIP_SCHEMA_SETUP`, `NUM_HISTORY_SHARDS`), `temporal-sql-tool` 스키마 디렉터리 경로, 헬스체크용 `temporal` CLI 포함 여부는 1.32 이미지로 확인 필요(as of 2026-09). 확인 후 `rag up`이 렌더하는 compose 정본을 고정.
8. **Kubernetes 하한·CNI.** Kubernetes 최소 버전과 NetworkPolicy `ipBlock.except` 지원 CNI 목록(Cilium FQDN 정책 대안 포함, 배포 아키텍처 미해결 이슈 7)을 확정해 §2.3·§4.2에 기입.
9. **오브젝트 스토리지 택1.** RustFS vs SeaweedFS(ADR-0011 실측) 전까지 compose `objectstore` 서비스와 `rag-platform-data` 서브차트는 플레이스홀더다. S3 포트(9000 vs 8333)·단일 컨테이너 모드·SSE 지원이 택1에 좌우된다.
10. **`lite`의 MCP 인증.** OIDC AS 없는 API 키 모드에서 `/.well-known/oauth-protected-resource`(RFC 9728)와 `/mcp` 인증이 어떻게 동작하는지(D-13은 외부 OIDC AS 전제) [MCP 서버](../05-api/05-mcp-server.md)에서 확정.
11. **GPU 드라이버·CUDA 매트릭스.** vLLM 0.29·TEI 1.9·PaddlePaddle 이미지의 CUDA 요구와 노드 드라이버 조합을 노드풀별로 values에 기록하는 형식(`serving.*.digest` 선택 규칙)은 [확장과 성능](04-scaling-and-performance.md) 실측 후 확정.
12. **smoke test 위치·인증 헤더.** `deploy/scripts/smoke-test.sh`는 바이블 §12 트리(`deploy/{helm,compose}/`)에 없다 — `deploy/scripts/` 추가 patch 요청. API 키 헤더 형식(`Authorization: Bearer` 가정)은 05-api/01 확정 대상.
13. **`models.lock` 항목 크기·저장소.** §6.1 표의 "확인 필요" 크기(gte-multilingual-reranker-base, spaCy `ko_core_news_lg`, GLiNER2, PP-OCRv5 server det·전처리 모델)와 RapidOCR ONNX 변환본의 저장소 id·revision은 10-development/05가 `models.lock`을 확정할 때 채운다.

## 참조

- [설계 브리프](../00-vision/00-design-brief.md) — D-01, D-02, D-08, D-13~D-17, §7 품질 목표, §8 산출물 맵, §9 문서 규약
- [설계 바이블](../02-architecture/00-design-bible.md) — §2.2~§2.3 컨테이너, §3.3 ADR 목록, §4.4 `StagePolicy`, §5.1 계약 인벤토리, §5.4 `IngestRequest`, §5.5 `QueryRequest`, §5.6 `CollectionSpec`·`Profile`, §5.7 열거·이벤트·오류 코드, §6.5 메트릭, §6.6 환경 변수, §6.7 패키지·이미지·엔드포인트, §7 프로파일, §11 오케스트레이션(§11.1 실행기, §11.2 큐, §11.6 개발 모드), §12 패키지 맵, §13 저장소, §14 API 표면, §15 리스크
- [배포 아키텍처](../02-architecture/08-deployment-architecture.md) — §2 프로파일 3종, §3 이미지·모델 캐시, §4 Helm 구조·values·훅, §5 네트워크·인그레스, §6 GPU·서빙, §7 사이징, §8 환경, §9 에어갭, §10 업그레이드
- [저장소 아키텍처](../02-architecture/04-storage-architecture.md) — §2.4 RLS·역할, §2.6 DB 분리, §3 오브젝트 스토리지, §4.2·§4.4·§4.6 Qdrant 컬렉션·payload 인덱스·운영 파라미터, §5.1 OpenSearch 템플릿, §6 Valkey, §9 백업 단위
- [컴포넌트 아키텍처](../02-architecture/02-component-architecture.md) — §5 설정 모델(`Settings`·`RAG_*`)
- [오케스트레이션과 워크플로우](../02-architecture/06-orchestration-and-workflows.md) — §3.6 큐·릴레이, §6.4 아웃박스 릴레이
- [계약 개요](../03-contracts/00-contract-overview.md) — 공통 봉투, `Acl`, `ProblemDetails`, `StageError`
- [프로파일·정책 계약](../03-contracts/15-collection-profile-and-policy-contracts.md) — `CollectionSpec` 필드, §3.9 로딩 검증 규칙, 예시 1
- [기술 선정 요약 및 선정 매트릭스](../07-tech-landscape/00-summary-and-selection-matrix.md) — 프로파일별 기본 조합, 운영·평가 공통 요구
- [오케스트레이션·메시징·API 프레임워크](../07-tech-landscape/08-orchestration-messaging-and-api-frameworks.md) — Temporal 셀프호스팅 의존성·리소스 표, KEDA 스케일러, GPU 공유·device plugin·DRA, TEI CUDA 요구
- [임베딩 모델과 서빙](../07-tech-landscape/05-embedding-models-and-serving.md) — vLLM pooling 진입점, TEI 엔드포인트, VRAM 표
- [벡터·렉시컬 인덱스 백엔드](../07-tech-landscape/06-vector-and-lexical-index-backends.md) — Nori 플러그인 설치 모델, Elasticsearch 이미지 라이선스
- [PDF 파싱·레이아웃·OCR](../07-tech-landscape/02-document-parsing-pdf-layout-ocr.md) — PaddlePaddle CUDA 결합, OCR 컨테이너 리소스
- 운영·개발 문서(작성 예정): [설정 레퍼런스](02-configuration-reference.md), [관측성](03-observability.md), [확장과 성능](04-scaling-and-performance.md), [보안과 컴플라이언스](05-security-and-compliance.md), [런북](06-runbooks.md), [백업과 재해 복구](07-backup-and-disaster-recovery.md), [업그레이드와 마이그레이션](08-upgrade-and-migration.md), [CI/CD](../10-development/05-ci-cd.md), [릴리스 프로세스](../10-development/08-release-process.md), [MCP 서버](../05-api/05-mcp-server.md)
- ADR: [0001](../06-adr/0001-license-grade-table-and-d02-interpretation.md), [0003](../06-adr/0003-orchestrator-neutral-pipeline-and-non-durable-local-runner.md), [0008](../06-adr/0008-ocr-default-rapidocr-ppocrv5-korean.md), [0009](../06-adr/0009-embedding-serving-vllm-pooling-tei-inprocess.md), [0011](../06-adr/0011-kv-and-object-storage-valkey-rustfs-seaweedfs.md), [0012](../06-adr/0012-lite-profile-qdrant-only-client-bm25.md), [0018](../06-adr/0018-api-rest-sse-mcp-no-grpc-rfc9457.md), [0021](../06-adr/0021-korean-analyzer-kiwi-promotion-and-interim-mecab-kss.md), [0027](../06-adr/0027-security-context-injection-and-acl-enforcement-points.md), [0028](../06-adr/0028-tenant-isolation-tiering-policy.md), [0031](../06-adr/0031-profile-schema-extends-and-quality-gates.md), [0034](../06-adr/0034-retrieval-hot-path-postgres-independence-and-hydrate.md), [0038](../06-adr/0038-outbound-egress-policy-and-webhook-signing.md)
