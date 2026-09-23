---
title: "ADR-0009: 임베딩 서빙: vLLM pooling + TEI + 인프로세스, Infinity 제외"
status: accepted
date: 2026-09-22
deciders: architecture
priority: P1
related: ["D-16"]
owner: architecture
version: 0.1.0
last_updated: 2026-09-22
depends_on:
  - ../00-vision/00-design-brief.md
  - ../02-architecture/00-design-bible.md
  - ../07-tech-landscape/00-summary-and-selection-matrix.md
  - ../07-tech-landscape/05-embedding-models-and-serving.md
  - ../07-tech-landscape/08-orchestration-messaging-and-api-frameworks.md
  - ../02-architecture/08-deployment-architecture.md
---

# ADR-0009: 임베딩 서빙: vLLM pooling + TEI + 인프로세스, Infinity 제외

> MADR 형식. 바이블 §3.3 표의 0009행이며 관련 결정은 D-16(브리프 §4 개정 v1.1, 바이블 §3.1 `amended`)이다. 이 ADR은 D-16의 **서빙(serving) 구성**만 다룬다. 같은 D-16의 모델 선택 근거·교체 후보·`late_interaction` 슬롯은 [ADR-0010](./0010-bge-m3-rationale-and-late-interaction-slot.md), sparse 표현은 [ADR-0014](./0014-sparse-representation-bge-m3-lexical-leg-kept.md), 경량 프로파일의 `sparse_bm25`는 [ADR-0012](./0012-lite-profile-qdrant-only-client-bm25.md)가 다룬다. 이 ADR은 바이블의 결정 하나를 근거·대안과 함께 기록하고 바이블 표를 바꾸지 않는다(바이블 §1.1).

## 맥락과 문제

브리프 D-16 원안(v1.0)은 기본 임베딩을 "BGE-M3(dense 1024d + sparse 단일 패스)"로, 서빙을 "TEI 또는 Infinity"로 정했다. 기술 지형 조사([05 임베딩 모델과 서빙](../07-tech-landscape/05-embedding-models-and-serving.md), [08 오케스트레이션·메시징·API](../07-tech-landscape/08-orchestration-messaging-and-api-frameworks.md), [선정 매트릭스](../07-tech-landscape/00-summary-and-selection-matrix.md) "브리프 수정 제안" D-16(서빙) 행)에서 다음 사실이 확정되었다.

| # | 사실 | 출처 |
|---|------|------|
| F1 | Text Embeddings Inference(TEI) v1.9.4(Apache-2.0)는 BGE-M3 dense·리랭커는 서빙하지만, `/embed_sparse`는 BERT/DistilBERT MaskedLM SPLADE 풀링 전용이고 `/embed_all`은 풀링 전 토큰 벡터라 colbert 선형층이 적용되지 않는다. 즉 TEI로는 **BGE-M3 sparse를 생산할 수 없다** | 05 §서빙 스택·§서빙 스택 비교, 매트릭스 `embedding_server` 행 |
| F2 | Infinity(`infinity-emb`, MIT)는 README 테스트 모델 목록에 "BAAI/bge-m3, no sparse"를 명시하고, 최종 릴리스 0.0.77(2025-08-22)·최종 커밋 2026-03-24로 릴리스가 정체되어 있다 | 05 §서빙 스택, §실패 모드 "Infinity 유지보수 정지", 매트릭스 D-16(서빙) 행 |
| F3 | vLLM 0.29.0(Apache-2.0) `--runner pooling`은 `BgeM3EmbeddingModel`로 `embed`(dense)/`token_classify`(sparse)/`token_embed`(colbert) 태스크를 제공하고, `bge_m3_sparse_plugin` IO 프로세서로 dense와 sparse를 **단일 응답**으로 돌려준다. 05 문서는 이를 "BGE-M3 3-in-1을 서버로 제공하는 유일한 검증 경로"로 판정했다 | 05 §서빙 스택, §BGE-M3 심층 비교 |
| F4 | `lite`는 단일 노드·GPU 0·사이드카 0·컨테이너 5이며, 개발 모드는 `rag up --profile lite`가 bge-m3 ONNX int8을 내려받아 `LocalRunner` 인프로세스로 동작한다. sentence-transformers v6.1.0은 ONNX/OpenVINO 백엔드(dense CPU 약 2.5배)를, FlagEmbedding 1.4.2는 BGE-M3 sparse의 참조 구현을 제공한다 | 바이블 §7.1·§11.6, 05 §서빙 스택 |
| F5 | 서빙 스택 간 fp16/bf16·Flash Attention 차이로 같은 모델의 벡터가 약 1e-3 수준으로 달라져 비트 단위 동일성은 보장되지 않는다. 05·매트릭스는 "같은 space 내 서빙 스택 교체는 코사인 ≥ 0.9999 동등성 게이트 필수"로 정리했다 | 05 §어댑터 계약 "결정성"·§실패 모드, 매트릭스 "어댑터·플러그인 공통 요구" 2 |
| F6 | 임베딩 프롬프트 불일치(색인 시 없음·질의 시 있음)가 가장 흔한 품질 사고이며, 프롬프트는 어댑터가 소유하고 `prompt_hash`가 벡터 공간을 정의해야 한다 | 05 §어댑터 계약 `mode`·§실패 모드, 매트릭스 공통 요구 4, 바이블 §2.3 `embedding-server` "프롬프트는 어댑터가 소유" |

문제: D-16의 "dense + sparse 단일 패스" 기본값을 D-16의 서빙 선택으로는 실현할 수 없다(F1·F2). 어떤 서빙 스택 조합으로 BGE-M3 3-in-1을 프로파일 계층(`lite`/`standard`/`premium`/`korean-gov`) 전체에서 제공하고, 스택 교체·프롬프트·캐시가 재현성(원칙 4)을 깨지 않도록 어떤 계약 장치로 강제하는가.

## 결정 동인(decision drivers)

| ID | 동인 | 내용 | 근거 |
|----|------|------|------|
| DR1 | 실현 가능성 | BGE-M3 dense + `sparse_learned`(`vocab_id=xlm-roberta-250k`)를 **한 번의 호출**로 생산하는 서버 경로가 기본 프로파일에 있어야 한다 | D-16, O-02(바이블 §3.2, ADR-0014) |
| DR2 | 프로파일 계층 | `lite`는 GPU 0·사이드카 0이므로 인프로세스가 필수, `standard` 이상은 GPU 1로 서버형 | 바이블 §7.1 인프라 행, §11.6 |
| DR3 | 재현성 | 서빙 이미지 digest가 `embedder_fingerprint`에, 프롬프트·양자화가 `embedding_space_id`에 들어가고, 같은 공간 내 교체는 동등성 게이트를 통과해야 한다 | 원칙 4, 바이블 §4.1 지문·§6.2, §15 리스크 #8 |
| DR4 | 라이선스 | 코어·기본 프로파일의 서빙 스택과 인프로세스 의존성은 A 등급(Apache-2.0/MIT)만 | D-02(개정 v1.1), ADR-0001 |
| DR5 | 운영 스택 수 | dense 전용 모델(TEI 지원 아키텍처면 인코더·디코더 불문, D-16 문구 "TEI(dense 전용 모델·리랭커)")과 크로스인코더 리랭커는 한 이미지 계열(TEI)로, BGE-M3 3-in-1과 TEI 미지원 디코더 **리랭커**(Qwen3-Reranker)는 LLM 서빙과 같은 스택(vLLM/SGLang)으로 묶어 운영 스택을 늘리지 않는다 | 08 §모델 서빙 인프라, 바이블 §2.2 `embedding-server`·`reranker-server`, §7.1 리랭커 행 |
| DR6 | 유지보수 | 활발한 릴리스와 pin-and-bump 가능성. 릴리스 정체 스택은 기본 목록에 두지 않는다 | 매트릭스 공통 요구 3, 바이블 §15 리스크 #9 |
| DR7 | 어댑터 소유권 | 프롬프트·`mode`·정규화·절단은 호출자가 아닌 `embedder` 어댑터가 소유하고, 공간 불일치는 비재시도 오류로 드러낸다 | 매트릭스 공통 요구 4·5, 바이블 §4.2 `embed` 행 |

## 고려한 대안

| 대안 | BGE-M3 dense | BGE-M3 sparse | 리랭커 | 유지보수(2026-09) | 라이선스(등급) | 판정 |
|------|:-:|:-:|:-:|------|------|------|
| A1 TEI 단독(브리프 원안 일부) | O | **X** | O(`/rerank`) | 활발(v1.9.4, 2026-09-15) | Apache-2.0(A) | **기각**(DR1) — dense 전용 모델·리랭커 역할로만 채택 |
| A2 Infinity(브리프 원안 일부) | O | **X** | O | 정지(최종 릴리스 2025-08-22) | MIT(A) | **기각·제외**(DR1·DR6) |
| A3 vLLM pooling(3-in-1) + TEI(dense 전용·리랭커) + 인프로세스(개발·`lite`) | O | O | O(TEI) | 활발(vLLM v0.29.0 2026-09-09) | Apache-2.0(A) | **채택** |
| A4 전 프로파일 인프로세스(FlagEmbedding/sentence-transformers) | O | O | O(`CrossEncoder`) | 활발(v6.1.0) | Apache-2.0·MIT(A) | 기각(기본) — `lite`·개발에서만 |
| A5 vLLM 단독(리랭커·dense 전용도 vLLM) | O | O | O(`/score`·`/rerank`) | 활발 | Apache-2.0(A) | 기각(기본) — `premium` 디코더 리랭커에서만 |
| A6 커스텀 서버(BentoML/LitServe + FlagEmbedding) | O | O | O | — | Apache-2.0·MIT(A) | 기각 — 폴백 후보로만 |
| A7 SGLang / Ollama / OVMS / Triton / Xinference | O | X 또는 확인 필요 | 일부 | 활발 | Apache-2.0·MIT·BSD-3(A) | 기각 — 조건부 대안으로만 |

- **A1 TEI 단독(바이블이 기각한 원안).** 설명: 브리프 v1.0의 "TEI 또는 Infinity" 중 TEI만으로 임베딩·리랭킹을 서빙한다. 장점: Rust/Candle 고성능, 가장 넓은 GPU 매트릭스(T4~Blackwell·ROCm·ARM64), 동적 배칭, Prometheus 메트릭, `dimensions`(MRL) 지원(05 §서빙 스택). 단점: F1대로 BGE-M3 sparse·colbert를 만들 수 없어 D-16의 dense+sparse 기본값이 실현 불가다. sparse를 위해 두 번째 인코더를 상시 운용하면 O-02 "추가 비용 0" 근거가 사라진다. 따라서 TEI는 **dense 전용 모델(`ko-quality` KURE-v1 등)과 크로스인코더 리랭커**의 1차 스택으로만 채택한다.
- **A2 Infinity(바이블이 기각한 원안).** 설명: `infinity-emb` OpenAI 호환 서버. 장점: 임베딩·리랭크·CLIP·ColBERT·ColPali 등 모델 유형이 넓고 MIT다. 단점: F2대로 BGE-M3 sparse 미지원이 README에 명시되어 있고 13개월 이상 릴리스가 없어 보안 패치 부재 위험이 있다(05 §실패 모드). 라이선스가 아니라 **능력·유지보수 사유**로 기본 목록에서 제외한다. 바이블 §15 리스크 #2의 라이선스 지뢰 목록에 Infinity가 포함되어 있으나 라이선스는 MIT(A)이며, 제외 사유인 "정체"의 근거는 매트릭스 종합 리스크 #2("AGPL/GPL/비상업/정체")와 05 §실패 모드 "Infinity 유지보수 정지"다.
- **A3 vLLM pooling + TEI + 인프로세스(채택).** 설명: 3-in-1이 필요한 BGE-M3는 vLLM `--runner pooling`(`embedding-server`), dense 전용 모델과 리랭커는 TEI(`reranker-server` 등), 개발·`lite`는 인프로세스로 나눈다. 장점: F3대로 dense+sparse를 단일 응답으로 받고, vLLM은 LLM 서빙·`premium` 디코더 리랭커(Qwen3-Reranker-4B)와 같은 스택이며(DR5), ColQwen3 계열은 vLLM 네이티브이고 한국어 ModernBERT ColBERT(KURE-v2)는 `token_embed` 서빙 실측 확인 필요(as of 2026-09; 05 미해결 이슈 17, ADR-0010 범위)다. 세 경로 모두 A 등급이고 릴리스가 활발하다. 단점: 스택 3종의 어댑터를 유지해야 하고, vLLM은 소형 인코더에 무거우며(메모리 사전 할당, 잦은 버전 변동) `--hf-overrides`·플러그인 인터페이스 변동 리스크가 있다(05 §리스크).
- **A4 전 프로파일 인프로세스(기각).** 설명: 워커 프로세스 안에서 FlagEmbedding `BGEM3FlagModel` 또는 sentence-transformers로 직접 인코딩한다. 장점: 어댑터 작성 최단 경로, sparse 참조 구현(정답 기준) 그대로 사용, 컨테이너 0개 추가. 단점: "서버가 아님(배칭·큐 자체 구현 필요)"(05 §서빙 스택), 큐별 워커 프로세스가 각각 모델을 적재하고 GPU를 나눠 쓰며, 질의 임베딩이 `api` 프로세스에 GPU를 요구한다. `standard` 멀티테넌트 처리량에는 부적합하므로 `lite`·개발(`LocalRunner`)에서만 채택하고, FlagEmbedding은 vLLM sparse 출력의 골든 기준·폴백으로 유지한다. 평가 하네스는 실행 셸만 `LocalRunner`이고 임베더는 평가 대상 프로파일이 바인딩한 플러그인을 그대로 쓴다(브리프 D-12 "프로덕션과 동일한 인프로세스 스테이지", 바이블 §2.3 `eval harness` "동일 스테이지 실행", §11.1) — 하네스 자체가 인프로세스 임베딩 경로를 고르는 것이 아니다.
- **A5 vLLM 단독(기각).** 설명: 리랭커·dense 전용 모델까지 vLLM `/score`·`/rerank`·`/v1/embeddings`로 통일한다. 장점: 스택 1종. 단점: 568M급 XLM-R 인코더·크로스인코더에 vLLM은 과하고, TEI가 리랭커(`bge-reranker-v2-m3`, `gte-multilingual-reranker-base` CPU)에 더 가볍다(매트릭스 `reranker` 행). `premium`의 Qwen3-Reranker-4B는 TEI 미지원이라 vLLM/SGLang을 쓰며(바이블 §7.1), 이는 `RerankBackend` 열거(`tei, vllm, sglang, …`)로 이미 표현된다.
- **A6 커스텀 서버(기각).** 설명: BentoML/LitServe로 FlagEmbedding을 감싼 자체 3-in-1 서버. 장점: 참조 구현과 수치 동일. 단점: 배칭·헬스·메트릭·GPU 스케줄링을 직접 유지하는 Not-Invented-Here(브리프 R2)이며 08 문서는 "커스텀 임베더" 용도로만 분류한다. vLLM pooling API가 연속 파손될 때의 폴백 후보로만 남긴다(재검토 조건 3).
- **A7 SGLang / Ollama / OVMS / Triton / Xinference(기각).** 설명: 기타 서버형 스택. 장점: SGLang은 LLM 스택을 SGLang으로 통일한 환경의 vLLM 대안, Ollama는 개발자 로컬 환경 최단 경로, OpenVINO Model Server는 GPU 없는 `lite`의 서버형 1차 후보, Triton은 멀티 프레임워크 백엔드·동적 배칭·다중 모델 동시 서빙, Xinference는 임베더+리랭커+LLM을 OpenAI 호환 API 한 서버로 묶어 컨테이너 수를 줄인다(05 §서빙 스택, 08 §E 모델 서빙 인프라). 단점: SGLang·Ollama는 BGE-M3 dense만(3-in-1 미지원), OpenVINO Model Server는 Intel 하드웨어 편중·IR 변환 필요(GPU 없는 `lite`의 서버형 대안 후보로만), Triton은 모델 리포지토리 변환 부담, Xinference는 sparse/colbert 노출 여부 "확인 필요(as of 2026-09)"(05 §서빙 스택, 08 §E 모델 서빙 인프라).

## 결정

**결정:** 브리프 D-16(개정 v1.1)의 서빙 항목 그대로 — "서빙은 **vLLM pooling(BGE-M3 3-in-1) + TEI(dense 전용 모델·리랭커) + 인프로세스(개발·lite)**(Infinity는 sparse 미지원·릴리스 정체로 제외; 같은 공간 내 서빙 교체는 코사인 ≥0.9999 동등성 게이트)". 바이블 §3.1 D-16 요지는 "서빙 **vLLM pooling + TEI + 인프로세스**(Infinity 제외)"이고, 프로파일 정본(바이블 §7.1 "임베딩·서빙" 행)은 `lite` = "bge-m3 dense ONNX int8 in_process + `sparse_bm25`(형태소 + TF 포화)", `standard` = "bge-m3 dense+sparse @ vLLM 0.29 pooling", `premium` = "`ko-quality`(KURE-v1 + PIXIE-Splade-v1.5) 또는 `quality-max`(Qwen3-Embedding-4B MRL 1024); `late_interaction` KURE-v2(M2)", `korean-gov` = "standard; 가중치·LICENSE 자체 미러링 필수"다. 컨테이너 책임(바이블 §2.3)은 `embedding-server` = "BGE-M3 3-in-1(vLLM pooling); 프롬프트는 어댑터가 소유"(격리 sidecar, `lite`는 sentence-transformers ONNX int8 인프로세스), `reranker-server` = "크로스인코더(TEI), TEI/Cohere 응답 스키마 2종"(`lite`는 TEI CPU 또는 생략)이다.

| 역할 | 프로파일 | 컨테이너·스택(버전은 07 문서 확인일 기준, 잠금 파일·이미지 digest가 정본) | `plugin_id`(바이블 §6.1·§12) | 격리(§4.2) | 엔드포인트(§2.2) | 산출(§5.4 `VectorBundle`) |
|------|----------|------|------|------|------|------|
| BGE-M3 3-in-1 | `standard`, `korean-gov`(`premium`은 `standard` 상속분; `ko-quality`·`quality-max` 선택 시 아래 dense 전용 행 + learned sparse 인코더 행) | `embedding-server`: vLLM 0.29 `--runner pooling`(`BgeM3EmbeddingModel` + `bge_m3_sparse_plugin`), K8s Deployment + KEDA(Prometheus 스케일러) | `embedder.vllm_pooling_bge_m3` | `sidecar`(외부 HTTP; `Producer.image_digest` 필수) | `POST /pooling`(수집 `embed`·질의 임베딩 공통) | `dense`(1024, L2 정규화, `pooling=cls`) + `sparse_learned`(`vocab_id=xlm-roberta-250k`) |
| dense 전용 모델 | `premium` `ko-quality`(KURE-v1, XLM-R 인코더)·`quality-max`(Qwen3-Embedding-4B, 디코더; TEI는 Qwen3 아키텍처 0.6B/4B/8B를 지원 목록에 등재, 05 §Qwen3-Embedding) 등 A/B 등급 교체 후보(ADR-0010). D-16 문구 "TEI(dense 전용 모델)"대로 1차는 TEI이며, 같은 모델을 vLLM `/v1/embeddings`로 서빙하는 것은 같은 공간 내 스택 선택(규칙 2·3) | TEI 1.9(`ghcr.io/huggingface/text-embeddings-inference:<tag>-1.9`; GPU 태그 `86`/`89`/`hopper`, CPU `cpu`) | `embedder.tei_dense` | `sidecar` | `POST /embed` | `dense`(모델 차원; MRL 절단 포함; 프롬프트는 어댑터가 부착 — Qwen3 인스트럭션 문자열은 프로파일 고정, `prompt_hash`에 반영) |
| learned sparse 인코더(dense 전용 모델과 짝) | `premium` `ko-quality`(PIXIE-Splade-v1.5; 8192 토큰 필요 시 splade-ko-v1 동일 어휘) — 바이블 §7.1 `premium` 행·§3.2 O-02, ADR-0014 "서빙 세부는 ADR-0009" | `sparse-encoder-server`: sentence-transformers `SparseEncoder.encode_query/encode_document` 래퍼 서빙 Deployment(02-architecture/08 §6.3 (d)·§3.1 이미지 표; 149M·약 0.3GB라 CPU 변형 가능). TEI `/embed_sparse`는 BERT/DistilBERT MaskedLM 전용이라 ModernBERT SPLADE 지원은 확인 필요(as of 2026-09; 05 미해결 이슈 2) — 확인되면 TEI로 대체 검토. 이 행은 ADR-0014·02-architecture/08·04-pipelines/12가 이미 쓰는 경로의 기록이며 새 결정이 아니다 | 미정 — 바이블 §12 `adapters/embed` 목록에 없음(04-pipelines/12 미해결 이슈 5의 제안 `embedder.sparse_encoder_splade`) | `sidecar`(`Producer.image_digest` 필수) | 제안 `POST /v1/embed_sparse {texts, mode}`(04-pipelines/12 §4.1; 03-contracts/16과 합의 후 확정) | `sparse_learned`(`vocab_id=ax-encoder-50k`) |
| 크로스인코더 리랭커 | `standard`·`korean-gov`: bge-reranker-v2-m3 GPU(100→20); `lite`: gte-multilingual-reranker-base CPU(30→10) 또는 생략 | `reranker-server`: TEI | `reranker.tei_cross_encoder`(`rerank.backend=tei`, `response_schema=tei`; Cohere 스키마 병행 파싱) | `sidecar` | `POST /rerank` | `RankedSet(stage=reranked)` |
| 인프로세스 | `lite`, 개발(`rag up --profile lite` + `LocalRunner`). 평가 하네스는 실행 셸만 `LocalRunner`이며 임베더는 평가 대상 프로파일의 바인딩을 그대로 쓴다(`standard` → `embedder.vllm_pooling_bge_m3`, `lite` → 이 행; 브리프 D-12, 바이블 §2.3 `eval harness`, §11.1) | sentence-transformers `>=6.0` ONNX int8(bge-m3 dense) + 플랫폼 `sparse_bm25`(ADR-0012); FlagEmbedding 1.4.x는 sparse 참조 구현·폴백 | `embedder.inprocess_sentence_transformers`, `embedder.sparse_bm25` | `in_process`(`image_digest = null`) | 없음 | `dense` + `sparse_bm25`(`vocab_id = analyzer_id`) |
| 제외 | 전 프로파일 | Infinity(`infinity-emb`) — 코어 의존성·entry point·프로파일 예시에 두지 않음 | 없음 | — | — | — |

D-16의 세 경로(vLLM pooling·TEI·인프로세스)와 `ko-quality` 한정 sparse 인코더 경로는 같은 `embedder` 계약으로 수렴하며 다음 규칙은 바이블 정본을 그대로 적용한다.

1. **지문**: `embedder_fingerprint = H("embedder", plugin_id, plugin_version, config_hash, image_digest or "", embedding_profile_hash)`(§6.2). `EmbeddedChunkSet.embedder_fingerprint`는 "서빙 스택 이미지 digest 포함"(§5.4)이며 SDK가 `fingerprint()`에 image digest·`embedding_space_id` 포함을 검증한다(§4.1).
2. **공간**: `embedding_space_id = H("space", model_id, revision, str(dim), str(normalized), prompt_hash, quantization, vocab_id or "")`(§6.2). 서빙 스택 이름은 공간 식에 들어가지 않으므로 같은 모델·프롬프트·양자화면 스택이 달라도 같은 공간이다. `vocab_id`·공간 불일치는 색인·질의 모두 `embed.space_mismatch`(비재시도, §5.7).
3. **동등성 게이트**: 같은 `embedding_space_id` 안에서 서빙 스택이나 이미지 digest를 바꿀 때는 프로파일 `ingest.embed.equivalence_gate: {cosine_min: 0.9999, sample: 1000}`(§7.3)을 통과해야 전환한다. 통과하지 못하면 **전환을 차단**한다. 게이트 실패만으로는 새 `embedding_space_id`가 생기지 않는다(규칙 2 — 서빙 스택·이미지 digest는 공간 식의 성분이 아니다). 그래도 신 스택으로 가야 하면 (a) 신 스택의 모델 출력 양자화가 달라진 경우(예: fp16 → int8)는 프로파일의 dense 설정 변경이 `quantization` 성분을 바꿔 자연히 새 공간이 되므로 컬렉션 blue/green 재색인이다(§6.2, §7.4; fp16 ↔ bf16은 `quantization = none`으로 같은 공간); (b) 같은 양자화면 `embedding_space_id`가 같아 청크 캐시 `H("embed", embedding_space_id, "document", embed_text)`가 구 스택 벡터를 그대로 적중하므로, 전환 전 `rag cache invalidate --stage embed`(§15 리스크 #8)로 테넌트 청크 캐시를 비운 뒤 신 이미지로 전량 재계산하고 컬렉션 blue/green으로 교체한다. 캐시 키에 스택 식별자를 넣을지는 [03-contracts/07](../03-contracts/07-embedded-chunk-set-and-index-record.md)·[04-pipelines/12](../04-pipelines/12-embedding.md)의 미해결 이슈로 위임한다.
4. **프롬프트·모드**: 프롬프트는 어댑터가 소유하고 호출자는 원문만 전달한다. `EmbeddedChunkSet.mode`는 `document`(스키마 `const`), 질의 측은 `query`(`EmbeddingMode`, §5.7). `prompt_hash`가 공간에 포함되므로 프롬프트 변경은 공간 변경이다.
5. **캐시**: 청크 단위 `H("embed", embedding_space_id, "document", embed_text)`(봉투 없음, 테넌트 내 공유, §4.1·§6.2), 세트 단위 `stage_key = H("stage", "embed", scope_key, enriched.blake3, fingerprint)`; 질의 임베딩은 Valkey `qemb:{embedding_space_id}:{H(normalized_query)}` 24h(§4.3·§13.4).
6. **실패 정책**(§4.2·§4.4·§5.7): `embed.server_unavailable` 재시도(최대 간격 5m), `embed.token_overflow` truncate + 경고, `embed.space_mismatch`·`embed.tokenizer_missing` 비재시도; 큐 `ingest-gpu-embed`, `start_to_close` 20m, 하트비트 60s, 5회, `Resumable`(`heartbeat_details.batch_offset`).
7. **배치 상한**: `ingest.embed.batch_max_tokens`(§7.2: `lite` 8,192 / `standard` 32,768 / `premium` 65,536 / `korean-gov` 32,768, 초안 목표)를 vLLM `max_num_batched_tokens`·TEI `--max-batch-tokens`와 정합시킨다(05 §BGE-M3 함정 (3)). 질의 임베딩 지연 예산은 `standard` 40ms(미스), `lite` ONNX int8 약 150ms(§8.3, 초안).

```mermaid
flowchart LR
    IN["EnrichedChunkSet.enrichments[*].embed_text<br/>QueryPlan.dense_query_text"] --> AD["embedder 어댑터<br/>프롬프트·mode·정규화·절단 소유<br/>캐시 H(embed, embedding_space_id, document, embed_text)"]
    AD -->|standard · korean-gov · premium(standard 상속분)| V["embedding-server<br/>vLLM 0.29 --runner pooling · POST /pooling<br/>embedder.vllm_pooling_bge_m3 · sidecar"]
    AD -->|premium ko-quality · quality-max dense| T["TEI 1.9 · POST /embed<br/>embedder.tei_dense · sidecar"]
    AD -->|premium ko-quality sparse| S["sparse-encoder-server<br/>SparseEncoder(PIXIE-Splade-v1.5) · sidecar<br/>plugin_id 미정 · TEI /embed_sparse 확인 필요"]
    AD -->|lite · LocalRunner 개발| P["sentence-transformers ONNX int8<br/>embedder.inprocess_sentence_transformers · in_process<br/>+ embedder.sparse_bm25"]
    V --> O["EmbeddedChunkSet.vectors<br/>dense 1024 + sparse_learned(xlm-roberta-250k)"]
    T --> O2["dense"]
    S --> O4["sparse_learned(ax-encoder-50k)"]
    P --> O3["dense + sparse_bm25(analyzer_id)"]
    RS["RankedSet(fused, hydrated)"] --> RR["reranker-server<br/>TEI · POST /rerank<br/>reranker.tei_cross_encoder"]
```

## 결과

**긍정**

- D-16의 "dense + sparse 단일 패스"가 서버 경로에서 실현되고, learned sparse를 위한 두 번째 인코더 상시 운용 비용이 기본 프로파일에서 사라진다(O-02 "추가 비용 0" 유지).
- 세 경로가 같은 `EmbeddedChunkSet`·`VectorBundle` 계약으로 수렴하므로 `index`·`retrieve`·`hydrate` 코드 경로가 하나다. 프로파일 승격은 `embed.dense.plugin` 값 변경과 재색인으로 끝난다.
- 서빙 스택·인프로세스 의존성이 모두 A 등급이라 Apache-2.0 채택성(바이블 §15 리스크 #2)이 보호된다.
- 운영 스택이 vLLM(BGE-M3 3-in-1; `premium` 디코더 리랭커 Qwen3-Reranker는 vLLM/SGLang, LLM 서빙과 공유)과 TEI(dense 전용 모델·크로스인코더 리랭커) 2종으로 정리된다(DR5). `ko-quality` 선택 시에만 `sparse-encoder-server`가 추가된다(엔진 확정은 05 미해결 이슈 2 이후).
- 이미지 digest 지문 + 동등성 게이트로 스택 교체가 무중단·재현 가능해진다(원칙 4, §15 리스크 #8).
- `lite` 5분 기동(§11.6)이 유지된다.

**부정**

- 어댑터 3종(`vllm_pooling_bge_m3`, `tei_dense`, `inprocess_sentence_transformers`; `ko-quality` 선택 시 sparse 인코더 어댑터 1종 추가)을 유지해야 하고, vLLM은 릴리스 주기가 빨라 pooling API 변동이 어댑터를 깰 수 있다(§15 리스크 #9). `uv lock --check`와 계약 테스트 코퍼스로 pin-and-bump한다.
- vLLM은 568M급 인코더에 무겁고(메모리 사전 할당) GPU 1장을 전제한다. 8192 토큰 배치는 활성화 메모리가 급증하므로 배치 토큰 상한 정합이 운영 필수 항목이다.
- 인프로세스 경로는 배칭·큐가 없고 워커 프로세스마다 모델을 적재한다. bge-m3 ONNX int8의 한국어 품질 손실은 미측정이다(05 미해결 이슈 3).
- vLLM `token_classify` sparse 출력이 FlagEmbedding `lexical_weights`와 수치적으로 동일한지(특수 토큰 제거·max 집계)는 골든 테스트로 확인해야 한다(05 미해결 이슈 1).

**중립**

- `lite`(ONNX int8)와 `standard`(vLLM fp16)는 §6.2 식의 `quantization`이 다르므로 다른 `embedding_space_id`다. 따라서 `lite → standard` 승격은 동등성 게이트 대상이 아니라 컬렉션 blue/green 재색인이며, ONNX int8이 `quantization` 값으로 어떻게 표기되는지는 [03-contracts/07](../03-contracts/07-embedded-chunk-set-and-index-record.md)·[04-pipelines/12](../04-pipelines/12-embedding.md)가 확정한다.
- 리랭커 서빙 백엔드(`tei` 기본, `premium`은 `vllm`/`sglang`)는 `RerankBackend` 열거로 이미 표현되며 이 ADR은 열거를 바꾸지 않는다. late interaction 서빙(vLLM `token_embed`/PyLate)은 ADR-0010 범위다.
- `quality-max`(Qwen3-Embedding-4B)의 1차 스택은 D-16 문구대로 TEI다. [02-architecture/08](../02-architecture/08-deployment-architecture.md) §6.3 표와 [04-pipelines/12](../04-pipelines/12-embedding.md)가 이를 vLLM에 배치한 것은 같은 모델·같은 공간 안의 서빙 스택 선택이라 규칙 2·3(동등성 게이트)의 적용 대상이며, 두 문서와 이 표의 정합은 해당 문서 개정 사항이다. last-token 풀링을 `Pooling{cls, mean, late}`로 표현하는 문제는 04-pipelines/12 미해결 이슈다.
- `ko-quality`의 learned sparse 서빙 경로(`sparse-encoder-server`)는 `plugin_id`·엔드포인트가 바이블 §12·§14에 없어 이 ADR은 이미 하위 문서가 쓰는 경로를 기록만 한다. 확정은 04-pipelines/12 미해결 이슈 5·03-contracts/16(사이드카 계약)·02-architecture/08 미해결 이슈 17에서 한다.
- 배포 형태(개발 Docker Compose, `standard` K8s Deployment + KEDA Prometheus 스케일러, 대량 초기 색인만 Ray Data)는 08 문서 판정을 따르며 세부는 [02-architecture/08](../02-architecture/08-deployment-architecture.md)이 정한다.
- Infinity 제외는 라이선스 사유가 아니므로 D-02 등급표(ADR-0001)에 영향이 없다.

## 준수 확인 방법

| 게이트 | 강제 내용 | 정의 위치 |
|--------|-----------|-----------|
| `rag profile validate` (2)·(4)·(8) | `embed.dense`·`embed.sparse`에 바인딩된 플러그인의 `capabilities()`가 요구 벡터(dense/sparse)를 선언해야 한다 — `embedder.tei_dense`를 `sparse` 슬롯에 두면 `plugin.capability_unsupported`; `chunk.tokenizer`는 임베딩 모델 토크나이저(`hf:BAAI/bge-m3`)와 일치; `embedding_space_ids` 재계산 불일치는 `profile.invalid`. 임베더 전용 능력 필드(dense/sparse/multivector, `max_input_tokens`, `requires_instruction`)는 `Capabilities.extra`에 두며 필드 정본은 03-contracts/00 U-7·03-contracts/15(`EmbedderCapabilities` 제안)가 확정한다 | 바이블 §7.4, §5.3 `Capabilities`, 매트릭스 공통 요구 5 |
| SDK 지문 검증 | `fingerprint()`가 외부 HTTP·`sidecar` 경로에서 `image_digest`(`sha256:…`)를, 모든 경로에서 `embedding_space_id`를 포함하지 않으면 플러그인 로드 거부. `latest`·`main` 태그 금지 | 바이블 §4.1·§6.2, 05 §캐싱과 버전 고정 |
| 동등성 게이트 | 같은 `embedding_space_id` 내 서빙 스택·이미지 digest 변경 배포 전, 하네스가 골든 샘플 1,000개의 신·구 벡터 코사인 최솟값 ≥ 0.9999를 확인한다. 실패 시 배포 차단. 그래도 전환하려면 규칙 3의 (a) 양자화 변경 → 새 공간 blue/green 또는 (b) 같은 양자화 → `rag cache invalidate --stage embed` 후 전량 재계산 + blue/green 절차만 허용하며, 캐시 무효화 없는 재색인은 신·구 스택 벡터가 한 인덱스에 섞이므로 금지한다(§15 리스크 #8). `equivalence_gate` 값은 §7.4 게이트 규칙에 따라 ADR 없이 바꿀 수 없다 | 바이블 §7.3 `ingest.embed.equivalence_gate`, §7.4; [04-pipelines/12](../04-pipelines/12-embedding.md), [10-development/05](../10-development/05-ci-cd.md) |
| 열거·오류 코드 CI 대조 | `Pooling{cls, mean, late}`, `EmbeddingMode{document, query}`(`EmbeddedChunkSet.mode`는 `const document`), `VectorName`, `RerankBackend`, `embed.*` 오류 코드가 `schemas/*.schema.json`과 §5.7 표에서 일치 | 바이블 §1.2, §5.7 |
| 적합성 키트(`contract_roundtrip`·`idempotency`) | 세 임베더 플러그인 공통: `mode = document`, `dense.dim`이 프로파일 `dim`과 일치·L2 정규화, `sparse_learned.vocab_id = xlm-roberta-250k`(3-in-1), `embed_text_hash` 재계산 일치, `truncated` 플래그, 동일 `embed_text`·동일 공간 → `cache_hits` 증가. `embedder.vllm_pooling_bge_m3`는 추가로 FlagEmbedding `lexical_weights`와의 sparse 골든 테스트 통과 | 바이블 §12 `testing/`, 05 미해결 이슈 1, [03-contracts/07](../03-contracts/07-embedded-chunk-set-and-index-record.md) |
| 의존성·라이선스 게이트 | `uv lock --check`; 코어 `pyproject.toml`·`uv.lock`에 `infinity-emb` 미포함(잠금 diff 검사); `PluginMeta.license_grade = A`; 서빙 이미지는 SBOM에 digest로 기록; 모델은 `models.lock`(id, revision, sha256, license, grade, territory) + 가중치·LICENSE 미러링 | ADR-0001, 매트릭스 `license_scanner` 행, 바이블 §7.1 `korean-gov` |
| 코드 리뷰 체크리스트 | (a) 프롬프트를 호출자가 아닌 어댑터가 부착하고 `prompt_hash`를 산출 (b) `vocab_id`·공간 불일치 → `embed.space_mismatch`(비재시도) (c) `embed.token_overflow`는 truncate + `Warning` (d) `batch_max_tokens` ↔ vLLM `max_num_batched_tokens`/TEI `--max-batch-tokens` 정합 (e) `heartbeat_details.batch_offset`로 `Resumable` (f) dense L2 정규화는 어댑터 책임 (g) Valkey `qemb:` 키에 `embedding_space_id` 포함 (h) 인프로세스 경로는 `image_digest = null`이므로 ONNX 산출물 해시·런타임 버전을 `config_hash`에 포함 — 바이블 §4.1 "SDK가 image digest 포함을 검증"의 인프로세스 대응으로 해석한 **제안**이며 정본 위치는 04-pipelines/12가 확정(§15 리스크 #8 "지문 누락 시 낡은 산출물 재사용") (i) 동등성 게이트 실패 배포는 `rag cache invalidate --stage embed` 없이 재색인 금지(규칙 3) | [10-development/07](../10-development/07-contributing.md), [04-pipelines/12](../04-pipelines/12-embedding.md) |

3-in-1 플러그인의 `PluginMeta`(바이블 §5.6 필드, 값은 예시; 이미지 참조는 배포 문서가 확정). `capabilities.extra`는 위 `rag profile validate` (2) 게이트가 요구하는 임베더 전용 능력 선언의 **제안 표기**이며 필드 정본은 03-contracts/00 U-7·03-contracts/15(`EmbedderCapabilities` `$defs` 제안)가 확정한다 — 그때까지 `extra`는 열린 객체다:

```json
{
  "plugin_id": "embedder.vllm_pooling_bge_m3",
  "extension_point": "embedder",
  "role": null,
  "version": "0.1.0",
  "license": "Apache-2.0",
  "license_grade": "A",
  "territory": [],
  "linkage": "pure_python",
  "isolation_supported": ["sidecar"],
  "model_ids": ["BAAI/bge-m3@<sha>"],
  "model_license_ack_required": false,
  "sidecar_image": "<vllm-pooling-image>:v0.29.0",
  "contracts_compat": ">=1.0,<2.0",
  "capabilities": {
    "isolation_modes": ["sidecar"],
    "supports_resumable": true,
    "contracts_compat": ">=1.0,<2.0",
    "input_formats": [],
    "model_ids": ["BAAI/bge-m3@<sha>"],
    "requires_gpu": true,
    "extra": {
      "dense": true,
      "sparse": true,
      "multivector": false,
      "max_input_tokens": 8192,
      "requires_instruction": false
    }
  }
}
```

## 재검토 조건

1. TEI가 BGE-M3 sparse(`token_classify` 상당) 출력을 지원하게 되면 `standard`의 3-in-1 서빙을 TEI 단일 스택으로 통합할지 동등성 게이트와 함께 재검토한다(운영 스택 1종 감소).
2. Infinity가 릴리스를 재개해 12개월 이상 지속하고 BGE-M3 sparse를 지원하면 폴백 후보 재평가를 한다. 그 전까지 제외를 유지한다.
3. vLLM pooling API(`--hf-overrides`, `bge_m3_sparse_plugin` 인터페이스) 변동으로 계약 테스트가 파손되면 FlagEmbedding 인프로세스 폴백으로 운영하며 핀을 갱신한다. 연속 두 릴리스에서 파손되면 커스텀 서버(A6)를 3-in-1 1차로 승격할지 재검토한다.
4. ADR-0010의 `ko-quality` 게이트(nDCG@10 +2p)가 통과되어 기본 임베딩이 dense 전용 모델 + 별도 sparse 인코더로 바뀌면, vLLM pooling의 필요성과 learned sparse 인코더 행의 엔진(`sparse-encoder-server` 유지 vs TEI `/embed_sparse` 대체 — PIXIE-Splade-v1.5 ModernBERT 지원은 "확인 필요(as of 2026-09)", 05 미해결 이슈 2)을 재검토한다. TEI 지원이 그 전에 확인되면 표의 해당 행만 patch로 갱신한다.
5. `lite`에서 서버형 임베딩이 필요해지면(워커 다중 프로세스의 모델 중복 적재 등) OpenVINO Model Server와 TEI CPU 이미지를 벤치마크 후 결정한다(08 §모델 서빙 인프라).
6. 한국어 골든셋에서 bge-m3 ONNX int8의 품질 손실(05 미해결 이슈 3)이 프로파일 `gate` 임계를 넘으면 `lite` 인프로세스의 양자화·dtype을 재검토한다.
7. 대량 초기 색인·모델 교체 재색인에서 Ray Data 실행 백엔드가 필요하다고 측정되면 08 §분산 배치 판정에 따라 `embedder` 실행 백엔드 옵션을 추가할지 재검토한다(서빙 스택 결정은 불변).

## 참조

- [설계 브리프](../00-vision/00-design-brief.md) §2 R2, §3 원칙 2·4·6, §4 D-02·D-10·D-15·D-16(개정 v1.1), §7 품질 목표, §9 문서 규약
- [설계 바이블](../02-architecture/00-design-bible.md) §1.1, §2.2·§2.3(`embedding-server`·`reranker-server`), §3.1 D-16 행, §3.2 O-02·O-04, §3.3 0009행, §4.1 지문·캐시, §4.2 `embed` 행, §4.4 embed, §5.3 `Producer`·`Capabilities`, §5.4 `EmbeddedChunkSet`·`VectorBundle`, §5.6 `PluginMeta`, §5.7 `Pooling`·`EmbeddingMode`·`VectorName`·`RerankBackend`·오류 카탈로그, §6.1·§6.2, §7.1·§7.2·§7.3·§7.4, §8.1 5단계, §8.3, §11.6, §12 `adapters/embed`, §13.4 Valkey `qemb:`, §15 리스크 #2·#8·#9, §16
- [기술 지형 종합: 선정 매트릭스](../07-tech-landscape/00-summary-and-selection-matrix.md) `embedding_server`·`dense_embedder`·`sparse_encoder`·`reranker` 행, "프로파일별 기본 조합" 임베딩·리랭커 행, "브리프 수정 제안" D-16(서빙) 행, ADR 발의 목록 P1, "어댑터·플러그인 공통 요구" 2·3·4·5
- [05 임베딩·스파스·멀티벡터 모델과 서빙](../07-tech-landscape/05-embedding-models-and-serving.md) §서빙 스택, §BGE-M3 심층 비교, §서빙 스택 비교, §서빙 권고, §어댑터 계약, §캐싱과 버전 고정, §실패 모드, §브리프와의 충돌, 미해결 이슈 1·2·3·17
- [08 오케스트레이션·메시징·API 프레임워크](../07-tech-landscape/08-orchestration-messaging-and-api-frameworks.md) §E 모델 서빙 인프라, §분산 배치: Ray Data와 Dask, §모델 서빙 인프라(심층 비교)
- 관련 ADR: [ADR-0001 라이선스 등급표](./0001-license-grade-table-and-d02-interpretation.md), [ADR-0010 BGE-M3 근거·late_interaction 슬롯](./0010-bge-m3-rationale-and-late-interaction-slot.md), [ADR-0012 경량 프로파일 sparse_bm25](./0012-lite-profile-qdrant-only-client-bm25.md), [ADR-0014 sparse 표현](./0014-sparse-representation-bge-m3-lexical-leg-kept.md), [ADR-0019 청크 토크나이저·recount](./0019-chunk-size-tokenizer-defaults-and-recount-stage.md), [ADR-0031 프로파일 게이트](./0031-profile-schema-extends-and-quality-gates.md), [ADR-0032 플러그인 SDK](./0032-plugin-sdk-stage-protocol-and-conformance-kit.md), [ADR-0033 사이드카 격리 사다리](./0033-sidecar-convert-contract-and-isolation-ladder.md), [ADR-0037 산출물 캐시 스코프](./0037-artifact-cache-scope-and-stage-key-composition.md)
- 하위 설계 문서: [04-pipelines/12 임베딩](../04-pipelines/12-embedding.md)(§4.1 `sparse-encoder-server` 계약 제안, §11.3 동등성 게이트 절차, 미해결 이슈 5·6), [04-pipelines/16 리랭킹](../04-pipelines/16-reranking.md), [03-contracts/07 EmbeddedChunkSet·IndexRecord](../03-contracts/07-embedded-chunk-set-and-index-record.md)(`quantization` 의미), [03-contracts/16 평가·피드백·사이드카 계약](../03-contracts/16-eval-feedback-and-sidecar-contracts.md), [02-architecture/08 배포 아키텍처](../02-architecture/08-deployment-architecture.md)(§3.1 이미지 표, §6.3 서빙 인스턴스 배치, 미해결 이슈 17), [09-operations/04 확장·성능](../09-operations/04-scaling-and-performance.md), [ADR 인덱스](./README.md)
