---
title: 바이블 개정 요청 통합 목록 (4단계 트리아지 입력)
status: active
owner: architecture
version: 1.0.0
last_updated: 2026-09-23
depends_on: ["04-phase3-document-ledger.md", "../02-architecture/00-design-bible.md"]
generated_by: tools/phase3/ledger.mjs
---

# 바이블 개정 요청 통합 목록

## 목적

3단계 에이전트들이 각 문서의 "## 미해결 이슈"와 결과 JSON `openIssues`에 남긴 항목 전부를 한 곳에 모아, 4단계 T1(Opus 트리아지)의 **단일 입력**으로 쓴다. 트리아지 에이전트는 결과 JSON을 다시 열지 않고 이 문서만 읽는다(앵커 읽기 비용 절감). 기계 생성 문서이며 재생성은 `node tools/phase3/ledger.mjs`.

## 범위

결과 JSON adr-fast.json, architecture.json, audit-2026-09-23.json, contracts-audit.json, contracts.json, finish.json, pipelines-pass1.json. 중복(앞 160자 동일)은 1건으로 병합. "바이블 관련" 판정은 정규식(바이블/§ 언급 + 개정·반영·추가·불일치 등 동사)이며 트리아지에서 재분류될 수 있다.

## 1. 집계

| 구분 | 건수 |
|------|-----:|
| 전체 미해결 이슈(중복 제거) | 480 |
| 바이블 관련(개정 요청 후보) | 200 |
| 문서 내부·기타 | 280 |
| 계약 감사 정본 결정(이미 계약에 적용, 하류 전파 대상) | 47 |

## 2. 바이블 개정 요청 후보 (바이블 절 순)

트리아지 판정 열은 T1 에이전트가 채운다: 채택(patch/minor/major) · 기각 · 보류(ADR-0039+).

| # | 바이블 절 | 출처 문서 | 결과 그룹 | 요청 내용 | 판정 |
|--:|---|---|---|---|---|
| 1 | §1 | 09-normalization-and-cleaning.md | pipelines-pass1 | [교차 문서] 10-chunking §1 `footnote_policy` 기본 attach를 정본으로 인용했으나 미주 `separate` 기본은 10과 합의 필요(미해결 5). 01 §3.2 '05 미해결 이슈 1'은 02-architecture/05-plugin-architecture 미해결 1(ctx.secret 포트)로 해석해 링크 — 01 문서의 표기 정정은 이 문서 범위 밖. | |
| 2 | §1.2 | 03-parsing-router-and-format-detection.md | pipelines-pass1 | ParsedDocument.lineage_refs.source: 이 문서·01은 fetch 출력, 02 §1.2는 detect 출력 — 02 정정 요청 | |
| 3 | §1.2 | 04-scaling-and-performance.md | finish | §1.2 'GPU 워커' 행의 확장 단위 열은 여전히 큐 이름(`ingest-gpu-ocr`·`ingest-gpu-embed`)으로 워커 파드를 가리킨다 — 바로 위 행에 Deployment↔큐 매핑을 추가해 해석이 명확해졌으므로 추가 수정하지 않았다. | |
| 4 | §1.2 | 08-upgrade-and-migration.md | finish | §1.2·§1.4·§2.2·§8.2의 '**제안:**' 표기는 유지 — 릴리스 프로세스(review)가 채택했으나 ADR(0039 slug 제안)이 아직 없어 앵커 규칙상 결정으로 승격하지 않음. | |
| 5 | §2.1 | 03-parsing-router-and-format-detection.md | finish | 반영하지 않은 리뷰 항목 없음(3건 모두 반영). 리뷰어가 제시한 두 대안 중 §2.1 문장을 '0.6까지 허용'으로 바꾸는 안은 채택하지 않았다 — 정본 02 §4.1은 가산을 9~11행에만 두고 12행(힌트 전용)은 0.5이므로 §2.5 가산을 신호 기반 판정에 한정하는 두 번째 대안이 정본과 일치한다. | |
| 6 | §2.2 | 00-contract-overview.md | contracts | 13-error-model 소유 파일(schemas/stage-error.schema.json, problem-details.schema.json)은 이 작업 범위 밖이라 수정하지 않았다. 00의 $defs와 필드 집합·제약은 동치로 맞췄으나, 두 파일을 $ref 래퍼로 전환하고 자기 $defs/ErrorCode·$defs/ErrorLocation을 제거하는 작업은 13 문서 개정(13 미해결 이슈 12)에서 해야 한다. 또한 13 §2.2 본문은 '제안 필드는 스키마·모델·예시에 없다'고 하는데 실제 13 파일에는 있어 13 내부 불일치가 남아 있다. | |
| 7 | §2.2 | 01-pipeline-framework.md | pipelines-pass1 | [미반영·이유] 리뷰(anchor) '§2.2 detect 행 vs §2.5 금지' 및 (tech) 'detect 서브스테이지' 항목 중 '`detect`를 캐시 비대상 인프로세스 서브스텝으로 내리는' 대안은 채택하지 않음 — 바이블 §4.2 표가 detect에 별도 stage_key를 정본으로 두므로 셸 소유 SubstageRunner(§5.6)로 구현. 04-pipelines/03(동시 작성 중)과의 합의 항목(format_detector 프로파일 위치, lineage_refs.source가 실을 SourceDocument 참조)은 미해결 이슈 18로만 등재. | |
| 8 | §2.2 | 01-system-overview.md | architecture | 바이블 §2.2 C4 다이어그램의 Rel(api, s3) 누락과 §14 테넌트 생성 API 부재는 본 문서 권한 밖이라 미해결 이슈 11·12로 바이블 소유자에게 갱신 요청만 등록했다(바이블 §1.2 절차). | |
| 9 | §2.2 | 02-source-document.md | contracts | [미반영] 리뷰(anchor·tech) 'authors 32 / tags 항목 64자 / custom 32키'로 맞추라는 지시: 01-ingest-request 실제 스키마·§2.2·§2.3·V10·IR-8은 authors 64, tags 항목 128자, custom 64키이며 01이 이미 02와 정합해 둔 값이라 01 정본을 유지했다(title 512·doc_type 패턴·uniqueItems·custom 키 패턴·string 1,024는 반영). | |
| 10 | §2.2 | 03-coding-standards.md | finish | 부수 관찰(수정 범위 밖): 문서 전반에서 '01 §x'가 10-development/01(저장소 구조)과 04-pipelines/01(파이프라인 프레임워크)을 모두 가리켜 모호함 — 이번 수정 지점(§2.2 주석·§10.2)만 '04-pipelines/01 §2.5'로 명시했고 나머지는 기존 표기 유지. | |
| 11 | §2.2 | 06-parser-doc-and-docx.md | pipelines-pass1 | parser_fingerprint.parser_version 다중 패키지 연결(';') 규약이 03 §2.2·바이블 §5.4의 단일 패키지 전제와 다름 — patch 제안 | |
| 12 | §2.2 | 13-indexing.md | pipelines-pass1 | [타 문서 제안] 08 §2.2 `backend_version` 문구('capabilities() 보고값')를 '어댑터 backend_version 속성(capabilities() 호출 시 조회)'로 정정하는 patch 제안(미해결 2); 바이블 §11.4 1670행 Note 세미콜론 patch 제안(미해결 17). 이 문서는 다른 파일을 수정하지 않았다. | |
| 13 | §2.2 | 15-collection-profile-and-policy-contracts.md | contracts | [minor, 대안 채택] 계약 간 교차 `$ref`: common-types 승격은 00 문서 권한이라 미해결 이슈 13으로 제안하고, 그때까지 profile/collection-spec 자기 `$defs` 사본 + CI 동치 대조로 처리(07 §2.2 선례). | |
| 14 | §2.3 | 05-plugin-architecture.md | architecture | build() -> Stage[Any, Any] 반환 타입: 질의 측을 Stage로 되돌려 리트리버·퓨저 문제는 해소됐지만 IndexBackend·role 포트(ContextRenderer·TokenCounter·KoreanAnalyzer)는 여전히 Stage가 아니므로 정적 타입 불일치가 남는다. 02 §2.3 개정 제안(반환 타입 합집합 또는 build_port())으로 §6.3 표·미해결 이슈 11에 명시했다. | |
| 15 | §2.3 | 08-index-commit.md | contracts | [미반영·타 문서] 07 미해결 이슈 3(visual-pages 변형의 `page_*` 공간 키)에 08의 기존 `page_*` 3키를 합류시키는 것은 07 문서 소유이므로 08 §2.3에서 참조만 했다. 07 편집자가 `EmbeddingSpaceIds` 변형을 추가하면 08은 `$ref`로 자동 반영. | |
| 16 | §2.4 | 01-deployment-guide.md | finish | 마이그레이션 로그인 역할의 rag_owner 멤버십(GRANT rag_owner TO rag_platform_admin)은 저장소 아키텍처 §2.4에 없는 이 문서의 제안이므로 미해결 이슈 3으로 남김(저장소 아키텍처 patch 또는 설정 레퍼런스 확정 필요) | |
| 17 | §2.4 | 01-pipeline-framework.md | pipelines-pass1 | [확인 요망] 05 §2.4('StageFailure 이외 예외 → contract.violation')와 02 §6.1 B2(재시도 가능 취급)의 충돌을 이 문서가 B2로 확정(§10.2, 미해결 이슈 3). 05 문서 patch가 반영되기 전까지 두 문서가 상충 상태. | |
| 18 | §2.4 | 05-plugin-architecture.md | architecture | ContextRenderer의 plugin_id: 02 §2.4 코드에는 없으나 05는 레지스트리 조회 키로 유지하고 '보완 제안'으로 표기했다(미해결 이슈 11). TokenCounter·KoreanAnalyzer 코드(§2.2)는 02와 동일하게 plugin_id 없이 두었다. | |
| 19 | §2.5 | 03-data-flow-and-document-lifecycle.md | architecture | [major 일부 미반영] 리뷰어의 (c) 주장 'A-6 `rollback_green`이 current_commit_id를 previous_commit_id로 되돌리고 green 커밋을 rolled_back으로 표시' 는 현재 06-orchestration §2.5(199행 A-6 `ledger.discard_green`, 283행 본문 결정)에 존재하지 않는다 — 06이 검증 중 개정되어 본 문서 제안을 채택했으므로 '상충'이 아닌 '채택·ADR-0026 개정 발의'로 기술했다. 리뷰어의 '바이블 §11.4 (5) 기준 06 개정 요청' 도 그대로 쓰지 않았다: 바이블 §13.4가 두 해시 불변 변경의 green 이름을 정하지 않아 대안 (a)(b) 모두 바이블 개정이 필요하므로, 본 문서는 모드 B 불채택 입장만 명시하고 택1·개정 방향은 미해결 11(=06 미해결 15)의 ADR로 넘겼다. | |
| 20 | §2.5 | 08-index-commit.md | contracts | [미반영] anchor 리뷰 이슈 1의 대안 경로("비재사용 주장 삭제")는 채택하지 않음 — 02-architecture/06 §2.5·§3.2와 03 §8.1이 이미 max+1·비재사용을 확정했으므로 권장안(max+1 통일)을 택했다. 바이블 §13.1에 `last_generation` 컬럼을 추가하는 안은 바이블에 없어 결정으로 쓰지 않고 미해결 14의 대안으로만 등재. | |
| 21 | §2.5 | 08-index-commit.md | contracts | [미반영] tech 리뷰가 언급한 `CommitStatus` 값 추가(예: discarded)는 채택하지 않음 — 06 §2.5 A-6이 폐기 green 커밋을 committed로 유지하기로 결정했고 열거 추가는 CI 열거 대조·소비자 배포 순서(14 §2.2 부류 A) 영향이 커서 미해결 6에 비권장으로 기록. | |
| 22 | §2.5 | 17-post-processing-and-context-packing.md | pipelines-pass1 | [tech minor §2.5 177행] 'used = sum(r.token_count_primary …)'로 고치라는 제안은 문자 그대로 반영하지 않음 — anchor 리뷰대로 RankedResult(바이블 §5.5·common-types)에 token_count_primary가 없음. child_tokens() 재카운트 헬퍼(초안) + 미해결 이슈 3(hydrate with_payload·RankedResult에 token_count_primary·ordinal 추가)으로 처리. | |
| 23 | §2.8 | 02-epics-and-backlog.md | finish | T-MGT-30 의존 변경으로 §2.8 '에픽 간 의존' 문단은 수정 불필요(T-CHK-23 언급 없음)했으나, 마일스톤 문서(01-milestones.md) 쪽에 T-MGT-30/T-CHK-23 의존을 인용한 문장이 있는지는 이 태스크 범위 밖이라 확인하지 않았다. | |
| 24 | §2.8 | 17-post-processing-and-context-packing.md | pipelines-pass1 | [검증 중 발견, 리뷰 외] diagnostics.filters_applied.security — 11 §2.8 본문은 principals_count, 11 저장 스키마(context-pack.schema.json $defs/FiltersApplied→SecurityFilter)·11 예시 1은 principals[] 필수·additionalProperties false. 이 문서는 저장 스키마를 따라 principals[]로 예시를 고쳤고(§3.7에 병기), 11 본문/스키마 불일치는 11 미해결 이슈 3의 소관으로 남김(11 파일은 수정하지 않음). | |
| 25 | §2.9 | 05-chunk-set.md | contracts | table_cell_views 채택으로 `type=table` 블록 + pii_policy_applied≠keep 문서는 뷰가 실질 필수가 되어 04 §2.9 필수 조건·바이블 §5.4 등재(이슈 13, 04 이슈 2)가 함께 확정되어야 함 — 04 문서 측 갱신은 이 작업 범위 밖 | |
| 26 | §2.9 | 17-post-processing-and-context-packing.md | pipelines-pass1 | [anchor major §2.9 부스트 위치] 리뷰가 요구한 '부스트를 fuse/rerank 반영으로 돌리고 apply_boosts 삭제'는 반영하지 않음. 근거: 15-hybrid-search-and-fusion §8 현재 본문은 '부스트의 kind·판정 원천·delta·적용 시점 정본은 17 §2.9(relevance_gate 뒤·mmr 앞)이며 fuser·retrieve는 부스트를 계산·가산하지 않는다'로 확정되어 리뷰가 인용한 15 §8 문구(fuser 가산·2^(−age/365))는 구버전이고, 바이블은 위치를 정하지 않음. 대신 header.title→title 정정, 전 프로파일 기본 끔, 권위 부스트 미지원, 10 §9 explain 표(boost_* fuse 행) patch 제안(미해결 이슈 14)을 반영. | |
| 27 | §2.15 | 06-parser-doc-and-docx.md | finish | Docling 잠금 버전은 문서 간 상이(기술 지형 03: 2.128.0 소스 확인 / 선정 매트릭스 이슈 8: 2.129.x 권고). 이 문서는 값을 단정하지 않고 uv.lock을 정본으로 위임했으므로 잠금 확정 시 §2.15 예시값만 갱신하면 된다(미해결 이슈 13과 연동). | |
| 28 | §3 | 03-retrieval-api.md | finish | 문서 기존 미해결 이슈 1~17은 그대로 유지(이번 리뷰 범위 밖). 특히 이슈 13 상류 불일치(09 §3 Cedar action=query vs 07 §4.1 search)와 이슈 14(보안 필드 거부 400 vs 바이블 422)는 상류 patch가 필요한 앵커 충돌로 남아 있다. | |
| 29 | §3 | 06-enriched-chunk-set.md | contracts | 04-pipelines/11 §3 `G` 행의 "≤ 100토큰"은 규칙 2(b)(generated == summary ≤ 1,024 코드포인트)와 여전히 충돌한다 — 지정 파일이 아니어서 수정하지 않았고 미해결 이슈 13에 patch 요청으로만 기록했다(04-pipelines/11 소유자가 예외 문구 추가 필요). | |
| 30 | §3 | 12-embedding.md | pipelines-pass1 | 07 계약 문서 §3 예시 `"int8"`→`onnx_int8` 대체, 06 `enricher.pipeline`·09 `query_transformer.pipeline`과의 `{extension_point}.pipeline` 단일 규약 공동 발의, 15 `EmbedConfig.sparse_bm25.avgdl`(N)·`dense.prompts`(N) 등재는 타 문서 수정이 필요해 이 문서 미해결 이슈(5·7·8·9·17·18)로만 남겼다. | |
| 31 | §3 | 18-advanced-retrieval-graph-raptor-agentic.md | pipelines-pass1 | 리뷰에서 요구하지 않았지만 관련 문서(11-enrichment §3 표 10행, 05 C-3, 13 §4.1, 09 §7.4 '팩에 전파' 문구)의 patch는 각 소유 문서에서 별도 수행해야 한다(이 문서는 제안만 기록) | |
| 32 | §3 | 19-update-delete-and-reindexing.md | pipelines-pass1 | 미반영: 리뷰 fix 중 '이름 불변 백엔드에는 is_current=false로만 적재하고 교체 시점에 일괄 플립' 대안 — committed 상태 의미(플립 완료)와 08 §3 상태 기계에 어긋나는 계약 변경이라 채택하지 않고 미정으로 처리. | |
| 33 | §3.1 | 06-parser-doc-and-docx.md | pipelines-pass1 | 03-contracts/03 §3.1 element_path 표에 DOCX 행 분리(OOXML 요소 경로 정본; Docling self_ref 행은 PDF·HTML 2차로 한정) — patch 제안 | |
| 34 | §3.1 | 14-schema-versioning-and-compatibility.md | contracts | [tech minor VersionedEnvelope additionalProperties] additionalProperties를 추가하는 대신 00 §3.1 결정(봉투는 별도 $defs 없음)에 따라 `$defs/VersionedEnvelope` 자체를 삭제해 해소했다. Pydantic 베이스 클래스는 코드 수준으로만 유지. | |
| 35 | §3.1 | 17-post-processing-and-context-packing.md | pipelines-pass1 | [anchor minor §3.1 safety_margin 원천] cfg(plan.pack) 대신 프로파일 query.pack.tokenizer.*를 PackContext가 읽는 것으로 정정. 09 PackPlan에 calibration_ratio·safety_margin(N) 추가는 미해결 이슈 15로 제안만(09 문서는 수정 권한 외). | |
| 36 | §3.2 | 01-system-overview.md | architecture | 리뷰 항목 'C-17 → 각주 이동'은 각주 대신 §3.2 표 아래 '표 밖 항목' 목록으로 구현했고, 결정 사항의 '(+ 외부 관측 백엔드)' 표현은 리뷰 제안대로 유지했다(의미 동일, 형식만 차이). | |
| 37 | §3.2 | 01-system-overview.md | architecture | 리뷰 대안 '컨테이너 라벨에 (standard+)/(premium) 접미 일관 부여'는 채택하지 않고 §3.2 표의 lite 포함 열 참조 방식을 택했다(parser-workers 라벨에만 'standard 이상' 추가). 라벨 접미 일관화가 필요하면 후속 개정에서 처리. | |
| 38 | §3.2 | 02-fetching-and-source-resolution.md | finish | 13-error-model §3.2·02-source-document §7의 `fetch.scheme_unsupported` 설명 patch(미해결 이슈 18)는 이 문서가 요청만 하며 해당 문서는 수정하지 않았다(다른 에이전트 소유). | |
| 39 | §3.2 | 02-source-document.md | contracts | [후속] 미해결 이슈 8·12·13·14·15·16은 00(common-types $defs 승격, §3.2 detect 행, Pydantic Bcp47), 15(EgressPolicy strip_query_keys), 바이블(§4.2·§5.4 fetch 잠정값 규약, §7.1 standard 열 Tika 표기) 소유자 반영이 필요하다. | |
| 40 | §3.2 | 03-data-flow-and-document-lifecycle.md | architecture | [minor 3 부분] O-11·O-12 번호는 '후보'로만 제안했다. 바이블 §3.2(및 브리프 §5)의 개방 결정 목록은 O-01~O-10으로 닫혀 있어 새 번호 배정은 바이블 소유자(patch)의 몫이며, 배정 전까지 `**미정(O-xx 미배정, 미해결 n):**` 표기를 쓴다. | |
| 41 | §3.2 | 05-ci-cd.md | finish | 리뷰 minor 3(quality-gate 예산)에서 '8분으로 올리고 §3.2·§4.7 갱신' 대안은 채택하지 않음 — 정본 §3.2 표·04 §19(품질 층 5분)에 스케치를 맞췄다. compose 기동 포함 5분이 실측에서 부족하면 §3.2 표·04 §19를 함께 minor 개정해야 함(초안 목표). | |
| 42 | §3.2 | 05-parser-pdf.md | pipelines-pass1 | bbox 좌표 프레임: 이 문서(표시 페이지 프레임으로 역변환) vs 03-contracts/03 §3.2('보정 후 좌표') 문구 정합 필요(03 patch 제안) | |
| 43 | §3.2 | 06-parser-doc-and-docx.md | pipelines-pass1 | Provenance.section_index를 OOXML w:sectPr 구역에도 허용할지(현재 page_break.section_index에만 기록) — 03 §3.2·바이블 §5.3 minor 제안 | |
| 44 | §3.2 | 09-normalization-and-cleaning.md | pipelines-pass1 | [교차 문서] `model_ids`의 `dict:{dictionary_hash}`가 컬렉션마다 달라 01 §3.2 'profile_hash당 1회' 인스턴스 규약과 충돌 가능 — 미해결 21로 01에 합의 요청, 이 문서에서 단정하지 않음. | |
| 45 | §3.2 | 18-advanced-retrieval-graph-raptor-agentic.md | pipelines-pass1 | RAPTOR 배치 (a)/(b) 중 어느 안을 이 문서가 선호하는지는 적지 않았다 — 바이블 §3.2 O-03이 `enricher`를 명시하고 §12가 `adapters/enrich/raptor_tree.py`를 두므로 개별 문서가 단정할 수 없어 ADR-0015 개정에 위임 | |
| 46 | §3.3 | 05-benchmark-plan-and-baselines.md | finish | 미반영(범위 외, 이번 리뷰 항목 아님): 2차 셋 `allganize-ko`에서 B0~B2를 돌리려면 그 코퍼스에도 `C_flat` 상당 컬렉션이 필요하다는 점은 §3.3 '계수하지 않음' 문장으로만 처리했고 별도 컬렉션 수를 추가 산정하지 않았음. | |
| 47 | §3.3 | 06-parser-doc-and-docx.md | pipelines-pass1 | 02-architecture/08 §3.3 lo-sidecar '요청별 임시 프로파일'과 이 문서 '슬롯 고정 프로파일 재사용' 불일치 — 콜드스타트 실측 후 08 patch | |
| 48 | §3.3 | 09-normalization-and-cleaning.md | finish | 계약 04 §3.3 M5 예시 문구(`CR LF→LF` 불투명 구간)와 이 문서의 M6 통일 표현 정합은 계약 04 소유 — 미해결 이슈 1에 patch 제안으로만 기록, 계약 04 파일은 수정하지 않음. | |
| 49 | §3.3 | 14-schema-versioning-and-compatibility.md | contracts | 13-error-model §3.3 제안 표에 contract.schema_type_mismatch·contract.upcast_failed·render.template_unsupported 추가 요청(미해결 이슈 8) — 13 문서 소유자 반영 필요. | |
| 50 | §3.5 | 17-post-processing-and-context-packing.md | pipelines-pass1 | [tech minor §3.5 7항 pii_policy] 원천을 '프로파일 ingest.normalize.pii.policy를 PackContext가 읽음(초안)'으로 잠정 결정하고 IndexRecord.pii_policy_applied hydrate 추가 vs QueryPlan 복사 택1은 미해결 이슈 16으로 등재(확정은 09/10/바이블 patch 필요). | |
| 51 | §3.9 | 09-normalization-and-cleaning.md | pipelines-pass1 | [minor, 부분 반영] §3.9·§3.13 글머리 목록에 리뷰어가 제안한 `ㆁ`(U+3181, 옛한글)은 넣지 않음 — 현대 공문서 글머리 근거 없음. `ㅁ`(U+3141)은 '실무 □ 대용'으로 포함했으나 초안 목표로 표기하고 미해결 18에서 골든셋 확정 대상으로 남김. | |
| 52 | §4 | 01-api-design-guidelines.md | finish | 잡 접수형 DELETE의 멱등 지문 규칙(wire_body를 {}로 둠)은 이 문서가 정한 규칙이며 수집 요청 계약 §4의 공식을 확장한 것 — 관리 API·갱신·삭제 문서 게시 후 대조 필요. | |
| 53 | §4.1 | 01-pipeline-framework.md | pipelines-pass1 | [확인 요망] 바이블 내부 표기 불일치: §4.1 일반식(input_ref.blake3)과 §4.2 detect·parse 행(content_hash)·recount 행(tokenizer_id). 이 문서는 '입력 해시는 §4.2 행별, 5번째 인자는 항상 fingerprint()'로 읽고 미해결 이슈 16에 바이블 patch를 제안함 — 바이블 소유자 확인 필요. | |
| 54 | §4.1 | 02-component-architecture.md | architecture | [설계 판단, 2차 리뷰 확인 요청] 질의 측 5종 확장 지점을 별도 프로토콜(리뷰 대안 b) 대신 `Stage[In, Out]` 특수화(대안 a)로 통일했다. 이는 바이블 §4.1(모든 스테이지 5멤버)·ADR-0032·D-10을 따르는 선택이지만 05-plugin-architecture의 `search(channel, variant, plan, security, ctx)`·`fuse(candidates, fusion, top_n)`와 시그니처가 갈리므로 05 문서 개정이 필요하다(미해결 이슈 4에 명시). 또 `StageContext.plan`(질의 측 QueryPlan) 멤버 추가가 바이블 §4.1 patch를 전제한다(미해결 이슈 2). | |
| 55 | §4.1 | 03-observability.md | finish | minor 6의 fix 제안 중 '§4.1·§4.3에 queue=serving 예외 명시' 대안은 채택하지 않고 별도 메트릭 분리 대안을 택했다(§9.3 원장 정합 검사와 충돌하기 때문). §4.3은 outcome 어휘 표라 queue 어휘를 넣지 않고 §4.1에 명시했다. | |
| 56 | §4.1 | 04-management-api.md | finish | 07 §4.1 `manage_tenants` 행 정정은 07 문서 소유이므로 이 문서에서는 §미해결 이슈 12의 요청으로만 남김(07 파일은 수정하지 않음) | |
| 57 | §4.1 | 05-chunk-set.md | contracts | 청커의 ParsedDocument 접근(ctx.lineage)은 바이블 §4.1 '`requires_lineage`는 index만' 문구와 어긋나므로 문서는 전제로만 두고 바이블 §4.1·§4.2 개정 제안(이슈 12)으로 남김 — 바이블 소유자 확정 필요 | |
| 58 | §4.1 | 05-plugin-architecture.md | architecture | StageContext.plan·artifacts(DerivedArtifacts)는 02에서도 제안 지위이므로 05도 제안으로 표기했다. 바이블 §4.1 표 갱신(02 미해결 이슈 2·10)이 선행돼야 결정으로 승격 가능. | |
| 59 | §4.1 | 07-backup-and-disaster-recovery.md | finish | 관찰(리뷰 범위 밖, 수정하지 않음): §4.1 OpenSearch 물리 인덱스 행이 RB-03을 참조하는데 06-runbooks에는 전용 RB-16(OpenSearch 클러스터 red)이 있다. 장애 모드 §9 색인은 RB-01~RB-12까지만 정의하므로 이 문서의 참조 범위와 일관되지만, 런북 문서 소유자가 RB-16을 색인에 올리면 해당 행 갱신을 검토할 것. | |
| 60 | §4.1 | 07-backup-and-disaster-recovery.md | finish | 관찰(수정하지 않음): §4.1 Object Storage 버킷 전체 손실 행이 'RB-05 준용'(디스크 풀 런북)을 쓴다. 전용 런북이 없어 준용으로 남긴 것이며 06-runbooks 소유자 판단 사항. | |
| 61 | §4.1 | 07-embedded-chunk-set-and-index-record.md | contracts | 새로 등재한 미해결 이슈 11~13은 바이블 §4.1·§4.2·§6.2 patch 및 ADR-0012 문구 정합 제안이므로 architecture 소유자의 바이블/ADR 반영이 필요하다. | |
| 62 | §4.1 | 07-multi-tenancy-and-security-architecture.md | architecture | §4.1 수정으로 '`tenant_admin`이 스스로에게 `pii_officer`를 부여'하는 경로의 직무 분리 통제는 09-operations/05(ISMS-P 매핑)로 위임됐다 — 해당 문서가 이를 받아야 한다(기존 미해결 이슈에 별도 항목으로 추가하지는 않았고 본문 문장으로만 위임). | |
| 63 | §4.1 | 11-enrichment.md | pipelines-pass1 | stage.enrich_llm의 requires_lineage=("ChunkSet",) 사용은 바이블 §4.1(index 한정)과 충돌 — §4.1·§4.2 patch 필요 | |
| 64 | §4.1 | 12-embedding.md | pipelines-pass1 | §4.1 sparse-encoder-server 엔드포인트는 (a) 이 문서 결정 승격이 아니라 (b) '제안 + 요청/응답 스키마 초안'으로 처리했다 — 08 미해결 이슈 17이 03-contracts/16과의 공동 확정을 요구하고 엔진(TEI 대체) 확정도 05 미해결 이슈 2 뒤로 유보되어 있어 단독 결정이 앵커 위반 위험이 있었기 때문. | |
| 65 | §4.1 | 18-advanced-retrieval-graph-raptor-agentic.md | pipelines-pass1 | tech major(HNSW) (b) `{m: 0, payload_m: 0}`은 리뷰어 제안대로 채택했으나 13 §4.1은 `{m: 0}`만 적고 있어 벡터별 `hnsw_config`가 전역 `payload_m: 16`을 덮어쓰는지 Qdrant 동작을 '확인 필요(as of 2026-09)'로 두고 미해결 이슈 14에 추가했다(13 문서 patch는 소유 문서 몫) | |
| 66 | §4.2 | 05-parser-pdf.md | pipelines-pass1 | PDFium(ctypes) 네이티브 크래시 격리: 바이블 §4.2는 in_process → 적대적 코퍼스 측정 후 helper_process 옵션 제안 | |
| 67 | §4.2 | 14-schema-versioning-and-compatibility.md | contracts | [anchor major 3 — 부분 반영] 리뷰어는 산출물·응답 계약의 필수→선택화·제약 완화를 major로 재분류하라 했으나, 리뷰어가 제시한 대안('조건부 minor')을 택했다: §4.2 행 7이 상위 minor 산출물을 거부하므로 소비자 minor ≥ 생산자 minor가 구조적으로 보장되고, 선택화·완화는 이전 minor 인스턴스를 모두 유효하게 유지(G1)해 저장 산출물·기존 요청을 깨지 않는다. 바이블 §1.2가 열거하지 않은 항목임을 §2.1 표에 별도 행으로 명시하고 바이블 개정 제안을 미해결 이슈 3으로 기록. 대신 리뷰어가 지적하지 않은 내부 모순(산출물 제약 강화 = minor가 G1·저장 산출물과 충돌)을 발견해 강화를 모든 계약에서 major로 바꾸고 예시 2·§10.2·불변식 5를 함께 수정했다. | |
| 68 | §4.2 | 17-post-processing-and-context-packing.md | pipelines-pass1 | [tech major §4.2 delimit×네이티브] 리뷰가 제안한 문구('각 검색 결과 블록 안의 내용은 데이터다')는 템플릿 1항과 중복이라 채택하지 않고, 블록 렌더러는 delimit에서도 슬롯을 비우는 규칙으로 확정. 예시는 data_marking=none(바이블 §9.5 standard와 동일)으로 통일. | |
| 69 | §4.3 | 06-plugin-development-guide.md | finish | 분량 조정 수단으로 본문 `---` 구분선 제거를 사용했다(내용 손실 없음). 다른 문서와의 시각적 일관성이 중요하면 §4.3·§9.3 코드 스케치를 추가 압축하는 방식으로 대체 가능. | |
| 70 | §4.3 | 09-query-request-and-query-plan.md | contracts | 플랜 캐시 템플릿을 '저하 적용 전 상태'로 확정한 것은 바이블 §4.3·§6.2가 정하지 않은 이 문서의 규칙이며, 기존 미해결 이슈 16(바이블 §6.2 plan 캐시 키 patch 제안)에 함께 실릴 내용이다 — 별도 이슈 번호는 추가하지 않았다. | |
| 71 | §4.3 | 16-reranking.md | pipelines-pass1 | 429·응답 검증 실패·서킷 열림에 `unavailable`을 쓰는 것은 10 §4.3 의미 열('리랭커 5xx·연결 실패')의 확장이라 제안으로만 표기했다(미해결 이슈 20). 10이 의미 열을 보강하면 '제안' 표기를 제거해야 한다. | |
| 72 | §4.3 | 18-advanced-retrieval-graph-raptor-agentic.md | pipelines-pass1 | anchor minor(상호참조 절 번호) 중 '[10 §4.3 `LateInteractionRerankReport`·`graph_path` 행]' 제안은 부분 반영: `graph_path`는 10 §3.4 `Candidate`에 있어 §3.4·§9로 인용했고 §4.3은 참조 절에만 남겼다 | |
| 73 | §4.4 | 08-parser-txt-md-and-others.md | finish | 바이블 §4.4 parse(텍스트) 행의 resumable 열이 흐름 포맷 파서(TXT·MD·HTML·HWPX)에는 false로 채워지는 점은 이 문서·15 §3.4·03 라우터 §5.3이 서로 정합하지만, 바이블 §4.4 표 자체에 '후보별 Capabilities로 결정' 비고가 없어 독자 혼동 소지가 남는다(바이블 patch 제안은 03 라우터/15 문서 소관으로 두고 이 문서에는 새 이슈로 추가하지 않았다). | |
| 74 | §4.4 | 08-release-process.md | finish | 리뷰어 제안 중 §4.4 예시를 '한 줄 안내' 또는 '{field} 플레이스홀더' 택일로 제시했으나 둘 다 적용했다(오독 방지 효과가 겹치지 않으므로 중복 아님). | |
| 75 | §4.4 | 13-indexing.md | pipelines-pass1 | [확인 필요] Qdrant `DatetimeIndexParams`가 `range`를 받지 않는다는 판단은 07-tech-landscape/06에 근거가 없어 '확인 필요(as of 2026-09)'로 표기하고 04 §4.4 정정 제안을 미해결 5에 병기했다 — 구현 스파이크에서 확인 필요. | |
| 76 | §4.5 | 05-parser-pdf.md | finish | 04-pipelines/03 §4.5·미해결 이슈 9는 여전히 `parse.pdf.route` 값을 `auto \| born_digital \| scanned \| mixed`(source_kind 강제)로 제안하고 있어 03-contracts/01 §2.5(라우트 이름)와 충돌한다. 이 문서는 03-contracts/01을 따랐고 충돌은 미해결 이슈 19로 기록했다. 04-pipelines/03 문서 자체의 정정은 이 작업 범위 밖(지정 파일만 수정). | |
| 77 | §5 | 09-normalization-and-cleaning.md | pipelines-pass1 | [부속 파일 없음] 이 문서는 schemas/*.schema.json을 소유하지 않으며(normalized-document.schema.json은 계약 04 소유) 스키마 파일 변경 없음. 계약 04에 요청한 정정(§5 web_article 조건, §8 dictionary_hash 행 예외, I-8·I-13 개정)은 미해결 1·4·10·19로 등재. | |
| 78 | §5 | 13-error-model.md | contracts | 리뷰 blocker/major (anchor·tech) '제안 필드 제거' 지시는 문자 그대로 반영하지 않음: 작업 중 depends_on 00 문서가 U-12로 해당 7필드·ErrorLocation·instance uri-reference를 common-types $defs에 선택(N) 필드로 수용해 두 정의가 동치가 되었고 바이블 §5 서문이 N 필드 추가를 허용하므로, 리뷰어의 대안 (b)에 해당하는 상태로 정합했다(필드는 N(U-12) 표기, 바이블 §5.3 표 갱신 ADR은 이슈 1로 유지). 00 §2 '전환 상태' 문단·§10.3 전환 규칙은 00 소유라 수정하지 않았고 전환 완료 갱신을 이슈 12에서 00에 요청했다. | |
| 79 | §5.1 | 02-component-architecture.md | architecture | [미반영] 리뷰 tech-minor '`VectorBundle`은 바이블에 없는 새 타입' — 바이블 §5.1 공용 타입 목록과 §5.4 `EmbeddedChunkSet` 표(L349, L689)에 `VectorBundle`이 정본으로 존재하므로 '제안' 표기·미해결 이슈 등재를 하지 않았다(앵커 우선). | |
| 80 | §5.1 | 14-schema-versioning-and-compatibility.md | contracts | [anchor minor §5.1 골든 예시 — 리뷰어 주장 불일치] 리뷰어가 인용한 '00 §10.3 schemas/examples/(초안 위치)'와 '00 미해결 U-12'는 00-contract-overview에 존재하지 않는다(00 미해결 이슈는 U-1~U-10, §10.3은 '골든 인스턴스의 정본은 문서 자체'). 00 §10.3 실제 문구에 맞춰 정본 = 문서 `## 예시`, 이전 버전 파일 보존 경로 tests/contracts/golden/은 제안(10-development/04 확정)으로 두었다. | |
| 81 | §5.2 | 07-embedded-chunk-set-and-index-record.md | contracts | 리뷰어 fix 중 택1: quality 쟁점은 '초안 표기 + 미해결 이슈' 대신 13 §5.2 손실 규칙에 맞춰 `truncated → quality=degraded`를 초안 규칙으로 채택하고 V-5·Pydantic에 반영했다(리뷰어의 두 번째 대안). 바이블 §4.2 embed 행이 반대로 확정되면 V-5·검증기 완화 필요(미해결 이슈 12). | |
| 82 | §5.2 | 10-candidate-set-and-ranked-set.md | contracts | `retriever.pipeline`(producer.plugin_id 합성 값)은 09의 `query_transformer.pipeline` 선례를 따른 제안이며 바이블 §5.2/§6.1 미등재 — 이슈 11로 patch 제안 | |
| 83 | §5.2 | 15-hybrid-search-and-fusion.md | pipelines-pass1 | 미해결 이슈 11(c) 02-architecture/04 §5.2 `index_text.bigram` → `cjk_bigram` 정정은 04 문서 소유(13 미해결 14와 공동 제안)로 남김. | |
| 84 | §5.3 | 00-contract-overview.md | contracts | ProblemDetails.instance를 바이블 §5.3 표기 string(uri)와 다르게 string(uri-reference)로 두었다(RFC 9457 §3.1.5, 13 파일, 두 리뷰어 일치). 바이블 patch 제안으로 U-12(b)에 기록했으며 바이블 개정 전까지는 표기상 차이가 남는다. | |
| 85 | §5.3 | 03-parsing-router-and-format-detection.md | pipelines-pass1 | 03 §5.3 (e) len(parser_chain)>1 문구를 '실패 뒤 성공'으로 정정 요청 | |
| 86 | §5.3 | 04-parser-hwpx-and-hwp.md | finish | 타 문서에 남는 정정 요청(이 문서가 수정할 수 없어 미해결 이슈로만 등재): 03-contracts/03 §5.3 (e) 문구·§3.1 caption 경로·§5.1 flow 행 source=ocr, 바이블 §9.5 element_path 예시·§12 hwpx_hwpxlib_sidecar 등재, 04-pipelines/01 §3 원본 바이트 포트, 02-architecture/08 §5.2 parser-workers Object Storage egress, 04-pipelines/03 §7.2 변환기 digest 기록 규약. | |
| 87 | §5.3 | 06-parser-doc-and-docx.md | pipelines-pass1 | 03 계약 P-1('사이드카면 producer.image_digest = sidecar_image_digest')·§5.3 (e)(len(parser_chain)>1 ⇒ degraded)가 then 변환 경로를 상정하지 않음 — 라우터 §6.4 정밀화 반영 patch(라우터 이슈 12와 공동) | |
| 88 | §5.3 | 07-parser-html.md | finish | 리뷰 7건 모두 반영(미반영 항목 없음). 다만 major 2의 처리에서 `docling_direct`·표 컨테이너 DOM 모드를 degraded로 둔 근거('본문 영역 판정 실패로 보일러플레이트가 furniture=false로 잔존'은 03 §5.3 (a)~(d)에 없는 이 문서 고유 손실 조건)는 라우터 §6.4의 '어댑터가 손실을 직접 아는 경우 표기' 규칙에 의존하며, 03 §5.3 (e) 확정 시 재검토 대상으로 미해결 이슈 14에 남겼다. | |
| 89 | §5.3 | 07-parser-html.md | finish | 교차 문서 충돌(이 문서 소유 아님): 03-parsed-document §5.3은 (e)를 미정으로 두는데 04-pipelines/03 §6.4는 (e)를 '실패 뒤 성공 = degraded'로 결정하고 03 문구 정정을 요청(라우터 미해결 12, 03 미해결 5). 이 문서는 두 문서와 모두 모순되지 않는 범위(어댑터 내부 사다리는 손실 기준)로 서술했으나 최종 정합은 03·라우터 문서 측 확정이 필요하다. | |
| 90 | §5.3 | 09-normalization-and-cleaning.md | pipelines-pass1 | [major, 선택지 중 하나 채택] N2 I-8 충돌: 리뷰어가 제시한 두 선택지 중 '채택 전 기본 enabled=false + 개정 채택을 선행 조건으로 명시'를 채택. 그 결과 §5.3 표의 N2 '켬'은 개정 채택 후 값이며(각주), 05 §4.1의 위임(하이픈 복원)은 개정 채택 전까지 기본 프로파일에서 실현되지 않음 — 계약 04 소유자의 minor 개정이 필요(미해결 1). | |
| 91 | §5.3 | 19-update-delete-and-reindexing.md | pipelines-pass1 | 부분 반영: 리뷰가 요구한 '§5.3·미해결 9의 [평가 전략] 인용 절 번호 대조' — 이 문서는 08-evaluation/01·06을 절 번호 없이 인용하므로 대조할 절 번호가 없음; 미해결 16에 존재 사실만 기록. | |
| 92 | §5.4 | 02-source-document.md | contracts | [미반영] 리뷰(anchor) 'container_flags를 fetch 출력에서 생략 가능(조건부)': 바이블 §5.4가 Y로 고정하므로 계약을 바꾸지 않고 자리표 판별 규약 명시 + 미해결 이슈 13(바이블 patch 또는 ADR)으로 남김. | |
| 93 | §5.4 | 04-normalized-document.md | contracts | 미반영 항목 없음 — 3건 모두 반영. 다만 major 항목의 두 대안 중 reviewer의 1안(NFKC 앞 forward 사상, 2단계 확장)을 채택하고 2안(NFKC 뒤 역사상)은 채택하지 않았다: 2안은 원문 유래 조합형 자모까지 접지만 호환 자모 연쇄 'ㄱㅏ'를 '가'로 합성해 풀어쓰기를 잃고(node 검증), 조각별 NFKC의 기존 결정 문구와 충돌하기 때문. 원문 유래 조합형 자모(옛한글) 문제는 바이블 §5.4 불변식·§4.2 실패 정책 개정이 필요해 미해결 이슈 18로 남겼다. | |
| 94 | §5.4 | 07-contributing.md | finish | CI/CD 미해결 이슈 11(봇 PR 자동 머지가 §5.4 '팀 1인' 규칙과 충돌)과 6(`Breaking-Kind`·`Cache-Invalidation` 트레일러의 PR 템플릿 반영)은 이 문서에서 결정하지 않고 미해결 이슈 13으로 기록 — CI/CD·릴리스 프로세스 소유자와 합의 필요. | |
| 95 | §5.4 | 08-release-process.md | finish | §5.4 릴리스 PR은 트레인 절단 시 PR만 기술하고 핫픽스 PR의 compat-matrix.json·CHANGELOG 갱신 주체는 명시하지 않는다 — §5.3 게이트 13이 '릴리스 파이프라인 재생성'으로 커버하지만 §5.4 표에 핫픽스 행을 추가할지는 리뷰 범위 밖이어서 손대지 않았다(후속 리뷰 시 검토 제안). | |
| 96 | §5.4 | 10-chunking-strategies.md | finish | 바이블 §5.4 `Chunk.ordinal` 행 문구('부모 내 순서')를 05 C-3 형제 정의로 갱신하는 minor patch는 이 문서가 제안만 하며 바이블·05 문서 수정은 각 소유 문서에서 처리해야 한다(미해결 이슈 15) | |
| 97 | §5.4 | 14-schema-versioning-and-compatibility.md | contracts | [tech major §5.4 dataschema] 리뷰어의 두 대안 중 (2) dataschema 생략 + API 조회를 채택; (1) 이벤트 데이터 스키마 인벤토리 추가는 12 문서 결정으로 미해결 이슈 17에 남김. | |
| 98 | §5.4 | 15-hybrid-search-and-fusion.md | pipelines-pass1 | 리뷰 항목 2의 '14 §5.4 결정·§5.1 표 vs 14 결정 요약·§14 예시·미해결 1이 서로 다르다 — 14 patch 요청' 미해결 이슈는 추가하지 않았다: 현행 14 L820(결정 요약)·L777(§14 예시 읽는 법)·L832(미해결 1)가 모두 치환형·가중 불변으로 이미 정합되어 있어 리뷰어가 본 불일치가 존재하지 않는다(14 미해결 1은 오히려 15 §2.1·§5.1·§6.2·§6.5의 패치를 요청하고 있었고, 이번 수정으로 충족됨). | |
| 99 | §5.5 | 05-benchmark-plan-and-baselines.md | finish | major 1의 리뷰어 제안 fix(`postprocess.order: [dedup]` 또는 `tau 0`)는 미채택 — 바이블 §5.5 `RankedSet.final_score`가 리랭크 미적용 시 min-max `fused`로 정의하므로 리뷰어의 '전 질의 게이트 실패' 전제가 앵커와 다름. 대신 의미를 문서에 명시하고 게이트 점수 기준 확정을 미해결 이슈 1로 남김(바이블 §8.2·15 문서 소관). | |
| 100 | §5.5 | 11-context-pack.md | contracts | `TokenizerSpec.name`의 형식은 09 문서를 따랐지만 바이블 §5.5·§9.5는 `name` 형식을 명시하지 않는다(§9.5 예시 `"<target-model-id>"`) — 바이블 patch 제안으로 이슈 4에 병기. | |
| 101 | §5.5 | 19-update-delete-and-reindexing.md | pipelines-pass1 | 미반영: 리뷰 fix 중 '§5.5 (a)를 이 문서의 잠정 규칙으로 승격' — (a)는 바이블 §13.4 물리 이름 규약 개정이므로 결정으로 승격하지 않고 권고+ADR 확정 대상으로 유지(앵커 우선). 대신 확정 전 그런 재색인은 자동 실행 불가(부모 잡 failed)와 운영자 대안(변경 묶기/새 컬렉션 이관)을 잠정 규칙으로 두었다. | |
| 102 | §5.6 | 03-golden-dataset-construction.md | finish | `relevance_max`·`topics_ref`·`language`의 바이블 §5.6 등재 여부는 16 미해결 이슈 1·2와 이 문서 미해결 이슈 4에 위임(바이블 개정은 이 문서 범위 밖) | |
| 103 | §5.7 | 03-parsed-document.md | contracts | 리뷰어가 제안한 P-5 대안(페이지 가구를 최내부 섹션의 자식으로 두기)은 채택하지 않고 '루트 형제 + 전위 순회 동치 제외' 안을 택했다 — 바이블 §5.7 `page_header/page_footer`는 furniture=true 루트 성격이고 기존 예시·§4.2 읽기 순서와 호환되기 때문 | |
| 104 | §5.7 | 05-chunk-set.md | contracts | ADR-0020 '표시 html(1차)/markdown' 대비 Chunk.text 기본 markdown은 (a) html 기본 전환이 아니라 (b) 역할 분담 명시 + ADR-0020 patch 제안(이슈 14)으로 처리 — 앵커 우선 규칙상 ADR은 Chunk.text 직렬화를 특정하지 않고 바이블 §5.7도 기본값이 없어 patch 제안이 적절하다고 판단; 편집 오케스트레이터가 (a)를 원하면 예시 2·sentence_spans·해시 재계산 필요 | |
| 105 | §5.7 | 06-parser-doc-and-docx.md | pipelines-pass1 | 전용 경고·오류 코드 부재: parse.element_path_synthesized(—), parse.table_structure_fallback(—), parse.footnote_unanchored(—), parse.container_limit_exceeded(no) — §5.7 카탈로그 minor ADR 제안(13 §3.3·03 계약 이슈 2와 공동) | |
| 106 | §5.7 | 07-parser-html.md | pipelines-pass1 | HTML 파서용 경고 코드가 §5.7 카탈로그에 없어 저하 사유를 warnings[]에 못 남김 — parse.extractor_fallback 등 추가 ADR(minor) 제안 | |
| 107 | §5.7 | 12-jobs-events-and-status.md | contracts | 진행률 SSE(tech major #4): (a) 스테이지 경계 진행률 명시 + I-20으로 반영. (b) job.progress.updated 이벤트 추가는 바이블 §5.7 카탈로그 개정이 필요해 미해결 이슈 15 제안으로만 남김 | |
| 108 | §6 | 10-candidate-set-and-ranked-set.md | contracts | `text_truncated`를 RankedResult 선택 필드로 직접 추가하지 않음(tech minor): RankedResult는 common-types $defs(additionalProperties: false, 00 문서 소유)라 이 문서가 필드를 추가하면 스키마 위반이 되므로 §6 명시 + 미해결 이슈 12(바이블 §5.5 patch → 00 minor)로만 남김 | |
| 109 | §6.1 | 02-epics-and-backlog.md | finish | 리뷰 minor 3번 후반(`packer.default` 개명) 미반영: 리뷰어 제안 `packer.packer`는 바이블에 근거가 없고, `packer.default`는 depends_on 밖 문서이지만 브리프 문서 맵에 있는 02-architecture/05-plugin-architecture.md 확장 지점 표(line 909)가 정본처럼 쓰는 이름이다. 바이블 §6.1에 packer 예시가 없으므로 단정 대신 미해결 이슈 13으로 등재하고 T-PCK-03(line 336)·§3.2(line 659) 표기는 유지했다. 바이블 §6.1 예시 표에 packer 항목이 추가되면 갱신 필요. | |
| 110 | §6.1 | 11-enrichment.md | pipelines-pass1 | API 모델 revision 표기(별칭에 날짜 없음) — Models API created_at 고정 제안, 바이블 §6.1 patch | |
| 111 | §6.2 | 01-pipeline-framework.md | pipelines-pass1 | [부분 반영] 리뷰(tech) `force` 항목의 '(a) golden_hash 동일이면 기존 유지'는 채택했으나 '(b) artifacts 행 버전 증가' 대안 대신 바이트 해시 키(§6.2 제안과 동일 규약)에 저장하는 방식을 택함 — 바이블 §13.3 patch 하나로 캐시 제외 스테이지 키·덮어쓰기 금지를 함께 제안(미해결 이슈 2). 조건부 PUT(If-None-Match) 지원은 RustFS·SeaweedFS·file://별 확인 필요(as of 2026-09). | |
| 112 | §6.2 | 02-configuration-reference.md | finish | `flip_order[] ⊆ backends[].role` 규칙은 15 불변식에 번호가 없어 §6.2에 '(제안)' 행으로만 두었다 — 03-contracts/15 등재 후 detail 접두를 그 번호로 바꿔야 함(미해결 이슈 5) | |
| 113 | §6.2 | 03-observability.md | finish | query_hash의 바이블 §6.2 해시 표 등재(라벨 없는 식 vs H() 라벨 규약 병존 해소)는 이 문서 범위 밖이며 03-contracts/12 미해결 이슈 8에 위임한 상태를 §6.3에 기록했다. 바이블이 H("query", …)로 확정하면 07-multi-tenancy §8.2·03-contracts/12·이 문서 세 곳을 함께 정정해야 한다. | |
| 114 | §6.2 | 03-parsing-router-and-format-detection.md | pipelines-pass1 | 범위 문서 §6.2의 HWP 5.0 pyhwp/PDF PyMuPDF/PDF 암호화 비지원 문구가 D-18 v1.1·ADR-0006·0007과 불일치 → 갱신 요청 | |
| 115 | §6.2 | 05-parser-pdf.md | pipelines-pass1 | 바이블 §6.2 derived 키에 옵션 해시가 없어 OCR 결과(DPI·언어 의존)를 파생물 캐시로 재사용 불가 → H("derived", content_hash, sidecar_image_digest, options_hash) 확장 제안 | |
| 116 | §6.2 | 12-jobs-events-and-status.md | contracts | 접수 이벤트(anchor major #4·tech major #1): ADR-0017·03-data-flow를 따라 '접수 시 job.state.changed 발행'으로 확정. 02-architecture/06 §6.2 'queued 생성 — 이벤트 없음' 행 정정은 이 문서가 고칠 수 없어 미해결 이슈 14에 등록(06 문서 소유자 patch 필요) | |
| 117 | §6.2 | 19-update-delete-and-reindexing.md | pipelines-pass1 | 부분 반영: 이 문서가 쓰는 audit.admin.action.action 값(delete_document 등)은 03-contracts/12 §6.2가 패턴만 정하므로 전부 제안으로 남겼다(12 문서와 어휘 합의 필요, 미해결 19). | |
| 118 | §6.3 | 02-component-architecture.md | architecture | [검증 범위] JSON 코드 블록은 §6.3 삭제로 문서에 남아 있지 않아 node 파싱 검증 대상이 없다. 부속 schemas/*.json 파일은 이 문서 소유가 아니어서 수정하지 않았다. import-linter INI(uvx import-linter, Python 3.12 스텁 트리)와 §5.2 Settings 블록(pydantic-settings 실행 + pyflakes)은 실증했으나, 다른 Python 코드 블록(sdk/stage.py·ports.py·retrieval.py 시그니처 조각)은 타 블록·계약에 정의된 이름을 참조하는 스케치라 실행 검증하지 않았다. | |
| 119 | §6.3 | 17-post-processing-and-context-packing.md | pipelines-pass1 | [tech minor §6.3 분량] stable_prefix·volatile_suffix를 '<…과 바이트 동일>' 축약 문자열로 대체하라는 제안은 반영하지 않음(JSON 블록 완전성 규약과 R-6 바이트 동일 조립 예시 요건에 어긋남). 대신 두 객체를 한 줄 블록으로 접어 약 30행을 회수(1094→1084행). 브리프 §9.11 상한(900행)은 여전히 초과 — 코드 예시 비중 조정은 후속 과제. | |
| 120 | §6.4 | 08-deployment-architecture.md | architecture | major 수정의 파급: 원 1차 리뷰 지시가 06 §6.4를 잘못 읽은 데서 비롯되었으므로, 1차 지시를 낸 리뷰 결과(또는 이를 참조한 다른 문서)가 relay→api SSE 푸시 전제를 가진다면 그쪽도 점검이 필요하다(이 문서 범위 밖). | |
| 121 | §6.5 | 02-retrieval-metrics-and-harness.md | finish | 리뷰 항목 2(`rag_eval_metric_value` 이름을 §6.5 `rag_<stage>_<name>_<unit>` 규약에 맞게 변경 또는 patch 제안 추가)는 반영하지 않음 — 바이블 §6.5 line 1207 정본 목록이 `rag_eval_metric_value{metric}`를 명시 등재하고 ADR-0036도 이를 유일한 예외로 적고 있어 앵커와 일치함. 이름 변경은 바이블·01·03·04·09-operations/03·10-development/05·11-roadmap 등 20여 문서에 걸친 변경이 되므로 이 문서 단독으로 다룰 사안이 아님. 대신 §12에 앵커 근거를 병기함. | |
| 122 | §6.5 | 03-observability.md | finish | 제안 메트릭 2종 추가(rag_eval_last_run_timestamp_seconds, rag_serving_gpu_seconds_total)로 §6.5 minor 개정 대상이 38종으로 늘었다 — 미해결 이슈 2에 반영. | |
| 123 | §6.5 | 03-parsing-router-and-format-detection.md | pipelines-pass1 | 제안 메트릭·스팬의 바이블 §6.5 등재(ADR-0022 minor) | |
| 124 | §6.5 | 05-ci-cd.md | finish | 새 미해결 이슈 16: `rag_eval_metric_value`에 데이터셋 라벨이 필요해지면 바이블 §6.5 허용 라벨 minor 개정(ADR)을 08-evaluation·09-operations/03 소유자와 발의 — 이 문서는 `EvalRun` 원장 분해로 대체. | |
| 125 | §6.5 | 12-jobs-events-and-status.md | contracts | source 집합(tech minor #11): eval을 독립 값에서 제외하고 api·worker로 확정했으나 바이블 §6.5 열거 명시·common-types 패턴 축소·14 예시 4 정정은 다른 문서 소유(미해결 이슈 6) | |
| 126 | §6.7 | 10-candidate-set-and-ranked-set.md | contracts | 09 §6.7 `RerankPlan.enabled=false`일 때도 `RankedSet.rerank`(applied=false)를 필수 출력하는 규칙은 이 문서 결정이라 09 측 병기 제안(이슈 1 잔여) | |
| 127 | §7 | 03-risks-and-mitigations.md | finish | 리뷰 항목 3의 1안(R-L-01/R-L-02를 L=4·16점 치명으로 승격)은 채택하지 않았다. 이유: 히트맵·치명 건수(5→7)·§7 비상 계획 상세 2절 신설·§4 목표 점수·결정 요약·01-milestones §11 정합까지 연쇄되어 minor 항목의 국소 수정 범위를 넘고, 바이블 #2가 이 문서에서 네 건으로 분해된 점을 고려하면 개별 가능성 3·2가 §1.2 정의에 부합한다. 대신 §3.2에 예외 근거를 명시하고 미해결 이슈 6(바이블 §15 동기화)에 포함했다. M1 종료 검토에서 바이블 patch 시 재판단 대상. | |
| 128 | §7 | 06-parser-doc-and-docx.md | finish | 03 ParsedDocument 계약 §7 각주·미주 행이 HWPX 전제(마커 원문 유지)로 쓰여 있어 OOXML 규칙과 방향이 다름 → 이 문서 미해결 이슈 16으로 등재; 03 문서 patch는 03 소유자 몫(이 문서는 03 파일을 수정하지 않았다). | |
| 129 | §7 | 12-embedding.md | pipelines-pass1 | 리뷰 항목 중 '§7 캐시 기록을 배치별 npz 조각 + 청크→(조각,행) 색인으로 구조 변경' 대안은 채택하지 않고, 적중 시 EXPIRE·비동기 기록·라이프사이클 규칙 추가 + 미해결 이슈 7(c)에 실측 후 전환 여부로 남겼다(구조 변경은 §7 값 형식·캐시 조회 경로 전체를 바꾸는 큰 변경이라 1차에서는 보류). | |
| 130 | §7.1 | 01-deployment-guide.md | finish | 바이블 §7.1 lite 열 머리 '컨테이너 5' 정밀화 patch는 배포 아키텍처 미해결 이슈 14로 이미 요청됨 — 이 문서에서는 중복 요청 대신 참조만 추가 | |
| 131 | §7.1 | 04-llm-judge-and-generation-quality.md | finish | minor 7: 리뷰어가 제시한 두 선택지 중 '예시를 @20260601로 맞추기'는 근거 없는 날짜 수치가 되어 채택하지 않고, §7.1에서 @<revision> 접미를 선택(optional)으로 명시하는 쪽으로 반영함 | |
| 132 | §7.1 | 05-parser-pdf.md | pipelines-pass1 | lite born_digital 문서의 소수 스캔 페이지(≤0.2)가 pdf_fast_cpu에서 OCR 없이 남는 문제 → lite도 page_route 적용 제안(바이블 §7.1 lite 행 주석) | |
| 133 | §7.1 | 08-parser-txt-md-and-others.md | finish | 미해결 이슈 17(바이블 §7.1 TXT·MD 행에 하위 경로 라이브러리 병기 + §12 모듈 맵 주석 patch)이 반영되기 전까지 clevercsv·orjson/ijson·lxml·mdit_py_plugins는 문서 전체에서 '제안' 지위다 — 바이블 소유자가 patch를 적용하면 §1.2·§5.1·§6.1·§7.6·§8·결정 요약·이슈 17의 '제안' 표기를 '결정'으로 되돌리는 후속 수정이 필요하다. | |
| 134 | §7.1 | 09-normalization-and-cleaning.md | pipelines-pass1 | [major, 선택지 (a) 채택] korean-gov 주민등록번호 reject: `PiiConfig.reject_entities`(reject만 허용) 도입 — 바이블 §7.1이 정본이므로 (b) '미지원' 대신 (a). 단 `dict` 대신 `tuple[str, ...]`(frozen 모델 해시 가능성)로 구현. 바이블 §7.3 `pii` 키·계약 15 스키마 minor 추가는 미해결 20으로 남김. | |
| 135 | §7.1 | 13-error-model.md | contracts | 리뷰 minor(tech) 'H7 404 → §7.1 404 행 추가': 채택 코드가 없어 '채택 전 임시: 400 contract.violation + detail'로 두었다. 이는 이 문서가 정한 초안 규칙이며 api.not_found 조기 채택(이슈 3)으로 해소된다. | |
| 136 | §7.2 | 11-enrichment.md | pipelines-pass1 | 예산 대조 기준 charged_tokens를 BudgetUsed에 기록할 필드가 없고, premium 기본 enrichment_budget_tokens 20,000이 8k 토큰 문서의 모드 B에서 경계에 걸림 — 06 문서 필드 제안 + §7.2 값 재산정 | |
| 137 | §7.3 | 02-fetching-and-source-resolution.md | finish | 리뷰 major 1이 매달린 참조로 지목한 §7.3 464행 '03-data-flow 미해결 이슈 18'은 이 문서가 아닌 03-data-flow 문서의 이슈 18(메타데이터 payload 갱신 경로 부재, 실제 존재)을 가리키는 외부 참조이므로 변경하지 않았다. | |
| 138 | §8 | 01-pipeline-framework.md | pipelines-pass1 | [부분 반영] 리뷰(anchor) '13개 미존재 링크' 항목: 브리프 §8 문서 맵 경로이므로 링크는 유지하고 '(동시 작성 중)' 표기와 절 번호 제거만 적용. 검증 결과 03-contracts/12·13은 이미 존재하여 '동시 작성 중'에서 제외함. | |
| 139 | §8 | 04-management-api.md | finish | 리뷰 항목 3에서 `max_bytes`·`connect_timeout_ms`·`allowed_ports`를 예시에서 제거하지 않고 15 §8 추가 필드(N)로 표기하는 쪽을 택했다 — 15 §8이 depends_on 문서로 세 필드를 N으로 정의하고 합성 규칙까지 두므로 정보를 유지하는 것이 유용하다고 판단; 바이블 §5.3 patch 채택 여부는 15 소유 이슈라 이 문서에 별도 미해결 이슈를 신설하지 않고 §2.1 본문에 종속 관계만 명시함 | |
| 140 | §8 | 06-runbooks.md | finish | RB-25~29 코드 블록의 k8s 배포 이름(deploy/rag-relay, app.kubernetes.io/name=rag-api\|otel-collector)·컨테이너 포트(8080)·알림 규칙 경로는 배포 매니페스트·관측성 §8 제안 경로 기준이며 문서 내 주석으로 '매니페스트 기준' 표기(기존 RB-04~24와 동일 수준의 가정) | |
| 141 | §8 | 06-runbooks.md | finish | 관측성 문서 §8 '런북' 열의 (제안) RB 번호 교체 요청은 기존 미해결 이슈 1로 유지(이 문서 범위 밖) | |
| 142 | §8 | 07-embedded-chunk-set-and-index-record.md | contracts | 미반영(tech minor): `../04-pipelines/12-embedding.md`·`13-indexing.md`·`17-post-processing-and-context-packing.md`·`19-update-delete-and-reindexing.md` 링크(10곳)는 저장소에 아직 없지만 브리프 §8 산출물 맵에 있는 경로이고 공통 규약이 '문서 맵 경로만 링크'를 허용하므로 유지했다('(작성 예정)' 표기는 05·06·08 등 형제 문서와의 관행 불일치를 만들어 추가하지 않음). 후속 단계에서 해당 파이프라인 문서 생성이 워크플로우에 등재되어야 한다. | |
| 143 | §8 | 08-deployment-architecture.md | architecture | minor(링크 12건): 링크 대상 미작성 문서는 브리프 §8 문서 맵 경로이므로 링크를 제거하지 않고 범위 절에 '전방 참조(작성 예정, depends_on 아님)' 1행만 추가했다 — 공통 규약('링크는 브리프 §8 산출물 맵에 있는 경로만 상대 경로로 쓴다')상 허용되는 전방 참조이며, 리뷰어도 verdict 미반영 항목으로 분류했다. | |
| 144 | §8 | 08-index-commit.md | contracts | [부분 반영] 존재하지 않는 문서 링크(04-pipelines/19, 05-api/04, 09-operations/07)는 삭제하지 않고 브리프 §8 문서 맵 경로 + "(작성 예정)" 표기로 유지(공통 규약 "링크만 문서 맵 경로로 건다"). validate-contracts.mjs의 '링크 대상 미존재' 경고 9건은 그 문서들이 게시되면 사라진다. | |
| 145 | §8 | 09-failure-modes-and-resilience.md | architecture | 리뷰 minor #3(03-contracts/08·10·11·12·15, 04-pipelines/*, 09-operations/*, 10-development/*, 11-roadmap/03 등 21개 상대 링크 대상 미작성): 리뷰어 권고대로 변경 없음 — 저장소 전체의 선참조 관행이며 브리프 §8 문서 맵 경로와 일치. 문서 생성 시 경로·파일명 변동 시 일괄 갱신 대상. | |
| 146 | §8 | 12-jobs-events-and-status.md | contracts | 분량(anchor minor #5·tech minor #13): 1168→1160행으로만 축소. 리뷰어 제안대로 Pydantic data 모델 17개를 축약하거나 §8·§9 운영 규약을 삭제하면 00 §10.3 Pydantic 동치 게이트·계약 문서 '스키마 전체 포함' 규약과 상충하고 major 수정(접수 이벤트·커서·I-19·I-20)으로 내용이 늘었으므로, 형식 압축(required 배열 한 줄, §12 중복 행 제거)만 적용하고 미해결 이슈 18로 등록 | |
| 147 | §8 | 16-reranking.md | pipelines-pass1 | [minor, 부분 반영] `../09-operations/04-scaling-and-performance.md` 링크 대상은 여전히 미존재 — 문서 맵(브리프 §8) 경로이므로 링크를 유지하고 '작성 예정(링크 검사 예외 등재 대상)'으로 표기했다. 스텁 생성은 다른 에이전트 소유 문서라 하지 않았다. 08-evaluation/05·06은 수정 중 작성되어 '작성 예정' 표기를 제거했다. | |
| 148 | §8 | 19-update-delete-and-reindexing.md | pipelines-pass1 | 다른 문서 반영 요청(이 문서 범위 밖): 03-contracts/08 §8·02-architecture/06 §2.5 A-7(supersedes/superseded_by 규칙), §2.7(stale_current 기준), 02-architecture/03 §7.1 규칙 6(collections.deleted_at), 04-pipelines/13 §2.1 retrieve·ADR-0034(hydrate 완화안), 바이블 §5.7·§11.2·§13.1(컬렉션 삭제 등재). | |
| 149 | §8.1 | 03-parsed-document.md | contracts | §8.1 체크박스 라벨 → form_field 매핑은 삭제하지 않고 별도 행 + '확인 필요·바이블 §5.7 주석 보강 제안'으로 유지했다(04-pipelines/05 확정 위임) | |
| 150 | §8.1 | 05-benchmark-plan-and-baselines.md | finish | §8.1 T1 사다리 표 행에는 B3-norerank를 추가하지 않음(보조 단; §3.3 S0 구성 7과 표 행 6이 다르지만 T1은 '사다리' 표로 한정). | |
| 151 | §8.1 | 09-query-request-and-query-plan.md | contracts | 리뷰 항목 중 반영하지 않은 것 없음. 단 §8.1 '저장 내용'의 제외 목록에서 `timeout`을 뺐다 — QueryPlan의 §6.1 degraded 목록에 plan 단계가 내는 `timeout` 항목이 없어(LLM 라우터 타임아웃은 `llm_failed`) 정합성을 위해 `latency_budget`·`unavailable`만 명시했다. | |
| 152 | §8.2 | 08-upgrade-and-migration.md | finish | §8.2 release-manifest.json 예시에 릴리스 프로세스 §9.2가 추가한 필드(release_kind·git·artifacts[] 등)는 넣지 않고 '이 문서 정의 필드만의 발췌'로 명시 — 정본 예시는 그 문서 §9.2. | |
| 153 | §8.2 | 11-context-pack.md | contracts | 분량 축소 방식: 리뷰가 제안한 §8.2 MCP 슬림 팩·§2.9 PackExplain·§15 API 표 삭제 대신 예시·스키마 JSON 재직렬화와 Pydantic 압축으로 1382행을 맞췌 세 절은 유지했다(내용 손실 회피). | |
| 154 | §8.2 | 14-schema-versioning-and-compatibility.md | contracts | 부속 파일 없음: 이 문서는 schemas/*.schema.json을 소유하지 않으며(범위 절) common-types는 00 소유라 수정하지 않았다. 00 소유자에게 넘길 제안: KebabName·ContractsCompat 승격, Capabilities.contracts_compat 패턴, SchemaVersion 원시 형식, §8.2 보완 목록(미해결 이슈 1·5·6). | |
| 155 | §8.3 | 02-source-document.md | contracts | [미반영] 리뷰(anchor) 'credentials_ref maxLength 512·패턴 {1,480}': 01 $defs/CredentialsRef 실제 값은 maxLength 256·{1,240}(01 §8.3이 02의 256에 맞춰 개정)이라 256 유지, 패턴만 추가. | |
| 156 | §8.3 | 02-source-document.md | contracts | [후속] 01 §8.3·미해결 이슈 15와 버전 이력이 02를 'string ≤256만·예시 kp://'로 서술하고 있어, 01 소유자가 02 패턴 채택 사실로 문구를 갱신하면 좋다(02 소유 범위 밖이라 수정하지 않음). | |
| 157 | §8.3 | 04-scaling-and-performance.md | finish | 리뷰어 fix 문구 중 '바이블 §8.3은 ~10KB 상한 가정'은 바이블 원문(§5.1·§8.3 '100 × ~10KB')이 상한이 아니라 예산 가정이므로 '예산을 잡았고 04는 하향 가정으로 명시'로 표현을 바꿔 반영했다(내용상 차이 없음). | |
| 158 | §9 | 03-data-flow-and-document-lifecycle.md | architecture | [minor 5 부분 반영] 리뷰어는 NFR 02 419행의 ≤ 5 s를 '목표값'으로 읽었으나 NFR §9 표의 열은 '논리 삭제 데드라인(최대)' / '물리 소거 데드라인(최대)' 로 둘 다 최대값이다. 따라서 헤더를 '목표/최대'로 바꾸지 않고 두 행을 논리 삭제/물리 소거로 명확히 라벨링하는 방식만 적용했다. | |
| 159 | §9 | 06-orchestration-and-workflows.md | architecture | 문서 길이 1023행으로 브리프 §9 권고(250~900행)를 초과한다. 1차 편집 시점(997행)에도 초과 상태였고 이번 지시가 국소 수정이라 분할하지 않았다; §9(처리량·사이징)를 09-operations/04로 이관하는 안을 검토할 것. | |
| 160 | §9 | 07-parser-html.md | finish | 블록 상한 초과 코드: 이 문서는 파서 사전 중단을 `parse.conversion_failed`(detail too_many_blocks)로, 셸 검증 적발은 `contract.violation`(03 §9)로 병기했다. 03 §9는 전용 코드 제안을 미해결 이슈 2로 두고 있어 코드 확정 시 §13 행 동기화 필요. | |
| 161 | §9 | 10-chunking-strategies.md | pipelines-pass1 | tech major(조 heading 승격) 옵션 (A)의 'numbering_path 원소로 사용'은 채택하지 않음 — 05 §9가 numbering_path를 heading 경로의 numbering_label로 정의하므로 비-heading 문단을 넣으면 heading_path와의 대응이 깨짐. 조 경계는 하드 경계·부모 묶음 경계만, heading 승격은 파서 측 제안(미해결 이슈 13) | |
| 162 | §9 | 11-enrichment.md | finish | minor 4는 코드 교체 대신 06 §9·바이블 §5.7 patch 제안(미해결 이슈 3(b))으로 반영 — 06 §9가 이미 재시도 코드 enrich.extractor_timeout을 청크 경고로 쓰고 있어 동일 관행의 확장으로 판단, 정본 변경은 06/바이블 소유자 결정 사항 | |
| 163 | §9 | 13-indexing.md | pipelines-pass1 | [신규 등재] 두 해시가 같은 컬렉션 프로파일 변경(06 모드 B)은 미정으로 남겼다(미해결 13). 04-pipelines/19·02-architecture/06·03과 공동 ADR로 확정해야 하며 확정 결과에 따라 §9 마지막 문단을 개정해야 한다. | |
| 164 | §9.2 | 14-query-understanding.md | pipelines-pass1 | Anchor-minor item '§9.2 근거를 바이블 §5.5 top_k 기본 10 + 09 P-11 min(top_k or 10, k_max)로 정정' NOT applied as stated: the current 09 document (P-11, §6.9, §7.2, 미해결 이슈 1, 버전 이력) explicitly retracted the min() combination and fixed pack.k_max = 프로파일 query.pack.k_max; bible §5.5 ('팩 k_max와 별개') + §7.2 standard/premium 20 is the anchor. Kept pack.k_max = profile value (standard row 근거 '바이블 §7.2; 09 P-11'), fixed §14.6 k_max 10→20 and the stale 결정 요약 min() formula, and recorded the top_k/k_max relation as 미해결 이슈 20 (joint with 09 issue 1). | |
| 165 | §9.3 | 02-ingestion-api.md | finish | [minor 2 미반영] 01-api-design-guidelines §9.3 표(line 346~360)의 마지막 열은 `operationId`(§17.3)이며 Cedar 액션 열이 아니다. `update_document_metadata`는 operationId(06 §5.1·04-management-api line 108도 동일 분리)로 07 §4.1 `reprocess_document` Cedar 액션과 충돌하지 않으므로 주석·이슈 추가 없이 현행 유지. 이 문서 §1 표 아래 문장이 이미 '한도 클래스·operationId는 01 §9.3, Cedar 액션은 07 §4.1'로 출처를 분리 명시함. | |
| 166 | §9.3 | 07-parser-html.md | pipelines-pass1 | 정제 XML 파생물 미디어 타입 application/xml이 00 §9.3 표에 없음 — patch 제안 | |
| 167 | §9.4 | 03-retrieval-api.md | finish | 반영하지 않은 리뷰 항목 없음(3건 모두 반영). 단 (3)은 리뷰어 제안(§9.4만 인용) 대신 §5.5 RenderedContext·§9.4·§9.2 세 곳을 인용했다 — §9.2 1480행 '`r1`은 항상 마지막(질의 직전)'이 질의 후치 순서의 직접 근거이기 때문. | |
| 168 | §9.11 | 01-pipeline-framework.md | pipelines-pass1 | [미반영] 문서 길이 1112행 — 브리프 §9.11의 250~900행 상한을 초과(편집 전 980행부터 초과 상태). 리뷰 항목이 아니어서 절 분리(예: §11~§13을 별도 문서로) 여부는 다음 라운드 판단 사항으로 남김. | |
| 169 | §9.11 | 02-component-architecture.md | architecture | [부분 반영] 리뷰 anchor-minor '브리프 §9.11 900행 이내' — 998행 → 993행. §6.3 ProblemDetails 예시 삭제, 배포 단위 표를 08-deployment 소유로 이관, 다이어그램 축약 등을 했으나 major 수정(QueryContext·DerivedArtifacts·Settings 클래스 정의·미해결 이슈 확장)으로 순증이 있어 900행 미달성. 남은 후보(§5.2 Settings 절 모델 일부를 09-operations/02로 이관, §3.2 표 축약)는 architecture 소유자가 브리프 §9.11 vs 감사 지시(500~1000행) 우선순위를 확정한 뒤 2차에서 처리 요청. | |
| 170 | §9.11 | 15-collection-profile-and-policy-contracts.md | contracts | [minor, 부분 반영] 문서 분량: 1,840행으로 검토 기준 1,300행을 초과. 스키마 7종 전문·예시·Pydantic 동치 모델(major 요구)을 모두 유지해야 하므로 축약 대신 브리프 §9.11 계약 문서 예외를 근거로 '결정'으로 명시(이슈 12 종결). §3.10·§11 축약은 정보 손실 대비 절감이 작아 미반영. | |
| 171 | §10 | 11-enrichment.md | finish | 06 §10 캐시 엔트리 초안(kind/plugin_id/output 형식)으로 §11을 정렬했으나 06 미해결 이슈 12·17(바이블 §6.2 patch)은 아직 열려 있음 — 바이블 반영 시 이 문서 §1·§3·§9·§11 표기 재확인 필요 | |
| 172 | §10 | 13-indexing.md | pipelines-pass1 | [tech minor, 인용 방식] `IndexConsistencyMismatchData`에는 불일치 종류·백엔드별 세대가 없어 §10의 `stale_current` 판정 근거를 이벤트만으로 전달할 수 없다. 스키마(`additionalProperties: false`) 개정 없이는 해결 불가하므로 12 §6.2 선택 필드 `kind`·`observed_generations` 추가를 미해결 16으로 제안(04 미해결 14 (a)와 공동). | |
| 173 | §10.1 | 01-ingest-request.md | contracts | [anchor minor, ACL A4] 리뷰의 '채택 전 400 대신 warnings/접수 허용으로 완화' 안은 본문 규칙으로 채택하지 않고 이슈 14에 완화안으로만 병기했다. 이유: 완화하면 Warning 코드(contract.acl_deny_all)가 또 카탈로그 밖 제안 코드가 되어 I-14와 충돌하므로, 바이블 §10.1 등재 결정까지 이 계약 불변식(IR-5)으로 400 유지가 더 일관적이다. | |
| 174 | §10.2 | 09-failure-modes-and-resilience.md | architecture | 08 §10.2가 GET /healthz를 liveness 프로브로 쓰는 것과 이 문서의 '/healthz 의존성 상태 노출'의 관계(의존성 down이 liveness 실패로 번지지 않게 하는 규칙)는 미해결 이슈 17(a)에 제안으로만 추가했고 결정하지 않음 — 05-api/04 또는 09-operations/03에서 확정 필요. | |
| 175 | §10.3 | 15-collection-profile-and-policy-contracts.md | contracts | [minor, 대안 채택] capabilities.schema.json `$defs` 별칭: 00 §10.3 patch는 이 문서 권한 밖(00 문서·common-types는 00만 수정)이라 별칭을 제거하고 순수 래퍼로 전환, 바이블 §5.1 행 patch 제안만 남김. | |
| 176 | §11 | 09-query-request-and-query-plan.md | contracts | §11 canonical_json 바이트 수는 직렬화기의 실수 최단 표현 규약(`1.0` vs `1`)에 따라 7,115/7,147로 갈린다 — 바이블 §6.2 '부동소수 최단 표현' 정의의 정밀화(정수값 실수 표기)는 00 문서·바이블 patch 대상으로 남아 있다(이 문서 미해결 이슈에는 추가하지 않고 본문 괄호로만 병기). | |
| 177 | §11.3 | 11-enrichment.md | pipelines-pass1 | enrich.llm_unavailable 재시도 소진 시 바이블 §11.3상 잡 failed — 결정적 결과 보유 시 partial로 완화하는 ADR-0016 개정 검토 | |
| 178 | §11.4 | 06-orchestration-and-workflows.md | architecture | 모드 A 원장 포인터 결정은 바이블 §11.4 사가의 예외이므로 바이블 자체는 수정하지 않았고 ADR-0026 개정 제안(미해결 이슈 18)으로만 등재했다. 03-data-flow 미해결 이슈 17·20의 정정·확정은 그 문서 소유자가 반영해야 한다(이 문서 미해결 17 (c)·18에 요청 기록). | |
| 179 | §11.4 | 08-index-commit.md | contracts | [제안 전달 필요] 미해결 14(바이블 §11.4 (6) N 원천 정밀화 patch), 15(05-api/04 commits 목록 정렬·커서·노출), 16(바이블 §11.5 `cancelling → succeeded` patch; 06 미해결 6·12 미해결 5와 공동), 12(`index.consistency.mismatch.expected_record_count`의 모드 A 기준 커밋을 12·06 §2.7에 명시)는 각 소유 문서에 전달해야 한다. | |
| 180 | §12 | 02-component-architecture.md | architecture | [설계 판단] `Settings`를 새 최상위 모듈 `rag_platform.settings`(L5, security\|profiles와 같은 계층)로 두었다 — 바이블 §12 트리에 없는 패키지이므로 '제안'으로 표기하고 트리 등재 또는 `orchestration/settings.py` 격하 여부를 미해결 이슈 9로 남겼다. 리뷰어 두 명이 각각 `rag_platform.settings`/`rag_platform.config`를 제안했는데 이름은 앵커 리뷰어 제안(`settings`)을 택했다. | |
| 181 | §12 | 02-component-architecture.md | architecture | [문서 간 불일치 발견, 미수정(타 문서)] 06-orchestration-and-workflows 스케치는 셸 모듈을 `orchestration/stage_shell.py`로 적었고 바이블 §12는 `orchestration/context.py`다. 이 문서는 바이블을 따르고 미해결 이슈 11로 06 문서 정정을 요청했다. | |
| 182 | §12 | 02-development-environment.md | finish | 문서 자체 미해결 이슈 13건(justfile 등 제안 파일의 바이블 §12 등재, CLI 하위 명령 등재, 개발 부트스트랩 범위, compose 오버레이 표면, 개발 프로파일 형태, [kiwi] extra 복원, Windows wheel 확인, samples 원문 확정, 대용량 픽스처 보관, pre-commit rev 고정, TS 코드젠 도구, ALLOWED_ROOTS 마운트 정합, 두 셸 동등성 테스트 흐름)은 그대로 유지 — 타 문서·ADR 소유 사항이라 이 수정 범위에서 다루지 않음. | |
| 183 | §12 | 02-retrieval-metrics-and-harness.md | finish | 참조에 추가한 09-operations/03·10-development/04·05는 frontmatter·grep 수준으로만 확인했으며 depends_on에는 추가하지 않았다(본문을 전부 읽지 않았으므로). 후속 정합성 검토에서 세 문서의 `tests/eval/`·워크플로우 서술과 이 문서 §12가 어긋나면 갱신 필요. | |
| 184 | §12 | 03-parsing-router-and-format-detection.md | pipelines-pass1 | ParseRouterStage 모듈 위치(adapters/parse/router.py 제안) 바이블 §12 등재 | |
| 185 | §12.1 | 07-multi-tenancy-and-security-architecture.md | architecture | 리뷰 4건 모두 반영했으며 미반영 항목은 없다. 리뷰어가 지목하지 않은 §12.1 L800 Note 텍스트의 `;`도 같은 mermaid 결함이라 추가로 수정했다. | |
| 186 | §12.3 | 15-hybrid-search-and-fusion.md | pipelines-pass1 | 미해결 이슈 6의 12 §12.3·13 §6 patch(values = 1.0 → 04-pipelines/15 tf_q 위임)는 다른 문서 수정이라 제안으로만 남김; bm25s 반복 질의 토큰 처리 확인 뒤 (a)/(b) 택1 필요. | |
| 187 | §13 | 04-testing-strategy.md | finish | 03-coding-standards §13 '마커(제안)' 12종 목록을 §21 인용으로 바꾸는 patch는 03 소유자 작업(03 미해결 이슈 10)이라 이 문서에서는 대응표와 미해결 이슈 15로만 남김. | |
| 188 | §13.1 | 01-ingest-request.md | contracts | [anchor/tech major, 배치 멱등성] 리뷰 요구대로 잠정안으로 격하했으나 정본 개정 없이는 구현할 수 없는 상태다. 잠정안의 파생 키 '{key}#{i}'는 '#'를 포함한 단건 키와 이론상 충돌할 수 있음을 본문에 명시했다. 바이블 §13.1(idempotency_keys.job_ids 또는 response jsonb, jobs.idempotency_key NULL 허용) 개정이 필요하며 이 문서가 결정할 수 없다(이슈 12). | |
| 189 | §13.1 | 12-jobs-events-and-status.md | contracts | SSE 커서(tech major #2): 리뷰어 제안 seq IDENTITY 컬럼은 바이블 §13.1 outbox 컬럼에 없어 단정할 수 없고, IDENTITY는 INSERT 시점 할당이라 늦은 커밋 문제를 해결하지 못하므로 채택하지 않음. 대신 바이블 컬럼만으로 발행 순 (published_at, event_id) 커서를 정의하고(단일 릴레이가 단조 부여) 전용 published_seq 컬럼은 미해결 이슈 16 제안으로 남김 | |
| 190 | §13.3 | 04-llm-judge-and-generation-quality.md | finish | PairwiseRecord와 온라인 judge.jsonl 경로는 이 문서 제안이며 바이블 §13.3 미등재 — 기존 미해결 이슈 6 범주에 속함(행 별도 추가 안 함) | |
| 191 | §13.4 | 13-indexing.md | pipelines-pass1 | [tech major, 부분 반영] Nori 필터 순서·stoptags: 리뷰어는 `nori_readingform → rag_pos_stop` 순서 변경과 stoptags에서 `SH`·`SN`·`SL` 제외를 요구했으나, 바이블 §13.4가 stoptags `J*`·`E*`·`S*` 전체를 확정했고 04 §5.1도 바이블 §1.1에 따라 그대로 쓰며 미해결 #7로만 남겼다. 앵커 우선 규칙에 따라 전문은 바꾸지 않고, §5.1에 죽은 필터(readingform)·색인/질의 비대칭 한계를 명시하고 미해결 15에 바이블 §13.4 minor 개정 제안(stoptags `E, J, SC, SE, SF, SP, SSC, SSO, SY`, 순서 `nori_readingform → rag_pos_stop → lowercase`)과 골든셋 A/B 게이트 조건을 등재했다. 참고: readingform은 POS 태그를 바꾸지 않으므로 순서만 바꿔도 SH가 제거되어 효과가 없어 stoptags 개정이 함께 필요하다. | |
| 192 | §13.4 | 13-indexing.md | pipelines-pass1 | [anchor minor, 대안 채택] cjk_bigram 명명: 리뷰어의 두 선택지 중 바이블 §13.4·§8.1 철자 `cjk_bigram`(별도 필드, copy_to)을 택했다. 이 문서가 매핑 정본으로 지정한 04 §5.2(`index_text.bigram` 하위 필드)와 어긋나므로 04 §5.2 정정 제안을 미해결 14에 등재 — 04 문서 소유자 확인 필요. | |
| 193 | §14 | 01-ingest-request.md | contracts | [tech minor, dry_run] 리뷰가 제시한 두 대안 중 '필드 추가 + 예시' 대신 '범위 절 제외 명시 + 이슈 9 보강'을 택했다. 이유: dry_run은 N 필드 하나가 아니라 응답 상태(202→200)·본문(IngestDryRunResult)·Idempotency-Key 소비 여부까지 바꾸는 엔드포인트 의미 변경이라 바이블 §14 행 개정(minor)이 선행되어야 한다고 판단(브리프 §11). | |
| 194 | §14 | 07-contributing.md | finish | minor 4 후속: 03-coding-standards §14 `plugin-{name}` 스코프·`Refs:` ADR 푸터·§15 브랜치 패턴이 이 문서(§7.1 `rag-plugin-{name}`, `ADR:` 푸터, §5.1 `{type}/{short-kebab}`)와 다르다 — 03 미해결 이슈 10에 따라 이 문서가 정본이므로 03 소유자에게 patch 인용 갱신 요청(이 문서 미해결 이슈 12로 기록). | |
| 195 | §21 | 04-testing-strategy.md | finish | 리뷰 minor의 대안 중 '§21에 dev 마커 추가'는 채택하지 않음 — 03 §13이 마커 확정을 이 문서에 위임했고 08/02 §12 자체가 '이 문서는 위치·마커·픽스처 규약만 배정한다'는 관계이므로 `slow` 재배정이 정본 규칙에 부합함. 08/02 §12의 'dev 마커' 표기 patch는 미해결 이슈 15로 08-evaluation 소유자에게 이관. | |
| 196 | - | 00-contract-overview.md | contracts | depends_on은 브리프·바이블·선정 매트릭스 3개를 유지했다. 13-error-model 파일을 대조용으로 읽었지만 13이 00에 의존하므로 순환을 피해 depends_on에 추가하지 않았다. | |
| 197 | - | 03-parsing-router-and-format-detection.md | finish | profile_option의 PDF 외 값(hwpx_standard 등)은 바이블에 없어 제안으로만 남김 — 기존 미해결 이슈 18에서 04·05·15 문서와 확정 필요(문서 본문에 반영됨). | |
| 198 | - | 11-context-pack.md | contracts | `relaxed_keys` 개명(`relaxed_applied_keys`)은 실제 개명 없이 미해결 이슈 3에 검토 항목으로만 기록했다(계약 필드명 변경은 바이블 반영 후). | |
| 199 | - | 13-error-model.md | contracts | 리뷰 minor 'instance 필드 표 타입 셀에 string(uri-reference)(바이블 표기 string(uri), 정정 제안) 병기'는 반영했으나, 리뷰어가 제안한 common-types 변경은 00 소유라 직접 하지 않음(00이 이미 uri-reference로 변경함을 확인하고 인용). | |
| 200 | - | 13-error-model.md | contracts | 리뷰 minor 'retrieve.security_context_missing 500 → 미정': 반영. 단 E7 문구가 400을 뜻하는지 별도 코드를 뜻하는지는 바이블 소유자 확인 필요로 남김(이슈 5). | |

## 3. 계약 감사 정본 결정 (하류 문서 전파 대상)

계약 감사(`contracts-audit`)가 03-contracts와 schemas/에는 이미 적용한 결정이다. 04-pipelines·05-api·08~11 문서가 같은 필드·열거를 쓰는 곳에 전파해야 한다.

| # | 결정 |
|--:|---|
| 1 | `lineage_refs.source`·`IndexCommit.artifact_refs.source` = **SourceDocument 계약 산출물**(detect 출력, `media_type=application/vnd.rag.source-document+json`, `schema_type=SourceDocument`), 원본 바이트가 아님 — 바이블 §5.2(lineage_refs는 상류 산출물 참조이며 셸이 `requires_lineage` 로드에 사용), §4.1(`index`의 requires_lineage: `SourceDocument`), §5.1(`SourceDocument` 소비: `index`(acl·metadata)); 00 §3.2 대응표·I-7이 이를 따른다. 원본 바이트는 `SourceDocument.artifact`·`ParsedDocument.source_ref`로만 참조. 06/07/08 예시·08 §2.4·index-commit.schema.json은 비정본. |
| 2 | `IndexCommit.embedding_space_ids`의 타입 정의 위치 = 자기 스키마 `$defs` 사본(common-types 승격 전) — 바이블 §5.1 마지막 행(계약 전용 하위 타입은 해당 계약 스키마의 `$defs`) + 00 §2 소유 규칙(공용 타입은 common-types `$defs`, 계약 간 교차 `$ref` 없음). 07 index-record·15 collection-spec의 사본 방식이 정본, 08의 교차 `$ref`는 비정본. |
| 3 | `BlockRef.original_char_start/original_char_end` = 모든 청크 종류에서 원문 `Block.text` 기준 `offset_map` 사상 결과(표 블록은 03 §6 선형화 텍스트 기준) — 바이블 §5.3 `BlockRef` 행, §6.3(Provenance 기준 = 원문 Block.text). 05의 표 청크 상수 `0, 0`은 비정본. |
| 4 | `requires_lineage`는 현재 `index`만 사용(`EnrichedChunkSet`·`ChunkSet`·`SourceDocument`) — 바이블 §4.1·§4.2 `chunk` 행(입력 `NormalizedDocument`만), 00 §3.2 `chunk` 행 `—`. 04 §1·05 §1의 `ctx.lineage["ParsedDocument"]`는 바이블 §4.1 patch 확정 전까지 제안(잠정)으로 취급. |
| 5 | 하류(`index`·`hydrate`·`pack`)는 `offset_map` 없이 `block_refs → Provenance`를 생성한다 — 바이블 §6.3. 따라서 07 §9의 `original_char_end` 클리핑은 `offset_map`을 요구하는 형태로 정의될 수 없다. |
| 6 | 봉투 `quality`는 상류 `degraded`를 되돌리지 않고 전파한다 — 바이블 §4.1 부분 성공 규약; 06 예시 2(`degraded`) → 08 예시 2도 `degraded`. |
| 7 | 부모(level 1) 청크의 `text` = 자식 리프 `text`의 U+000A 결합, `block_refs` = 자식 refs 재기준 — 정본은 상류 생산자 05 C-4·§5 규칙 5(바이블 §5.4 `ChunkSet` 계층 서술 "부모 = 반환 단위"의 정밀화); 06 예시 1·07 예시 3의 heading 포함 부모 텍스트는 비정본. |
| 8 | 인라인 열거의 등재 위치 = `{Type}.{path}` 이름으로 `$defs`에 등재(파일 미지정) — 바이블 §5.7; 00 §2의 "모두 common-types" 문구는 과도한 좁힘이므로 00을 바이블에 맞춰 정정. |
| 9 | `schema_version`은 `$id` major와 같이 움직인다(major 1 스키마는 1.x만 수용) — 바이블 §6.4·§5(스키마 파일 `$id = urn:rag:schema:{kebab-name}:{major}`); 01·02가 정본 형태, 03~08 스키마도 같은 좁힘을 가져야 한다. |
| 10 | `analyzer_id` 형식 = `{engine}:{version}:{dictionary}` 단일 패턴 — 바이블 §6.1; chunk-set/normalized-document/index-commit 패턴이 정본, index-record의 완화 패턴은 비정본. |
| 11 | `detect` 출력의 `lineage_refs = {}`(fetch 출력을 `source`에 넣지 않음) — 바이블 §5.2 "자기 자신 제외"·§4.2 detect 행(입출력 같은 schema_type)에서 도출되며 00 §3.2 표에 `detect` 행이 추가되어야 한다(00 > 02이지만 02 §1.2 결정이 바이블과 정합). |
| 12 | `Enrichment.keywords[].weight`의 스키마 제약 = 00 소유 `common-types $defs/Enrichment`(현재 하한 없음)가 정본(00 > 06); 06 E-12의 `≥ 0`은 00 minor 제안으로 처리. |
| 13 | `acl_hash`·`metadata_hash` 입력 정규화 규약은 바이블 §6.2가 침묵 → 02 §3("값 없는 선택 필드 제거")이 현행 정본이나 기본값 동치 문제는 바이블 §6.2 patch로 해소해야 한다. |
| 14 | QueryRequest.top_k와 pack.k_max는 별개다: 바이블 §5.5 QueryRequest.top_k "기본 10(팩 k_max와 별개)"·§16 G-08 "최종 K = pack.k_max"·§7.2 standard k_max 20이 정본이며, 09의 `pack.k_max = min(top_k, 프로파일 k_max)`(P-11)는 바이블 patch 전까지 비정본. 11 §2.2 `budget.k_max = 프로파일 query.pack.k_max`가 정본에 부합. |
| 15 | k_max 상한: 바이블 §5.1 ContextPack "항목 20(초안)"·§5.5 budget.k_max → 11 `Budget.k_max 1..20`·`items maxItems 20`이 정본; 09 `PackPlan.k_max 1..50`은 20으로 정합해야 한다. |
| 16 | ContextPack.content_hash: 바이블 §6.2 `H("pack", canonical_json(items))(타임스탬프·trace_id 제외)`와 §9.1 결정성("같은 RankedSet·설정이면 바이트 동일")이 정본 → `items[].acl.checked_at`은 해시 입력에서 제외되어야 하며 11 P-13의 `as_of` 조건 추가는 비정본. |
| 17 | filters.effective_hash: 바이블 §6.2 "백엔드 전송 필터 트리(security+strategy+user+self_query)"·§5.5 CandidateSet.filters_applied "실제 전송 필터(감사)"·§5.5 QueryPlan "순수 데이터"가 정본 → QueryPlan.filters.effective_hash는 계획 트리의 불변 해시, 실전송(page 변환·완화 반영) 트리와 해시는 CandidateSet.filters_applied가 기록(생산자 10), ContextPack.diagnostics는 그 값을 복사. 09 §5.4의 QueryPlan 갱신 규칙은 비정본. `:as_of` 바인드 이름 직렬화는 09의 잠정 해석(바이블 §6.2 patch 대기). |
| 18 | filters_applied 형태: 바이블 §5.5 CandidateSet.filters_applied `{security, strategy, user, self_query}`·§10.2 세 그룹 구분과 §6.4 "식별자 이름은 의미당 하나"에 따라 10의 `FiltersApplied`(09 SecurityFilter/StrategyFilter `$ref`)가 정본 형태; 11의 `PackFiltersApplied`는 `$ref`로 전환하거나 다른 이름을 써야 한다(주체 목록 생략은 바이블 §5.5 diagnostics patch로만). |
| 19 | hydrate 조건 필수 필드: 바이블 §5.5 RankedSet 표(18개: text, context_prefix, heading_path, numbering_path, title, source_uri, external_id, doc_date, doc_type, page_start, page_end, lang, text_source, ocr_confidence_min, chunk_set_blake3, acl, block_refs, sentence_spans)가 §4.3·§8.1 9단계 with_payload 목록(heading_path·numbering_path·page_start·page_end 누락)보다 우선한다 — 10 `HydratedRequired`가 정본과 일치. |
| 20 | RankedResult→ContextItem 승계: 바이블 §5.5 ContextItem 표(common-types `$defs/ContextItem`)가 정본. `heading_path→header.section_path`, `page_*` null→생략, `acl`→`{classification, checked, checked_at=SecurityContext.as_of, source}` 축약, `variant_ids`·`channels_hit`·`block_refs`는 승계되지 않는다(따라서 11 §6·§9의 `item.variant_ids`·`block_refs[j].char_start` 참조는 RankedSet 입력 기준으로 고쳐야 한다). |
| 21 | 오프셋 기준(바이블 §6.3): `Provenance.char_*`·`BlockRef.original_char_*`는 원문 Block.text 코드포인트, `sentence_spans`·`segments`·`BlockRef.char_*`는 Chunk.text 코드포인트. 절단(§5.4)으로 좌표를 재계산할 때 원문 좌표에 display 절단 위치를 대입할 수 없다(07 §9 정정 대상). |
| 22 | 제외 항목 동일성: 바이블 §5.5 CandidateSet "같은 chunk_id가 두 컬렉션에 있으면 별개 후보"에 따라 후보·결과·제외 항목의 동일성 키는 `(collection_id, chunk_id)` — 10 RS-11이 정본, 11 P-6(chunk_id만)은 정합해야 한다. |
| 23 | text_preview: 바이블 §5.4 IndexRecord.text_preview "≤ 200자(MCP concise·디버그)"가 정본 → 07 `text[:200]`·10 payload_slim ≤200이 부합, 11 §8.2 "앞 2개 세그먼트 ≤ 300"은 비정본. |
| 24 | tokenizer.name: 바이블 §6.1 `tokenizer_id`(`hf:`/`tiktoken:`/`anthropic:`/`gemini:`)·§13.4 `tok:{tokenizer_id}:{hash}`가 정본 → 09·11 `TokenizerId` 패턴이 부합하며 바이블 §9.5 예시 `"name": "<target-model-id>"`가 예외(바이블 patch 대상). |
| 25 | 열거 위치: 바이블 §5.7(고유 PascalCase, `$defs` 키 = 열거명)과 00 §2 "열거 타입은 모두 common-types `$defs`"가 정본 → 인라인 열거 `{Type}.{path}`(공급자 열거 3중 정의 포함)는 00 소유 common-types에 등재해야 하며 계약 로컬 `$defs`는 00 §2 규칙 개정 없이는 비정본. |
| 26 | 계약 간 공유 하위 타입(`SecurityFilter`·`StrategyFilter`·`ChannelRunId`·`EmbeddingSpaceIds`·`TableRef`·`ProfileId`·`AnalyzerId`): 00 §2(공용 타입은 common-types, 계약 전용은 자기 `$defs`)에 따라 common-types 승격이 정본 방향; 10의 계약 간 직접 `$ref`와 07의 사본은 모두 과도기 표현. |
| 27 | 봉투 `schema_version`: 바이블 §6.4(`$id` major와 schema_version major 결합)에 따라 `:1` 스키마는 1.x만 수용해야 하며 09의 `^1\.` 패턴이 정본 방향(10·11·07 정합 대상). |
| 28 | 보안 필드(D-09·바이블 §10.2): QueryPlan.security_context+filters.security, CandidateSet.filters_applied.security+security_context_hash, RankedResult.acl(hydrated), ContextItem.acl+classification_max, RenderedContext.tenant_id/collection_ids(공급자 페이로드 제외)가 모두 존재함을 확인 — 정본 위반 없음. |
| 29 | JobState 전이: 바이블 §11.5 상태 기계가 정본(cancelling → cancelled만, cancelling → succeeded 없음). 08 §3 규칙 (6)의 '플립 후 취소 보류 → committed → 잡 상태만 반영'은 표현 불가 전이이므로 바이블 §11.5 patch(ADR) 채택 전까지 12 ALLOWED_TRANSITIONS를 유지하고 08이 정합해야 한다. |
| 30 | 삭제 커밋 존재: 바이블 §11.2 delete.document.v1 · §5.4 IndexCommit.kind('삭제는 record_count=0 커밋')가 정본 → 삭제 잡은 항상 tombstone 커밋을 만들고 12 I-8·IngestDocumentDeletedData(commit_id 필수)가 유효. 08 §7 'current 커밋 없으면 커밋 미생성·index_commit_id=null'은 바이블 미해결 patch 채택 전까지 비정본. |
| 31 | CommitStatus 9단·플립 순서(렉시컬 → 벡터)·보상 2모드: 바이블 §11.4·§5.7 CommitStatus가 정본이며 08·12·common-types 열거가 일치함을 확인. index_generation 할당식 max(index_commits.index_generation)+1은 바이블 §11.4 (6)이 원천을 정하지 않은 영역의 08 정밀화로 인정(patch 제안). |
| 32 | 이벤트 카탈로그 24종·오류 코드 68종·접두 22종: 바이블 §5.7 표가 정본이고 common-types $defs/EventType·ErrorCodeCatalog·12 EVENT_BINDINGS·13 §3.2 표의 철자·개수가 일치함을 확인. recount는 ingest.document.chunked(stage=recount)로 투영(12 결정, 바이블에 recounted 없음). |
| 33 | 경고·폴백 코드의 재시도 열: 바이블 §5.7 표 서두 정의('—' = 오류가 아닌 경고·폴백 코드, Warning.code로만 기록)를 정본으로 하여 normalize.segmenter_fallback·embed.token_overflow는 StageError로 발생하지 않는다(13 §3.2·G5·I4). 바이블 표의 yes 열 배치는 오기로 patch 대상. |
| 34 | StageError ↔ ProblemDetails: 바이블 §5.3 필드(StageError 7·ProblemDetails 9)와 type = urn:rag:error:{code} 1:1(§4.1)이 정본. 00 U-12로 수용된 선택 필드(message·occurred_at·attempt·location·cause·retry_after·request_id·ErrorLocation)와 instance의 uri-reference 표기는 바이블 §5.3 개정 ADR 채택 전까지 N 확장으로만 인정한다(바이블 §5 서문). 변환 규칙(H1~H7, I9 location.pointer)은 00 §2가 해설을 13에 위임했으므로 13 §6이 정본. |
| 35 | StagePolicy: 바이블 §4.4 표·§5.3 행이 정본. non_retryable_error_codes는 카탈로그 no(또는 yes→no 최종) 코드의 투영(13 §4.2 R1~R4), contract.violation·plugin.*는 암묵 포함; 프로파일 YAML의 policy는 부분 선언이고 로더가 §4.4 기본값으로 완성(15 §3.4). |
| 36 | TieringPolicy 경로: 바이블 §5.6 Profile 타입 표의 security.tiering이 정본(§7.3 YAML의 ingest.index.tiering은 patch 대상). 15가 ingest.index.tiering을 false 스키마로 거부하는 것은 정본과 일치. |
| 37 | 게이트 값 형식: 바이블 §5.6 '게이트 값' 행 {value, gate{metric, grid?, min_delta?, min_qrels?, candidate?, dataset, max_cost_per_doc_usd?}}이 정본. §7.3 YAML이 metric·dataset을 생략하므로 15 GateSpec의 metric?·dataset?(기본 ndcg@10·eval.datasets[0])와 min_delta_pt·promote_to·tool 추가는 §5.6 minor 개정 제안으로만 인정; 16 GateOutcome.condition 열거는 15 EvalGate·GateSpec 판정 키와 1:1. |
| 38 | contracts_compat 문법: 바이블 §5.3은 예시(">=1.0,<2.0")만 주므로 계약 개요(00)에 정의가 없고, 상류 소유 문서인 14 §4.3(MAJOR.MINOR 비교절, (>=\|<=\|==\|<\|>), 쉼표 결합, patch 불참)이 정본. schemas/plugin-meta.schema.json ContractsCompat(~= 허용, 3성분 허용)은 14로 맞춘다. |
| 39 | EmbeddingSpaceIds 참조 방식: 00 §2 소유 규칙('계약 전용 하위 타입은 해당 계약 스키마의 자기 $defs')과 15 결정(계약 간 교차 $ref 금지, 사본 + CI 동치)이 정본; 08의 embedded-chunk-set 교차 $ref는 예외이며 common-types 승격(08 미해결 8·15 미해결 13) 전까지 사본 방식으로 통일한다. |
| 40 | EvalRun.index_commit_ids의 'current 커밋': 08 §8·IC-5(생산자 계약; documents.current_commit_id가 가리키는 committed ∧ superseded_by 없음 커밋; 재색인 모드 A의 green 커밋 제외)가 정본. 16 EF-9의 'committed ∧ superseded_by 없음'은 필요조건일 뿐. |
| 41 | EvalRun.index_commit_ids 상한: 바이블 §5.1(EvalRun 64KB·CloudEventEnvelope 64KB)이 정본이며 12 EvalRunCompletedData maxItems 1000이 봉투 64KB에 근거한 값. 16의 2,000은 EvalRun 인스턴스 64KB 안에서 재산정하고 이벤트에는 해시(index_commits_hash)로 완전성을 보장한다. |
| 42 | CloudEventEnvelope.source 컴포넌트: 바이블 §6.5 source = urn:rag:{component}·§2.3 컨테이너 표(api, worker, relay…)가 정본이며 12 §5가 값 집합을 api\|worker로 정한다. 14 예시 4의 urn:rag:index는 정본 밖 값. |
| 43 | dataschema: 바이블 §5.3 CloudEventEnvelope.dataschema(N)·14 §5.4('data가 완전한 인스턴스일 때만')·12 §5('24종 모두 생략')가 정본. 00 §4.12 예시의 urn:rag:schema:job-status:1은 정본과 불일치. |
| 44 | dictionary_hash·analyzer_id·lexical_profile_hash: 바이블 §6.1 analyzer_id {engine}:{version}:{dictionary}, §6.2 dictionary_hash = H("dict", *sorted(정규화 행)), lexical_profile_hash = H("lex", analyzer_id, dictionary_hash, mapping_version)이 정본. 정규화 행 정의는 16 §6.2(생산자)가 확정하되 §6.2 patch 제안; mapping_version의 계약 위치는 미정(15 반영 제안). |
| 45 | ConvertRequest/ConvertResponse ↔ parse 정책: 바이블 §5.6 표·§4.2 parse 실패 정책(document_encrypted·distribution_document·unsupported_variant·corrupt_container 비재시도, sidecar_unavailable 재시도 후 폴백, conversion_failed 폴백 체인)이 정본. 16 §7.3의 '비재시도 parse.*는 폴백 없이 전파'는 바이블과 일치하며 ADR-0033 문구가 patch 대상. |
| 46 | 한계 수치: 바이블 §5.1 마지막 열이 정본(JobStatus 8KB, CloudEventEnvelope 64KB, StageError/ProblemDetails 4KB, CollectionSpec 32KB, Profile 256KB, PluginMeta 8KB, Convert* 16KB, Eval* 64KB, UserDictEntry 2KB/행, FeedbackEvent 8KB, Capabilities 4KB, StagePolicy/TieringPolicy 2KB, EgressPolicy 4KB, ContextPack 항목 20, CandidateSet 채널 런당 300). 15 PackConfig.k_max ≤ 100·ChannelConfig.top_k ≤ 1000은 정본 초과. |
| 47 | 오프셋 기준: 바이블 §6.3(유니코드 코드포인트, 0-based, 끝 미포함; Provenance·AnswerSpanRecord는 원문 Block.text 기준, BlockRef.char_*는 Chunk.text 기준, original_char_*는 원문 기준)이 정본이며 16 AnswerSpanRecord·span_hit_rate@k(block_refs.original_char_* 교차)·13 ErrorLocation(page 1-based, block_id hex32, chunk_id hex64)이 일치함을 확인. |

## 4. 문서 내부·기타 미해결 이슈 (출처 문서 순)

바이블 개정이 아닌 항목(문서 자체 보강, 외부 확인 필요, 다른 문서 소유자 결정 대기). 4단계 P1 전파 에이전트가 해당 문서를 다룰 때 함께 처리한다.

| # | 출처 문서 | 결과 그룹 | 내용 |
|--:|---|---|---|
| 1 | 00-contract-overview.md | contracts | StageError.cause의 '중첩 깊이 ≤ 3'은 JSON Schema로 표현하지 않고 Pydantic 검증에만 두었다(스키마는 무제한 재귀). 스키마 수준 강제가 필요하면 unrolled 정의가 필요하다. |
| 2 | 00-contract-overview.md | contracts | 리뷰 항목 '샘플링 수치는 04-pipelines/01 실측 후 기입'은 실측 자료가 없어 수치를 넣지 않고 U-5 절차로만 남겼다(반영 보류가 아니라 의도된 미확정). |
| 3 | 00-contract-overview.md | contracts | ajv·Python이 로컬에 없어(npm install 네트워크 실패) 골든 예시 검증은 common-types가 쓰는 키워드 서브셋을 구현한 자체 검증기로 수행했고, Pydantic 블록은 실행 없이 정독으로만 문법을 확인했다. CI의 §10.3 게이트(ajv/jsonschema + Pydantic 동치)에서 재확인이 필요하다. |
| 4 | 00-contract-overview.md | contracts | HWPX/HWP 미디어 타입(application/hwp+zip vs application/vnd.hancom.hwpx, application/x-hwp)은 확인 필요(as of 2026-09)로 표기했고 정본 확정은 02-source-document에 위임했다. |
| 5 | 01-api-design-guidelines.md | finish | 리뷰 항목은 모두 반영했으며 미반영 항목 없음. |
| 6 | 01-api-design-guidelines.md | finish | 앵커 간 잔존 간극(문서 내 미해결 이슈 2에 기록): 바이블 §10.3 E1과 계약 개요 §4.5는 본문 tenant_id를 422로 정하지만 바이블 §5.7 카탈로그에 422 코드가 없어 auth.tenant_mismatch 채택 전까지 400 임시 응답이 E1의 상태와 어긋난다 — 조기 채택 요청으로 남김. |
| 7 | 01-api-design-guidelines.md | finish | DELETE /v1/collections/{collection_id} 202·JobKind는 여전히 (초안)(기존 미해결 이슈 8). |
| 8 | 01-deployment-guide.md | finish | compose YAML 블록 4개는 파서(js-yaml/pyyaml/docker compose config)가 환경에 없어 기계 검증을 못 했다 — 구조 수동 확인만 수행 |
| 9 | 01-deployment-guide.md | finish | temporal-sql-tool 플래그(--ep/-p/-u/--db)·SQL_PASSWORD 환경 변수·스키마 디렉터리 경로(./schema/postgresql/v12/{temporal,visibility}/versioned)는 Temporal 1.32 이미지로 확인 필요(문서 내 단서 유지, 미해결 이슈 7) |
| 10 | 01-ingest-request.md | contracts | [anchor major, 503] 13 §3.3이 contract.violation 대용을 부적절로 판정해 503의 채택 전 대안 코드가 존재하지 않는다. api.orchestrator_unavailable·api.dependency_unavailable 조기 채택을 '구현 전제'로 적었으나 채택 여부는 13·바이블 소유자 결정(이슈 13). |
| 11 | 01-ingest-request.md | contracts | [검증 한계] 이 머신에 Python이 없어 Pydantic 블록은 AST 파싱 대신 육안 검토만 했다(224행). 예시 검증은 ajv가 없어 스크래치패드의 자체 JSON Schema 2020-12 부분집합 validator(ir-validate.js)로 수행했다 — $ref·pattern·uniqueItems·maxProperties·required·if/then은 검사하지만 format 검증은 하지 않는다. |
| 12 | 01-ingest-request.md | contracts | [schema_version] IngestAccepted.required 축소·CredentialsRef 상한 축소·배열 상한 상향은 스키마 변경이지만 게시 전 초판이라 schema_version 1.0.0을 유지하고 버전 이력 1.0.0 행에 '리뷰 1차 반영'으로 기록했다. 이미 게시된 것으로 취급해야 하면 1.1.0(가산)/2.0.0(CredentialsRef 축소는 강화) 판단이 필요하다. |
| 13 | 01-ingest-request.md | contracts | [frontmatter version] 지시에 없어 문서 version 0.1.0을 유지했다(status만 active로). |
| 14 | 01-ingest-request.md | contracts | [미반영 없음 확인] 리뷰 18항목 중 blocker/major 6건 전부 반영, minor 12건 전부 반영(dry_run·A4 완화안은 위 사유로 대안 경로 선택). |
| 15 | 01-pipeline-framework.md | pipelines-pass1 | [검증 한계] YAML 발췌 블록(§4.2)은 바이블 §7.3에서 복사·재배치한 것으로 별도 YAML 파서 검증은 수행하지 않음(node에 yaml 라이브러리 없음). Mermaid 5블록은 문법을 육안 확인만 함(sequenceDiagram의 alt/opt 중첩 사용). |
| 16 | 01-repository-structure.md | finish | 리뷰 항목 1의 첫 대안(ADR-0035 표의 FastAPI 범위 이식)은 미반영 — ADR-0035에 FastAPI 버전 범위가 존재하지 않고 발췌 자체가 범위 없이 `fastapi`를 나열하므로(앵커 우선) 주석 방식으로만 반영 |
| 17 | 01-repository-structure.md | finish | 문서 자체의 미해결 이슈 1~16은 그대로 유지(다른 문서 소유자 확정 대기) |
| 18 | 01-system-overview.md | architecture | frontmatter version은 0.1.0 유지(지시가 status·last_updated만 명시). 개정 이력이 필요하면 0.1.1로 올릴 것. |
| 19 | 01-system-overview.md | architecture | 바이블 §4.2 index 행('commit_id·index_generation은 워크플로우가 1회 발급·할당')과 §11.4 (6)('index_generation은 원장 documents 행 잠금 아래 할당') 사이의 표현 차이는 §11.4 (6)을 따랐다. 바이블 내부 표현 통일은 바이블 소유자 판단 사항. |
| 20 | 02-component-architecture.md | architecture | [미반영] 리뷰 tech-minor 'ADR-0026/0027/0031/0032/0033 링크 끊김' — 현재 저장소에 해당 파일이 존재하므로(0001~0033) '작성 예정' 표기는 실제 미작성인 0034·0035·0037과 04-pipelines/01·09-operations/02·10-development/01에만 붙였다. |
| 21 | 02-component-architecture.md | architecture | [설계 판단] Valkey 설정을 필수(`ValkeySettings.url: str`, `RuntimeServices.kv`·`acl_hints` 비Optional)로 바꿨다(바이블 §2.2·§11.6 lite 필수 컨테이너 근거). `backend_tokens`만 Optional 유지(OpenSearch 없는 lite). |
| 22 | 02-component-architecture.md | architecture | [확인 필요] `BackendClientFactory.qdrant()/opensearch()` 반환 타입 주석의 `AsyncQdrantClient`·`AsyncOpenSearch`는 라이브러리 클래스명이며 07-tech-landscape 근거를 직접 확인하지 않았다(코드에서는 `Any`로 두어 단정하지 않음). |
| 23 | 02-component-architecture.md | architecture | [eval.run.v1 실행 위치] §7.1에서 worker 열에 `maintenance` 큐 `eval.run.v1`을 ●로 적었으나 운영 기본 실행 위치(CI 프로세스/maintenance 워커/별도 Job)는 01-system-overview 미해결 이슈 6이 06 문서에 위임한 상태라 이 문서에서는 확정하지 않았다. |
| 24 | 02-configuration-reference.md | finish | 리뷰어가 제시한 대안(S-6에 tier=lite 예외를 두어 기동 실패 대신 rerank 비활성 + degraded 경고)은 채택하지 않았다 — fail-closed 결정(§6.1, 결정 사항 요약)을 유지하고 내장 lite를 enabled: false로 두는 제1안이 바이블 §7.1·배포 가이드와 더 직접 정합하기 때문 |
| 25 | 02-configuration-reference.md | finish | 내장 lite가 rerank.enabled: false가 되면서 standard 전문에 바이블 §7.3에는 없는 선택 키 `enabled: true`가 필요해졌다 — 바이블 §7.3 patch 또는 RerankConfig.enabled 생략 시 병합 해석 규칙(15 §3.8, ADR-0031 minor) 확정을 미해결 이슈 15로 등재 |
| 26 | 02-configuration-reference.md | finish | P-2는 메타 불변식(규칙 3·6·10·11·12를 스키마가 강제)이라 별도 detail 메시지가 없다 — 검증기 구현 시 해당 규칙 번호로 보고한다고 표기 |
| 27 | 02-configuration-reference.md | finish | YAML 블록은 실제 YAML 파서로 검증하지 못했다(환경에 PyYAML·js-yaml 없음, npm 레지스트리 접근 차단) — 구조 검사만 통과; CI 골든 예시 추출(10-development/05 tools/docs/extract_examples.py)에서 재검증 필요 |
| 28 | 02-development-environment.md | finish | 리뷰 항목 중 미반영 항목 없음(minor 1건 전부 반영). |
| 29 | 02-epics-and-backlog.md | finish | 참조 ADR 목록에 T-EVL-19가 텍스트로 언급하는 0006·0019는 여전히 링크가 없다(리뷰 항목 아님, 일관성 차원의 후속 후보). |
| 30 | 02-fetching-and-source-resolution.md | finish | 리뷰 major 3이 제안한 전용 코드명 `fetch.storage_unavailable` 대신 depends_on 계약 02-source-document 미해결 이슈 7이 이미 제안한 `fetch.store_failed`를 채택했다(계약 문서와 이름 통일). |
| 31 | 02-fetching-and-source-resolution.md | finish | 리뷰 범위 밖이지만 같은 원칙(`fetch.upstream_error`는 원천 전용)에 따라 'KeyProvider 일시 불가'도 §9.1의 `fetch.upstream_error` 행에서 '플랫폼 내부 의존성 장애(코드 없음, 셸 재시도)' 행으로 옮겼다. |
| 32 | 02-fetching-and-source-resolution.md | pipelines-pass1 | E16 scope per scheme (operator endpoints for s3/gs/az/smb exempt from deny_cidrs) needs ADR-0038 patch and bible §10.3 E16 wording ('tenant-controlled destination') |
| 33 | 02-fetching-and-source-resolution.md | pipelines-pass1 | checksum_hint / expected_size_bytes / fetch_report.checksum_verified fields and fetch.checksum_mismatch code (FR-ING-09) need ADR minor on bible §5.4/§5.7 and 01/02 schema updates |
| 34 | 02-fetching-and-source-resolution.md | pipelines-pass1 | Supplying the previous SourceDocument to fetch (conditional GET, previous_doc_version): proposed requires_lineage=(SourceDocument,) with lineage_source=ledger_current; needs 01-pipeline-framework/06 patch and bible §4.1 wording change |
| 35 | 02-fetching-and-source-resolution.md | pipelines-pass1 | Post-fetch decision mechanics: decide_after_fetch local activity (06) and how collection/tenant defaults (pii_policy, dedup_policy) reach the stage (ctx.policies vs API-filled values; conflicts with 01 §6 'defaults not filled') |
| 36 | 02-fetching-and-source-resolution.md | pipelines-pass1 | Local spool only in v1; multipart staging key tenants/{tenant_id}/staging/{request_id} reserved but unimplemented; conditional PUT support per store unverified (as of 2026-09) |
| 37 | 02-fetching-and-source-resolution.md | pipelines-pass1 | Five proposed error codes (fetch.tls_failed, fetch.checksum_mismatch, fetch.malware_detected, fetch.scanner_unavailable, fetch.container_unsupported) require 13-error-model §3.3 listing + ADR minor; tls_failed early adoption recommended to avoid wasted retries |
| 38 | 02-fetching-and-source-resolution.md | pipelines-pass1 | Malware scan hook: MalwareScanner port, clamd address/Helm optIn not in bible §12 or manifests; ClamAV license and clamd stream limit need verification (as of 2026-09) |
| 39 | 02-fetching-and-source-resolution.md | pipelines-pass1 | Observability proposals (rag.fetch.call kind=source, rag_fetch_* metrics, scheme label, golden-hash exclusion of fetched_at/duration_ms/bytes_per_sec) need 09-operations/03 agreement and ADR-0022 minor |
| 40 | 02-fetching-and-source-resolution.md | pipelines-pass1 | sftp scheme absent from bible; smb plugin naming differs between 01 (rag-plugin-smb) and 05 (rag-plugin-smb-fetcher / fetcher.smbprotocol) |
| 41 | 02-fetching-and-source-resolution.md | pipelines-pass1 | Fetch-output artifact key: byte-hash key adopted vs 02's fetch_key proposal; bible §13.3 patch needed |
| 42 | 02-fetching-and-source-resolution.md | pipelines-pass1 | Native conditional GET support for gs/az and fsspec ETag exposure unverified (as of 2026-09); HEAD comparison is the fallback rule |
| 43 | 02-fetching-and-source-resolution.md | pipelines-pass1 | resolve_pin feasibility with httpx/httpcore sni_hostname extension unverified (as of 2026-09); fallback is ADR-0038 review condition 1 (egress proxy) |
| 44 | 02-fetching-and-source-resolution.md | pipelines-pass1 | zip_members v1.1 path requires SourceDocument.container_manifest_ref, ctx.artifacts.get_source, child-job creation activity in 06, parent aggregation rules in 12, member-limit warning code; json_array 'members are separate documents' (01) vs router-internal split (bible §7.3) tension left to 04-pipelines/03 |
| 45 | 02-fetching-and-source-resolution.md | pipelines-pass1 | allowed_hosts semantics for object-storage schemes (URI authority = bucket/container) needs 03-contracts/15 §8 wording patch |
| 46 | 02-fetching-and-source-resolution.md | pipelines-pass1 | ingest.document.fetched extension key not_modified (and 03-data-flow's conditional_304) needs 03-contracts/12 agreement |
| 47 | 02-fetching-and-source-resolution.md | pipelines-pass1 | uri_fetcher library research (fsspec vs obstore vs SDKs, httpx, smbprotocol; versions/licenses) still not performed; selection remains provisional with §2.4 criteria |
| 48 | 02-ingestion-api.md | finish | [관찰, 이 문서 범위 밖] 04-management-api.md line 108은 같은 엔드포인트 응답을 `Document`(+`reprocess_suggested`)로 적어 이 문서의 `DocumentMeta`(+`reprocess_suggestion`)와 이름이 다르다. 04는 depends_on이 아니고 동시 작성 중이므로 수정하지 않음 — 이 문서 미해결 이슈 3(DocumentMeta 소유·04 링크)에서 마무리 단계에 정합 필요. |
| 49 | 02-ingestion-api.md | finish | [유지] SDK `client.jobs.wait_all(job_ids, timeout=, on_event=)` 키워드 인자와 `IngestBatchAccepted.jobs`·`.replayed` 속성은 06 §3.5·§5.1 방향과 부합하나 06이 정확한 시그니처를 확정하지 않아 예시 수준으로 둠. |
| 50 | 02-source-document.md | contracts | [미반영] 리뷰(anchor) 'dependentRequired {pii_tokenize_mode: [pii_policy]} 추가': pii_policy가 required라 중복 제약이어서 생략, if/then/else만으로 S-5와 동치. |
| 51 | 02-source-document.md | contracts | [미반영] 리뷰(tech) 'detector_plugin_id == producer.plugin_id 불변식 추가' 대안: 필드를 제거하는 쪽을 택해 불변식은 불필요. |
| 52 | 02-source-document.md | contracts | [미반영] 리뷰(tech) 'S-13 완화(not_modified ⇒ source_bytes_reused만)': 검증자 원천을 커밋된 세대로 한정하는 쪽을 택해 S-13 원문 유지. |
| 53 | 02-source-document.md | contracts | [미반영] 리뷰(anchor) 'PluginId를 common에서 임포트': detector_plugin_id 제거로 사용처가 없어져 로컬 정의만 삭제(임포트 불필요). Bcp47은 00 Pydantic 절에 없어 로컬 유지 + 미해결 이슈 15. |
| 54 | 03-coding-standards.md | finish | 리뷰 3건 모두 반영. 미반영 항목 없음. |
| 55 | 03-coding-standards.md | finish | §3.1 mypy 멤버 검사 방식(--config-file 공유 vs 멤버별 [tool.mypy])은 01 §3.3 템플릿에 [tool.mypy]가 없다는 현재 상태를 근거로 공유 방식으로 서술했으며, 최종 확정은 미해결 이슈 1(CI 첫 잡 검증)·05-ci-cd에 맡김. |
| 56 | 03-data-flow-and-document-lifecycle.md | architecture | [minor 6 링크] 15개 미작성 링크는 공통 규약('depends_on 문서가 없으면 링크만 문서 맵 경로로 건다')에 따라 유지하고 '(미작성)' 코드 스팬 대체는 하지 않았다. 미해결 1에 전체 목록과 게시 후 재검사 규칙을 추가했다. 리뷰어가 13개로 집계했으나 열거된 경로는 15개다. |
| 57 | 03-data-flow-and-document-lifecycle.md | architecture | [후속 대조 필요] 06-orchestration 미해결 17(b)의 `index.commit.published`·`ingest.document.deleted` 발행 주체 통일(`stage.index` 사가 vs `stage.publish`)은 본 문서 §10 표의 '발행 주체 = publish' 표기와 다를 수 있어 03-contracts/12 게시 후 대조 항목으로 미해결 1에 남겼다(본문 표는 바꾸지 않음). |
| 58 | 03-data-flow-and-document-lifecycle.md | architecture | [후속] 03-contracts/02-source-document가 fetch 출력(`fetch_key`, artifacts 행 없음)/detect 출력(`stage_key`, artifacts 등재) 이원화를 결정했으므로 §2.1 fetch 행과 §5.3 (d)·§7.3의 임시 규칙은 fetch 출력 봉투에만 해당한다 — 바이블 §13.3 patch 확정 후 본문 정리가 필요하며 미해결 19에 기록했다. |
| 59 | 03-golden-dataset-construction.md | finish | 반영하지 않은 리뷰 항목 없음(3건 모두 반영) |
| 60 | 03-golden-dataset-construction.md | finish | Sonnet 5·Opus 5의 `budget_tokens`·`temperature` 400 거부는 확인 필요(as of 2026-09)로 표기만 했고 실제 API 확인은 미해결 이슈 11 첫 배치 실행 시 수행 |
| 61 | 03-parsed-document.md | contracts | 예시 2 `model_ids`의 RapidOCR 항목은 `RapidAI/RapidOCR@<40-hex>` 플레이스홀더로 두었다 — 기술 지형 02는 GitHub 리포만 확인하고 HF 리포·revision 표기 근거가 없어 '확인 필요(as of 2026-09)'로 표기하고 미해결 이슈 14로 등재(리뷰어 제안 'ADR-0008이 정한 모델 식별자'는 ADR-0008에 존재하지 않아 그대로 반영하지 못함) |
| 62 | 03-parsed-document.md | contracts | Pydantic `LineageRefs`·`Producer`·`Warning`은 00 게시 블록에 없지만 00 도입부 문구('나머지 공용 타입은 $defs와 1:1')와 04-normalized-document의 동일 임포트 관행을 근거로 임포트를 유지하고, 원시 별칭 3개만 로컬 선언했다(00 명시 추가 제안은 미해결 이슈 11) |
| 63 | 03-parsed-document.md | contracts | §6 선형화 비가역성은 리뷰어의 두 대안 중 'U+2028 치환 규칙'이 아닌 '파생 문자열·경계 복원 금지 명시' 안을 택했다(셀 text 원문 보존 원칙 유지) |
| 64 | 03-parsed-document.md | contracts | schemas/parsed-document.schema.json은 변경하지 않았다 — 반영 항목이 모두 JSON Schema로 표현 불가한 불변식·문서 서술·Pydantic·예시 수준이며 문서 내 블록과 저장 파일이 바이트 동일함을 확인 |
| 65 | 03-parsed-document.md | contracts | 리뷰 항목 외 잔여 사항: 예시 2가 통과한다고 선언한 JSON Schema 검증(ajv 등)은 이 환경에 검증기가 없어 node 스크립트로 불변식·구조만 검증했고 스키마 엔진 검증은 00 §10.3 CI 게이트에 위임 |
| 66 | 03-parsing-router-and-format-detection.md | finish | 이 문서는 스키마 파일을 소유하지 않으므로 schemas/* 변경 없음; 02 문서(SourceDocument) 예시·Pydantic은 이미 정본 규칙과 일치해 변경 요청 없음. |
| 67 | 03-parsing-router-and-format-detection.md | pipelines-pass1 | 판별·스캔·품질 신호 임계값 전부 초안 목표 → 골든 코퍼스로 확정 |
| 68 | 03-parsing-router-and-format-detection.md | pipelines-pass1 | then 깊이 1·then 대상 체인 then 금지·lite sidecar 거부의 프로파일 검증 규칙 추가(15 문서) |
| 69 | 03-parsing-router-and-format-detection.md | pipelines-pass1 | SourceFormat에 pptx·xlsx·csv·image 값 부재로 2급·실험 포맷이 unknown 거절 → 열거 추가 minor ADR |
| 70 | 03-parsing-router-and-format-detection.md | pipelines-pass1 | stage.parse 정책 선택이 잠정 format 기반; source_kind 확정 후 OCR 큐 재디스패치는 06과 합의 필요 |
| 71 | 03-parsing-router-and-format-detection.md | pipelines-pass1 | cost_class 계약 부재(Capabilities.extra 제안) |
| 72 | 03-parsing-router-and-format-detection.md | pipelines-pass1 | profile_overrides.parse.pdf.route 값 집합과 stage_key 반영 경로(overrides_hash) 미정 — 확정 전 force=true |
| 73 | 03-parsing-router-and-format-detection.md | pipelines-pass1 | SplitRoute 멤버 전개 주체(fetch vs 디스패처)·멤버 상한·경고 코드 미정(01 이슈 5) |
| 74 | 03-parsing-router-and-format-detection.md | pipelines-pass1 | 품질 신호 기록용 경고 코드·probe_thresholds 키가 카탈로그·프로파일 스키마에 없음 |
| 75 | 03-parsing-router-and-format-detection.md | pipelines-pass1 | 라우터 지문이 전 포맷 멤버 지문을 합성해 한 멤버 변경이 모든 parse 캐시를 미스시킴 — 포맷별 지문·지연 조회 검토 |
| 76 | 03-parsing-router-and-format-detection.md | pipelines-pass1 | format_detector 프로파일 위치(parse.detect 키 vs 고정 기본)와 02 예시 plugin_id 표기 통일 |
| 77 | 03-parsing-router-and-format-detection.md | pipelines-pass1 | parser.hwpx_hwpxlib_sidecar·parser.hwp5_tika_distribution 모듈 맵 부재; hwplib 암호 HWP 지원·FileHeader 비트·hwp3 시그니처·hwpml-package+xml 허용은 확인 필요(as of 2026-09) |
| 78 | 03-parsing-router-and-format-detection.md | pipelines-pass1 | page_route 병합의 element_path 유일성·page_break·읽기 순서와 복수 파서 지문 표현(parser_chain_report 제안) |
| 79 | 03-parsing-router-and-format-detection.md | pipelines-pass1 | then 체인의 parser_chain 기록 순서(04 문서 lo-sidecar 절과 상이)와 Tika 경로 plugin_id 명칭 불일치(04 vs 05) |
| 80 | 03-risks-and-mitigations.md | finish | 리뷰 항목 4의 '(비정본) 표기' 지시는 그대로 따르지 않았다. 이유: judged@10은 바이블 §5.1·§7.3 정본이고 span_hit_rate@k도 바이블 §5.1 EvalReport.metrics 정본 키여서, 비정본 표기보다 정본 식별자(rag_eval_metric_value{metric="span_hit_rate@10"}, eval.gates.judged@10.warn_below)로 교체하는 것이 앵커 우선 규칙에 맞다. 원천 문서 명시 요구는 §5.2 신설 행(08-evaluation/03·05 링크)으로 충족. |
| 81 | 03-risks-and-mitigations.md | finish | 이 문서 미해결 이슈 13(02-epics-and-backlog·10-development/05-ci-cd·05-api/04-management-api와 동시 작성으로 내용 대조 미완)은 이번 수정 범위 밖이며 그대로 남아 있다. |
| 82 | 04-llm-judge-and-generation-quality.md | finish | major 3: 리뷰어 제안 ULID 01J9ZP7Q2W4E6R8T0Y1U3I5A7S는 Crockford base32 금지 문자 I·U를 포함해 스키마 패턴에 실패하므로 그대로 쓰지 않고 유효한 값으로 대체함 |
| 83 | 04-llm-judge-and-generation-quality.md | finish | JudgeRecord.schema_version은 필드 추가에도 1.0.0 그대로 둠(계약 게시 전 제안 스키마이므로 버전 이력 없음) |
| 84 | 04-management-api.md | finish | 삭제 감사 값 어휘(`manage_collection` vs 19의 `delete_collection` 값 제안)는 리뷰 범위 밖이라 §미해결 이슈 6에 메모만 추가하고 본문 결정은 바꾸지 않음 |
| 85 | 04-normalized-document.md | contracts | Python이 이 머신에 없어 Pydantic 블록의 py_compile을 수행하지 못했다. 같은 알고리즘(fold + 조각별 NFKC)을 node로 실행해 ㉠/㈀/ﾡ/ﾠ 사상·고정점·조합형 자모 부재를 확인했고 추가 코드는 표준 구문(str.maketrans 단일 문자 키 dict, 스타 튜플)만 사용했다. |
| 86 | 04-normalized-document.md | contracts | analyzer_token_count 70(예시 2)은 Kiwi 실행 없이 추정한 예시값(N 필드, 이전 판 58도 동일 성격). |
| 87 | 04-normalized-document.md | contracts | 타 문서 patch는 요청만 기록(이 문서 범위 밖): 09 §3.11·§3.14·N14 행, 05 미해결 이슈 13, common-types $defs/NormalizedBlock.lexical_text description(00 소유), 바이블 §5.4·§6.3. |
| 88 | 04-parser-hwpx-and-hwp.md | finish | 리뷰의 5개 major 항목은 모두 반영했으며 반영하지 않은 항목은 없다. |
| 89 | 04-parser-hwpx-and-hwp.md | finish | lo-sidecar도 같은 convert 계약(input.uri 직접 읽기)을 쓰는데 08 §5.2·이 문서 §4.6은 egress 0으로 적는다 — 리뷰 범위 밖이라 미해결 이슈 20에 확인 요청으로만 덧붙였다. |
| 90 | 04-parser-hwpx-and-hwp.md | pipelines-pass1 | OWPML tag/attribute names flagged 확인 필요 (hp:tc/@header, hp:tbl/@repeatHeader, hp:caption/@side values, hp:shapeComment, hp:header/@applyPageType, tracked-change and memo element names, hp:fieldBegin/@type list and hp:parameters, hh:charPr/@height unit, hh:paraHead placeholder, content.hpf meta names, encryption manifest entry, hp:hyphen replacement) must be verified against python-hwpx 6.4.x schema docs and hwpxlib source |
| 91 | 04-parser-hwpx-and-hwp.md | pipelines-pass1 | No artifacts[].kind for HWPX BinData original bytes; figure_crop is reused — propose figure_source (minor) or clarify figure_crop semantics |
| 92 | 04-parser-hwpx-and-hwp.md | pipelines-pass1 | No catalog warning codes for structure loss / skipped elements / preview mismatch / spacing suspicion; propose parse.structure_lost, parse.element_skipped, parse.preview_mismatch, parse.spacing_suspect (minor ADR with 13-error-model) |
| 93 | 04-parser-hwpx-and-hwp.md | pipelines-pass1 | Heading tier-3 score thresholds, table role heuristics, and genre inference thresholds are drafts to be tuned on the corpus |
| 94 | 04-parser-hwpx-and-hwp.md | pipelines-pass1 | Inline (treatAsChar) formulas split into separate formula blocks leave no position marker in paragraph text; consider [formula:{block_id}] placeholder with 03 owner |
| 95 | 04-parser-hwpx-and-hwp.md | pipelines-pass1 | No contract path connects the opt-in page_map derived artifact to IndexRecord.page_start/page_end or FilterableField.page; Provenance.page stays null |
| 96 | 04-parser-hwpx-and-hwp.md | pipelines-pass1 | content.hpf timestamp timezone interpretation (Asia/Seoul assumption) is a draft rule |
| 97 | 04-parser-hwpx-and-hwp.md | pipelines-pass1 | Encrypted HWPX decryption via korean-gov hwpxlib sidecar has no dedicated plugin_id; recorded as parser.hwpx_python_hwpx + profile_option=hwpx_encrypted_hwpxlib pending bible §12 decision |
| 98 | 04-parser-hwpx-and-hwp.md | pipelines-pass1 | deadline_ms derivation ratio differs between 04-pipelines/01 (0.8) and 03-contracts/16 (0.9); propose 0.8 |
| 99 | 04-parser-hwpx-and-hwp.md | pipelines-pass1 | Sidecar-path parser_fingerprint.parser_version cannot carry Java library versions; propose composite notation with 03 open issue 4 |
| 100 | 04-parser-hwpx-and-hwp.md | pipelines-pass1 | unhwp JSON output field names/stability unconfirmed, helper spawn overhead unmeasured, linux-arm64 wheel absent (ADR-0007 review condition 4) |
| 101 | 04-parser-hwpx-and-hwp.md | pipelines-pass1 | No A-grade decryptor for encrypted HWP 5.0 even with credentials_ref; hwp-cli/openhwp claims unverified — stays parse.document_encrypted in v1 |
| 102 | 04-parser-hwpx-and-hwp.md | pipelines-pass1 | Fallback-rate metric not in the canonical metric list; propose rag_parse_fallback_total{stage, outcome} |
| 103 | 04-parser-hwpx-and-hwp.md | pipelines-pass1 | HWP 5.0 FileHeader bit positions, record tag numbers, and control IDs are based on public implementations, not the spec PDF (HTTP 403) — verify |
| 104 | 04-parser-hwpx-and-hwp.md | pipelines-pass1 | 04-pipelines/03 parsing router was being written concurrently; router item isolation default, then: semantics, and detect cache rules were taken from bible/ADR text and need cross-check after 03 is published |
| 105 | 04-scaling-and-performance.md | finish | 리뷰 항목 2건 모두 반영 — 미반영 항목 없음. |
| 106 | 04-scaling-and-performance.md | finish | 기존 미해결 이슈 1~16(문서당 청크 수 c 불일치, 읽기 복제 DSN, 리랭커 GPU 등급과 top_n_in, api 사이징 상수 등)은 이번 리뷰 범위 밖이며 그대로 유지. |
| 107 | 04-storage-architecture.md | architecture | Tech minor `_id` citation: kept brief D-06 as the primary cite (brief D-06 v1.2 explicitly states `OpenSearch _id = record_id`, so the reviewer's claim that D-06 only covers content-hash versioning is incorrect); added bible §5.4 `record_id` row and ADR-0004 alongside rather than replacing. |
| 108 | 04-storage-architecture.md | architecture | Anchor major (compression): the reviewer described 03-contracts/00 §9.2 as specifying '1MB threshold, zstd level 3, derived uncompressed'; the current file's §9.2 contains only 미정(U-4) delegating to this document with stored-bytes semantics. Applied the substantive fix (ADR-0011 removed, §9.2/U-4 anchoring, difference table, issue #6 rewritten) but the difference table reflects the actual current §9.2 text, not the quoted content. No new ADR number assigned (bible §3.3 governs numbering) — slug proposed only. |
| 109 | 04-storage-architecture.md | architecture | Tech major (RLS for relay): chose the separate `rag_maintenance` role with cross_tenant policies rather than the alternative of excluding `outbox` from RLS, to stay within bible §13.1 'all tables RLS FORCE'. |
| 110 | 04-storage-architecture.md | architecture | Tech major (heading_path): did not introduce a `heading_path_top2` field (would add an IndexRecord field beyond bible §5.4); indexed the full `heading_path` keyword array with filter-builder depth limiting and left the separate-field idea as open issue #17 for 03-contracts/07. |
| 111 | 04-storage-architecture.md | architecture | Tech minor (Nori DEFAULT_STOP_TAGS count): changed to 'Lucene DEFAULT_STOP_TAGS 18개; 07-tech-landscape/13 122행의 30개는 세분 표기 — 확인 필요(as of 2026-09)' because the reviewer's count is an external fact not verifiable from repository sources; 07-tech-landscape/13 itself was not edited (not this task's file). |
| 112 | 04-storage-architecture.md | architecture | `optimizers_config.default_segment_number` per-profile row added as 초안 목표 (lite 2 / others 4) — values are unmeasured assumptions pending 09-operations/04. |
| 113 | 04-storage-architecture.md | architecture | `outbox` retention implemented as daily RANGE partitions + DROP; the reviewer's alternative (no partition + DELETE WHERE published_at < now()-7d) was not adopted. |
| 114 | 04-storage-architecture.md | architecture | Length: reduced to 899 lines (limit 900) mainly by compacting JSON blocks and ER attribute blocks; further growth from future edits will need offsetting cuts. |
| 115 | 04-testing-strategy.md | finish | `test_public_baseline`의 `slow` 배정은 리뷰 항목이 아니며 P5(PR CI egress 금지)와의 일관성을 위해 이 문서 권한(마커 배정)으로 추가한 것 — 08/02 소유자가 PR 층 실행을 원하면 조정 필요. |
| 116 | 05-benchmark-plan-and-baselines.md | finish | minor 4의 '`ko-quality` 1 컬렉션' 제안은 2 컬렉션으로 조정 — E-O02 절차가 sparse 단독 교체 (i)와 ko-quality 전체 (ii) 두 섀도를 요구함. |
| 117 | 05-benchmark-plan-and-baselines.md | finish | ADR 파일은 사용자 지시(ADR 제외)에 따라 읽지도 수정하지도 않음; ADR 번호·slug는 문서 기존 표기 유지. |
| 118 | 05-chunk-set.md | contracts | 리뷰어 제안 중 '표 블록에 pii_spans가 없을 때 TableData.cells[].text 허용'은 채택하지 않음: 04 pii_spans는 블록 display_text 기준이고 표 블록 display_text가 ""라 셀 PII를 표현할 수 없어 조건이 항상 공허하게 참이 됨 — keep 정책만 허용으로 좁힘 |
| 119 | 05-chunk-set.md | contracts | 리뷰어 제안 '규칙 3에서 item_kind ∈ {table, figure, page_image} 구간 제외' 중 figure·page_image는 text가 캡션/alt_text이면 display_text 부분 문자열이므로 텍스트 ref로 두고 table_ref 보유 구간만 재직렬화 ref로 면제; 빈 text 리프는 금지(C-19)하고 그림 text 원천 순서는 04-pipelines/10 위임(이슈 11) |
| 120 | 05-chunk-set.md | contracts | 문서 version을 0.1.0→0.2.0으로 올렸으나 schema_version은 1.0.0 유지(게시 전 초판에 흡수) — 버전 정책이 다르면 조정 필요 |
| 121 | 05-chunk-set.md | contracts | 문서 길이 1,040행(브리프 §9.11 250~900행 초과; 계약 문서는 스키마 전문·Pydantic·예시 2개 포함이라 불가피) |
| 122 | 05-chunk-set.md | contracts | AnalyzerId는 여전히 이 계약 $defs 로컬 정의(이슈 6; common-types 등재는 00 소유) |
| 123 | 05-chunk-set.md | contracts | level 2(RAPTOR) 표현 불가 사실은 기록했으나 해소는 ADR-0015 후속(이슈 2) |
| 124 | 05-chunk-set.md | contracts | Pydantic 검증은 rag_platform.* 스텁으로 수행(실제 패키지 부재); 계보 필요 검증(규칙 3·4 텍스트 대조, C-11 heading_tree 대조, C-12 격자 범위)은 적합성 키트 몫으로 명시 |
| 125 | 05-ci-cd.md | finish | 리뷰 minor 1(C4)에서 '계약·통합도 두 인터프리터로 실행' 대안은 채택하지 않음 — 04 §19 표가 L1 단위만 매트릭스로 명시하고 §3.2·§4.5·§11.1이 모두 unit만 매트릭스이므로 원칙 문장을 표에 맞췄다. |
| 126 | 05-ci-cd.md | finish | release.yaml 스케치의 push(release/**) 이벤트 처리: 버전이 없는 후보 실행은 게이트만 돌리고 tag 이하를 건너뛰도록 했으나, staging-rehearsal에 넘기는 후보 식별자(`inputs.version \|\| github.sha`)와 promote.yaml의 `candidate: true` 입력 의미는 promote.yaml 확정 시 함께 정해야 함(이 문서 제안). |
| 127 | 05-ci-cd.md | finish | supply-chain 스케치의 trivy 플래그(`--ignorefile .trivyignore.yaml`, `--scanners vuln,secret,misconfig`, `--ignore-unfixed`)와 09/05 §6의 세부 정책 대응은 도구 버전 확인 필요(as of 2026-09) 상태 그대로. |
| 128 | 05-mcp-server.md | finish | 리뷰 항목 중 미반영은 없음(3건 모두 반영). |
| 129 | 05-mcp-server.md | finish | FR-MCP-03 충돌은 이 문서가 고칠 수 없어 미해결 이슈 16으로 기능 요구사항 문서 patch 제안만 남김(01-functional-requirements.md FR-MCP-03 행·미해결 이슈, 01-system-overview.md 미해결 이슈 7 갱신 필요). |
| 130 | 05-mcp-server.md | finish | SDK v2 4 MiB 초과 시 오류 표현(HTTP 413 vs JSON-RPC 파싱 오류)은 SDK 동작 확인 필요(as of 2026-09)로 표기. |
| 131 | 05-parser-pdf.md | finish | 리뷰 minor 3의 대안(해당 구간을 `empty`로 명시)은 채택하지 않고 `scanned`로 귀결시켰다. 이유: 작은 이미지 안에 글자가 있을 수 있어 OCR을 거치는 편이 정보 손실이 없고, 이미지가 실제로 비면 전면 OCR 결과가 비어 `page_break`만 남아 `empty`와 동일 결과가 된다(초안 규칙, 골든셋으로 조정). |
| 132 | 05-parser-pdf.md | finish | `decide_route`의 `tier` 인자는 이전 판과 마찬가지로 코드 안에서 쓰이지 않는다(등급별 허용 구성 검증은 입구 422로 처리한다고 적었음). 코드 예시 수준의 잔여 정리 항목. |
| 133 | 05-parser-pdf.md | pipelines-pass1 | ParsedDocument.fields[] 설명이 HWPX 한정 → PDF AcroForm 포함으로 바이블 §5.4·03 FormFieldEntry 문구 확장(patch) |
| 134 | 05-parser-pdf.md | pipelines-pass1 | 전용 경고 코드 부재(OCR 엔진 폴백, 저신뢰 OCR 페이지, ocr_failed/skipped 페이지) → parse.ocr_engine_fallback·parse.low_ocr_confidence·parse.page_ocr_failed·parse.page_skipped 카탈로그 추가 ADR; 그때까지 parse.sidecar_unavailable을 경고 코드로 재사용 |
| 135 | 05-parser-pdf.md | pipelines-pass1 | 빈 문서(전 페이지 empty 또는 OCR 텍스트 0)를 quality=full·page_break만인 결과로 둘지 parse.conversion_failed로 볼지(13 §5.1 C4 미해결 이슈 9와 합의) |
| 136 | 05-parser-pdf.md | pipelines-pass1 | page_route에서 두 파서가 함께 산출할 때 parser_chain·producer.plugin_id·parser_fingerprint.parser_id 의미(03 P-1 '마지막 원소 = 산출 파서'와 정합) → 조립 파서 규약 또는 parser_chain 항목 role 확장 |
| 137 | 05-parser-pdf.md | pipelines-pass1 | outline(북마크) 보존 계약 필드 부재 → ParsedDocument.metadata.outline(N) 추가 제안 |
| 138 | 05-parser-pdf.md | pipelines-pass1 | 표 셀 단위 OCR 신뢰도 필드 부재 → TableCell.confidence(N) 추가 제안 |
| 139 | 05-parser-pdf.md | pipelines-pass1 | 3단 이상 컬럼·표 안 다단·회전 혼합 페이지의 읽기 순서는 v1 범위 밖(단일/2단만) |
| 140 | 05-parser-pdf.md | pipelines-pass1 | 소유자 비밀번호 '복사 금지' 권한 PDF의 텍스트 추출 정책(법무 확인; respect_pdf_permissions 테넌트 정책 키 제안) |
| 141 | 05-parser-pdf.md | pipelines-pass1 | 수천 페이지 문서의 블록 200,000 한계와 PDF 첨부 분할 수집 → SplitHint pdf_page_ranges·pdf_attachments 추가 또는 자식 액티비티 팬아웃 |
| 142 | 05-parser-pdf.md | pipelines-pass1 | 태그 PDF 구조 트리(/StructTreeRoot)를 heading·읽기 순서·/Alt 신호로 쓸지(pypdfium2 API 확인 후 pdf.use_struct_tree 옵션) |
| 143 | 05-parser-pdf.md | pipelines-pass1 | GPU·ONNX 추론 미세 비결정성으로 동일 지문에서 OCR 텍스트가 달라질 수 있음 → 적합성 키트 idempotency에 OCR 경로 완화 모드 제안(ADR-0032 재검토) |
| 144 | 05-parser-pdf.md | pipelines-pass1 | 외부 API 확인 필요(as of 2026-09): Docling convert(page_range)·document_timeout·RapidOcrOptions 모델 경로 필드·OcrOptions.mode·bitmap_area_threshold·ProvenanceItem.coord_origin·DocItemLabel 값(CHART, HANDWRITTEN_TEXT), pypdfium2 get_toc/폼/이미지 추출 API, pdftext dictionary_output, /Rotate 페이지 좌표 프레임 |
| 145 | 05-parser-pdf.md | pipelines-pass1 | pdf_vlm_gpu 1순위(PaddleOCR-VL vs MonkeyOCRv2-B-Parsing)와 VLM 출력의 ParsedDocument 매핑은 골든셋 비교 후 별도 절 추가 |
| 146 | 05-parser-pdf.md | pipelines-pass1 | 04-pipelines/03(파싱 라우터)·09·10·11, 08-evaluation/03·05가 아직 없어 문서 맵 경로로만 링크(동시 작성 중) |
| 147 | 05-plugin-architecture.md | architecture | 모든 리뷰 항목(major 2, minor 3)을 반영했다. 미반영 항목 없음. |
| 148 | 05-plugin-architecture.md | architecture | index_backend 처리: 리뷰 fix는 포트 4개 한정만 요구했으나 02 §2.4 표는 index_backend를 Stage[EmbeddedChunkSet, IndexCommit] 행으로 적으면서 실제 진입점은 IndexBackend 포트 메서드다. 두 표현을 그대로 병기하고(§3.1 표 '형태' 열) run()의 의미 합의를 미해결 이슈 11(a)에 등재했다 — 02 §2.4·04-pipelines/13 확정 필요. |
| 149 | 05-plugin-architecture.md | architecture | Evaluator 입력 전달: Stage 형태로 바꾸면서 기존 `evaluate(run, packs: AsyncIterator[ContextPack], ctx)`의 packs 스트리밍 인자가 사라졌다. 골든셋·ContextPack 집합을 ctx.lineage로 받는 requires_lineage 확장은 바이블 §4.1('index만 사용')과 어긋나므로 새 미해결 이슈 19로 등재했다(08-evaluation/02·03-contracts/16 합의 필요). |
| 150 | 05-security-and-compliance.md | finish | None of the three review items were rejected; all applied. |
| 151 | 05-security-and-compliance.md | finish | Issue 17 (new): 422 rejection of body tenant_id/as_of has no matching error code in bible §5.7 (contract.violation is 400/500) — delegated to ../03-contracts/13-error-model.md; SB-02 checks status code only until resolved. |
| 152 | 05-security-and-compliance.md | finish | platform_admin API-key issuance scope note added in §3.5 is an operational narrowing (not a matrix change) and was not added to §3.6 decision block since it does not alter the RBAC matrix. |
| 153 | 06-enriched-chunk-set.md | contracts | 리뷰 1건(major)의 2안(같은 섹션의 2..N번째 청크를 cache_hit=true·llm_cache_hits += 1로 계수)은 채택하지 않았다 — 섹션 단위 1회 생성 후 배정하는 구현 루프와 맞지 않고 적중 수를 부풀리기 때문. 대신 1안(고유 쌍 계수)을 택했으며 근거를 미해결 이슈 7에 남겼다. 바이블 §5.4 Enrichment.summary 행·stats.llm_cache_hits 계수 단위 명시는 바이블 소유자 patch로 남아 있다. |
| 154 | 06-enriched-chunk-set.md | contracts | 예시 2개는 node JSON.parse와 변경 조건(E-7/E-8/E-10, then 분기 엔티티 조항)에 대한 수기 스크립트 검사만 통과했다 — 이 환경에 ajv 등 JSON Schema 검증기가 없어 common-types $ref 해석을 포함한 전체 스키마 검증은 CI 게이트(00 §10.3)에서 확인해야 한다. |
| 155 | 06-orchestration-and-workflows.md | architecture | 리뷰 minor 7(깨진 링크) 중 ADR-0037은 파일 `06-adr/0037-artifact-cache-scope-and-stage-key-composition.md`가 이미 존재해 변경하지 않았다; 나머지 미게시 문서 링크는 삭제 대신 '동시 작성 중' 표기로 두었다(관행 유지, 링크 검사 CI는 문서 세트 게시 시). |
| 156 | 06-orchestration-and-workflows.md | architecture | `ledger.advance_pointers`가 alias 교체 뒤에 실행되므로 교체~전진 사이 짧은 창에 alias는 green을, `documents.current_*`는 blue를 가리킨다. 03-data-flow §9.2 (3)의 '조회 API는 CollectionSpec.profile_hash 일치 최신 committed 커밋을 서빙 중으로 표시' 규칙으로 흡수했으나 순서(전진 먼저 vs 교체 먼저)의 최종 선택은 04-pipelines/19 실측 후 확정. |
| 157 | 06-parser-doc-and-docx.md | finish | 리뷰 항목 미반영 없음 — 3건 모두 반영(전부 minor). |
| 158 | 06-parser-doc-and-docx.md | finish | 브리프 전체·바이블 헤더 전수 재독은 사용자 지시('ADR 제외, 리뷰 빠르게')에 따라 생략하고 리뷰 항목에 해당하는 바이블 §5.3·03 계약 §7·기술 지형 03·선정 매트릭스 관련 행만 직접 확인했다. |
| 159 | 06-parser-doc-and-docx.md | pipelines-pass1 | ParsedDocument.artifacts.kind에 conversion_report·page_render 값 없음(현재 vendor_json으로 표기, 저장 경로는 derived/conversion_report/) — 열거 minor 제안·경로/kind 일치 규칙 |
| 160 | 06-parser-doc-and-docx.md | pipelines-pass1 | fields[](계약 설명 'HWPX 필드')를 OOXML 양식 필드·콘텐츠 컨트롤로 확장 사용 — 03 §2.5 설명 확장 patch |
| 161 | 06-parser-doc-and-docx.md | pipelines-pass1 | page_map(추정 페이지) 파생물의 API·MCP 노출 방식(05-api/04·05) — Provenance·IndexRecord 전파 금지는 확정 |
| 162 | 06-parser-doc-and-docx.md | pipelines-pass1 | 목록 사이 들여쓰기 본문 문단의 컨테이너 부재(형제로 둠) — 청커 list_group 흡수 규칙 확인 또는 BlockContainer.list_body 제안 |
| 163 | 06-parser-doc-and-docx.md | pipelines-pass1 | 차트 데이터 표 블록화·OLE 임베딩 원 개체(Excel·HWP) 파싱·EMF/WMF 래스터화 깊이 — M2 골든셋 후 |
| 164 | 06-parser-doc-and-docx.md | pipelines-pass1 | DOC FIB fEncrypted·RTF \password·ODT manifest 암호화 근거가 02 계약 §4 encrypted 목록에 없음 — patch; FIB 오프셋·비트 스파이크 확인 |
| 165 | 06-parser-doc-and-docx.md | pipelines-pass1 | 확인 필요(as of 2026-09): Docling DOCX 옵션 클래스명·한국어 스타일명 매칭, docx2python 파일 객체 입력·footnote↔w:id 대응·ListItem.marker 한국어 numFmt, msoffcrypto 레거시 DOC(RC4/XOR) 지원, LibreOffice 프로파일 보안 설정 경로명, unoserver 3.x API |
| 166 | 06-parser-doc-and-docx.md | pipelines-pass1 | 04-pipelines/03 §1·§9의 후보 호출 run(source, ctx)에 in_process 멤버용 바이트 전달(payload, origin)과 maybe_reroute_then 입력 타입(ConvertedSource)이 미정 — 03 §9 의사코드 patch 후 정합 |
| 167 | 06-parser-doc-and-docx.md | pipelines-pass1 | 사이드카 자체 메트릭(rag_parse_lo_*)은 바이블 §6.5 정본에 없고 egress 0으로 수집 경로도 없음 — 워커 스팬 속성으로 대체; otel-collector 단일 egress 예외는 09-operations/03·08 이슈 12에서 결정 |
| 168 | 06-plugin-development-guide.md | finish | 리뷰 항목 중 반영하지 않은 것 없음(3건 모두 minor이며 합리적이어서 반영). |
| 169 | 06-plugin-development-guide.md | finish | §5.4의 `self._physical`(등록된 물리 이름·alias 허용 목록)과 `BackendHit.identity_fields()`는 스케치용 보조 구조로 05 §3.8 `IndexBackend` 포트 정의에는 없는 구현 세부이며, 정본 인터페이스에 영향을 주지 않는다. |
| 170 | 06-plugin-development-guide.md | finish | `schemas/conformance-report.schema.json` 파일은 여전히 미생성(문서 미해결 이슈 5: 03-contracts/14·00 합의 후 생성). |
| 171 | 06-runbooks.md | finish | 리뷰 항목 3의 대안('주 FMEA' 열 제목 변경)은 채택하지 않고 표를 헤더 목록에 맞추는 쪽을 택함 — 표·헤더가 완전 일치하므로 추가 설명 문장은 불필요 |
| 172 | 06-runbooks.md | finish | 설계 브리프·바이블 전체 정독은 사용자 지시('리뷰는 빠르게')에 따라 생략하고, 리뷰 검증에 필요한 바이블 §5.7 이벤트 카탈로그(line 1111)·§6.5 메트릭 정본(line 1207)·§13 usage_ledger(line 1798)·JobState(line 1089)·Renderer(line 1086)와 관측성 §4.2·§8, 03-contracts/12·16 해당 행만 직접 확인함 |
| 173 | 07-backup-and-disaster-recovery.md | finish | 리뷰 항목 중 미반영 항목 없음(4건 전부 반영). |
| 174 | 07-contributing.md | finish | 반영하지 않은 리뷰 항목 없음(5건 전부 반영). |
| 175 | 07-contributing.md | finish | DCO 검사 앱은 CI/CD 미해결 이슈 7에서도 확인 필요 상태라 §5.2·§6의 '확인 필요(as of 2026-09)' 표기를 유지(미해결 이슈 2에 대체 경로 `pr / meta` 명시). |
| 176 | 07-contributing.md | finish | status를 active로 바꿨으나 §8.2 규정상 `review → active`는 NFR M7 체크리스트 통과 후 owner가 하는 것이므로 마무리 단계의 일괄 처리 판단에 따름(지시대로 설정). |
| 177 | 07-embedded-chunk-set-and-index-record.md | contracts | 리뷰어 fix 중 택1: acl_embargo_until/acl_expires_at는 Y(nullable) 승격이 아니라 '명시적 null = to_payload 백엔드 전용, 계약 인스턴스는 00 §8.1 4행(N \| null)' 방식으로 정합했다(바이블 §5.4 N 유지, 필수화(major) 회피). |
| 178 | 07-embedded-chunk-set-and-index-record.md | contracts | Pydantic 블록은 이 머신에 Python이 없어 AST 파싱 검증을 못 했고 수동 검토만 했다(변경은 `_invariants` 검증기에 3줄 추가). |
| 179 | 07-embedded-chunk-set-and-index-record.md | contracts | 미해결 이슈 4 확장: `EmbeddingSpaceIds`가 embedded-chunk-set·index-record(+ IndexCommit) 세 계약에 사본으로 존재하므로 00 문서(common-types 소유)가 `$defs/EmbeddingSpaceIds`·`$defs/TableRef` 승격(minor)을 처리해야 사본 드리프트가 해소된다. |
| 180 | 07-multi-tenancy-and-security-architecture.md | architecture | ADR-0037·0038 대조 결과 불일치가 없어 새 미해결 이슈는 등록하지 않았다. 다만 ADR-0038 자체가 남긴 개방 항목(프로파일 AND 테넌트 합성 규칙·allowed_hosts 일치 방식은 03-contracts/15, s3/gs/az 클라이언트 엔드포인트 취급은 04-pipelines/02)은 이 문서 범위 밖이라 옮겨 적지 않았다. |
| 181 | 07-parser-html.md | finish | 리뷰어가 제안한 `parse.conversion_failed` 이외 경고 코드(parse.extractor_fallback 등, 이 문서 미해결 이슈 3)는 여전히 카탈로그 부재 상태로 ADR 제안에 머문다. |
| 182 | 07-parser-html.md | pipelines-pass1 | §5.3·§12 임계값(본문 200자, 비율 0.10, 표 비율 0.60, Jaccard 0.9, 상한값)과 §13 성능 목표는 초안 — 한국어 HTML 골든셋 200+ 페이지로 확정 |
| 183 | 07-parser-html.md | pipelines-pass1 | 사이트 규칙 텍스트 매칭 선택자(th:-soup-contains)는 lxml cssselect에 없음 — MetaSelector{selector, text_equals} 구조로 개정 필요 |
| 184 | 07-parser-html.md | pipelines-pass1 | Docling HTML 백엔드가 요소 id를 DoclingDocument에 보존하는지 미확인 — 보존되면 Docling을 전체 순회기로 승격 검토 |
| 185 | 07-parser-html.md | pipelines-pass1 | 날짜만 아는 발행일을 web.published_at에 T00:00:00.000Z로 채우면 정밀도 손실 — WebMetadata.published_at_precision 또는 published_date 제안 |
| 186 | 07-parser-html.md | pipelines-pass1 | blockquote·details·정의 목록 의미가 BlockType에 없어 paragraph/list_item으로 흡수 — 필요 시 BlockType quote 추가 ADR |
| 187 | 07-parser-html.md | pipelines-pass1 | 첨부·이미지 링크 성격이 Link에 없음 — Link.rel(N) 제안, 채택 전 추출 보고 attachments[] |
| 188 | 07-parser-html.md | pipelines-pass1 | figure.artifact 필수여서 원격 이미지를 figure로 표현 불가 — figure.source_url(N) 추가 및 artifact nullable 검토(major 취급) |
| 189 | 07-parser-html.md | pipelines-pass1 | parser_fingerprint.parser_version {package}=={version} 규약이 다중 라이브러리를 표현 못함 — ';' 연결 표기를 03 §2.2에 명시 |
| 190 | 07-parser-html.md | pipelines-pass1 | Trafilatura 2.2.0 키워드 인자 집합·cell span 보존·dl/math/figcaption 처리, readability-lxml 0.9 bytes 입력은 소스 확인 필요(as of 2026-09) |
| 191 | 07-parser-html.md | pipelines-pass1 | 렌더링된 HTML 주입용 fetcher 플러그인 계약(POST /v1/convert 재사용 여부)은 02-fetching 문서 소유 |
| 192 | 07-parser-html.md | pipelines-pass1 | 이 문서의 element_path 문법과 03 §3.1 HTML 행·바이블 §5.3 'HTML XPath' 문구 정밀화(patch) |
| 193 | 07-parser-html.md | pipelines-pass1 | 폴백 사다리 산출을 degraded로 보는 규칙은 라우터 문서(04-pipelines/03)와 합의 필요 |
| 194 | 07-parser-html.md | pipelines-pass1 | depends_on에 지정된 04-pipelines/03-parsing-router-and-format-detection.md는 작성 시점에 없어 바이블 §4.2·§7.3을 정본으로 삼았고 링크만 걸었음(현재 다른 에이전트가 생성 중) |
| 195 | 08-deployment-architecture.md | architecture | minor(models.lock): RapidOCR ONNX 변환본의 저장소 id를 예시에서 `RapidAI/RapidOCR`로 두었으나 07-tech-landscape/02는 RapidAI GitHub·모델 목록 URL만 제공하므로 id·revision은 본문에 '확인 필요(as of 2026-09)'로 표기했고, 형식 확정(포맷별 항목 분리 vs consumers[] 객체 배열)은 미해결 이슈 5로 10-development/05에 위임했다. |
| 196 | 08-index-commit.md | contracts | [미반영·타 문서] 12 예시 3(`ingest.document.indexed`, "08 예시 1의 문서")의 `doc_version`(3e5f7092…)·`commit_hash`(e4d3c2b1…)·`record_count`(218)가 08 예시 1(cf266a7a…, 4ac76a64…, 2)과 다르다 — 12 문서 편집자가 08 값으로 정렬해야 함(08은 commit_id·commit_hash·record_count를 바꾸지 않았다). |
| 197 | 08-index-commit.md | contracts | [플레이스홀더 유지] 예시 1·3의 `artifact_refs.embedded`(stage_key 117b5acd…)는 07 예시 1이 자기 stage_key를 싸지 않으므로 독립 플레이스홀더로 남겼다(형식 규약 준수, 스키마 통과). |
| 198 | 08-index-commit.md | contracts | [정합 필요] 예시 1·3의 OpenSearch `physical_name` rag_lex_e6df9c850d31은 `lexical_profile_hash` 플레이스홀더에서 유도된 값으로 15 문서 `CollectionSpec` 예시와 대조 필요(15 게시본 확인 전). |
| 199 | 08-index-commit.md | contracts | [검증 범위] Pydantic 블록은 정적 검토만 했다(저장소에 Python 런타임 없음). 스키마·예시는 tools/validate-contracts.mjs(2020-12 서브셋 검증기)로 통과·거부를 확인했으며, ajv 등 완전한 검증기로의 재확인은 CI에 맡긴다. |
| 200 | 08-index-commit.md | contracts | [모드 B 미결] 02-architecture/06 §2.5 모드 B(롤링 세대 플립)와 02-architecture/03 §9.1(불채택) 사이의 상충은 이 계약이 결정하지 않는다(§9 말미에 양쪽 미해결 번호만 인용; 어느 쪽이든 필드 의미 불변). |
| 201 | 08-parser-txt-md-and-others.md | finish | 리뷰 3건 모두 반영했으며 미반영 항목 없음. |
| 202 | 08-parser-txt-md-and-others.md | pipelines-pass1 | 리뷰 4건 모두 반영함 — 미반영 항목 없음 |
| 203 | 08-parser-txt-md-and-others.md | pipelines-pass1 | 부속 참고: §7.3 flatten의 depth ≥ 6 객체 heading은 기존 클램프(min(depth+offset,6))로 같은 level 6 형제가 되어 트리가 평탄화되는데, 이는 03 §4.1 위반은 아니고(가장 가까운 level<6 heading 아래로 놓임) 리뷰 범위도 아니라 그대로 두었다; max_depth 기본 8과 함께 골든 코퍼스에서 재검토 대상 |
| 204 | 08-parser-txt-md-and-others.md | pipelines-pass1 | XML 하위 분할이 txt/md 중 무엇을 쓰는지(json.text_format 공유 여부)는 §8 기존 문구("TXT 하위 분할"·"TXT/MD 하위 분할")를 유지했고 별도 xml.text_format 옵션은 정의하지 않았다 |
| 205 | 08-release-process.md | finish | 리뷰 4건 모두 반영했으며 미반영 항목 없음. |
| 206 | 08-release-process.md | finish | 미해결 이슈 15가 인용하는 04·05·06 문서는 아직 status: review이므로 절 번호 재검사는 해당 문서 active 전환 후 필요. |
| 207 | 08-upgrade-and-migration.md | finish | 리뷰 2의 대안 '검사 뒤 절 번호를 채우고 항목을 삭제' 중 '항목 삭제'는 채택하지 않음 — 09-operations/02·03·05·06 인용은 여전히 절 번호가 없고, 인용한 세 문서(릴리스 프로세스·CI/CD·관리 API)가 review 상태라 재검사 항목으로 미해결 17을 유지. |
| 208 | 09-failure-modes-and-resilience.md | architecture | frontmatter version은 0.1.0 유지(지시가 status·last_updated만 지정; 08 문서는 0.1.1이나 이 문서의 버전 상향은 소유자 판단에 맡김). |
| 209 | 09-failure-modes-and-resilience.md | architecture | 인그레스 503 본문의 application/problem+json 여부는 13 문서 §7.1 '확인 필요' 항목을 그대로 인용했으며 이 문서가 확정하지 않음(09-operations/01 소유). |
| 210 | 09-normalization-and-cleaning.md | finish | 반영하지 않은 리뷰 항목 없음(4건 모두 반영). |
| 211 | 09-normalization-and-cleaning.md | finish | PII tokenize 키 공급자의 설정 키 경로는 바이블 §7.3 미등재로 미확정 유지(미해결 이슈 13, 02-architecture/05 미해결 이슈 1과 합의 대상). |
| 212 | 09-normalization-and-cleaning.md | finish | 참조된 09-operations/02·10-development/04·06·05-api/04는 존재하나 status: review 상태 — 링크만 유지, 내용 정합은 마무리 단계 일괄 확인 대상. |
| 213 | 09-normalization-and-cleaning.md | pipelines-pass1 | [major, 선택지 중 하나 채택] heading I-13: 리뷰어 선택지 (b) path 절단 + (a) I-13 완화 개정 제안을 병행. `reinfer` 기본은 `auto` 유지(절단이 계약을 만족시키므로 off로 바꾸지 않음). 절단은 정보 손실이며 채택 후 제거. |
| 214 | 09-normalization-and-cleaning.md | pipelines-pass1 | [tech minor] `TableStep` 주석의 model_validator: `NormalizeConfig` 수준으로 이동해 실제 코드 추가. `spacing_corrector` 플러그인 존재·kss fast 변형 검증은 레지스트리 정보가 필요해 Pydantic 모델이 아닌 `rag profile validate`에 남김(리뷰어 제안 '같은 자리에서'는 불가). |
| 215 | 09-normalization-and-cleaning.md | pipelines-pass1 | [검증 한계] 이 환경에 Python 인터프리터가 없어 §5.2 Pydantic 블록은 AST 파싱 대신 괄호 균형·임포트·데코레이터 존재만 확인. YAML도 파서 없이 괄호 균형만 확인. |
| 216 | 10-candidate-set-and-ranked-set.md | contracts | 분량 축소(1620행 vs 목표 ≤1000, anchor·tech 공통 minor) 미반영: 예시 1(RRF 계산표)·2·3이 6후보 단일 시나리오로 상호 검증되어 후보 수를 줄이면 fused_score·fused_rank·n_in/candidates_in 등을 전부 재계산해야 하고, 저장소의 다른 계약 문서(09 1185행, 11 1682행, 16 1610행)와 같은 수준이라 국소 수정 범위를 넘는다고 판단. 2차에서 Pydantic 블록 별도 파일 분리 여부와 함께 판단 필요 |
| 217 | 10-candidate-set-and-ranked-set.md | contracts | Pydantic 블록은 Python 미설치로 ast 검증을 못 했고 눈으로만 확인함(JSON 블록·스키마 파일은 node로 검증) |
| 218 | 10-candidate-set-and-ranked-set.md | contracts | TREC 문서 접기 집계(max) 및 `fused` 단계 export 범위(hydrate.top_n)는 초안이며 16 §4.1·08-evaluation/02(미게시)에서 확정 필요(이슈 8) |
| 219 | 10-chunking-strategies.md | finish | 반영하지 않은 리뷰 항목 없음(minor 1건 전부 반영) |
| 220 | 10-chunking-strategies.md | pipelines-pass1 | anchor minor(문서 맵 링크 7건): 미존재 문서 링크를 삭제하지 않고 유지 — 공통 규약이 '문서 맵 경로만 링크'를 허용하고 다른 04-pipelines 문서도 같은 관행이므로, 참조 절에 '작성 예정 문서' 표기만 추가 |
| 221 | 10-chunking-strategies.md | pipelines-pass1 | tech major(그림) 세부: 리뷰어의 'Block.figure.alt_text 직접 읽기(original_char_* = 0,0)'는 채택하지 않음 — 03 §2가 그림 Block.text를 alt_text 또는 ""로 정하므로 그림 블록 display_text가 곧 alt_text 뷰이고, display_text 밖 문자열을 길이>0 텍스트 ref로 두면 05 §5 규칙 3(부분 문자열)을 깨뜨림. 대신 display_text 경로 + 길이 0 ref 규칙으로 05 규칙 6·이슈 11 의도를 충족 |
| 222 | 10-chunking-strategies.md | pipelines-pass1 | anchor major(폴백 라우팅) 권장안(셸이 flat_text를 별도 Stage로 실행, stage_key fingerprint=flat_text 지문)은 채택하지 않음 — stage_key는 입력 로드 전에 계산되어(01 §5.1) 라우팅 결과로 지문을 바꿀 수 없음. tech 옵션 (B)(평면 키 편입)를 채택했고, 01 §2.3 예약 키 fallback·바이블 §7.3 중첩 표기와의 정합은 미해결 이슈 14(로더 투영 규칙 patch)로 남김; tech 옵션 (A) chunker.router 합성 스테이지는 바이블 §7.3에 없는 새 플랫폼 스테이지라 미채택 |
| 223 | 10-chunking-strategies.md | pipelines-pass1 | anchor 리뷰의 '`chunk.fallback_routed` 경고 추가' 방향(기존 미해결 이슈 9)은 철회 — 경고가 있으면 C-18로 quality=degraded가 되어 폴백 세트가 모두 degraded가 되므로 chunker_id를 기록으로 삼음 |
| 224 | 10-chunking-strategies.md | pipelines-pass1 | 상위 문서 patch 요청(이 문서 밖, 미해결 이슈 1·2·13·14로 기록): 바이블 §4.1·§4.2 chunk 행 requires_lineage, 03-contracts/15 프로파일 스키마 선택 키 및 fallback 평면 투영, 05 §3.1 producer 문구(producer.plugin_id ≠ chunker_id 허용), 파서 문서(04-pipelines/04·05)의 제N조 heading_inferred 규칙 |
| 225 | 11-context-pack.md | contracts | 빈 segments(level 2 파생 항목): 리뷰의 두 안 중 합성 block_id 발명을 피해 `segment_range=[0, 0]` 완화안을 채택했다(§3.4·R-1). 합성 세그먼트가 필요하면 05/06 문서의 level 2 block_id 규약 확정 후 재검토. |
| 226 | 11-context-pack.md | contracts | `exact_*`에 safety_margin을 적용할지는 바이블 §9.1에 근거가 없어 미정으로 두고(미해결 이슈 14) 근사 경로에만 적용했다 — 리뷰가 허용한 선택지. |
| 227 | 11-context-pack.md | contracts | tools/validate-contracts.mjs 펜스 정규식을 줄 시작 앵커로 강화하라는 제안은 이 문서 범위 밖(도구 파일 미수정); 대신 문서에서 인라인 삼중 백틱을 제거해 우회했다. |
| 228 | 11-context-pack.md | contracts | Pydantic 블록은 Python 런타임이 없어 기계 검증 없이 수동 검토만 했다(한 줄 클래스·`;` 구문 포함). |
| 229 | 11-context-pack.md | contracts | 검증기가 여전히 보고하는 오류 3건(00 §예시 1 ParsedDocument, 14 schema-diff-report 스키마 파일 부재·ParsedDocument 예시)은 다른 문서 소유라 건드리지 않았다. |
| 230 | 11-enrichment.md | finish | §12.4 예시의 호출당 입력 토큰(71,200/150 ≈ 475)은 문서 전체를 접두어로 넣는 모드 B에서 낮은 편이나(vLLM prompt_tokens는 접두어 캐시 적중분도 포함), 리뷰 범위 밖이고 예시 수치의 §12.2 식 일관성은 확보되어 수치 자체는 유지함 — 실측 후 미해결 이슈 13 절차로 교체 가능 |
| 231 | 11-enrichment.md | finish | 부속 스키마 파일은 이 문서 소유가 아니므로 미수정; BudgetUsed.charged_tokens(N) 추가 제안(미해결 이슈 2)은 06 문서 소유자가 반영해야 함 |
| 232 | 11-enrichment.md | pipelines-pass1 | 가상 질문 plugin_id(enricher.hypothetical_questions)·프로파일 키가 바이블 §7.3에 없음 |
| 233 | 11-enrichment.md | pipelines-pass1 | Message Batches 백필 시 30m start_to_close·캐시 병용 조건 확인 필요(as of 2026-09) |
| 234 | 11-enrichment.md | pipelines-pass1 | KeyBERT·YAKE 대안 키워드 추출기: 07-tech-landscape 연구 없음, KeywordSource 열거값 없음 |
| 235 | 11-enrichment.md | pipelines-pass1 | Chunk.lang 오판 대비 enricher.lang_check(fastText lid 등) 라이선스·정확도 확인 필요 |
| 236 | 11-enrichment.md | pipelines-pass1 | RAPTOR level=2 요약 노드가 enrichments 키 집합 규칙(06 E-4)과 충돌 — 18 문서에서 ChunkSet 재발급 방식 확정 |
| 237 | 11-enrichment.md | pipelines-pass1 | risk_flags 어휘 열거(RiskFlag) 고정과 pii_residual 대응 Warning 코드(enrich.pii_residual) 부재 |
| 238 | 11-enrichment.md | pipelines-pass1 | Valkey llmtb:{tenant} 키·테넌트 정책 llm_tokens_per_minute·캐시 적중률/partial 비율 메트릭이 바이블 §13.4·§13.1·§6.5 정본에 없음 |
| 239 | 11-enrichment.md | pipelines-pass1 | korean-gov 외부 API 테넌트 옵트인 강제를 프로파일 로딩 검증 규칙(§7.4)으로 두는 문법 부재 |
| 240 | 11-enrichment.md | pipelines-pass1 | GLiNER2 한국어 F1 미측정(KLUE-NER), 라벨 10종·임계 0.5·상한 128, 키워드 64·불용어, 병렬 8, 하트비트 50청크, 비용 표·지연 목표 등 모든 수치는 초안 목표 |
| 241 | 11-enrichment.md | pipelines-pass1 | max_tokens:0 캐시 예열 요청·Batch API 할인·단가는 확인 필요(as of 2026-09); 09-operations/02 단가표가 정본 |
| 242 | 12-embedding.md | pipelines-pass1 | Mermaid 렌더 미검증: 로컬에 mermaid/mmdc가 없어(전역 npm 모듈 없음) 렉서 규칙 추론으로만 확정했다. 간선 라벨에서 중괄호·괄호를 모두 제거하고 노드 라벨은 전부 큰따옴표 인용으로 두었으므로 안전한 편이나 렌더 재확인 권장. |
| 243 | 12-embedding.md | pipelines-pass1 | 부속 스키마 파일 미수정: 이 문서는 schemas/*.schema.json을 소유하지 않는다(embedded-chunk-set.schema.json은 03-contracts/07 소유). 문서 내 JSON 예시 5개만 node로 검증했다. |
| 244 | 12-embedding.md | pipelines-pass1 | 리뷰가 지적하지 않은 잔여 사항: §14 표의 '08 §7.3은 보수적으로 150 청크/s 가정'과 §14 근거 문구의 08 §7.3 인용은 컴퓨트 사이징 절이므로 그대로 두었다(정합 여부는 08 문서 재확인 권장). |
| 245 | 12-jobs-events-and-status.md | contracts | query_hash(anchor minor #11): §6.4·스키마 description은 07 §8.2 정의(라벨 없음)를 인용했고 바이블 §6.2 H() 라벨 규약과의 택1은 미해결 이슈 8에 남김 |
| 246 | 12-jobs-events-and-status.md | contracts | Pydantic 코드 블록은 이 환경에 Python이 없어 ast 파싱을 못 했고 육안 검토만 수행(변경 부분: _invariants I-3/I-4 검사, _transition progress 검사, _STAGES 튜플화, verify_webhook 재작성) |
| 247 | 12-jobs-events-and-status.md | contracts | 종결 event_id 최대 규약(I-19)은 02-architecture/06 §3.2 _event_ids 발급 코드가 단조 ULID·state_changed 마지막 순서를 따라야 성립하며, 그 정합은 미해결 이슈 14(b)로 06 문서에 위임 |
| 248 | 13-error-model.md | contracts | normalize·chunk의 Temporal 타임아웃은 의미가 맞는 기존 코드가 없어 매핑 없음(미정)으로 두었고 그동안 JobStatus.last_error가 null인 failed가 가능함을 I12 예외로 명시했다 — {stage}.timeout 조기 채택 필요(이슈 3). 12 문서(JobStatus 소유)에 반영 제안 상태. |
| 249 | 13-error-model.md | contracts | I12·I13은 각각 12·10 문서 소유 타입에 대한 불변식이라 '반영 제안'으로 출처 표기했으며, 두 문서가 아직 없어 링크는 문서 맵 경로만 걸었다. |
| 250 | 13-error-model.md | contracts | temporalio ApplicationError 시그니처(details 가변 위치 인자)는 07-tech-landscape/08에 직접 근거가 없어 '확인 필요(as of 2026-09)'로 표기했다. |
| 251 | 13-error-model.md | contracts | 예시 JSON은 ajv가 없어 자체 미니 검증기(type/required/additionalProperties/pattern/enum/min·max/$ref/dependentRequired/uri·date-time·json-pointer format)로 검증했다; 메타스키마 검증과 완전한 format 어설션은 CI(00 §10.3)에서 수행되어야 한다. |
| 252 | 13-error-model.md | contracts | frontmatter version은 지시에 없어 0.1.0 유지(status만 active로). |
| 253 | 13-indexing.md | pipelines-pass1 | [부속 파일 없음] 이 문서는 스키마 파일을 소유하지 않으며 docs/schemas 디렉터리도 저장소에 없어 schemas/*.schema.json 수정은 해당 없음. 문서 내 JSON 5블록만 node로 검증했다. |
| 254 | 14-query-understanding.md | pipelines-pass1 | Tech-major '§10 조회 시점' resolved as a variant of option (A): lookup only when the final effective_hash is computable without an LLM call (default/fast always; quality only on sq: cache hit, else skip lookup); storage always under the final hash so cache_keys.plan equals the lookup key (09 P-13). The reviewer's literal '사전 해시 키' was not used because it would make the stored plan's cache_keys.plan differ from the lookup key. |
| 255 | 14-query-understanding.md | pipelines-pass1 | 15-hybrid-search-and-fusion.md §2.1, §5.1, §6.2, §6.5 still describe the old HyDE model (original.channels=[sparse, lexical], fusion.weights.dense=2.0); this is outside the assigned file and is recorded in 미해결 이슈 1 for the 15 owner (quality run count stays 3 + 3×3 = 12). |
| 256 | 14-query-understanding.md | pipelines-pass1 | Full JSON Schema validation of the §14.6 example against schemas/query-plan.schema.json was not run (ajv not installed in this environment); instead node JSON.parse plus a scripted check of 09 invariants P-1/P-2/P-5/P-6/P-8/P-9/P-11/P-12, hex64/ULID formats and the 32KB limit was performed and passed. |
| 257 | 14-query-understanding.md | pipelines-pass1 | No schema file is owned by this document (query-plan.schema.json is owned by 03-contracts/09), so no schemas/*.schema.json were modified. |
| 258 | 14-query-understanding.md | pipelines-pass1 | Reviewer statement that 15 §2.1 line 94 computes 13 runs does not match the current 15 file (it says 2 + 3×3 + 1 = 12); both are the superseded model and are covered by 미해결 이슈 1. |
| 259 | 14-query-understanding.md | pipelines-pass1 | Bible §5.5 latency_budget_ms row cites a non-existent §8.6; this document keeps its interpretation (stage caps + ctx.remaining_ms()) and flags the bible text for a patch in 미해결 이슈 18. |
| 260 | 14-schema-versioning-and-compatibility.md | contracts | [tech minor §2.4 ADR-0032 대안] 리뷰어가 두 릴리스 규칙 근거로 ADR-0032(플러그인 SDK) 인용 대안을 제시했으나 범위 밖이라 채택하지 않고 신규 ADR 필요로 강등(미해결 이슈 2). |
| 261 | 14-schema-versioning-and-compatibility.md | contracts | Python 블록은 환경에 python이 없어 ast 파싱을 못했다(육안 검토만). JSON 5블록은 node로 파싱·구조 검증 완료. |
| 262 | 15-collection-profile-and-policy-contracts.md | contracts | [minor, 미반영] `allowed_hosts` 항목 pattern·`DateTime` 등 Annotated 타입의 common-types/00 게시는 00 소유라 제안(이슈 13)만 남기고 이 문서는 로더 검사·패턴 사본으로 대체. |
| 263 | 15-collection-profile-and-policy-contracts.md | contracts | [tech minor, 부분 반영] 예시 2 `revision` SHA: models.lock 정본 대조 불가(저장소에 models.lock 없음)라 값 확정 대신 '형식 예시, 확인 필요(as of 2026-09)' 문구 추가. |
| 264 | 15-collection-profile-and-policy-contracts.md | contracts | [신규] 테넌트 정책 등록(`PATCH /v1/tenants/{tenant_id}/policies`)에서 합성 공집합 거부 코드를 `profile.invalid`(422 초안)로 두었으나 13 §7.1에 전용 행이 없음 — 05-api/04·13 확정 필요(이슈 15). |
| 265 | 15-collection-profile-and-policy-contracts.md | contracts | [검증 한계] Python 런타임·ajv가 환경에 없어 Pydantic 블록은 구조 검사(괄호 균형·클래스 중복·전방 참조)만, 스키마 검증은 자체 최소 검증기(사용 키워드 부분집합)로 수행. |
| 266 | 15-hybrid-search-and-fusion.md | pipelines-pass1 | 02-architecture/04 §5.2는 Grep으로만 확인(본문 전체 미독)하여 depends_on에 넣지 않고 프로스 참조만 했다. |
| 267 | 16-eval-feedback-and-sidecar-contracts.md | contracts | 분량(1,621행)은 검토 기준 600~1100행을 초과하지만 브리프 §9.11(계약 문서는 스키마 전체 포함)에 따라 스키마 7개·Pydantic·예시 17개를 유지했다 — 압축(예시 병합·결정 요약 축약)은 하지 않음. |
| 268 | 16-eval-feedback-and-sidecar-contracts.md | contracts | `../08-evaluation/02·03·04·06`, `../05-api/04` 링크는 파일이 아직 없지만 공통 규약('링크만 문서 맵 경로로 건다')과 브리프 §9.6 괄호('문서 맵에 있는 경로만')에 따라 유지했다(다른 계약 문서 12개도 같은 경로를 링크 중). `04-pipelines/09`는 실제로 존재하므로 리뷰 지적은 오류. |
| 269 | 16-eval-feedback-and-sidecar-contracts.md | contracts | `EvalRun.index_commit_ids` 상한 2,000은 유지했다(64KB 도출). 12 `EvalRunCompletedData.index_commit_ids` maxItems 1,000과의 정렬은 이벤트 data에 앞 1,000개만 싣는 규칙 + 12에 `index_commits_hash`(N) 추가 제안으로 미해결 이슈 4에 기록 — 12와 합의 후 값 통일 필요. |
| 270 | 16-eval-feedback-and-sidecar-contracts.md | contracts | Mermaid 5개 블록은 렉서 규칙(`;`·`#` 부재)으로만 점검했고 실제 렌더링(mermaid-cli)은 npm 미가용으로 미실행. |
| 271 | 16-eval-feedback-and-sidecar-contracts.md | contracts | 예시↔스키마 검증은 ajv 미설치로 Node 자체 스크립트(required·additionalProperties·condition enum·derived URI·pii≠reject)로 구조 검증만 수행; $ref 해소를 포함한 완전 검증은 CI 골든 예시 회귀에 위임. |
| 272 | 16-eval-feedback-and-sidecar-contracts.md | contracts | PII 정책 원천(미해결 이슈 18)과 `name` 유일성(이슈 17), 파생물 `{kind}` 열거(이슈 19), 게이트 통과 조건 세 해석 규칙(이슈 20)은 초안 결정으로 남겨 바이블/12/15/02-architecture/04/08-evaluation/02와 공동 확정이 필요하다. |
| 273 | 16-reranking.md | pipelines-pass1 | 바이블 §4.3 `rerank` 행('`rerank.timeout`(300ms)·5xx → 폴백')과 03-contracts/13 §3.1 L230·§3.2 L365('300ms 초과·5xx → degraded{rerank, timeout}')는 여전히 5xx를 timeout에 묶는다 — 이 문서 범위 밖(바이블·13 소유)이며 10 미해결 이슈 19와 이 문서 미해결 이슈 20에 patch 대상으로 등재만 했다. |
| 274 | 16-reranking.md | pipelines-pass1 | 이 문서는 스키마 파일을 소유하지 않아 `schemas/ranked-set.schema.json`(10 소유)은 수정하지 않았다 — 파싱·값 일치(L87 description)만 확인했다. |
| 275 | 17-post-processing-and-context-packing.md | pipelines-pass1 | [frontmatter] 지시는 status·last_updated만 명시했으나 15 문서 선례(리뷰 반영 후 0.1.1)에 맞춰 version을 0.1.1로 올림. |
| 276 | 17-post-processing-and-context-packing.md | pipelines-pass1 | 부속 파일 없음 — 이 문서는 스키마 파일을 소유하지 않으며 context-pack/rendered-context/ranked-set 스키마는 03-contracts 소유라 수정하지 않음. 검증 하네스(scratchpad/validate17.cjs)는 임시 파일이며 산출물이 아님. |
| 277 | 18-advanced-retrieval-graph-raptor-agentic.md | pipelines-pass1 | anchor minor(존재하지 않는 문서 링크)·tech minor(끊어진 링크): 링크를 텍스트로 바꾸지 않고 유지했다 — 공통 규약이 '링크만 문서 맵 경로로 건다'를 명시하므로 코퍼스 규약 우선. 대신 미해결 이슈 18에 재검증 메모를 추가. 편집 중 05-api/03·08-evaluation/02·03·11-roadmap/01이 생성되어 현재 미존재 링크는 05-api/05·08-evaluation/05·09-operations/03 3건이며, 신규 생성 문서의 인용 절 번호는 미검증 |
| 278 | 18-advanced-retrieval-graph-raptor-agentic.md | pipelines-pass1 | anchor major(ContextPack.session_id) fix의 '미해결 이슈 10에 병합' 대안 대신 별도 이슈 16으로 분리했다(이슈 10은 `Strategy.iterative` 의미로 주제가 다름) |
| 279 | 19-update-delete-and-reindexing.md | pipelines-pass1 | 미반영: 리뷰 fix 중 'U-2에 명시적 예외 추가' — 단계 3을 폐기했으므로 예외가 불필요해 U-2는 그대로 유지. |
| 280 | 19-update-delete-and-reindexing.md | pipelines-pass1 | 동시 작성 중인 문서로 인해 미해결 16 목록(현재 6개 미작성)은 게시 시점에 다시 바뀔 수 있다. |

## 결정 사항 요약

- 이 목록이 4단계 T1의 유일한 입력이다. T1 이후 새로 발생하는 요청은 4단계 백로그로 넘긴다.

## 미해결 이슈

- "바이블 관련" 자동 판정의 오분류는 T1에서 정정한다.

## 참조

- [3단계 문서 원장](04-phase3-document-ledger.md) · [4·5단계 계획](02-phase4-5-plan.md) · [설계 바이블](../02-architecture/00-design-bible.md)
