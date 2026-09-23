---
title: "ADR-0033: 사이드카 convert 계약과 격리 사다리"
status: accepted
date: 2026-09-22
deciders: architecture
priority: P1
related: ["K5", "O-10"]
owner: architecture
version: 0.1.1
last_updated: 2026-09-23
depends_on:
  - ../00-vision/00-design-brief.md
  - ../02-architecture/00-design-bible.md
  - ../07-tech-landscape/00-summary-and-selection-matrix.md
  - ../07-tech-landscape/01-document-parsing-hwpx-hwp.md
  - ../07-tech-landscape/02-document-parsing-pdf-layout-ocr.md
  - ../07-tech-landscape/03-document-parsing-office-html-text.md
  - ../07-tech-landscape/08-orchestration-messaging-and-api-frameworks.md
  - ../07-tech-landscape/12-security-multitenancy-pii-and-licensing.md
---

# ADR-0033: 사이드카 convert 계약과 격리 사다리

> MADR(Markdown Architectural Decision Record) 형식. 바이블 §3.3 표의 0033행이며 관련 결정은 K5(하나의 커널·두 개의 셸 + 단일 해시 식, 바이블 §2.1)와 O-10(gRPC 제공 여부, 바이블 §3.2 `resolved`)이다. 이 ADR은 바이블 §4.1 격리 모드·§5.6 `ConvertRequest`/`ConvertResponse`·§6.7 사이드카 명명·§10.3 E16의 결정을 근거·대안과 함께 기록하고 바이블 표를 바꾸지 않는다(바이블 §1.1). 외부 API 규약과 gRPC 미제공의 일반 근거는 [ADR-0018](./0018-api-rest-sse-mcp-no-grpc-rfc9457.md), HWP 5.0 체인은 [ADR-0007](./0007-hwp5-java-sidecar-first-pyhwp-demoted.md), 라이선스 등급표는 [ADR-0001](./0001-license-grade-table-and-d02-interpretation.md)이 소유한다. 이 문서가 다루는 "사이드카 변환 계약"의 대상은 바이블 §2.2의 "사이드카" 경계(`parser-workers`·`lo-sidecar`·`ocr-gpu`)이며, "모델 서빙" 경계(`embedding-server` vLLM `/pooling`, `reranker-server` TEI `/rerank`)는 같은 `sidecar` 격리 등급과 `image_digest` 지문 규칙만 공유하고 `POST /v1/convert`는 쓰지 않는다([ADR-0009](./0009-embedding-serving-vllm-pooling-tei-inprocess.md)).

## 맥락과 문제

파서 어댑터가 감싸는 오픈소스는 런타임이 네 가지다 — JVM(hwplib·hwp2hwpx·hwpxlib·Tika), LibreOffice(+H2Orestart), CUDA 결합 프레임워크(PaddleOCR), Rust 네이티브(unhwp). 기술 지형 조사에서 확정된 사실은 다음과 같다(버전·일자는 07 문서 확인일 2026-09-18~22 기준, 잠금 파일이 정본).

| # | 사실 | 출처 |
|---|------|------|
| F1 | JPype 인프로세스는 프로세스당 JVM 1개·`shutdownJVM` 후 재기동 불가·모든 파서 워커 이미지에 JDK 포함·mypy strict와 동적 프록시 타입 불일치로 배제되었다. 사이드카는 OOM·무한 루프가 Python 워커를 죽이지 않고 Temporal 액티비티 타임아웃과 자연스럽게 결합한다 | [01](../07-tech-landscape/01-document-parsing-hwpx-hwp.md) §JPype vs 사이드카 |
| F2 | unhwp 0.11.0은 단일 `py3-none-any` 휠에 네이티브 라이브러리를 번들해 `ctypes.CDLL`로 로드한다. Rust 패닉·세그폴트가 Python 워커를 함께 죽이고 linux-arm64 바이너리가 없어 `OSError`로 import가 실패한다 | 01 §후보 E, 매트릭스 `hwp5_parser` 행 |
| F3 | LibreOffice headless는 프로파일 락(두 번째 프로세스가 종료 코드 1로 조용히 실패), 좀비 프로세스, 행 걸림, 콜드스타트 1~3s, 컨테이너 1GB+가 확인된 운영 이슈다. 03 문서의 `lo-sidecar` 규격은 워커별 `-env:UserInstallation` 프로파일 분리·프로세스 그룹 KILL·`tini`·네트워크 egress 차단·읽기 전용 루트 FS·`/healthz` 샘플 변환을 요구한다 | [03](../07-tech-landscape/03-document-parsing-office-html-text.md) §LibreOffice 사이드카 서비스 설계 제안 |
| F4 | PaddleOCR은 PaddlePaddle 프레임워크(CUDA 버전 결합, 대용량 wheel)에 의존해 파서 워커와 분리된 OCR 컨테이너가 권고된다. RapidOCR(ONNX Runtime)은 인프로세스 가능하다 | [02](../07-tech-landscape/02-document-parsing-pdf-layout-ocr.md) §PaddleOCR 함정, 매트릭스 `ocr_engine` 행 |
| F5 | H2Orestart는 GPL-3.0(MIT 표기는 오류), pyhwp는 AGPL-3.0+, PyMuPDF는 AGPL-3.0/상용 듀얼이다. D-02(개정 v1.1) C 등급은 "별도 컨테이너 + 네트워크 API만·코어 이미지 미포함·별도 저장소 고지·Helm opt-in"이다 | [12](../07-tech-landscape/12-security-multitenancy-pii-and-licensing.md) §6.1·§6.2, ADR-0001 |
| F6 | 상충 J-6: 01 문서는 내부 사이드카에 gRPC(바이너리 페이로드·스트리밍·타입드 스키마)를 권고했고 03·08 문서는 REST(FastAPI) 우선을 권고했다. 매트릭스는 "사이드카 요청·응답은 오브젝트 스토리지 참조(`ArtifactRef`)만 주고받으므로 gRPC 스트리밍 이득이 작고, 런타임 넷에 계약 하나(REST + RFC 9457)를 두는 운영 단순성이 우선한다"로 REST를 채택했다 | [매트릭스](../07-tech-landscape/00-summary-and-selection-matrix.md) J-6, O-10 권고 |
| F7 | Temporal 액티비티 페이로드는 단일 2MB(gRPC 메시지 4MB) 한계가 있어 경계 페이로드는 `ArtifactRef`만이다. Tika 4.0은 자체 포크 프로세스 격리와 `apache/tika-grpc` 이미지를 제공하지만 03 문서는 REST 이미지로 통일했다 | [08](../07-tech-landscape/08-orchestration-messaging-and-api-frameworks.md) §Temporal, 바이블 §4.1, 03 §Tika |
| F8 | 캐시 키 = 멱등성 키 규칙에서 지문에 사이드카 이미지 digest가 빠지면 낡은 변환본이 조용히 재사용된다(리스크 #8). 03 문서의 `lo-sidecar` 초안 API(`source_ref, target, timeout_s` → `artifact_ref, duration_ms, lo_version`)와 01 문서의 Java 사이드카는 필드명이 서로 달랐다 | 바이블 §15 #8, 03 §sequenceDiagram, 01 §어댑터 계약 |

문제: (1) 어댑터를 어느 격리 단에 두는지 판정 기준과 그 강제 지점은 무엇인가. (2) 런타임 넷의 사이드카가 공유할 요청·응답·헬스·오류·비밀·추적 계약은 무엇이며 스트리밍은 어떻게 대체하는가. (3) 사이드카 이미지는 어느 저장소·어느 배포 단위에 속하고, 지문·캐시·폴백에 어떻게 연결되는가.

## 결정 동인(decision drivers)

| ID | 동인 | 내용 | 근거 |
|----|------|------|------|
| DR1 | 라이선스 경계 | 코어 이미지·인프로세스 의존은 A 등급 순수 Python만. C 등급은 네트워크 API 뒤·별도 저장소·Helm opt-in | D-02, ADR-0001, 바이블 §12 "코어는 A 등급 순수 Python만 인프로세스 의존" |
| DR2 | 장애 격리 | 네이티브 크래시·JVM OOM·LibreOffice 행 걸림이 Python 워커와 다른 문서의 잡을 죽이지 않아야 한다. 경계 밖 크래시는 타입드 오류로 변환 | 매트릭스 공통 요구 1, 바이블 §11.3 `fallback` |
| DR3 | 계약 하나 | 런타임 넷에 헬스체크·오류 매핑·타임아웃·OTel 계측을 한 번만 만든다 | J-6, O-10, ADR-0018 |
| DR4 | 단일 페이로드 | 경계를 넘는 값은 `ArtifactRef`만(K5). 사이드카도 참조를 받아 스토리지에서 직접 읽는다 | 바이블 §2.1 K5, §4.1 경계 페이로드, F7 |
| DR5 | 재현성·멱등 | `fingerprint`에 `image_digest`, 파생물 키에 `sidecar_image_digest`. 같은 원본·같은 이미지는 재변환 생략, 이미지 범프는 재변환 유발 | 원칙 4, 바이블 §4.1 지문, §6.2 `derived`, 리스크 #8 |
| DR6 | 보안 | 비밀은 `credentials_ref` 간접 참조만, 사이드카 호출은 서비스 디스커버리 주소만, GPL 사이드카는 네트워크 차단·비루트·tini | 바이블 §6.6, §10.3 E16, §2.3 `lo-sidecar` 행 |
| DR7 | 오류 모델 1개 | `StageError` ↔ RFC 9457 `type = urn:rag:error:{code}` 1:1, 재시도 여부는 카탈로그가 결정 | 바이블 §4.1 오류 모델, §5.7, ADR-0018 |
| DR8 | `lite` 자립 | `lite`는 단일 노드·GPU 0·사이드카 0 구성이다. 격리 사다리는 사이드카 없이도 HWP 5.0 1차(unhwp, `helper_process`)가 서는 단을 포함해야 하고, 라우터의 사이드카 항목이 미설치(`optIn` 꺼짐)면 런타임에 `parse.unsupported_format`으로 처리된다(로딩 시 정적 거부 규칙은 아님) | 바이블 §7.1 `lite` 열(HWP 5.0·DOC/RTF/ODT 행), §7.3 라우터 주석(`lo-sidecar` 미설치 시 `parse.unsupported_format`) |
| DR9 | 관측성 | 요청마다 `trace_id`, 응답마다 `took_ms`·`producer`; 사이드카 불가는 `rag_parser_sidecar_unavailable_total` | D-11, 바이블 §6.5 |

## 고려한 대안

| # | 대안 | 판정 |
|---|------|------|
| A1 | 내부 사이드카를 gRPC(스트리밍·proto 스키마)로 통일 — 01 문서 권고 | **기각**(O-10, J-6) |
| A2 | JNI(JPype)·ctypes 네이티브를 파서 워커에 인프로세스 링크 | **기각** |
| A3 | 사이드카별 상이한 계약(LO `source_ref/target/timeout_s`, Tika `PUT /tika`, Java 자체 JSON) | **기각** |
| A4 | 스트리밍 변환(서버 스트림·청크 응답으로 페이지 진행 전달) | **기각** → 페이지 단위 부분 산출물 + 폴링 |
| A5 | 2단 사다리(`in_process` / `sidecar`만; unhwp도 사이드카) | **기각** |
| A6 | 요청 본문에 원본 바이트 인라인·비밀번호 평문 전달 | **기각** |
| A7 | GPL/AGPL 사이드카 이미지를 본 저장소 `sidecars/`·기본 Helm에 포함 | **기각**(D-02 C) |
| A8 | 3단 격리 사다리 + 공통 REST `POST /v1/convert` 계약 + `ArtifactRef` 교환 + RFC 9457 | **채택** |

- **A1 gRPC 사이드카(바이블이 기각한 01 문서 권고).** 설명: hwplib 변환기를 gRPC-Java 서버로 두고 원본 바이트를 클라이언트 스트림으로 보내며 proto로 Java·Python 타입을 공유한다. 장점: 스토리지 왕복 없는 바이트 전달, 페이지 진행의 서버 스트림, 강타입 코드젠(08 §D grpcio 성숙도 매우 높음). 단점: `ConvertRequest.input`·`ConvertResponse.output`이 `ArtifactRef`이므로 대용량 전달 전제가 사라진다(J-6). 런타임 넷에 계약이 둘이면 헬스·오류·타임아웃·계측을 두 번 만들고(DR3), protobuf가 JSON Schema 정본(D-05) 옆의 이중 정본이 된다. `grpc.aio`는 C 코어 위 래퍼라 asyncio 통합이 복잡하다(08 §D). 판정: 기각. gRPC가 필요해지면 ADR-0018의 `connectrpc` 경로만 허용한다.
- **A2 인프로세스 JNI/ctypes 링크.** 설명: JPype로 hwplib을, `ctypes.CDLL`로 unhwp를 워커 프로세스에 직접 로드한다. 장점: 호출 지연 최소, 객체 모델 직접 순회, 배포 단위 추가 없음(01 §JPype 표). 단점: F1(JVM 재기동 불가·JDK 전 이미지·mypy strict 불일치)과 F2(패닉이 워커 사망, arm64 import 실패). 크래시가 같은 워커의 다른 액티비티까지 죽여 D-17 재시도·하트비트 모델이 무너지고, AGPL/GPL 컴포넌트는 링크 자체가 D-02 위반이다(F5). 판정: 기각. 순수 Python(A 등급)만 `in_process`다.
- **A3 사이드카별 상이한 계약.** 설명: 각 사이드카가 자기 API를 정의하고 어댑터가 개별 클라이언트를 갖는다(F8의 초안들). 장점: 사이드카 구현 자유도, 기존 이미지(`apache/tika`) 그대로 사용. 단점: 워커의 `SidecarStage` 하나로 지문·오류 변환·`deadline_ms` 전파·`trace_id` 계측을 공통화할 수 없고, `output=null → error 필수` 같은 불변식을 사이드카마다 검증해야 한다. Tika 서버를 쓰더라도 앞에 얇은 `convert` 어댑터를 둔다. 판정: 기각.
- **A4 스트리밍 변환.** 설명: OCR·대형 HWP 변환의 페이지 진행을 HTTP 청크 응답이나 gRPC 서버 스트림으로 워커에 밀어 준다. 장점: 진행률 실시간 반영, 부분 결과 조기 사용. 단점: 스트림은 액티비티 재시도·`Resumable` 재개와 맞지 않고(연결 끊김 = 처음부터), 부분 결과가 콘텍스트 주소화 산출물로 남지 않아 재현·캐시가 깨진다. 바이블 §3.2 O-10대로 사이드카가 페이지 단위 부분 산출물을 `derived/`에 저장하고 워커가 하트비트 주기로 존재를 폴링하면 O-08의 `page_status[]`·`Resumable`·`heartbeat_details.page`와 같은 모델을 재사용한다. 판정: 기각(대체 수단 확정).
- **A5 2단 사다리.** 설명: 헬퍼 프로세스 단을 없애고 네이티브 위험 어댑터도 사이드카로 보낸다. 장점: 격리 모델 단순, 계약 하나. 단점: `lite`는 사이드카 0이어야 하는데(DR8) unhwp가 `lite` HWP 5.0 1차다(바이블 §7.1). 문서 1건마다 단기 `multiprocessing spawn` 프로세스는 휠만으로 동작하고 크래시를 `parse.conversion_failed`로 변환할 수 있다(01 §후보 E (a)). 판정: 기각. 3단 유지.
- **A6 본문 바이트 인라인·비밀 평문.** 설명: `ConvertRequest`에 원본 base64와 문서 비밀번호를 담는다. 장점: 사이드카가 스토리지 자격 증명을 갖지 않아도 된다. 단점: 200MB 원본(§5.1 `fetch.max_bytes`)이 JSON 본문 16KB 한계와 Temporal 2MB 한계를 넘고, 비밀번호 평문은 세 제안 심사가 제거한 치명 결함(`document_password` 평문, 바이블 §목적)이며 로그·트레이스 유출 경로가 된다. 판정: 기각. 본문은 참조만, 비밀은 `credentials_ref`.
- **A7 GPL/AGPL 이미지를 본 저장소·기본 Helm에 포함.** 장점: 단일 빌드·릴리스. 단점: "코어만 설치"가 성립하지 않고 AGPL 컨테이너 배포를 금지하는 조직이 기본 경로를 쓸 수 없다(F5, ADR-0007 A2). 판정: 기각. 별도 저장소 `rag-platform-gpl-sidecars`, 본 저장소는 Helm `optIn.*` 값과 이미지 참조 링크만.

## 결정

**결정:** 어댑터 격리 모드는 바이블 §4.1 그대로 3단 — `in_process`(A 등급 순수 Python) / `helper_process`(`multiprocessing spawn`, ctypes·네이티브 크래시 위험) / `sidecar`(JVM·LibreOffice·CUDA·GPL/AGPL; REST `POST /v1/convert`) — 이며, K7대로 어댑터 격리 3단(`in_process/helper_process/sidecar`)과 테넌트 격리 3단(`payload_filter/shard_key/index_per_tenant`)을 `TieringPolicy` 하나로 선언·검증한다. 프로파일 `parse.router` 항목이 `isolation`·`image`를 선언하고(§7.3 예: `{plugin: parser.hwp5_java_sidecar, isolation: sidecar, image: parser-workers}`, `{plugin: parser.hwp5_unhwp, isolation: helper_process}`) `StagePolicy.isolation`(enum(IsolationMode) | null)이 격리 모드를 강제한다. 모든 변환 사이드카는 공통 계약 `POST /v1/convert`(`ConvertRequest{input: ArtifactRef, options, tenant_id, document_id, deadline_ms, trace_id, credentials_ref}` → `ConvertResponse{output: ArtifactRef | null, derived[], warnings, error: StageError | null, took_ms, producer}`, `output=null`이면 `error` 필수; 본문은 참조만, 비밀은 `credentials_ref`)와 `GET /healthz`(모델·JVM·LO 준비 상태)를 제공한다(§5.6, §6.7, §14). O-10 해결대로 "내부 사이드카도 REST `POST /v1/convert` + `ArtifactRef` + RFC 9457. Qdrant `prefer_grpc=True`·Temporal 클라이언트 gRPC는 라이브러리 설정. 스트리밍 필요 사이드카는 부분 산출물 페이지 단위 저장 + 폴링"이다. 사이드카 이미지 `parser-workers`, `ocr-gpu`는 본 저장소 `sidecars/`(별도 이미지, 코어 의존 없음, 모두 `POST /v1/convert`), GPL/AGPL 이미지·플러그인(`lo-sidecar`, `rag-plugin-pyhwp-sidecar`, `rag-plugin-pymupdf-sidecar`)은 별도 저장소 `rag-platform-gpl-sidecars`(별도 LICENSE/NOTICE, 코어 이미지 미포함, 독립 빌드·태깅·릴리스)에서 관리하고 본 저장소는 Helm `optIn.*` 값과 이미지 참조 링크만 둔다(§6.7, §12). `lo-sidecar`는 tini·프로세스 그룹 KILL·프로파일 락·네트워크 차단(§2.3). 지문은 `fingerprint = H("producer", plugin_id, plugin_version, config_hash, image_digest, model_ids)`(SDK가 사이드카 image digest 포함을 검증)과 `Producer.image_digest`·`parser_fingerprint.sidecar_image_digest`로 남기고, 파생물은 봉투가 없어 스코프 없이 `H("derived", content_hash, sidecar_image_digest or "", options_hash or "")`(`options_hash = H("config", canonical_json(DPI·OCR 언어 등 파생물 옵션))`, 테넌트 내 공유, `tenants/{tenant_id}/derived/{kind}/…`)로 캐시한다(바이블 §6.2 1.3.0 AM-40; §4.1, §13.3). 사이드카 호출은 서비스 디스커버리 주소만(E16). `parse.sidecar_unavailable` 재시도 후 폴백 체인, `parse.conversion_failed` 폴백 체인(§4.2 `parse` 행).

기각 대안: gRPC 사이드카(O-10), 인프로세스 JNI/ctypes 링크, 사이드카별 상이한 계약, 스트리밍 변환(페이지 단위 부분 산출물 + 폴링으로 대체).

**격리 사다리 배정 기준과 강제 지점**(플러그인 ID는 바이블 §6.1·§12, 열거는 §5.7 `IsolationMode`·`Linkage`·`LicenseGrade`):

| 단 | 배정 조건 | 예(바이블 §4.2·§7.3) | 선언·강제 | 경계 밖 실패 → 오류 |
|----|-----------|----------------------|-----------|---------------------|
| `in_process` | `PluginMeta.linkage = pure_python`이고 `license_grade ∈ {A}`(B는 `dynamic` + 선택 extra만, §7.4 (1)) | `parser.hwpx_python_hwpx`, `parser.pdf_docling_standard`, `parser.pdf_fast_pdftext`, `parser.docx_docling_docx2python`, `parser.html_trafilatura_docling`, `parser.text_charset_markdown_it`, RapidOCR(ONNX) | 라우터 항목에 `isolation` 생략 시 `in_process`로 해석(해석; [04-pipelines/03](../04-pipelines/03-parsing-router-and-format-detection.md) 확정); `isolation_supported`에 `in_process` 포함 필수 | 예외는 스테이지 오류 카탈로그 그대로; 비재시도 코드(`parse.document_encrypted`·`parse.distribution_document`·`parse.unsupported_variant`·`parse.corrupt_container`)는 폴백 없이 체인을 끊고 전파, `parse.conversion_failed`만 폴백 체인 진행(바이블 §4.2 1.3.0, CR-45) |
| `helper_process` | 네이티브 코드를 `ctypes`·확장 모듈로 로드해 크래시가 인터프리터를 죽일 수 있는 A 등급(`linkage ∈ {dynamic, static_bundled}`) | `parser.hwp5_unhwp`(문서 1건당 단기 `multiprocessing spawn`, x64만; arm64는 로딩 시 비활성 + 경고) | 라우터 `isolation: helper_process`; 어댑터는 헬퍼 래퍼만 호출(직접 `ctypes` 로딩 금지) | 비정상 종료·시그널·`OSError` → `parse.conversion_failed`(폴백 후 no) |
| `sidecar` | JVM·LibreOffice·CUDA 결합 프레임워크, 또는 C 등급(GPL/AGPL) — 코어 이미지에 들어갈 수 없는 모든 것 | `parser.hwp5_java_sidecar`(`parser-workers`, A), `parser.office_lo_sidecar`(`lo-sidecar`, C, opt-in), `ocr-gpu`(PaddleOCR PP-OCRv5 server, `premium`), Tika `HwpV5Parser`(`parser-workers` 동거) | 라우터 `isolation: sidecar` + `image`; `PluginMeta.sidecar_image` 비-null, `Producer.image_digest` 비-null; C 등급은 `license_policy.max_grade` 초과 시 `optIn` 명시 없이 `profile.invalid` | 연결 실패·503·`/healthz` 실패 → `parse.sidecar_unavailable`(재시도 yes, `parse` 정책 `max_attempts` 3, §4.4) → 소진 시 폴백; 200 + `error` → `parse.conversion_failed` 즉시 폴백 |

**계약 세부**(필드·타입·필수는 바이블 §5.6 표 그대로; "의미" 열은 이 ADR이 확정하는 해석이고 스키마 `convert-request.schema.json`·`convert-response.schema.json`은 [03-contracts/16](../03-contracts/16-eval-feedback-and-sidecar-contracts.md)이 소유한다):

| 타입 | 필드 | 타입 | 필수 | 의미 |
|------|------|------|------|------|
| `ConvertRequest` | `input` | `ArtifactRef` | Y | 원본 또는 상류 파생물 참조(`uri`는 §13.3 키, `s3://`·`file://`만). 사이드카는 자기 스토리지 자격 증명으로 직접 읽는다 |
| | `options` | object | N | 사이드카별 옵션(예 `lo-sidecar` 대상 포맷, `ocr-gpu` 언어·페이지 범위). 스키마는 각 사이드카가 게시; URL·비밀 금지 |
| | `tenant_id`, `document_id` | string(ulid) | Y | 파생물 키 접두(`tenants/{tenant_id}/derived/`)와 감사용. 캐시 키에는 들어가지 않는다(§4.1 봉투 없는 파생물) |
| | `deadline_ms` | integer | Y | 요청 시점 기준 잔여 예산(밀리초). 워커가 `StagePolicy.start_to_close` 잔여 시간에서 파생하며 사이드카는 초과 전에 `error`로 반환한다 |
| | `trace_id` | string | Y | OTel 트레이스 ID. 사이드카 스팬은 `rag.ingest.parse`의 자식(§6.5) |
| | `credentials_ref` | string \| null | N | 문서 비밀번호 등 비밀의 간접 참조(§6.6 `RAG_SECRETS__PROVIDER`). 평문 금지 |
| `ConvertResponse` | `output` | `ArtifactRef` \| null | Y(nullable) | 요청된 주 산출물 1개(HWPX 변환본·DOCX 변환본·OCR 결과). §13.3 `derived/` 키에 콘텍스트 주소화 저장 |
| | `derived` | array<ArtifactRef> | Y | 부속 파생물(페이지 이미지·변환 보고서·표 HTML). 빈 배열 허용. `ParsedDocument.artifacts[]`로 전파 |
| | `warnings` | array<Warning> | Y | `stage.reason` 코드(§5.7), 콘텐츠 미포함 |
| | `error` | `StageError` \| null | N | `output=null`이면 필수(`stage = parse`, `plugin_id` = 사이드카 어댑터) |
| | `took_ms`, `producer` | integer / `Producer` | Y | 처리 시간; `producer.image_digest`는 사이드카 자기 보고(`sha256:…`, 비-null) |

HTTP 의미([03-contracts/13](../03-contracts/13-error-model.md) §6.4와 동일): 변환 실패는 **200 + `ConvertResponse{output: null, error}`**, `ProblemDetails`는 전송·검증 오류에만 — 400 `contract.violation`(요청 본문), 503 `parse.sidecar_unavailable` + `Retry-After`(미준비·과부하). 워커(`sdk/SidecarStage`)는 연결 실패·타임아웃·503을 `parse.sidecar_unavailable`로 합성한다. `GET /healthz`는 모델·JVM·LO 준비 상태를 반환하며 `lo-sidecar`는 샘플 DOC 1건 변환 5s 이내(03 문서 초안 목표)를 준비 조건으로 삼는다.

```mermaid
sequenceDiagram
    participant W as worker · SidecarStage(stage.parse)
    participant O as Object Storage(tenants/{tenant_id}/…)
    participant S as 사이드카(parser-workers | lo-sidecar | ocr-gpu)
    W->>W: derived 키 = H("derived", content_hash, sidecar_image_digest, options_hash) 조회 → 히트면 호출 생략
    W->>S: POST /v1/convert {input: ArtifactRef, options, tenant_id, document_id, deadline_ms, trace_id, credentials_ref}
    S->>O: GET input.uri (자기 자격 증명)
    S->>S: 변환(JVM | soffice 프로세스 그룹 | CUDA); deadline_ms 감시
    S->>O: PUT derived/{kind}/{blake3} (output, derived[])
    S-->>W: 200 ConvertResponse{output, derived[], warnings, error: null, took_ms, producer}
    Note over W,S: output=null → error 필수 → parse.conversion_failed → 폴백 체인 · 연결 실패/503 → parse.sidecar_unavailable → 재시도 후 폴백
```

예시(`parser-workers` HWP 5.0 → HWPX; 값은 예시, ID 규약은 §6.1, `media_type`은 [03-contracts/02](../03-contracts/02-source-document.md) §4.2 대응표 값):

```json
{"input": {"uri": "s3://rag-artifacts/tenants/01J9ZQ4K7X2M8N3P5R6S7T8V9W/sources/9f/9f3a7c1e5b2d4f6a8c0e2b4d6f8a1c3e5b7d9f1a3c5e7b9d1f3a5c7e9b1d3f5a", "blake3": "9f3a7c1e5b2d4f6a8c0e2b4d6f8a1c3e5b7d9f1a3c5e7b9d1f3a5c7e9b1d3f5a", "media_type": "application/x-hwp", "size_bytes": 1843200},
 "options": {"target": "hwpx"}, "tenant_id": "01J9ZQ4K7X2M8N3P5R6S7T8V9W", "document_id": "01J9ZQ5B2C3D4E5F6G7H8J9K0M",
 "deadline_ms": 840000, "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736", "credentials_ref": null}
```

```json
{"output": {"uri": "s3://rag-artifacts/tenants/01J9ZQ4K7X2M8N3P5R6S7T8V9W/derived/derived_source/4d/4d2e8b1a6c3f9e0d7b5a2c8e1f4a6d9b3e7c0a5d8f2b6e1c9a4d7f0b3e6c2a8d.hwpx", "blake3": "4d2e8b1a6c3f9e0d7b5a2c8e1f4a6d9b3e7c0a5d8f2b6e1c9a4d7f0b3e6c2a8d", "media_type": "application/hwp+zip", "size_bytes": 2211840},
 "derived": [], "warnings": [], "error": null, "took_ms": 1930,
 "producer": {"plugin_id": "parser.hwp5_java_sidecar", "plugin_version": "0.1.0", "config_hash": "a1b2c3d4e5f60718293a4b5c6d7e8f900f1e2d3c4b5a69788796a5b4c3d2e1f0", "image_digest": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", "model_ids": []}}
```

## 결과

**긍정**

- 코어 이미지와 `uv.lock`은 A 등급 순수 Python만 품는다. JVM·LibreOffice·CUDA·GPL/AGPL은 이미지 경계 뒤에 있어 Apache-2.0 채택성(리스크 #2)이 보호되고, AGPL 컨테이너 배포를 금지하는 조직도 `standard`(`parser-workers`는 A 등급)를 쓸 수 있다.
- 네이티브 패닉·JVM OOM·LibreOffice 행 걸림이 워커 프로세스와 다른 문서의 액티비티를 죽이지 않고 `parse.conversion_failed`/`parse.sidecar_unavailable`로 변환되어 폴백 체인(ADR-0007)과 `parser_chain[]` 감사로 이어진다.
- 계약이 하나라 `SidecarStage` 한 클래스가 지문(`image_digest`)·`deadline_ms` 전파·`trace_id` 계측·오류 합성·`derived` 캐시를 공통 처리하고, 사이드카 계약 테스트도 한 세트다. 새 사이드카(VLM 파서, Tika 단독)는 얇은 `convert` 어댑터만 추가한다.
- `ArtifactRef` 교환이라 Temporal 2MB 한계와 정합하고(ADR-0003), 사이드카가 상태 없는 변환기로 남아 수평 확장·KEDA 스케일링이 단순하다.
- `H("derived", content_hash, sidecar_image_digest or "", options_hash or "")`(바이블 §6.2 1.3.0, AM-40) 캐시로 같은 원본·같은 이미지·같은 옵션의 재파싱·재청킹(프로파일 변경, blue/green)은 변환을 생략하고, 이미지 범프나 옵션 변경은 재변환을 유발한다(리스크 #8 완화).

**부정**

- `standard` 이상은 컨테이너 1~3개(`parser-workers` JVM 힙 512MB~2GB, `lo-sidecar` 1~2GB, `ocr-gpu` GPU; 01·03 문서 초안 목표)와 네트워크 홉·스토리지 왕복이 추가된다. 소형 문서에서는 스토리지 PUT/GET이 변환 시간보다 길 수 있다.
- 페이지 단위 스트리밍을 폴링으로 대체하므로 진행률 지연과 폴링 비용을 감수한다. §7 처리량(스캔 PDF 100페이지 < 5min GPU OCR) 미달이 확인되면 재검토 조건이다.
- 헬퍼 프로세스는 문서 1건마다 `spawn` 기동 비용이 있고(01 §리소스 요구 "벤치마크 필요"), 사이드카는 JSON 직렬화 비용을 감수한다.
- 사이드카가 스토리지 자격 증명을 가져야 하므로 사이드카 이미지도 보안 경계(비루트·읽기 전용 FS·NetworkPolicy)의 대상이다. 이미지 digest가 지문에 들어가 이미지 범프는 대량 코퍼스의 재변환 비용을 유발한다(설계 의도).
- GPL 사이드카 사용 조직은 별도 저장소의 독립 릴리스를 추적하고 코어와의 계약 `schema_version` 호환(`contracts_compat`)을 관리해야 한다.

**중립**

- 어댑터 계약(`SourceDocument → ParsedDocument`)과 `parse` `StagePolicy`(§4.4)는 변경 없다. 사이드카 호출 시간은 액티비티 타임아웃 안에 든다.
- 모델 서빙(vLLM `/pooling`, TEI `/rerank`)은 공급자 API 그대로이며 `embedder`·`reranker` 어댑터가 감싼다. 격리 등급·`image_digest` 지문·서비스 디스커버리 규칙만 이 ADR과 공유한다.
- 헬퍼 프로세스 크래시의 전용 코드(`parse.helper_crashed`)는 13 문서 미해결 이슈 3의 제안이며 채택 전까지 `parse.conversion_failed`로 표현한다.

## 준수 확인 방법

| 게이트 | 강제 내용 | 정의 위치 |
|--------|-----------|-----------|
| 열거·스키마 기계 대조(§1.2) | `IsolationMode = {in_process, helper_process, sidecar}`, `Linkage`, `LicenseGrade`가 `schemas/*.schema.json` `$defs`와 바이블 §5.7 표에서 일치. `convert-response.schema.json`은 `if output == null then required: [error]` 제약, `ConvertRequest`는 `input`이 `ArtifactRef` `$ref`이고 바이트·비밀번호 필드가 없음(`additionalProperties: false`) | [03-contracts/16](../03-contracts/16-eval-feedback-and-sidecar-contracts.md), [03-contracts/00](../03-contracts/00-contract-overview.md) |
| `rag profile validate` (1)·(2)·(10) | 라우터 항목의 `isolation` ∈ `PluginMeta.isolation_supported` ∩ `capabilities().isolation_modes`((2) 요구 능력 ↔ `capabilities()` 대조); `isolation: sidecar`이면 `image` 필수·`PluginMeta.sidecar_image`와 일치(§7.3 라우터 예·§5.6 `sidecar_image`에 대한 이 ADR의 해석); C 등급 이미지는 `license_policy.max_grade` 초과 시 `optIn` 명시 없이 `profile.invalid`((1) 라이선스 등급·`linkage`); `parse.router`가 `SourceFormat` 전 값 커버((10)). `lite`의 `sidecar` 라우터 항목을 로딩 시 정적으로 거부하는 규칙은 §7.4에 없다 — 미설치 사이드카는 §7.3 라우터 주석대로 런타임 `parse.unsupported_format`(재검토 조건 9) | 바이블 §7.4 (1)·(2)·(10), §7.3 `parse.router`, [03-contracts/15](../03-contracts/15-collection-profile-and-policy-contracts.md) |
| `StagePolicy.isolation` 강제 | 셸(`orchestration/context`)이 `isolation`이 설정된 스테이지를 다른 모드로 실행하면 `contract.violation`; `sidecar` 모드는 `SidecarStage` 경유만 | 바이블 §5.3 `StagePolicy`, §12 |
| 금지 임포트 린트 | `src/rag_platform/**`에서 `jpype`, `hwp5`, `fitz`(PyMuPDF), `grpc` 직접 임포트 금지(ruff banned-api); `adapters/parse/*`에서 `ctypes` 직접 로딩 금지(헬퍼 래퍼만); import-linter `adapters`는 `storage`를 모른다(§12 의존 방향) | [10-development/03](../10-development/03-coding-standards.md) |
| SDK 지문 검증 | `SidecarStage.fingerprint()`가 `image_digest`를 포함하지 않으면 등록 거부; `ConvertResponse.producer.image_digest`와 배포 시 해석된 이미지 digest 불일치는 `contract.violation` | 바이블 §4.1 지문, [ADR-0032](./0032-plugin-sdk-stage-protocol-and-conformance-kit.md) |
| 적합성 키트 `contract_roundtrip`·`idempotency` | 사이드카 플러그인 공통 항목: 같은 `content_hash` + 같은 `image_digest` → `derived` 캐시 히트로 호출 0회; `image_digest` 변경 → 재호출; `output=null`이면 `error` 존재; `error.code`가 §5.7 카탈로그 철자; 두 테넌트가 같은 바이트를 수집해도 `stage_key`는 각자(E17)이고 `derived/`는 테넌트 접두 아래 | 바이블 §12 `testing/`, §10.3 E17, [10-development/04](../10-development/04-testing-strategy.md) |
| 사이드카 계약 테스트(공통 하네스) | 세 이미지 모두 `GET /healthz` 200 → `POST /v1/convert` 정상·`deadline_ms` 초과·손상 입력(200 + `error`)·존재하지 않는 `input.uri`(200 + `error`)·잘못된 본문(400 `contract.violation`)·미준비(503 + `Retry-After`) 6경로; 응답 본문에 콘텐츠 문자열·비밀 부재 | [10-development/05](../10-development/05-ci-cd.md) |
| egress·네트워크(E16) | 사이드카 주소는 설정(`RAG_` 접두)의 서비스 디스커버리 이름만; `ConvertRequest.input.uri` 스킴은 `s3`·`file`(개발)만; `lo-sidecar` NetworkPolicy는 오브젝트 스토리지·OTel Collector 외 egress 차단; 이미지 검사: PID 1 `tini`, 비루트 UID, 읽기 전용 루트 FS, `killpg` 타임아웃 경로 | 바이블 §10.3 E16, [02-architecture/08](../02-architecture/08-deployment-architecture.md), [09-operations/05](../09-operations/05-security-and-compliance.md) |
| 저장소·라이선스 경계 | `sidecars/`에는 `parser-workers`·`ocr-gpu`만; pip-licenses + liccheck + SBOM(Syft)으로 코어 이미지·`sidecars/*` 이미지에 GPL/AGPL 산출물(H2Orestart `.oxt`, `libreoffice-*`, `pyhwp`, PyMuPDF) 부재; Helm 기본 values에서 `optIn.*` 전부 `false` | ADR-0001, 바이블 §6.7·§12, [02-architecture/08](../02-architecture/08-deployment-architecture.md) |
| 운영 메트릭 | `rag_parser_sidecar_unavailable_total` 증가율 알림; `parser_chain[]`에서 2차 이하 경로 비율 감시(사이드카 장애로 구조 손실 경로가 기본이 되는 상황 탐지) | 바이블 §6.5, [09-operations/03](../09-operations/03-observability.md) |

코드 리뷰 체크리스트: (a) 새 어댑터의 격리 단이 배정 기준 표와 일치하고 `PluginMeta.linkage`·`license_grade`·`isolation_supported`가 그것을 뒷받침하는가, (b) 사이드카 호출이 `SidecarStage` + `ConvertRequest`만 쓰고 `ArtifactRef` 외 페이로드·비밀 평문을 보내지 않는가, (c) `output`·`derived[]`가 `derived/` 키로 저장되고 `ParsedDocument.artifacts[]`·`parser_fingerprint.sidecar_image_digest`에 전파되는가, (d) 실패가 카탈로그 코드(`parse.sidecar_unavailable`/`parse.conversion_failed`)로만 변환되고 `retryable`을 코드가 직접 정하지 않는가, (e) 페이지 진행이 필요한 사이드카가 스트림 대신 페이지 단위 부분 산출물 + 폴링을 쓰는가, (f) 헬퍼 프로세스가 문서 1건마다 `spawn`이고 크래시 경로가 테스트되는가.

## 재검토 조건

1. 스캔 PDF 100페이지 < 5min(GPU OCR, 브리프 §7)을 "페이지 단위 부분 산출물 + 폴링"으로 달성하지 못함이 골든셋 부하 테스트로 입증될 때 → 스트리밍 대체 수단을 ADR-0018과 공동 재검토(`connectrpc` 서버 스트림 포함).
2. 리트리벌·수집 핫패스 p95 측정에서 JSON 직렬화가 유의미한 비율을 차지하거나 `connectrpc`가 1.0에 도달할 때(ADR-0018 재검토 조건과 동일).
3. 헬퍼 프로세스 `spawn` 오버헤드 측정([08-evaluation/05](../08-evaluation/05-benchmark-plan-and-baselines.md))이 문서당 변환 시간을 지배하면 01 문서 옵션 (b) CLI 바이너리 서브프로세스 또는 상주 헬퍼 풀을 재검토한다. unhwp가 arm64 휠을 내면 `lite` arm64 체인을 함께 재검토한다(ADR-0007 조건 4).
4. `parse.helper_crashed`(13 문서 미해결 이슈 3)·`StageError.diagnostics_ref`(이슈 2)가 §1.2 minor 절차로 채택되면 배정 표의 "경계 밖 실패" 열과 사이드카 계약 테스트를 갱신한다.
5. `/healthz` 본문에 `image_digest`를 포함할지, `options` 스키마를 사이드카별 `$defs`로 게시할지를 03-contracts/16이 확정하면 계약 세부 표를 그에 맞춘다.
6. 변환 사이드카가 넷(VLM 파서 `pdf_vlm_gpu`, Tika 단독 등)을 넘어 늘어나면 사이드카 측 공통 SDK(Java·Python 서버 골격)를 본 저장소 `sidecars/`에 둘지 재검토한다.
7. H2Orestart·pyhwp가 A 등급으로 재라이선스되거나 D-02 등급표(ADR-0001)의 C 등급 배포 규칙이 바뀌면 저장소 경계·Helm `optIn.*` 규약을 맞춘다.
8. Temporal 페이로드 한계(2MB)나 `ArtifactRef` 경계 규칙(ADR-0003)이 바뀌어도 사이드카 계약은 참조 교환을 유지한다 — 인라인 전달 재도입은 별도 ADR이다.
9. `lite` 프로파일의 `isolation: sidecar` 라우터 항목을 로딩 시 정적으로 거부할 필요가 운영에서 확인되면(예: 미설치 사이드카 항목이 폴백 체인을 조용히 짧게 만드는 경우) 바이블 §7.4 검증 규칙 추가를 §1.2 minor 절차로 제안한다. 채택 전까지 미설치 사이드카는 §7.3 라우터 주석대로 런타임 `parse.unsupported_format`이며 이 ADR은 그런 규칙을 전제하지 않는다.

## 참조

- [설계 브리프](../00-vision/00-design-brief.md) §3 원칙 2·3·4·9, §4 D-01·D-02(개정 v1.1)·D-17·D-18(개정 v1.1), §5 O-07·O-10, §7 품질 목표, §9 문서 규약
- [설계 바이블](../02-architecture/00-design-bible.md) §1.1~1.2, §2.1 K5·K7, §2.2 사이드카 경계, §2.3 `worker`·`parser-workers`·`lo-sidecar`·`ocr-gpu` 행, §3.2 O-07·O-10, §3.3 0033행, §4.1 지문·멱등성 키·격리 모드·오류 모델, §4.2 `parse` 행, §4.4 parse 정책, §5.1 `ConvertRequest`/`ConvertResponse` 행, §5.3 `ArtifactRef`·`Producer`·`StageError`·`ProblemDetails`·`Capabilities`·`StagePolicy`, §5.4 `ParsedDocument`(`parser_fingerprint`·`parser_chain`·`artifacts`), §5.6 `PluginMeta`·`ConvertRequest`/`ConvertResponse`, §5.7 `IsolationMode`·`Linkage`·`LicenseGrade`·오류 카탈로그, §6.2 `fingerprint`·`derived`·`parser_fingerprint_hash`, §6.5·§6.6·§6.7, §7.1 `lite` 열, §7.3 `parse.router`, §7.4 (1)·(2)·(10), §10.3 E16·E17, §11.3, §12 `sdk/SidecarStage`·`sidecars/`·의존 방향, §13.3 파생물 키, §14 사이드카 행, §15 리스크 #2·#4·#8, §16 격리 사다리·사이드카 변환 계약
- [기술 지형 종합: 선정 매트릭스](../07-tech-landscape/00-summary-and-selection-matrix.md) 판정 J-1·J-6, `hwp5_parser`·`doc_converter`·`ocr_engine`·`api_framework` 행, 개방 결정 권고 O-07·O-10, 어댑터·플러그인 공통 요구 1·2, ADR 발의 목록 P1·P2
- [01 HWPX/HWP 파싱](../07-tech-landscape/01-document-parsing-hwpx-hwp.md) §후보 C·E, §JPype vs 사이드카, §어댑터 계약(파생 산출물·프로세스 격리·타임아웃), §리소스 요구, §개방 결정 O-10 의견(기각 대안 A1)
- [02 PDF 레이아웃·OCR](../07-tech-landscape/02-document-parsing-pdf-layout-ocr.md) §PaddleOCR 함정(CUDA 결합 → 분리 컨테이너), §RapidOCR
- [03 DOCX/DOC/HTML/TXT 파싱](../07-tech-landscape/03-document-parsing-office-html-text.md) §LibreOffice 사이드카 서비스 설계 제안(운영 규격·헬스·실패 모드), §Tika 4.0, §개방 결정 O-10 의견
- [08 오케스트레이션·메시징·API](../07-tech-landscape/08-orchestration-messaging-and-api-frameworks.md) §Temporal 페이로드 한계, §D gRPC·ConnectRPC·RFC 9457, §O-10 의견
- [12 보안·멀티테넌시·PII·라이선스](../07-tech-landscape/12-security-multitenancy-pii-and-licensing.md) §6.1 등급표, §6.2 의존성 라이선스 지도(H2Orestart·pyhwp·PyMuPDF·LibreOffice)
- 관련 ADR(바이블 §3.3 번호·slug): [ADR-0001](./0001-license-grade-table-and-d02-interpretation.md), [ADR-0003](./0003-orchestrator-neutral-pipeline-and-non-durable-local-runner.md), [ADR-0006](./0006-pdf-fast-path-pypdfium2-pdftext-replaces-pymupdf.md), [ADR-0007](./0007-hwp5-java-sidecar-first-pyhwp-demoted.md), [ADR-0008](./0008-ocr-default-rapidocr-ppocrv5-korean.md), [ADR-0009](./0009-embedding-serving-vllm-pooling-tei-inprocess.md), [ADR-0018](./0018-api-rest-sse-mcp-no-grpc-rfc9457.md), [ADR-0028](./0028-tenant-isolation-tiering-policy.md), [ADR-0032](./0032-plugin-sdk-stage-protocol-and-conformance-kit.md), [ADR-0037](./0037-artifact-cache-scope-and-stage-key-composition.md), [ADR-0038](./0038-outbound-egress-policy-and-webhook-signing.md), [ADR 인덱스](./README.md)
- 이 결정을 전제로 하는 설계 문서(문서 맵): [03-contracts/13 오류 모델](../03-contracts/13-error-model.md) §6.4, [03-contracts/16 평가·피드백·사이드카 계약](../03-contracts/16-eval-feedback-and-sidecar-contracts.md), [02-architecture/05 플러그인 아키텍처](../02-architecture/05-plugin-architecture.md), [02-architecture/08 배포 아키텍처](../02-architecture/08-deployment-architecture.md), [02-architecture/09 실패 모드](../02-architecture/09-failure-modes-and-resilience.md), [04-pipelines/03 파싱 라우터](../04-pipelines/03-parsing-router-and-format-detection.md), [04-pipelines/04 HWPX/HWP](../04-pipelines/04-parser-hwpx-and-hwp.md), [04-pipelines/05 PDF](../04-pipelines/05-parser-pdf.md), [04-pipelines/06 DOC/DOCX](../04-pipelines/06-parser-doc-and-docx.md), [10-development/06 플러그인 개발 가이드](../10-development/06-plugin-development-guide.md)
