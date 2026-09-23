---
title: 요구사항 추적 매트릭스 (Traceability Matrix)
status: active
owner: architecture
version: 1.0.3
last_updated: 2026-09-23
depends_on: ["../01-requirements/01-functional-requirements.md", "../01-requirements/02-non-functional-requirements.md", "../11-roadmap/02-epics-and-backlog.md"]
generated_by: tools/traceability.mjs
---

# 요구사항 추적 매트릭스

## 목적

01-requirements가 정의한 모든 FR·NFR·UC·US ID에 대해 **어느 설계 문서(02~11)가 인용하는지**와 로드맵 백로그(11-roadmap/02)의 어느 태스크가 구현하는지를 기계적으로 집계한다. 3단계 완전성 검토 누락 #4(FR 74% 미인용)에 대한 대응이며, 문서 본문에 인용을 억지로 추가하는 대신 이 매트릭스가 추적성의 정본이 된다. 재생성: `node tools/traceability.mjs --date <날짜>`.

## 범위

정의: 01-requirements/01·02·03·04의 표 첫 열 또는 제목의 ID. 인용: docs/ 아래 01-requirements와 12-appendix를 제외한 모든 문서의 본문. 로드맵 매핑: 11-roadmap/02의 같은 행에 등장하는 태스크 ID(`T-XXX-nn`).

## 1. 집계

| 구분 | 정의 | 설계 문서 인용 | 인용률 |
|------|-----:|-----:|-----:|
| FR | 217 | 57 | 26% |
| NFR | 150 | 113 | 75% |
| UC | 20 | 6 | 30% |
| US | 91 | 91 | 100% |

미정의 ID 인용(설계 문서가 쓰지만 요구사항 문서에 없음): 1건 — NFR-REL-17(07-backup-and-disaster-recovery.md)

## 2. 매트릭스

### FR (217)

| ID | 제목 | 정의 문서 | 인용 설계 문서 | 로드맵 태스크 |
|---|---|---|---|---|
| FR-API-01 | 수집 API | 01-functional-requirements.md | 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| FR-API-02 | 리트리벌 API | 01-functional-requirements.md | **미인용** | - |
| FR-API-03 | 문서·청크 조회 API | 01-functional-requirements.md | 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| FR-API-04 | OpenAPI 명세 게시 | 01-functional-requirements.md | 02-architecture/00-design-bible, 05-api/01-api-design-guidelines, 05-api/04-management-api | - |
| FR-API-05 | 표준 오류 모델 | 01-functional-requirements.md | **미인용** | - |
| FR-API-06 | API 버전 관리 | 01-functional-requirements.md | **미인용** | - |
| FR-API-07 | 페이지네이션·필터 | 01-functional-requirements.md | **미인용** | - |
| FR-API-08 | 스트리밍 응답 | 01-functional-requirements.md | 05-api/03-retrieval-api | - |
| FR-API-09 | 레이트 리밋 | 01-functional-requirements.md | **미인용** | - |
| FR-API-10 | 클라이언트 SDK | 01-functional-requirements.md | **미인용** | - |
| FR-API-11 | 레퍼런스 답변 엔드포인트 | 01-functional-requirements.md | 05-api/03-retrieval-api, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| FR-API-12 | 헬스·준비 상태 | 01-functional-requirements.md | 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| FR-API-13 | 최종 사용자 챗 UI 비포함 | 01-functional-requirements.md | 02-architecture/01-system-overview | - |
| FR-API-14 | 웹훅 구독 관리 | 01-functional-requirements.md | 05-api/07-webhooks-and-events, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| FR-API-15 | 이벤트 전달 보장 | 01-functional-requirements.md | 05-api/07-webhooks-and-events, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| FR-API-16 | 공통 스칼라 형식 | 01-functional-requirements.md | 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| FR-CHK-01 | 구조 인식 청킹 | 01-functional-requirements.md | 11-roadmap/02-epics-and-backlog | (로드맵 02 언급), T-CHK-24 |
| FR-CHK-02 | 토큰 예산 기반 병합 | 01-functional-requirements.md | **미인용** | - |
| FR-CHK-03 | 부모-자식 계층 청크 | 01-functional-requirements.md | **미인용** | - |
| FR-CHK-04 | 제목 경로 부착 | 01-functional-requirements.md | **미인용** | - |
| FR-CHK-05 | 표 전용 청킹 | 01-functional-requirements.md | **미인용** | - |
| FR-CHK-06 | 청크 출처 범위 | 01-functional-requirements.md | **미인용** | - |
| FR-CHK-07 | 오버랩 제어 | 01-functional-requirements.md | **미인용** | - |
| FR-CHK-08 | 의미 기반 분할 옵션 | 01-functional-requirements.md | **미인용** | - |
| FR-CHK-09 | 고급 청킹 전략 옵션 | 01-functional-requirements.md | **미인용** | - |
| FR-CHK-10 | 청크 ID와 결정적 콘텐츠 키 | 01-functional-requirements.md | **미인용** | - |
| FR-CHK-11 | 청크 타입 분류 | 01-functional-requirements.md | 02-architecture/01-system-overview | - |
| FR-CHK-12 | 미세 청크 제거 | 01-functional-requirements.md | **미인용** | - |
| FR-EMB-01 | dense 임베딩 생성 | 01-functional-requirements.md | 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| FR-EMB-02 | learned sparse 임베딩 생성 | 01-functional-requirements.md | **미인용** | - |
| FR-EMB-03 | 다중 벡터(late interaction) 옵션 | 01-functional-requirements.md | **미인용** | - |
| FR-EMB-04 | 임베딩 서빙 어댑터 | 01-functional-requirements.md | 02-architecture/01-system-overview | - |
| FR-EMB-05 | 모델 식별자 기록 | 01-functional-requirements.md | **미인용** | - |
| FR-EMB-06 | 질의·문서 비대칭 처리 | 01-functional-requirements.md | **미인용** | - |
| FR-EMB-07 | 배치·재시도 | 01-functional-requirements.md | **미인용** | - |
| FR-EMB-08 | 입력 길이 초과 처리 | 01-functional-requirements.md | **미인용** | - |
| FR-EMB-09 | 임베딩 캐시 | 01-functional-requirements.md | **미인용** | - |
| FR-EMB-10 | 다중 임베딩 필드 | 01-functional-requirements.md | **미인용** | - |
| FR-ENR-01 | 문맥 요약 부착 | 01-functional-requirements.md | 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| FR-ENR-02 | 키워드·핵심구 추출 | 01-functional-requirements.md | **미인용** | - |
| FR-ENR-03 | 가상 질문 생성 | 01-functional-requirements.md | **미인용** | - |
| FR-ENR-04 | 엔티티·관계 추출 | 01-functional-requirements.md | **미인용** | - |
| FR-ENR-05 | 청크 언어·도메인 태깅 | 01-functional-requirements.md | 00-vision/02-design-principles | - |
| FR-ENR-06 | 보강 출처·모델 기록 | 01-functional-requirements.md | **미인용** | - |
| FR-ENR-07 | 보강 실패 격리 | 01-functional-requirements.md | **미인용** | - |
| FR-ENR-08 | PII 감지 훅 | 01-functional-requirements.md | 00-vision/02-design-principles, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| FR-ENR-09 | 보강 캐시 | 01-functional-requirements.md | **미인용** | - |
| FR-EVL-01 | 골든셋 포맷 | 01-functional-requirements.md | 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| FR-EVL-02 | 오프라인 검색 메트릭 | 01-functional-requirements.md | **미인용** | - |
| FR-EVL-03 | 컨텍스트 품질 메트릭 | 01-functional-requirements.md | **미인용** | - |
| FR-EVL-04 | 프로파일 비교 실행 | 01-functional-requirements.md | **미인용** | - |
| FR-EVL-05 | 스테이지별 진단 | 01-functional-requirements.md | **미인용** | - |
| FR-EVL-06 | LLM-judge 평가 | 01-functional-requirements.md | **미인용** | - |
| FR-EVL-07 | 합성 골든셋 생성 | 01-functional-requirements.md | **미인용** | - |
| FR-EVL-08 | 회귀 게이트 | 01-functional-requirements.md | **미인용** | - |
| FR-EVL-09 | 온라인 피드백 수집 | 01-functional-requirements.md | 08-evaluation/06-online-feedback-loop | - |
| FR-EVL-10 | 평가 결과 저장·비교 | 01-functional-requirements.md | **미인용** | - |
| FR-EVL-11 | 한국어 벤치마크 내장 | 01-functional-requirements.md | **미인용** | - |
| FR-EVL-12 | 평가기 플러그인 | 01-functional-requirements.md | **미인용** | - |
| FR-IDX-01 | 인덱스 백엔드 추상화 | 01-functional-requirements.md | 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| FR-IDX-02 | 하이브리드 레코드 저장 | 01-functional-requirements.md | **미인용** | - |
| FR-IDX-03 | 한국어 렉시컬 분석 | 01-functional-requirements.md | **미인용** | - |
| FR-IDX-04 | 테넌시 필드 강제 | 01-functional-requirements.md | **미인용** | - |
| FR-IDX-05 | 원자적 커밋 | 01-functional-requirements.md | **미인용** | - |
| FR-IDX-06 | 커밋 롤백 | 01-functional-requirements.md | 02-architecture/01-system-overview, 02-architecture/03-data-flow-and-document-lifecycle | - |
| FR-IDX-07 | 커밋 해시 재현성 | 01-functional-requirements.md | **미인용** | - |
| FR-IDX-08 | 경량 단일 백엔드 프로파일 | 01-functional-requirements.md | **미인용** | - |
| FR-IDX-09 | 페이로드 필터 인덱스 | 01-functional-requirements.md | **미인용** | - |
| FR-IDX-10 | 부모·문서 저장소 | 01-functional-requirements.md | **미인용** | - |
| FR-IDX-11 | 그래프 인덱스 옵션 | 01-functional-requirements.md | **미인용** | - |
| FR-IDX-12 | 인덱스 스키마 마이그레이션 | 01-functional-requirements.md | **미인용** | - |
| FR-ING-01 | URI 기반 수집 요청 수신 | 01-functional-requirements.md | 04-pipelines/02-fetching-and-source-resolution, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| FR-ING-02 | 다중 URI 스킴 지원 | 01-functional-requirements.md | **미인용** | - |
| FR-ING-03 | 배치 수집 요청 | 01-functional-requirements.md | **미인용** | - |
| FR-ING-04 | 비동기 잡 응답 | 01-functional-requirements.md | **미인용** | - |
| FR-ING-05 | 콘텐츠 해시 기반 멱등성 | 01-functional-requirements.md | **미인용** | - |
| FR-ING-06 | 클라이언트 멱등 키 | 01-functional-requirements.md | **미인용** | - |
| FR-ING-07 | 외부 메타데이터 보존 | 01-functional-requirements.md | **미인용** | - |
| FR-ING-08 | 원본 보존 및 콘텐츠 주소화 저장 | 01-functional-requirements.md | 02-architecture/03-data-flow-and-document-lifecycle, 04-pipelines/02-fetching-and-source-resolution | - |
| FR-ING-09 | 원본 무결성 검증 | 01-functional-requirements.md | 04-pipelines/02-fetching-and-source-resolution, 11-roadmap/02-epics-and-backlog | T-ING-09 |
| FR-ING-10 | 크기·시간 제한 | 01-functional-requirements.md | 04-pipelines/02-fetching-and-source-resolution | - |
| FR-ING-11 | 문서 버전 관리 | 01-functional-requirements.md | **미인용** | - |
| FR-ING-12 | 삭제 요청 수집 | 01-functional-requirements.md | **미인용** | - |
| FR-ING-13 | 수집 정책 오버라이드 | 01-functional-requirements.md | **미인용** | - |
| FR-ING-14 | 잡 상태 조회 및 이벤트 | 01-functional-requirements.md | 02-architecture/01-system-overview, 05-api/07-webhooks-and-events | - |
| FR-ING-15 | 잡 취소 | 01-functional-requirements.md | 04-pipelines/02-fetching-and-source-resolution | - |
| FR-ING-16 | 원천 크롤링 비포함 | 01-functional-requirements.md | 02-architecture/01-system-overview, 04-pipelines/02-fetching-and-source-resolution | - |
| FR-MCP-01 | 표준 도구 제공 | 01-functional-requirements.md | 05-api/05-mcp-server, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| FR-MCP-02 | 도구 스키마 동기화 | 01-functional-requirements.md | 05-api/05-mcp-server, 11-roadmap/02-epics-and-backlog | T-MCP-02 |
| FR-MCP-03 | 렌더 형식 선택 | 01-functional-requirements.md | 05-api/05-mcp-server | - |
| FR-MCP-04 | 테넌트 컨텍스트 전달 | 01-functional-requirements.md | **미인용** | - |
| FR-MCP-05 | 인용 해소 도구 | 01-functional-requirements.md | 02-architecture/01-system-overview, 05-api/05-mcp-server | - |
| FR-MCP-06 | 전송 방식 | 01-functional-requirements.md | 02-architecture/01-system-overview, 05-api/05-mcp-server | - |
| FR-MGT-01 | 테넌트 관리 | 01-functional-requirements.md | 00-vision/04-scope-and-non-goals, 02-architecture/00-design-bible, 06-adr/0039-bible-1-3-additive-amendment-bundle, 06-adr/README, 09-operations/01-deployment-guide, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| FR-MGT-02 | 컬렉션 관리 | 01-functional-requirements.md | **미인용** | - |
| FR-MGT-03 | 프로파일 정의 | 01-functional-requirements.md | **미인용** | - |
| FR-MGT-04 | 프로파일 불변성 | 01-functional-requirements.md | **미인용** | - |
| FR-MGT-05 | 기본·경량 프로파일 내장 | 01-functional-requirements.md | **미인용** | - |
| FR-MGT-06 | 재인덱싱 | 01-functional-requirements.md | **미인용** | - |
| FR-MGT-07 | 프로파일 마이그레이션 | 01-functional-requirements.md | **미인용** | - |
| FR-MGT-08 | 잡 관리 | 01-functional-requirements.md | **미인용** | - |
| FR-MGT-09 | 산출물 조회·다운로드 | 01-functional-requirements.md | **미인용** | - |
| FR-MGT-10 | 사전 관리 | 01-functional-requirements.md | **미인용** | - |
| FR-MGT-11 | 설정 검증 | 01-functional-requirements.md | **미인용** | - |
| FR-MGT-12 | 통계 조회 | 01-functional-requirements.md | 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| FR-MGT-13 | 오케스트레이션 러너 교체 | 01-functional-requirements.md | **미인용** | - |
| FR-MGT-14 | 고품질 프로파일 내장 | 01-functional-requirements.md | **미인용** | - |
| FR-NRM-01 | 텍스트 정규화 | 01-functional-requirements.md | 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| FR-NRM-02 | 제목 계층 복원 | 01-functional-requirements.md | **미인용** | - |
| FR-NRM-03 | 보일러플레이트 제거 | 01-functional-requirements.md | **미인용** | - |
| FR-NRM-04 | 언어 판별 | 01-functional-requirements.md | 00-vision/02-design-principles | - |
| FR-NRM-05 | 표 텍스트 직렬화 | 01-functional-requirements.md | **미인용** | - |
| FR-NRM-06 | 그림 텍스트화 | 01-functional-requirements.md | **미인용** | - |
| FR-NRM-07 | 각주·미주 연결 | 01-functional-requirements.md | **미인용** | - |
| FR-NRM-08 | 목록 구조 보존 | 01-functional-requirements.md | **미인용** | - |
| FR-NRM-09 | 문서 품질 점수 | 01-functional-requirements.md | **미인용** | - |
| FR-NRM-10 | 정규화 규칙 플러그인 | 01-functional-requirements.md | **미인용** | - |
| FR-OBS-01 | 분산 트레이스 | 01-functional-requirements.md | 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| FR-OBS-02 | GenAI 시맨틱 컨벤션 | 01-functional-requirements.md | **미인용** | - |
| FR-OBS-03 | 표준 메트릭 | 01-functional-requirements.md | **미인용** | - |
| FR-OBS-04 | 검색 설명(explain) | 01-functional-requirements.md | **미인용** | - |
| FR-OBS-05 | 구조화 로그 | 01-functional-requirements.md | **미인용** | - |
| FR-OBS-06 | 외부 익스포터 | 01-functional-requirements.md | **미인용** | - |
| FR-OBS-07 | 품질 드리프트 지표 | 01-functional-requirements.md | 08-evaluation/06-online-feedback-loop | - |
| FR-OBS-08 | 잡 진행률 | 01-functional-requirements.md | **미인용** | - |
| FR-OBS-09 | 샘플링·마스킹 제어 | 01-functional-requirements.md | **미인용** | - |
| FR-OBS-10 | 비용 계측 | 01-functional-requirements.md | **미인용** | - |
| FR-PCK-01 | 토큰 예산 패킹 | 01-functional-requirements.md | 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| FR-PCK-02 | 중복·오버랩 제거 | 01-functional-requirements.md | **미인용** | - |
| FR-PCK-03 | 부모 확장(small-to-big) | 01-functional-requirements.md | **미인용** | - |
| FR-PCK-04 | 다양성 제어 | 01-functional-requirements.md | **미인용** | - |
| FR-PCK-05 | 위치 최적 정렬 | 01-functional-requirements.md | **미인용** | - |
| FR-PCK-06 | 인용 ID 부여 | 01-functional-requirements.md | **미인용** | - |
| FR-PCK-07 | 출처 메타데이터 포함 | 01-functional-requirements.md | **미인용** | - |
| FR-PCK-08 | 표·그림 텍스트 포함 | 01-functional-requirements.md | **미인용** | - |
| FR-PCK-09 | 신뢰도 및 저신뢰 경고 | 01-functional-requirements.md | **미인용** | - |
| FR-PCK-10 | 공급자 중립 JSON | 01-functional-requirements.md | **미인용** | - |
| FR-PCK-11 | 공급자별 렌더러 | 01-functional-requirements.md | **미인용** | - |
| FR-PCK-12 | 프롬프트 템플릿 힌트 | 01-functional-requirements.md | **미인용** | - |
| FR-PCK-13 | 컨텍스트 압축 옵션 | 01-functional-requirements.md | **미인용** | - |
| FR-PCK-14 | 토큰 통계 | 01-functional-requirements.md | **미인용** | - |
| FR-PCK-15 | 렌더링 결정성 | 01-functional-requirements.md | **미인용** | - |
| FR-PLG-01 | 확장 지점 정의 | 01-functional-requirements.md | 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| FR-PLG-02 | 엔트리포인트 레지스트리 | 01-functional-requirements.md | **미인용** | - |
| FR-PLG-03 | 계약 적합성 검사 | 01-functional-requirements.md | **미인용** | - |
| FR-PLG-04 | 플러그인 설정 스키마 | 01-functional-requirements.md | **미인용** | - |
| FR-PLG-05 | 적합성 테스트 키트 | 01-functional-requirements.md | **미인용** | - |
| FR-PLG-06 | 능력 선언 | 01-functional-requirements.md | **미인용** | - |
| FR-PLG-07 | 격리 실행 옵션 | 01-functional-requirements.md | 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| FR-PLG-08 | 플러그인 관측성 | 01-functional-requirements.md | **미인용** | - |
| FR-PLG-09 | 플러그인 SDK | 01-functional-requirements.md | **미인용** | - |
| FR-PLG-10 | 라이선스 메타데이터 | 01-functional-requirements.md | **미인용** | - |
| FR-PRS-01 | 포맷 감지 및 라우팅 | 01-functional-requirements.md | 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| FR-PRS-02 | HWPX 1급 파싱 | 01-functional-requirements.md | **미인용** | - |
| FR-PRS-03 | HWPX 표 병합 셀 보존 | 01-functional-requirements.md | **미인용** | - |
| FR-PRS-04 | HWP 5.0 바이너리 파싱 | 01-functional-requirements.md | **미인용** | - |
| FR-PRS-05 | PDF 레이아웃 인식 파싱 | 01-functional-requirements.md | **미인용** | - |
| FR-PRS-06 | PDF 표 구조 추출 | 01-functional-requirements.md | **미인용** | - |
| FR-PRS-07 | 스캔 PDF 판별 및 OCR | 01-functional-requirements.md | **미인용** | - |
| FR-PRS-08 | OCR 신뢰도 기록 | 01-functional-requirements.md | **미인용** | - |
| FR-PRS-09 | DOCX 구조 파싱 | 01-functional-requirements.md | **미인용** | - |
| FR-PRS-10 | DOC 레거시 파싱 | 01-functional-requirements.md | **미인용** | - |
| FR-PRS-11 | HTML 본문 추출 | 01-functional-requirements.md | **미인용** | - |
| FR-PRS-12 | HTML 메타데이터 수확 | 01-functional-requirements.md | **미인용** | - |
| FR-PRS-13 | 텍스트·마크다운 파싱 | 01-functional-requirements.md | **미인용** | - |
| FR-PRS-14 | 출처(provenance) 필수 기록 | 01-functional-requirements.md | **미인용** | - |
| FR-PRS-15 | 그림·이미지 추출 | 01-functional-requirements.md | 11-roadmap/02-epics-and-backlog | T-PRS-20 |
| FR-PRS-16 | 수식·코드 블록 식별 | 01-functional-requirements.md | **미인용** | - |
| FR-PRS-17 | 파서 폴백 체인 | 01-functional-requirements.md | **미인용** | - |
| FR-PRS-18 | 부분 파싱 결과 허용 | 01-functional-requirements.md | **미인용** | - |
| FR-PRS-19 | 암호화·손상 문서 처리 | 01-functional-requirements.md | **미인용** | - |
| FR-PRS-20 | 압축 컨테이너 전개 | 01-functional-requirements.md | **미인용** | - |
| FR-PRS-21 | HWP 고급 개체 지원 | 01-functional-requirements.md | **미인용** | - |
| FR-PRS-22 | 문서 변환기 격리 및 폴백 | 01-functional-requirements.md | **미인용** | - |
| FR-QRY-01 | 질의 계획 생성 | 01-functional-requirements.md | 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| FR-QRY-02 | 질의 정규화 | 01-functional-requirements.md | **미인용** | - |
| FR-QRY-03 | 질의 재작성·확장 | 01-functional-requirements.md | **미인용** | - |
| FR-QRY-04 | 복합 질의 분해 | 01-functional-requirements.md | **미인용** | - |
| FR-QRY-05 | 구조화 필터 추출 | 01-functional-requirements.md | **미인용** | - |
| FR-QRY-06 | 대화 이력 반영 | 01-functional-requirements.md | **미인용** | - |
| FR-QRY-07 | 질의 언어 판별 및 교차 언어 | 01-functional-requirements.md | **미인용** | - |
| FR-QRY-08 | 전략 라우팅 | 01-functional-requirements.md | **미인용** | - |
| FR-QRY-09 | 예산 배정 | 01-functional-requirements.md | **미인용** | - |
| FR-QRY-10 | 질의 임베딩 캐시 | 01-functional-requirements.md | **미인용** | - |
| FR-QRY-11 | 오탈자 후보 제시 | 01-functional-requirements.md | **미인용** | - |
| FR-RET-01 | dense 벡터 검색 | 01-functional-requirements.md | 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| FR-RET-02 | sparse 벡터 검색 | 01-functional-requirements.md | **미인용** | - |
| FR-RET-03 | 렉시컬 검색 | 01-functional-requirements.md | **미인용** | - |
| FR-RET-04 | 병렬 실행 | 01-functional-requirements.md | **미인용** | - |
| FR-RET-05 | 결과 융합 | 01-functional-requirements.md | **미인용** | - |
| FR-RET-06 | 필수 필터 강제 | 01-functional-requirements.md | 02-architecture/01-system-overview | - |
| FR-RET-07 | 메타데이터 필터 결합 | 01-functional-requirements.md | **미인용** | - |
| FR-RET-08 | 점수 분해 기록 | 01-functional-requirements.md | **미인용** | - |
| FR-RET-09 | 다중 컬렉션 검색 | 01-functional-requirements.md | **미인용** | - |
| FR-RET-10 | 그래프·계층 리트리버 옵션 | 01-functional-requirements.md | **미인용** | - |
| FR-RET-11 | 반복(agentic) 검색 옵션 | 01-functional-requirements.md | **미인용** | - |
| FR-RET-12 | 빈 결과·저신뢰 신호 | 01-functional-requirements.md | **미인용** | - |
| FR-RNK-01 | 크로스인코더 리랭킹 | 01-functional-requirements.md | 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| FR-RNK-02 | 리랭킹 입력 구성 | 01-functional-requirements.md | **미인용** | - |
| FR-RNK-03 | 리랭커 어댑터 | 01-functional-requirements.md | 02-architecture/01-system-overview | - |
| FR-RNK-04 | LLM 리랭커 옵션 | 01-functional-requirements.md | 11-roadmap/02-epics-and-backlog | T-RET-25 |
| FR-RNK-05 | late interaction 리랭킹 옵션 | 01-functional-requirements.md | **미인용** | - |
| FR-RNK-06 | 리랭킹 생략·폴백 | 01-functional-requirements.md | **미인용** | - |
| FR-RNK-07 | 점수 보정 | 01-functional-requirements.md | **미인용** | - |
| FR-RNK-08 | 리랭킹 점수 분해 | 01-functional-requirements.md | **미인용** | - |
| FR-SEC-01 | 인증 연동 | 01-functional-requirements.md | 02-architecture/01-system-overview, 02-architecture/07-multi-tenancy-and-security-architecture, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| FR-SEC-02 | 역할 기반 권한 | 01-functional-requirements.md | 02-architecture/07-multi-tenancy-and-security-architecture | - |
| FR-SEC-03 | 테넌트 격리 | 01-functional-requirements.md | **미인용** | - |
| FR-SEC-04 | 문서 수준 ACL | 01-functional-requirements.md | **미인용** | - |
| FR-SEC-05 | ACL 갱신 | 01-functional-requirements.md | **미인용** | - |
| FR-SEC-06 | 원본 URI 접근 자격 증명 | 01-functional-requirements.md | 02-architecture/07-multi-tenancy-and-security-architecture, 04-pipelines/02-fetching-and-source-resolution | - |
| FR-SEC-07 | 감사 로그 | 01-functional-requirements.md | **미인용** | - |
| FR-SEC-08 | PII 처리 정책 | 01-functional-requirements.md | 02-architecture/07-multi-tenancy-and-security-architecture, 05-api/04-management-api, 09-operations/05-security-and-compliance | - |
| FR-SEC-09 | 파서 격리 실행 | 01-functional-requirements.md | **미인용** | - |
| FR-SEC-10 | 삭제 완결성 | 01-functional-requirements.md | 02-architecture/03-data-flow-and-document-lifecycle, 02-architecture/06-orchestration-and-workflows, 04-pipelines/19-update-delete-and-reindexing | - |
| FR-SEC-11 | 웹훅 서명 | 01-functional-requirements.md | 02-architecture/07-multi-tenancy-and-security-architecture, 05-api/07-webhooks-and-events, 09-operations/05-security-and-compliance | - |
| FR-SEC-12 | 프롬프트 주입 표면 축소 | 01-functional-requirements.md | 02-architecture/07-multi-tenancy-and-security-architecture | - |

### NFR (150)

| ID | 제목 | 정의 문서 | 인용 설계 문서 | 로드맵 태스크 |
|---|---|---|---|---|
| NFR-AVL-01 | 리트리벌 API 가용성(브리프 §7) | 02-non-functional-requirements.md | 00-vision/01-vision-and-goals, 02-architecture/01-system-overview, 02-architecture/09-failure-modes-and-resilience | - |
| NFR-AVL-02 | 수집 API(요청 접수·상태 조회) 가용성 | 02-non-functional-requirements.md | 02-architecture/09-failure-modes-and-resilience | - |
| NFR-AVL-03 | 관리 API 가용성 | 02-non-functional-requirements.md | 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| NFR-AVL-04 | 무중단 배포. 롤링 업데이트 중 요청 실패와 잡 유실이 없다 | 02-non-functional-requirements.md | 02-architecture/09-failure-modes-and-resilience, 11-roadmap/02-epics-and-backlog | T-MGT-27 |
| NFR-AVL-05 | ENV-M 이상에서 핵심 경로에 단일 장애점이 없다 | 02-non-functional-requirements.md | 02-architecture/09-failure-modes-and-resilience, 09-operations/06-runbooks, 11-roadmap/03-risks-and-mitigations | - |
| NFR-AVL-06 | 헬스·레디니스 엔드포인트는 의존성 상태를 반영한다 | 02-non-functional-requirements.md | 02-architecture/09-failure-modes-and-resilience, 11-roadmap/02-epics-and-backlog | T-MGT-16 |
| NFR-AVL-07 | 인덱스 재구축·프로파일 마이그레이션 중 검색이 지속된다 | 02-non-functional-requirements.md | 02-architecture/01-system-overview, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| NFR-AVL-08 | 오류 예산 정책을 운영한다 | 02-non-functional-requirements.md | 02-architecture/09-failure-modes-and-resilience, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급), T-OBS-18 |
| NFR-AVL-09 | 캐시 계층(질의 임베딩·결과 캐시)은 비핵심 의존성이다. 캐시 전체 중단 시 검색은 캐시 미스 경로로 계속 응답한다(레이트리밋의 캐시 중단 시  | 02-non-functional-requirements.md | 02-architecture/01-system-overview, 02-architecture/07-multi-tenancy-and-security-architecture, 02-architecture/09-failure-modes-and-resilience, 09-operations/04-scaling-and-performance, 11-roadmap/02-epics-and-backlog, 11-roadmap/03-risks-and-mitigations | (로드맵 02 언급), T-SEC-22 |
| NFR-CMP-01 | 플랫폼 코드는 Apache-2.0으로 배포되고 모든 소스 파일에 SPDX 식별자가 있다(D-02) | 02-non-functional-requirements.md | 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| NFR-CMP-02 | 의존성은 §14.2 라이선스 정책을 따르고 CI 라이선스 게이트가 위반을 차단한다 | 02-non-functional-requirements.md | 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| NFR-CMP-03 | AGPL 컴포넌트는 네트워크로 분리된 별도 컨테이너·서비스로만 사용하고 코어 프로세스에 임포트하지 않는다(D-02) | 02-non-functional-requirements.md | 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| NFR-CMP-04 | 기본 프로파일의 모델 가중치는 상업적 사용을 허용하는 라이선스만 사용한다 | 02-non-functional-requirements.md | **미인용** | - |
| NFR-CMP-05 | 릴리스마다 SBOM(CycloneDX 또는 SPDX)을 이미지·패키지와 함께 게시한다 | 02-non-functional-requirements.md | **미인용** | - |
| NFR-CMP-06 | NOTICE·서드파티 라이선스 파일을 자동 생성해 최신 상태로 유지한다 | 02-non-functional-requirements.md | 11-roadmap/02-epics-and-backlog | T-SEC-15 |
| NFR-CMP-07 | 개인정보 규제(한국 개인정보보호법, GDPR 등) 준수를 지원하는 기능(삭제·보존·처리 기록·거주성)을 제공한다. 규제 준수 자체는 운영자 책임 | 02-non-functional-requirements.md | **미인용** | - |
| NFR-CMP-08 | 감사 증적 내보내기. 감사 로그(NFR-SEC-08)를 표준 포맷(JSON Lines)으로 기간·테넌트별 내보낼 수 있다 | 02-non-functional-requirements.md | 11-roadmap/02-epics-and-backlog | T-SEC-10 |
| NFR-CMP-09 | 외부 데이터 전송 투명성. 배포 설정에서 활성화된 외부 API 호출 목록(호스트, 목적, 전송 데이터 종류)을 관리 API로 조회할 수 있다 | 02-non-functional-requirements.md | 11-roadmap/02-epics-and-backlog | T-SEC-08, T-SEC-18 |
| NFR-CMP-10 | 플러그인 레지스트리(D-10) 메타데이터에 라이선스 식별자(SPDX)를 필수로 포함하고 정책 위반 플러그인은 로드 시 경고·차단 옵션을 제공한다 | 02-non-functional-requirements.md | 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| NFR-CST-01 | 벡터 양자화(int8, binary) 옵션으로 dense 인덱스 메모리를 절감하고 품질 저하를 제한한다 | 02-non-functional-requirements.md | 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| NFR-CST-02 | LLM 보강 비용 상한. 컬렉션별 토큰 예산과 일일 한도를 두고 초과 시 보강을 건너뛰며 경고를 기록한다(미정(O-05): 기본 켬/끔과 비용  | 02-non-functional-requirements.md | 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| NFR-CST-03 | 산출물 저장 비용. 콘텐츠 주소화로 동일 산출물 중복 저장이 없고 산출물 총량은 원본의 3배 이하 | 02-non-functional-requirements.md | **미인용** | - |
| NFR-CST-04 | GPU 유휴 비용. 임베딩·리랭커 서빙은 scale-to-zero 또는 최소 replica 설정을 지원한다 | 02-non-functional-requirements.md | **미인용** | - |
| NFR-CST-05 | 비용 메트릭. 테넌트·컬렉션별 처리 토큰, GPU 초, 저장 바이트, 질의 수를 집계한다 | 02-non-functional-requirements.md | 11-roadmap/02-epics-and-backlog | (로드맵 02 언급), T-MGT-30 |
| NFR-CST-06 | 캐시로 반복 비용을 절감한다. 질의 임베딩 캐시·결과 캐시(옵션)를 제공하고 히트 시 GPU 호출을 생략한다 | 02-non-functional-requirements.md | 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| NFR-CST-07 | 재처리 회피. 동일 콘텐츠 해시의 원본은 파싱·정규화를 건너뛰고 산출물을 재사용한다 | 02-non-functional-requirements.md | 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| NFR-CST-08 | 비용 추정 문서. 부하 프로파일(LP-S/M/L)별 자원 산정표(§3.5 산정식 포함)를 배포 가이드에 제공하고 릴리스마다 갱신한다 | 02-non-functional-requirements.md | **미인용** | - |
| NFR-MNT-01 | 모든 계약은 `schema_version`을 가지며(브리프 원칙 1), 버전 표기와 호환성 규칙은 [스키마 버저닝·호환성](../03-contr | 02-non-functional-requirements.md | 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| NFR-MNT-02 | 후방 호환성은 CI로 검증한다. 14-schema-versioning-and-compatibility가 "호환"으로 정의한 변경 범위 안에서,  | 02-non-functional-requirements.md | 10-development/04-testing-strategy, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| NFR-MNT-03 | 테스트 커버리지. 코어 패키지 라인 커버리지와 계약 모델의 JSON 라운드트립 테스트 | 02-non-functional-requirements.md | 10-development/04-testing-strategy, 10-development/05-ci-cd, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| NFR-MNT-04 | 정적 분석. ruff 오류 0, mypy strict 통과(D-01) | 02-non-functional-requirements.md | 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| NFR-MNT-05 | 플러그인 API 안정성. 확장 지점 인터페이스(D-10)는 명시적 버전을 가지며(규칙은 NFR-MNT-01과 동일 문서 준용) 폐기(deprec | 02-non-functional-requirements.md | 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| NFR-MNT-06 | 어댑터 격리. 벤더 타입(DoclingDocument, Unstructured Element 등)이 코어 계약 모듈로 임포트되지 않는다(원칙 2 | 02-non-functional-requirements.md | 11-roadmap/02-epics-and-backlog | (로드맵 02 언급), T-PRS-26 |
| NFR-MNT-07 | 파서 회귀 방지. 포맷별 샘플 코퍼스(HWPX·HWP·PDF·DOCX·DOC·HTML·TXT)에 대한 `ParsedDocument`(D-04)  | 02-non-functional-requirements.md | 10-development/04-testing-strategy, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| NFR-MNT-08 | 스키마 파일(`schemas/`)과 계약 문서·Pydantic 모델의 1:1 동기화를 CI가 검증한다 | 02-non-functional-requirements.md | 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| NFR-MNT-09 | 업그레이드. N-1 마이너 버전에서 무중단 업그레이드가 가능하고 DB 마이그레이션은 전진·후진 스크립트를 제공한다 | 02-non-functional-requirements.md | 10-development/08-release-process, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| NFR-MNT-10 | 설정 검증. 시작 시 프로파일·설정을 스키마로 검증하고 실패 시 필드 경로를 포함한 오류로 종료한다 | 02-non-functional-requirements.md | 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| NFR-MNT-11 | 프로파일 변경 시 산출물 기반 재인덱싱(재파싱 없이 청킹 이후만 재실행)을 지원한다 | 02-non-functional-requirements.md | 04-pipelines/12-embedding, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| NFR-MNT-12 | 코드·문서 규약. 문서는 브리프 §9 규약을, 코드는 [코딩 표준](../10-development/03-coding-standards.md)을 | 02-non-functional-requirements.md | **미인용** | - |
| NFR-OBS-01 | 모든 스테이지(D-05 경계)는 OpenTelemetry 스팬을 남기고 GenAI semantic conventions를 따른다(D-11) | 02-non-functional-requirements.md | 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| NFR-OBS-02 | 메트릭 명명은 `rag_<stage>_<name>_<unit>`을 따르고 RED(Rate, Errors, Duration) 지표를 모든 API· | 02-non-functional-requirements.md | **미인용** | - |
| NFR-OBS-03 | 설명 가능성. `RankedSet`의 모든 항목은 dense·sparse·lexical·rerank 점수와 융합 기여를 분해해 제공한다 | 02-non-functional-requirements.md | 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| NFR-OBS-04 | 구조화 로그(JSON)에 `trace_id`, `tenant_id`, `job_id`가 상관 키로 포함된다 | 02-non-functional-requirements.md | **미인용** | - |
| NFR-OBS-05 | 잡 상태 전이 이벤트는 저지연으로 발행된다 | 02-non-functional-requirements.md | 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| NFR-OBS-06 | SLI 대시보드 템플릿(Grafana)을 제공한다 | 02-non-functional-requirements.md | **미인용** | - |
| NFR-OBS-07 | SLO 번레이트(burn-rate) 알림 규칙을 기본 제공한다 | 02-non-functional-requirements.md | 02-architecture/09-failure-modes-and-resilience, 11-roadmap/02-epics-and-backlog | T-OBS-08 |
| NFR-OBS-08 | 메트릭 카디널리티를 제한한다. `tenant_id` 라벨은 상위 N 또는 해시 버킷, 청크·문서 ID는 라벨 금지 | 02-non-functional-requirements.md | **미인용** | - |
| NFR-OBS-09 | 트레이스 샘플링. 오류·저하 요청은 100%, 정상 요청은 설정 가능 | 02-non-functional-requirements.md | **미인용** | - |
| NFR-OBS-10 | 검색 품질 지표(nDCG@10, Recall@20, MRR)를 릴리스별로 기록·추적한다(목표값은 NFR-QLT-01~03) | 02-non-functional-requirements.md | 11-roadmap/02-epics-and-backlog | (로드맵 02 언급), T-OBS-19 |
| NFR-OBS-11 | 재현용 리플레이. 옵트인 시 `QueryRequest`·`QueryPlan`·백엔드 응답 요약을 저장해 동일 질의를 재실행할 수 있다 | 02-non-functional-requirements.md | **미인용** | - |
| NFR-OBS-12 | 비용·자원 메트릭(GPU 초, 토큰, 저장 바이트)을 테넌트 단위로 집계한다(NFR-CST-05와 연계) | 02-non-functional-requirements.md | 11-roadmap/02-epics-and-backlog | T-OBS-13 |
| NFR-PERF-01 | 리트리벌 API는 GPU 리랭커 환경에서 브리프 §7 지연 목표를 만족한다 | 02-non-functional-requirements.md | 02-architecture/01-system-overview, 08-evaluation/05-benchmark-plan-and-baselines, 11-roadmap/01-milestones, 11-roadmap/02-epics-and-backlog, 11-roadmap/03-risks-and-mitigations | (로드맵 02 언급) |
| NFR-PERF-02 | 리트리벌 API는 CPU 전용 환경에서도 실용적 지연을 만족한다 | 02-non-functional-requirements.md | 08-evaluation/05-benchmark-plan-and-baselines | - |
| NFR-PERF-03 | 중위 지연은 대화형 사용에 적합해야 한다 | 02-non-functional-requirements.md | **미인용** | - |
| NFR-PERF-04 | 꼬리 지연을 제한한다 | 02-non-functional-requirements.md | **미인용** | - |
| NFR-PERF-05 | 리랭커를 끈 하이브리드 검색은 저지연 모드로 동작한다 | 02-non-functional-requirements.md | **미인용** | - |
| NFR-PERF-06 | dense 단독 검색 경로의 지연 하한을 확보한다 | 02-non-functional-requirements.md | **미인용** | - |
| NFR-PERF-07 | 질의 임베딩 지연은 전체 p95 예산의 GPU 5%, CPU 15% 이하이어야 한다 | 02-non-functional-requirements.md | 02-architecture/01-system-overview, 04-pipelines/12-embedding | - |
| NFR-PERF-08 | 텍스트 PDF 100페이지를 브리프 §7 시간 내 end-to-end 처리한다 | 02-non-functional-requirements.md | 02-architecture/01-system-overview, 09-operations/04-scaling-and-performance, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| NFR-PERF-09 | 스캔 PDF 100페이지를 GPU OCR로 브리프 §7 시간 내 처리한다 | 02-non-functional-requirements.md | 02-architecture/01-system-overview, 09-operations/04-scaling-and-performance, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| NFR-PERF-10 | HWPX 100페이지는 텍스트 PDF와 동등한 시간 내 처리한다 | 02-non-functional-requirements.md | 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| NFR-PERF-11 | 임베딩 서빙 처리량은 부하 프로파일의 수집 처리량 목표(§3.4)를 병목 없이 뒷받침한다. 필요한 GPU 수는 §3.5 산정식으로 유도한다 | 02-non-functional-requirements.md | 04-pipelines/12-embedding, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| NFR-PERF-12 | 인덱스 커밋의 원자 교체는 검색 지연에 영향 없이 빠르게 끝난다 | 02-non-functional-requirements.md | 09-operations/04-scaling-and-performance, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| NFR-PERF-13 | API 계층 자체 오버헤드는 최소화한다 | 02-non-functional-requirements.md | 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| NFR-PERF-14 | 후처리·패킹은 저비용이어야 한다 | 02-non-functional-requirements.md | 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| NFR-PERF-15 | MCP 서버 경로는 REST 대비 추가 지연이 미미해야 한다 | 02-non-functional-requirements.md | 09-operations/04-scaling-and-performance, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급), T-MCP-10 |
| NFR-PERF-16 | 잡 상태 조회는 폴링에 적합해야 한다 | 02-non-functional-requirements.md | 09-operations/04-scaling-and-performance, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급), T-ING-11 |
| NFR-PERF-17 | 콜드 스타트 시간은 오토스케일에 적합해야 한다 | 02-non-functional-requirements.md | 02-architecture/01-system-overview, 02-architecture/08-deployment-architecture, 04-pipelines/12-embedding, 09-operations/04-scaling-and-performance | - |
| NFR-PERF-18 | 수집 큐 대기는 정상 부하에서 짧아야 한다 | 02-non-functional-requirements.md | 09-operations/04-scaling-and-performance | - |
| NFR-PERF-19 | 수집 부하가 검색 지연을 크게 저하시키지 않는다 | 02-non-functional-requirements.md | 04-pipelines/12-embedding, 09-operations/04-scaling-and-performance | - |
| NFR-PERF-20 | 리랭커 서빙 처리량은 피크 QPS × 리랭크 후보 수(§3.1)를 뒷받침한다. 필요한 GPU 수는 §3.5 산정식으로 유도한다 | 02-non-functional-requirements.md | **미인용** | - |
| NFR-PORT-01 | 컨테이너 이미지는 `linux/amd64`, `linux/arm64`를 제공한다 | 02-non-functional-requirements.md | 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| NFR-PORT-02 | Kubernetes(Helm)와 Docker Compose(경량 프로파일) 두 배포 경로를 제공한다 | 02-non-functional-requirements.md | 11-roadmap/01-milestones, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| NFR-PORT-03 | GPU 없이 기능적으로 완전하게 동작한다(성능 목표는 CPU 열 적용) | 02-non-functional-requirements.md | **미인용** | - |
| NFR-PORT-04 | 에어갭 설치. 모델 가중치·의존성·이미지를 오프라인 번들로 설치할 수 있다 | 02-non-functional-requirements.md | **미인용** | - |
| NFR-PORT-05 | S3 호환 스토리지 어디서나 동작한다(MinIO, Ceph RGW, AWS S3, 호환 게이트웨이) | 02-non-functional-requirements.md | **미인용** | - |
| NFR-PORT-06 | `IndexBackend` 교체 가능성. 계약 준수 테스트 스위트를 통과한 백엔드는 설정만으로 교체된다(D-15) | 02-non-functional-requirements.md | 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| NFR-PORT-07 | 클라우드 비종속 코어. 클라우드 SDK는 `fetcher` 등 플러그인(D-10)에만 존재한다 | 02-non-functional-requirements.md | **미인용** | - |
| NFR-PORT-08 | Python 3.12 이상을 지원하고 최신 안정 버전 호환을 CI 매트릭스로 검증한다(D-01) | 02-non-functional-requirements.md | **미인용** | - |
| NFR-PRV-01 | PII 탐지 훅. `enricher` 확장 지점에서 PII 태깅(예: Presidio 어댑터)을 옵션으로 제공한다 | 02-non-functional-requirements.md | 02-architecture/07-multi-tenancy-and-security-architecture, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| NFR-PRV-02 | PII 마스킹·가명화. 인덱스 저장 전 마스킹을 컬렉션 정책으로 켤 수 있다 | 02-non-functional-requirements.md | **미인용** | - |
| NFR-PRV-03 | 삭제권. 문서 삭제 요청은 §9의 데드라인(최대) 내에 모든 저장소에 반영된다 | 02-non-functional-requirements.md | 02-architecture/03-data-flow-and-document-lifecycle, 08-evaluation/06-online-feedback-loop, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| NFR-PRV-04 | 로그·트레이스에 문서 본문·질의 원문을 기본 기록하지 않는다. 필요 시 해시 또는 옵트인 샘플링 | 02-non-functional-requirements.md | 02-architecture/07-multi-tenancy-and-security-architecture, 08-evaluation/01-evaluation-strategy, 08-evaluation/06-online-feedback-loop, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| NFR-PRV-05 | 데이터 거주성. 테넌트별 오브젝트 스토리지 버킷·리전 고정을 지원한다 | 02-non-functional-requirements.md | **미인용** | - |
| NFR-PRV-06 | 외부 LLM·API 호출 통제. 보강·judge·질의 재작성에 외부 API를 사용할 때 테넌트 정책 플래그가 필요하며 기본값은 비활성 | 02-non-functional-requirements.md | 02-architecture/07-multi-tenancy-and-security-architecture, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급), T-RET-19 |
| NFR-PRV-07 | 보존 정책. 컬렉션별 TTL을 설정할 수 있고 만료 문서는 §9 절차로 자동 삭제된다 | 02-non-functional-requirements.md | 02-architecture/07-multi-tenancy-and-security-architecture | - |
| NFR-PRV-08 | 처리 기록. 테넌트별 데이터 흐름(저장소, 외부 호출, 보존 기간)을 관리 API로 조회할 수 있다 | 02-non-functional-requirements.md | 02-architecture/07-multi-tenancy-and-security-architecture, 11-roadmap/02-epics-and-backlog | T-SEC-18 |
| NFR-PRV-09 | 삭제는 멱등하다. 이미 삭제된 문서의 재삭제는 오류 없이 완료 상태를 반환한다 | 02-non-functional-requirements.md | 02-architecture/03-data-flow-and-document-lifecycle, 02-architecture/07-multi-tenancy-and-security-architecture, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| NFR-PRV-10 | 삭제 중 재수집 경쟁을 방지한다. 동일 문서의 삭제와 수집이 겹치면 최종 상태는 마지막 요청의 의도를 따른다 | 02-non-functional-requirements.md | 02-architecture/03-data-flow-and-document-lifecycle, 02-architecture/07-multi-tenancy-and-security-architecture, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| NFR-PRV-11 | 컬렉션·테넌트 단위 삭제는 문서 수에 비례하지 않는 시간 안에 논리 삭제된다 | 02-non-functional-requirements.md | 02-architecture/03-data-flow-and-document-lifecycle | - |
| NFR-QLT-01 | 기본 프로파일은 내부 한국어 골든셋에서 브리프 §7 순위 품질 목표를 만족한다 | 02-non-functional-requirements.md | 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| NFR-QLT-02 | 리랭크 입력 단계에서 관련 청크의 대부분이 후보에 포함된다 | 02-non-functional-requirements.md | **미인용** | - |
| NFR-QLT-03 | 하이브리드+리랭크 기본 프로파일은 dense-only 베이스라인을 유의하게 앞선다 | 02-non-functional-requirements.md | **미인용** | - |
| NFR-QLT-04 | 기본 프로파일의 변경은 회귀 게이트(FR-EVL-08)를 통과한 뒤에만 게시된다 | 02-non-functional-requirements.md | 09-operations/04-scaling-and-performance | - |
| NFR-REL-01 | 수집은 at-least-once로 처리된다. 접수된 `IngestRequest`는 워커·브로커·API 장애에도 유실되지 않는다 | 02-non-functional-requirements.md | 02-architecture/01-system-overview, 02-architecture/09-failure-modes-and-resilience, 09-operations/07-backup-and-disaster-recovery, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| NFR-REL-02 | 처리는 멱등하다. 동일 `IngestRequest` + 동일 프로파일 버전은 동일 `IndexCommit` 해시를 만든다(브리프 §7 재현성) | 02-non-functional-requirements.md | 02-architecture/01-system-overview, 02-architecture/09-failure-modes-and-resilience, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| NFR-REL-03 | 중복 접수는 억제된다. 멱등 키가 같은 재요청은 새 잡을 만들지 않고 기존 `job_id`를 반환한다 | 02-non-functional-requirements.md | **미인용** | - |
| NFR-REL-04 | 일시적 오류는 지수 백오프 + 지터로 재시도한다(§5.2 정책) | 02-non-functional-requirements.md | 02-architecture/09-failure-modes-and-resilience | - |
| NFR-REL-05 | 비재시도 오류는 즉시 실패로 종결하고 원인을 [오류 모델](../03-contracts/13-error-model.md)로 보고한다 | 02-non-functional-requirements.md | 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| NFR-REL-06 | 최대 재시도를 초과한 잡은 데드레터(DLQ)로 이동하고 관리 API로 재처리할 수 있다 | 02-non-functional-requirements.md | 02-architecture/09-failure-modes-and-resilience, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| NFR-REL-07 | `IndexCommit`은 원자적이다. 부분 인덱싱 상태가 검색에 노출되지 않는다 | 02-non-functional-requirements.md | 02-architecture/01-system-overview, 02-architecture/09-failure-modes-and-resilience, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| NFR-REL-08 | 배치 내 한 문서의 실패는 다른 문서 처리에 영향을 주지 않는다 | 02-non-functional-requirements.md | 02-architecture/09-failure-modes-and-resilience, 09-operations/06-runbooks, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| NFR-REL-09 | 장시간 활동(OCR, LLM 보강, 대량 임베딩)은 하트비트로 생존을 알린다 | 02-non-functional-requirements.md | 02-architecture/09-failure-modes-and-resilience, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| NFR-REL-10 | 스테이지별 타임아웃이 존재하며 초과 시 재시도 정책을 따른다(§5.3) | 02-non-functional-requirements.md | **미인용** | - |
| NFR-REL-11 | 원본·산출물의 내구성은 S3 호환 스토리지에 위임하고, 메타 DB는 PITR(point-in-time recovery)을 지원한다 | 02-non-functional-requirements.md | 02-architecture/01-system-overview, 09-operations/07-backup-and-disaster-recovery | - |
| NFR-REL-12 | 인덱스는 파생 데이터다. 산출물(`EmbeddedChunkSet` 이하)에서 인덱스를 100% 재구축할 수 있다 | 02-non-functional-requirements.md | 02-architecture/01-system-overview, 02-architecture/03-data-flow-and-document-lifecycle, 02-architecture/09-failure-modes-and-resilience, 09-operations/07-backup-and-disaster-recovery, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급), T-EMB-21 |
| NFR-REL-13 | 검색은 부분 저하(graceful degradation)한다. 리랭커 장애 시 융합 결과를, 렉시컬 장애 시 dense+sparse 결과를 `d | 02-non-functional-requirements.md | 02-architecture/01-system-overview, 02-architecture/09-failure-modes-and-resilience, 09-operations/07-backup-and-disaster-recovery, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급), T-RET-26 |
| NFR-REL-14 | 재현성을 위해 모델·프로파일·플러그인 버전을 `IndexCommit`에 기록한다 | 02-non-functional-requirements.md | 02-architecture/09-failure-modes-and-resilience, 04-pipelines/12-embedding, 09-operations/06-runbooks, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| NFR-REL-15 | 백업·복구 목표를 만족한다 | 02-non-functional-requirements.md | 02-architecture/01-system-overview, 02-architecture/09-failure-modes-and-resilience, 09-operations/04-scaling-and-performance, 09-operations/06-runbooks, 09-operations/07-backup-and-disaster-recovery | - |
| NFR-REL-16 | 워크플로우 정의는 결정적(deterministic)이다. 비결정 호출(시간, 난수, 외부 I/O)은 활동(activity)에만 존재한다 | 02-non-functional-requirements.md | 11-roadmap/02-epics-and-backlog | (로드맵 02 언급), T-MGT-19 |
| NFR-SCAL-01 | 단일 컬렉션이 LP-L 규모까지 성능 목표를 유지한다 | 02-non-functional-requirements.md | **미인용** | - |
| NFR-SCAL-02 | 배포 단위당 다수 테넌트·컬렉션을 수용한다 | 02-non-functional-requirements.md | 02-architecture/01-system-overview, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| NFR-SCAL-03 | 수집 워커는 수평 확장으로 처리량이 준선형 증가한다 | 02-non-functional-requirements.md | 02-architecture/01-system-overview, 09-operations/04-scaling-and-performance | - |
| NFR-SCAL-04 | API 계층은 무상태로 수평 확장된다 | 02-non-functional-requirements.md | 02-architecture/01-system-overview, 02-architecture/08-deployment-architecture, 09-operations/04-scaling-and-performance | - |
| NFR-SCAL-05 | 인덱스 백엔드 샤딩·사본 수를 `IndexBackend` 계약으로 구성할 수 있다 | 02-non-functional-requirements.md | 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| NFR-SCAL-06 | 단일 문서 한도를 명시하고 초과 시 명확히 거절한다 | 02-non-functional-requirements.md | 09-operations/04-scaling-and-performance | - |
| NFR-SCAL-07 | 배치 수집 요청 크기를 제한한다 | 02-non-functional-requirements.md | 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| NFR-SCAL-08 | 대기 중 잡 수는 워커 수와 무관하게 수용된다 | 02-non-functional-requirements.md | **미인용** | - |
| NFR-SCAL-09 | 워커 축소(scale-in) 시 진행 중 작업이 유실되지 않는다 | 02-non-functional-requirements.md | 09-operations/04-scaling-and-performance | - |
| NFR-SCAL-10 | 임베딩·리랭커 서빙은 큐 깊이 기반 오토스케일을 지원한다 | 02-non-functional-requirements.md | 04-pipelines/12-embedding | - |
| NFR-SEC-01 | 테넌트 격리. 모든 인덱스 질의는 서버 측에서 `tenant_id` 필터를 강제하며 클라이언트가 우회할 수 없다(D-09) | 02-non-functional-requirements.md | 02-architecture/01-system-overview, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| NFR-SEC-02 | ACL 강제. `acl` 필드와 호출자 주체(principal)의 매칭이 모든 리트리버·MCP 도구에 동일하게 적용된다 | 02-non-functional-requirements.md | 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| NFR-SEC-03 | 인증. OIDC(JWT) 및 서비스 계정 API 키를 지원하고 미인증 요청은 거절한다 | 02-non-functional-requirements.md | **미인용** | - |
| NFR-SEC-04 | 인가. [기능 요구사항](../01-requirements/01-functional-requirements.md) FR-SEC-02의 역할(`t | 02-non-functional-requirements.md | 02-architecture/07-multi-tenancy-and-security-architecture | - |
| NFR-SEC-05 | 전송 암호화. 외부 노출 엔드포인트는 TLS 1.2 이상(권장 1.3), 내부 서비스 간 mTLS를 옵션으로 제공한다 | 02-non-functional-requirements.md | 02-architecture/07-multi-tenancy-and-security-architecture, 05-api/05-mcp-server, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| NFR-SEC-06 | 저장 암호화. 오브젝트 스토리지 SSE, DB·인덱스 볼륨 암호화를 배포 매니페스트 기본값으로 제공한다 | 02-non-functional-requirements.md | 04-pipelines/02-fetching-and-source-resolution | - |
| NFR-SEC-07 | 비밀 관리. 비밀은 환경·시크릿 매니저에서만 주입되며 로그·트레이스·오류 응답에 노출되지 않는다 | 02-non-functional-requirements.md | 02-architecture/07-multi-tenancy-and-security-architecture, 09-operations/05-security-and-compliance, 09-operations/07-backup-and-disaster-recovery, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급), T-SEC-09 |
| NFR-SEC-08 | 감사 로그. 수집·삭제·검색·관리 작업을 주체·시각·대상·결과와 함께 불변 저장한다 | 02-non-functional-requirements.md | 02-architecture/03-data-flow-and-document-lifecycle | - |
| NFR-SEC-09 | URI 페치의 SSRF·경로 탈출 방지. `http(s)://`는 스킴·호스트 허용 목록, 사설·링크로컬 IP 차단, 리다이렉트 제한을 적용한다 | 02-non-functional-requirements.md | 02-architecture/01-system-overview, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| NFR-SEC-10 | 파서 샌드박스. 신뢰되지 않은 파일은 비루트·읽기 전용 루트·egress 차단 워커에서 처리하며 zip bomb·XXE·경로 탈출(HWPX·DO | 02-non-functional-requirements.md | 02-architecture/01-system-overview, 02-architecture/07-multi-tenancy-and-security-architecture, 04-pipelines/02-fetching-and-source-resolution, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급), T-SEC-12 |
| NFR-SEC-11 | 의존성 취약점. 릴리스 시점 Critical·High 취약점이 없고 SBOM을 제공한다 | 02-non-functional-requirements.md | 10-development/08-release-process | - |
| NFR-SEC-12 | 입력 검증. 모든 API 입력은 JSON Schema로 검증되고 요청 본문·필드 길이 상한이 있다 | 02-non-functional-requirements.md | 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| NFR-SEC-13 | 레이트 리밋·할당량. 테넌트별 QPS, 동시 잡, 일일 수집 바이트 한도를 적용하고 초과 시 429와 `Retry-After`를 반환한다 | 02-non-functional-requirements.md | 02-architecture/07-multi-tenancy-and-security-architecture, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| NFR-SEC-14 | 프롬프트 인젝션 표면 최소화. Context Pack은 문서 콘텐츠를 지시가 아닌 데이터로 표기하고 렌더러가 콘텐츠·지시를 구조적으로 분리한다 | 02-non-functional-requirements.md | 02-architecture/07-multi-tenancy-and-security-architecture, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급), T-MCP-17, T-PCK-18, T-SEC-14 |
| NFR-SEC-15 | 컨테이너 이미지 서명·스캔. 릴리스 이미지는 서명되고 스캔 결과가 공개된다 | 02-non-functional-requirements.md | 11-roadmap/02-epics-and-backlog | T-SEC-15 |
| NFR-SEC-16 | MCP 서버 보안. 인증 토큰 필수, REST와 동일한 테넌트·ACL 필터 강제, 도구 입력 스키마 검증 | 02-non-functional-requirements.md | 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| NFR-SEC-17 | 위협 모델을 문서화하고 릴리스마다 검토한다 | 02-non-functional-requirements.md | 02-architecture/07-multi-tenancy-and-security-architecture, 09-operations/05-security-and-compliance, 11-roadmap/02-epics-and-backlog | T-SEC-19 |
| NFR-USA-01 | 첫 검색까지의 시간(time-to-first-query). 신규 개발자가 Docker Compose 퀵스타트로 수집·검색을 완료한다 | 02-non-functional-requirements.md | 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| NFR-USA-02 | OpenAPI 3.1 문서 완전성. 모든 엔드포인트에 요청·응답 예시와 오류 코드가 있다 | 02-non-functional-requirements.md | **미인용** | - |
| NFR-USA-03 | 오류 응답은 [오류 모델](../03-contracts/13-error-model.md)을 따르며 기계 판독 코드와 해결 힌트를 포함한다 | 02-non-functional-requirements.md | **미인용** | - |
| NFR-USA-04 | 클라이언트 SDK(Python, TypeScript)는 계약에서 생성되고 타입이 완전하다 | 02-non-functional-requirements.md | **미인용** | - |
| NFR-USA-05 | 문서는 한국어 기본(D-03)이며 코어 문서(브리프, 설계 바이블, API 가이드, 퀵스타트)는 영어 번역을 제공한다 | 02-non-functional-requirements.md | 10-development/07-contributing | - |
| NFR-USA-06 | 국제화(i18n). 사용자 대면 메시지는 메시지 코드 + 로캘 리소스로 분리하고 기본 로캘 `ko`, `en`을 제공한다 | 02-non-functional-requirements.md | **미인용** | - |
| NFR-USA-07 | 유니코드 정규화. 텍스트는 NFC 정규화, 언어 태그는 BCP 47(D-06), 한글·한자·전각 문자 혼용 문서를 손실 없이 처리한다 | 02-non-functional-requirements.md | 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| NFR-USA-08 | 접근성. 문서 사이트와 레퍼런스 UI(제공 시)는 WCAG 2.2 AA를 따르고 모든 Mermaid 다이어그램에 텍스트 설명이 동반된다 | 02-non-functional-requirements.md | **미인용** | - |
| NFR-USA-09 | CLI는 비대화식 실행, 의미 있는 종료 코드, `--json` 출력을 지원한다 | 02-non-functional-requirements.md | 11-roadmap/02-epics-and-backlog | (로드맵 02 언급), T-MGT-15 |
| NFR-USA-10 | 플러그인 개발. 템플릿과 계약 준수 테스트로 스켈레톤 플러그인을 빠르게 만들 수 있다 | 02-non-functional-requirements.md | 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| NFR-USA-11 | 설정 참조 문서는 설정 스키마에서 자동 생성되어 코드와 어긋나지 않는다 | 02-non-functional-requirements.md | 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| NFR-USA-12 | 시간·숫자 표기. API는 RFC 3339 UTC(D-06)만 사용하고 로캘 의존 포맷을 반환하지 않는다 | 02-non-functional-requirements.md | 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| NFR-USA-13 | 한국어 검색 사용성. 띄어쓰기 변형, 조사 결합, 한자 병기 질의를 렉시컬 경로가 처리한다 | 02-non-functional-requirements.md | 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |

### UC (20)

| ID | 제목 | 정의 문서 | 인용 설계 문서 | 로드맵 태스크 |
|---|---|---|---|---|
| UC-01 | 테넌트 온보딩 | 03-personas-and-use-cases.md | **미인용** | - |
| UC-02 | 컬렉션 생성과 프로파일 고정 | 03-personas-and-use-cases.md | **미인용** | - |
| UC-03 | 공공기관 HWPX 대량 수집 | 03-personas-and-use-cases.md | **미인용** | - |
| UC-04 | 스캔 PDF OCR 수집 | 03-personas-and-use-cases.md | **미인용** | - |
| UC-05 | 혼합 포맷 배치 수집과 포맷 자동 감지 | 03-personas-and-use-cases.md | **미인용** | - |
| UC-06 | 수집 잡 상태 추적과 웹훅 수신 | 03-personas-and-use-cases.md | **미인용** | - |
| UC-07 | 문서 갱신 전파(재색인과 원자적 교체) | 03-personas-and-use-cases.md | 02-architecture/03-data-flow-and-document-lifecycle | - |
| UC-08 | 문서 삭제 전파 | 03-personas-and-use-cases.md | 02-architecture/03-data-flow-and-document-lifecycle | - |
| UC-09 | 하이브리드 검색 후 LLM 답변 생성(Context Pack 소비) | 03-personas-and-use-cases.md | **미인용** | - |
| UC-10 | 에이전트가 MCP로 반복 검색 | 03-personas-and-use-cases.md | **미인용** | - |
| UC-11 | ACL 기반 결과 필터링 | 03-personas-and-use-cases.md | **미인용** | - |
| UC-12 | 검색 결과 설명(점수 분해와 트레이스 조회) | 03-personas-and-use-cases.md | 08-evaluation/01-evaluation-strategy | - |
| UC-13 | 골든셋 구축과 오프라인 평가 실행 | 03-personas-and-use-cases.md | 08-evaluation/01-evaluation-strategy | - |
| UC-14 | 프로파일 A/B 평가 | 03-personas-and-use-cases.md | 08-evaluation/01-evaluation-strategy | - |
| UC-15 | 임베딩 모델 교체와 컬렉션 재색인 | 03-personas-and-use-cases.md | 02-architecture/03-data-flow-and-document-lifecycle, 08-evaluation/01-evaluation-strategy | - |
| UC-16 | 플러그인 파서 추가 | 03-personas-and-use-cases.md | **미인용** | - |
| UC-17 | 장애 복구(워커 중단 후 재개) | 03-personas-and-use-cases.md | **미인용** | - |
| UC-18 | 감사 로그 조회와 PII 처리 검증 | 03-personas-and-use-cases.md | **미인용** | - |
| UC-19 | 인용으로 원문 위치 확인 | 03-personas-and-use-cases.md | **미인용** | - |
| UC-20 | 플랫폼 업그레이드와 계약 버전 호환 | 03-personas-and-use-cases.md | **미인용** | - |

### US (91)

| ID | 제목 | 정의 문서 | 인용 설계 문서 | 로드맵 태스크 |
|---|---|---|---|---|
| US-CHK-01 | 구조 인식 계층 청킹 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| US-CHK-02 | 부모-자식(small-to-big) 청크 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones | - |
| US-CHK-03 | 표 전용 청킹 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones | - |
| US-CHK-04 | 오버랩과 미세 청크 제어 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones, 11-roadmap/02-epics-and-backlog | T-CHK-06 |
| US-CHK-05 | 결정적 문맥 접두어 부착 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones | - |
| US-CHK-06 | LLM 기반 문맥 요약·가상 질문(옵션) | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| US-CHK-07 | 키워드·언어·도메인 태깅 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| US-CHK-08 | 대안 청킹 전략 옵션 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones | - |
| US-EMB-01 | dense·sparse 동시 임베딩 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| US-EMB-02 | 임베딩 모델·서빙 교체 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| US-EMB-03 | 임베딩 캐시와 재처리 회피 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones | - |
| US-EMB-04 | 하이브리드 레코드 인덱싱과 테넌시 필드 강제 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones | - |
| US-EMB-05 | 원자적 인덱스 커밋과 롤백 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones | - |
| US-EMB-06 | 경량 단일 백엔드 프로파일 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones | - |
| US-EMB-07 | 인덱스 백엔드 교체와 스키마 마이그레이션 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| US-EVL-01 | 골든셋 포맷과 로딩 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| US-EVL-02 | 오프라인 검색·컨텍스트 메트릭 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones | - |
| US-EVL-03 | 프로파일 A/B 비교와 스테이지 진단 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| US-EVL-04 | 회귀 게이트 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones, 11-roadmap/02-epics-and-backlog | T-EVL-12 |
| US-EVL-05 | LLM-judge와 인용 정확도 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| US-EVL-06 | 합성 골든셋과 한국어 벤치마크 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones | - |
| US-EVL-07 | 온라인 피드백 수집과 평가기 플러그인 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| US-ING-01 | URI 기반 단건 수집 요청 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급), T-PCK-15 |
| US-ING-02 | 다중 URI 스킴에서 원본 가져오기 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones | - |
| US-ING-03 | 배치 수집 요청 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| US-ING-04 | 잡 상태 조회와 이벤트 수신 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones | - |
| US-ING-05 | 콘텐츠 해시 기반 멱등 수집 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones | - |
| US-ING-06 | 문서 갱신과 버전 교체 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급), T-EMB-18, T-ING-25 |
| US-ING-07 | 문서 삭제 요청 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones | - |
| US-ING-08 | 잡 취소와 데드레터 재처리 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones | - |
| US-ING-09 | 수집 정책 오버라이드와 한도 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones | - |
| US-ING-10 | 웹훅 구독 관리와 전달 보장 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones | - |
| US-MCP-01 | 표준 도구 세 가지 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| US-MCP-02 | 렌더 형식 선택 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones | - |
| US-MCP-03 | 테넌트 컨텍스트와 인증 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones | - |
| US-MCP-04 | `resolve_citation` 인용 해소 도구 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급), T-MCP-15 |
| US-MCP-05 | 전송 방식 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones | - |
| US-MGT-01 | 테넌트와 컬렉션 관리 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| US-MGT-02 | 프로파일 정의·불변성·기본 제공 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| US-MGT-03 | 재인덱싱과 프로파일 마이그레이션 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones | - |
| US-MGT-04 | 잡 관리와 산출물 조회 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones | - |
| US-MGT-05 | OpenAPI·오류 모델·API 버전 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones | - |
| US-MGT-06 | 클라이언트 SDK와 문서·청크 조회 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| US-MGT-07 | 헬스·레디니스·레이트 리밋·레퍼런스 answer | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| US-MGT-08 | 오케스트레이션 러너 교체와 배포 프로파일 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones | - |
| US-OBS-01 | 종단 간 분산 트레이스 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| US-OBS-02 | RED 메트릭과 대시보드 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones | - |
| US-OBS-03 | 검색 설명(explain)과 리플레이 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones | - |
| US-OBS-04 | 구조화 로그와 상관 키 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| US-OBS-05 | 잡 진행률과 이벤트 지연 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones | - |
| US-OBS-06 | 외부 익스포터·드리프트·비용 계측 | 04-user-stories-and-acceptance-criteria.md | 08-evaluation/06-online-feedback-loop, 11-roadmap/01-milestones, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| US-PCK-01 | 토큰 예산 내 패킹 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| US-PCK-02 | 중복·오버랩 제거와 다양성 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| US-PCK-03 | 부모 확장과 위치 최적 정렬 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones | - |
| US-PCK-04 | 인용 ID와 출처 메타데이터 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones | - |
| US-PCK-05 | 표·그림 텍스트화 포함 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones | - |
| US-PCK-06 | 신뢰도와 프롬프트 힌트 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones | - |
| US-PCK-07 | 공급자 중립 JSON과 렌더러 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones | - |
| US-PCK-08 | 컨텍스트 압축 옵션 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| US-PLG-01 | 확장 지점 인터페이스와 레지스트리 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| US-PLG-02 | 계약 적합성 검사와 테스트 키트 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| US-PLG-03 | 플러그인 설정 스키마와 스캐폴딩 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| US-PLG-04 | 격리 실행 옵션 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| US-PLG-05 | 플러그인 관측성 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| US-PLG-06 | 라이선스 메타데이터와 정책 게이트 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| US-PRS-01 | 포맷 감지와 파서 라우팅 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| US-PRS-02 | HWPX 1급 구조 파싱 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones | - |
| US-PRS-03 | HWP 5.0 바이너리 파싱과 변환기 폴백 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| US-PRS-04 | 텍스트 PDF 레이아웃·표 인식 파싱 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones | - |
| US-PRS-05 | 스캔 PDF 판별과 OCR | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones | - |
| US-PRS-06 | DOCX·DOC 파싱 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones | - |
| US-PRS-07 | HTML 본문 추출과 메타 수확 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones | - |
| US-PRS-08 | TXT·Markdown 파싱과 한국어 인코딩 감지 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones | - |
| US-PRS-09 | 정규화와 부분 파싱 허용 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones | - |
| US-RET-01 | 하이브리드 검색 한 번 호출 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| US-RET-02 | 크로스인코더 리랭킹과 폴백 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| US-RET-03 | 필수 필터 강제와 메타데이터 필터 결합 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones | - |
| US-RET-04 | 점수 분해와 설명 가능성 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones | - |
| US-RET-05 | 질의 정규화·언어 판별·교차 언어 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones | - |
| US-RET-06 | 질의 재작성·확장(옵션) | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| US-RET-07 | 빈 결과·저신뢰 신호 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones | - |
| US-RET-08 | 다중 컬렉션 검색 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones | - |
| US-RET-09 | 고급 리트리벌 옵션(그래프·RAPTOR·agentic) | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| US-SEC-01 | OIDC 인증과 서비스 계정 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| US-SEC-02 | 역할 기반 권한 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones | - |
| US-SEC-03 | 테넌트 격리 강제 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones | - |
| US-SEC-04 | 문서 수준 ACL과 갱신 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones | - |
| US-SEC-05 | 원본 접근 자격 증명과 SSRF 방지 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones | - |
| US-SEC-06 | 감사 로그와 내보내기 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones | - |
| US-SEC-07 | PII 처리 정책과 삭제 완결성 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones, 11-roadmap/02-epics-and-backlog | (로드맵 02 언급) |
| US-SEC-08 | 안전한 파싱·웹훅 서명·프롬프트 주입 표면 축소 | 04-user-stories-and-acceptance-criteria.md | 11-roadmap/01-milestones | - |

## 결정 사항 요약

- **결정:** 추적성의 정본은 이 매트릭스다. 설계 문서는 관련 요구사항을 자연스럽게 인용하되, 인용률을 올리기 위한 형식적 인용은 금지한다.

## 미해결 이슈

- 미인용 요구사항은 (a) 실제로 어느 설계 문서도 다루지 않는 갭인지, (b) 다루지만 ID를 쓰지 않은 것인지 4단계 P1에서 표본 판정한다.

## 참조

- [기능 요구사항](../01-requirements/01-functional-requirements.md) · [비기능 요구사항](../01-requirements/02-non-functional-requirements.md) · [에픽과 백로그](../11-roadmap/02-epics-and-backlog.md) · [3단계 완전성 검토](01-phase3-completeness-review.md)
