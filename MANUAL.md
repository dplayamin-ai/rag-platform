# MANUAL.md — 사용자 매뉴얼 (RAG Platform M1 lite)

이 문서는 RAG Platform을 **쓰는 사람**을 위한 매뉴얼이다. 문서를 넣고(수집), 질문해서 LLM에게 줄 문맥(Context Pack)을 받는 방법을 설치부터 문제 해결까지 순서대로 설명한다. 코드를 고치려는 개발자는 [DEVELOPER.md](DEVELOPER.md)를, 다른 머신에서 검증을 이어받는 사람은 [HANDOFF.md](HANDOFF.md)를 본다.

## 0. 지금 무엇을 할 수 있고 무엇은 아직인가

먼저 기대치를 맞춘다. 이 저장소는 2026-09-24 기준 **M1 lite 코어**가 층 1(순수 Python)에서 검증된 상태다.

| 기능 | 상태 | 비고 |
|------|------|------|
| CLI로 문서 수집(`rag ingest`) | **동작** | HWPX·PDF(디지털)·HTML·TXT/MD·JSON. 결과는 로컬 `.rag/` 디렉터리 |
| CLI로 질의(`rag query`) | **동작** | dense + BM25 하이브리드 → RRF → 후처리 → Context Pack → 렌더 |
| 검색 품질 | **아직 무의미** | dense 임베더가 결정적 가짜(`FakeEmbedder`)다. BM25(키워드) 채널만 실제 신호다. 실제 BGE-M3는 모델이 있는 머신에서 층 2b 검증 후 |
| 프로파일 검증(`rag profile validate`) | **동작** | 내장 5종(`base`·`lite`·`standard`·`premium`·`korean-gov`) |
| REST API 서버(`rag serve api`) | **부분** | 인증(Bearer)·오류 형식(RFC 9457)·잡 조회·팩 캐시는 실제. 그러나 수집은 스텁 1단, 질의는 스텁 팩을 돌려준다. API 키를 넣을 설정 파일도 아직 없어 코드 밖에서는 401만 받는다 |
| MCP 서버(`rag serve mcp`) | **미배선** | 도구 3종(`search`·`get_document`·`list_collections`)의 핸들러와 커서 페이지네이션은 테스트됐지만, stdio 서버 조립이 없어 명령이 서버를 띄우지 못한다 |
| Docker 스택(`deploy/compose/compose.lite.yaml`), PostgreSQL 원장, Valkey, Qdrant 서버 모드 | **미검증** | 작성만 됨. [HANDOFF.md](HANDOFF.md) 절차로 다른 머신에서 |
| HWP 5.0(`.hwp`)·DOCX·스캔 PDF(OCR)·리랭커·OpenSearch·Temporal | **미구현** | M2 이후 |

요약하면 지금 "쓸 수 있는 제품 표면"은 CLI다. 이 매뉴얼의 §2~§5가 그 부분이고, §6~§7은 API·MCP가 배선되면 그대로 쓰게 될 계약을 미리 설명한다.

## 1. 설치

요구 사항: Python 3.12 또는 3.13, [uv](https://docs.astral.sh/uv/) 0.12 이상, Node 20 이상(문서·스키마 검증 스크립트용, 선택). Docker와 GPU는 필요 없다. Windows·Linux·macOS 모두 된다.

```bash
git clone <repo-url> rag-platform && cd rag-platform
uv sync --all-extras --group dev
uv run rag --help
```

`uv sync`가 가상 환경을 만들고 잠금 파일(`uv.lock`) 그대로 의존성을 설치한다. `--all-extras`는 선택 기능(`kiwi` 형태소 분석기 등)까지 넣는다. 사내 프록시 뒤라면 `HTTPS_PROXY`를 설정한 뒤 실행한다.

설치 확인:

```bash
uv run pytest -q
```

`886 passed, 27 xfailed` 계열의 결과가 나오면 정상이다(`xfailed`는 알려진 계약 문서 예시 오류이며 사용에 영향 없다).

## 2. 5분 사용법

```bash
# 1) 표본 문서(공공누리 제1유형 보도자료 3건 + 합성 문서 1건)를 demo 컬렉션에 수집
#    디렉터리를 주면 지원 확장자인 MANIFEST.json도 한 건으로 같이 수집된다(무해, 총 5개 경로)
uv run rag ingest samples/hwpx --collection demo

# 2) 질의
uv run rag query "추석 연휴 응급환자 이송체계 점검" --collection demo
uv run rag query "에이전틱 AI 개인정보 규율체계" --collection demo --format json
```

수집 결과는 경로마다 한 항목씩 JSON 배열로 나온다(아래는 5개 중 1개).

```json
[
  {"path": "...kogl1-mohw-emergency-care-20260923.hwpx", "document_id": "...", "commit_id": "...", "record_count": 37, "status": "committed"}
]
```

`status`가 전부 `committed`이면 종료 코드 0, 하나라도 아니면 1이다. 질의의 기본 출력(`--format text`)은 첫 줄에 `items=<개수> sufficiency=<충분성 상태>`, 다음 줄부터 렌더된 문맥이다.

## 3. 명령 레퍼런스

### 3.1 `rag ingest` — 문서 수집

```bash
uv run rag ingest <경로...> --collection <이름> [--profile lite-dev] [--state-dir .rag]
```

| 인자 | 의미 | 기본값 |
|------|------|--------|
| `<경로...>` | 파일 또는 디렉터리(재귀). 지원 확장자: `.hwpx` `.pdf` `.html` `.htm` `.txt` `.md` `.markdown` `.json` | 필수 |
| `--collection` | 컬렉션 이름. 없으면 새로 만든다 | 필수 |
| `--profile` | 프로파일. 현재 `lite-dev`(= 내장 `lite`)만 실 배선 | `lite-dev` |
| `--state-dir` | 상태 디렉터리 | `.rag` |

동작: 경로마다 `fetch → parse → normalize → chunk → enrich → embed → index` 순서로 처리하고 Qdrant 로컬 모드에 커밋한다. 같은 파일을 다시 넣으면 문서 ID가 같고(결정적), 새 세대가 이전 세대를 대체한다(`insert_then_delete`). 확장자 필터는 **디렉터리를 재귀 탐색할 때만** 적용되고, 파일을 직접 지정하면 확장자와 무관하게 그대로 처리한다. 종료 코드: 0 전부 `committed`, 1 하나라도 실패, 2 처리할 파일이 하나도 없음(예: 지원 파일이 없는 디렉터리). 존재하지 않는 파일이나 파싱 불가 파일은 현재 스테이지 예외가 잡히지 않아 트레이스백과 함께 1로 끝난다(경로별 `status: failed` 항목으로 정리하는 일은 알려진 이슈).

포맷별 주의:
- **HWPX**: 표·각주·그림 캡션까지 블록으로 나온다. 한글 2010 이후 OWPML 표준 파일이어야 한다. 구형 `.hwp`(5.0 바이너리)는 **아직 지원하지 않으며 현재 동작도 깔끔하지 않다**: 빈 `.hwp`는 `status: committed, record_count: 0`으로 조용히 넘어가고, 실제 HWP5 바이너리는 포맷 판별 단계의 `StageError(binary:no_signature)`가 잡히지 않아 CLI 전체가 트레이스백과 함께 종료 코드 1로 죽는다(알려진 이슈, 설계 갭 원장 참조). `.hwp`는 넣지 않는다.
- **PDF**: 텍스트가 들어 있는 디지털 PDF만 고속 경로로 처리한다. 스캔 PDF(OCR 필요)는 M2다.
- **HTML**: 본문 추출(trafilatura) 후 표를 원본 `rowspan`/`colspan`으로 재구성한다. 광고·내비게이션은 버린다.
- **TXT/MD/CSV/JSON**: 문자 인코딩(CP949 포함)을 자동 판별한다. JSON은 배열이면 항목별로 나눈다.

### 3.2 `rag query` — 질의

```bash
uv run rag query "<질의문>" --collection <이름> [--state-dir .rag] [--format text|json]
```

| 인자 | 의미 | 기본값 |
|------|------|--------|
| `"<질의문>"` | 자연어 질의(한국어 권장) | 필수 |
| `--collection` | 수집해 둔 컬렉션 이름. 없으면 종료 코드 2 | 필수 |
| `--format` | `text`(요약 + 렌더 결과) 또는 `json`(`{context_pack, rendered}` 전체) | `text` |

동작: `lite` 프로파일의 검색 경로를 그대로 탄다 — 질의 정규화·규칙 라우팅 → dense 채널(top_k 100)과 lexical 채널(BM25 희소 벡터, top_k 100) 병렬 검색 → RRF 융합(k=60) → payload에서 본문 채움 → 후처리(`relevance_gate → dedup → mmr → parent_expand → dedup`) → 패킹(ACL 재검사 → 토큰 예산 절단 → "중간 소실" 회피 순서 → 인용 ID 정렬) → 렌더. lite 기본 예산은 최대 10항목, 문맥 12,000 토큰, 답변 예약 2,000 토큰이다.

`--format json`의 `context_pack`이 LLM에게 넘길 정본이다. 핵심 필드:

| 필드 | 의미 |
|------|------|
| `items[]` | 순서대로 넣을 문맥 조각. 각 항목에 `cite_id`(`d1`, `d2`…), `text`, `document_id`, `chunk_id`, `rank`, 점수 분해 |
| `sufficiency.status` | 검색이 답하기에 충분한지의 판정. 부족하면 "모른다"고 답하게 하는 근거 |
| `budget` | 사용 토큰·상한·토크나이저 정보 |
| `diagnostics` | 적용된 필터·채널별 결과 수·후처리 통계 |

`rendered`(RenderedContext)에는 `provider_payload`(렌더러별 출력)와 `citation_map`(`cite_id` → 원문 위치 매핑, LLM 답변의 인용을 원문으로 되돌릴 때 쓴다)이 있다. `provider_payload`는 렌더러별 출력이다. 렌더러는 요청의 `renderer` 또는 `target_model.provider`로 정해지며 기본은 `markdown`이다. `anthropic_search_result`는 Anthropic 검색 결과 블록 + 인용 형식으로 낸다.

### 3.3 `rag profile validate` — 프로파일 검증

```bash
uv run rag profile validate lite
# lite -> lite: valid (profile_hash=fa4414df...)
```

내장 프로파일 ID(`base`·`lite`·`standard`·`premium`·`korean-gov`) 또는 별칭(`lite-dev`)을 받아 상속(`extends`)을 풀고 스키마·불변식을 검사한 뒤 결정적 `profile_hash`를 출력한다. 종료 코드 0 유효, 1 무효.

### 3.4 `rag serve` — 서버 기동(현재 부분 동작)

```bash
uv run rag serve api [--host 127.0.0.1] [--port 8000]   # uvicorn rag_platform.api.app:app
uv run rag serve mcp                                    # python -m rag_platform.mcp.server
```

`serve api`는 FastAPI 앱을 uvicorn으로 띄운다(기동 로그가 뜨고 포트를 연다). §0의 표대로 이 앱은 아직 API 키 설정 경로가 없어 외부에서 호출하면 401 `problem+json`을 받는다. 계약 확인 용도로는 §6의 파이썬 스니펫(인프로세스 `TestClient`)을 쓴다. `serve mcp`는 `python -m rag_platform.mcp.server`를 띄우지만 그 모듈에 실행 진입점이 없어 **아무 일도 하지 않고 종료 코드 0으로 끝난다**(임포트 때문에 15~30초 걸릴 수 있다). stdio 서버 조립은 §7 참조.

## 4. 상태 디렉터리 `.rag/`

모든 로컬 상태는 `--state-dir`(기본 `.rag`) 아래에 있다. 통째로 지우면 초기화된다.

| 경로 | 내용 |
|------|------|
| `collections.json` | 컬렉션 이름 → `tenant_id`·`collection_id`·문서 ID 매핑. CLI가 만든 단일 테넌트 |
| `artifacts/` | 스테이지별 산출물 JSON(`SourceDocument`… `EmbeddedChunkSet`). 디버깅할 때 어느 스테이지에서 이상해졌는지 여기서 본다 |
| `qdrant/` | Qdrant 로컬 모드 데이터. 벡터(`dense`, `sparse_bm25`)와 payload(본문·메타·ACL 해시) |

여러 프로젝트를 분리하려면 `--state-dir`를 다르게 준다. 디렉터리를 다른 머신으로 복사하면 그대로 질의할 수 있다(모두 파일 기반).

## 5. 프로파일 — 무엇을 조절할 수 있나

프로파일은 `src/rag_platform/profiles/builtin/*.yaml`이며 `base`를 상속해 티어별 차이만 적는다. 현재 CLI는 `lite`만 실 배선하므로, 조절 가능한 값도 `lite.yaml`의 다음 항목이다(값을 바꾸면 `rag profile validate lite`로 먼저 검증한다).

| 항목 | lite 기본값 | 효과 |
|------|------------|------|
| `ingest.chunk.leaf_max_tokens` / `parent_max_tokens` / `merge_min_tokens` | 512 / 2048 / 64 | 자식 청크 크기, 부모 청크 크기, 병합 하한 |
| `ingest.chunk.table_row_group_tokens` | 256 | 표를 행 그룹으로 자를 때의 크기 |
| `query.channels[].top_k` | 100 / 100 | dense·lexical 채널이 가져오는 후보 수 |
| `query.fusion` | rrf, k=60, 가중 1:1, 변형 0.5 | 융합 방식(등가 검증된 골든 벡터 있음) |
| `query.postprocess.relevance_gate.tau` | 0.3 | 이 점수 미만은 버린다 |
| `query.postprocess.dedup.cosine_threshold` | 0.95 | 중복 판정 |
| `query.postprocess.mmr.lambda` | 0.7 | 다양성 대 관련성 |
| `query.postprocess.parent_expand` | ratio 0.5, 최대 2048 토큰 | 자식 여러 개가 맞으면 부모로 승격 |
| `query.pack.k_max` / `max_context_tokens` / `reserved_answer_tokens` | 10 / 12,000 / 2,000 | Context Pack 예산 |
| `query.pack.ordering` | `litm_alternating` | "중간 소실" 회피 배치 |
| `query.pack.renderer` | `anthropic_search_result` | 기본 렌더러(요청이 덮어쓸 수 있음) |

`rerank`·`enrich.generated_prefix`·`late_interaction`처럼 lite에서 꺼져 있거나 모델이 필요한 항목은 값을 바꿔도 이 머신에서는 효과가 없다. 프로파일 전체 의미는 바이블 §7(`docs/02-architecture/00-design-bible.md`).

## 6. REST API (계약 안내 — 배선 완료 시 그대로 사용)

경로와 오류 형식은 `docs/05-api/openapi.yaml`이 정본이다. 현재 구현된 네 경로와 계약:

| 메서드·경로 | 본문 | 응답 |
|-------------|------|------|
| `POST /v1/ingest` | `IngestRequest` 부분집합(문서 URI·메타). 헤더 `Idempotency-Key` 권장 | 202 `{job_id, ...}` |
| `GET /v1/jobs/{job_id}` | — | 200 `JobStatus`(`failed`·`partial`도 200), 없으면 404 |
| `POST /v1/query` | `QueryRequest` 계약 전체(`query`, `collection_ids`, `top_k`, `filters`, `renderer` 또는 `target_model`, …) | 200 `{context_pack, rendered?}`; `pack_id`는 10분간 캐시 |
| `POST /v1/render` | `{pack_id}` 또는 `{context_pack}` + `renderer`, `options` | 200 `RenderedContext`; 주체가 다르거나 만료면 404 |

공통 규칙:
- 인증은 `Authorization: Bearer <api_key>`뿐이다. 키는 `service:<subject>` 주체가 되고 `visible_set=[public]`이다. 요청 본문에 `security_context`를 넣어도 무시된다(서버가 주입).
- 오류는 전부 `application/problem+json`(RFC 9457)이며 `code`(예: `auth.unauthenticated`, `api.not_found`, `plan.filter_field_forbidden`)로 분기한다. 메시지 문자열로 분기하지 않는다.
- 결과 캐시는 없다(ACL 시점성). `pack_id` 캐시는 렌더 재요청 용도이고 검색을 재사용하지 않는다.

지금 API를 만져 보려면 인프로세스로 키를 등록한다(외부 설정 파일이 생기면 이 단계가 사라진다).

```python
from fastapi.testclient import TestClient
from rag_platform.api.app import create_app

app = create_app()
app.state.api_keys.register("dev-key", tenant_id="01J9ZQ4K7X2M8N3P5R6S7T8V9W", subject="me")
client = TestClient(app)
body = {                                   # QueryRequest 계약의 최소 유효 본문
    "schema_version": "1.0.0",
    "query": "정보공개 청구를 받은 공공기관은 며칠 이내에 공개 여부를 결정해야 하나요?",
    "collection_ids": ["01J9ZQ5A1B2C3D4E5F6G7H8J9K"],
    "target_model": {"provider": "anthropic", "model": "claude-opus-5"},
    "requested_at": "2026-09-22T09:00:00.000Z",
}
r = client.post("/v1/query", headers={"Authorization": "Bearer dev-key"}, json=body)
print(r.status_code, r.headers["content-type"])   # 200 application/json
print(sorted(r.json()))                            # ['context_pack', 'rendered']
```

주의: 이 경로의 `context_pack`은 스텁이다. 실제 검색 결과가 필요하면 §3.2의 CLI를 쓴다.

## 7. MCP 서버 (계약 안내)

LLM 에이전트가 직접 부르는 도구 3종이다(`docs/05-api/05-mcp-server.md`). 전부 읽기 전용·멱등이며 웹 검색이 아니라 "조직 내부 문서 검색"으로 스스로를 설명한다.

| 도구 | 인자 | 반환 |
|------|------|------|
| `search` | `query`(필수), `collection_ids?`, `top_k=10`, `filters?`, `response_format="concise"\|"detailed"`, `cursor?` | Context Pack 항목 페이지. `concise`는 항목당 200자 미리보기. 잘리면 `truncated=true`와 `next_cursor` |
| `get_document` | `document_id`(필수), `view="normalized"`, `cursor?` | 문서 본문. 20k 토큰 단위로 잘리며 `cursor`로 이어 읽는다 |
| `list_collections` | — | 호출 주체가 볼 수 있는 컬렉션 목록 |

커서는 발급 주체에 묶이고 10분 뒤 만료된다. 만료·타주체 커서는 오류(`cursor 없이 다시 검색하십시오`)로 답한다. 페이지 절단은 렌더 순서가 아니라 관련도(`rank`) 순이다. 현재 `rag serve mcp`는 조립이 없어 기동하지 않으므로, 이 표는 배선이 끝났을 때의 사용 계약이다.

## 8. 문제 해결

| 증상 | 원인 | 조치 |
|------|------|------|
| `rag ingest: no input files found` (종료 2) | 디렉터리 안에 지원 확장자 파일이 없음 | §3.1 확장자 표 확인. `.hwp`(5.0)·`.docx`는 아직 미지원 |
| 수집 결과 `status`가 `committed`가 아님 | 파서 실패(암호화 HWPX, 손상 PDF, 스캔 PDF 등) | `.rag/artifacts/` 아래 마지막으로 생성된 산출물이 어느 스테이지인지 보고, 해당 스테이지의 `StageError.code`(예: `parse.unsupported_format`)로 판단 |
| `rag query: "unknown collection 'x'; run rag ingest --collection x ... first"` (종료 2) | 그 `--state-dir`에 컬렉션이 없음 | 같은 `--state-dir`로 먼저 수집. `.rag/collections.json`에서 이름 확인 |
| 질의 결과 `items=0` | 키워드가 문서에 전혀 없거나 `relevance_gate`에 걸림 | 문서에 실제로 있는 용어로 다시 질의. dense 채널이 가짜라 의미 유사 검색은 아직 안 된다(§0) |
| 결과가 항상 같은 순서·같은 점수 | 정상 | 임베더가 결정적 가짜라 재현성이 완벽하다. 실제 모델 배선 전까지 품질 평가에 쓰지 않는다 |
| API가 항상 401 | 키 미등록 | §6 스니펫처럼 인프로세스 등록. 외부 설정 파일은 아직 없음 |
| `rag serve mcp`가 15~30초 뒤 아무 출력 없이 종료 코드 0으로 끝남 | 서버 모듈에 실행 진입점·stdio 조립이 없음 | §7. 배선 작업은 [DEVELOPER.md §8](DEVELOPER.md) |
| `rag query` 출력이 `UnicodeEncodeError`로 죽음(Windows 콘솔) | 콘솔 인코딩이 CP949 | 최신 코드는 CLI가 UTF-8로 재설정한다. 구버전이면 `PYTHONIOENCODING=utf-8`을 설정 |
| `rag ingest`가 트레이스백을 내며 종료 코드 1 | 없는 파일·파싱 불가 파일(`.hwp` 등)이 스테이지 예외를 냄 | 경로를 확인하고 지원 포맷만 넣는다. 경로별 실패 항목으로 정리하는 일은 알려진 이슈 |
| Windows에서 `python`이 Microsoft Store로 감 | 시스템 Python 없음 | 항상 `uv run ...`으로 실행 |
| 결과 파일 줄바꿈이 CRLF | Windows 편집기 | 저장소는 `.gitattributes`로 LF 고정. 커밋 시 자동 정규화 |

로그·진단: 질의 `--format json`의 `diagnostics`에 채널별 후보 수·적용 필터·후처리 통계가 있다. 수집 산출물은 `.rag/artifacts/`에 계약 JSON 그대로 남으므로 `jq`로 본다.

## 9. 보안·데이터 취급 요약

- 모든 검색은 `tenant_id`·ACL **사전 필터**가 걸린 상태로만 실행된다. 필터 없는 검색은 코드가 예외를 던진다. CLI는 로컬 단일 테넌트를 자동 생성한다.
- 리트리벌 결과 캐시는 없다. 권한 회수는 다음 질의부터 즉시 반영된다.
- `fetch`는 사설 IP 대역과 `file://` 허용 루트 밖 경로를 거부한다(프로파일 `runtime.egress`).
- 개인정보 마스킹(`normalize.pii`)은 프로파일에 정의돼 있지만 lite-dev 배선에는 아직 없다. 민감 문서는 넣기 전에 직접 가린다.
- 라이선스: 코어는 Apache-2.0. 선택 extra `kiwi`(형태소 분석기 kiwipiepy)는 LGPL 정적 휠이라 배포 시 검토가 필요하다.

## 10. 로드맵에서 사용자에게 보이는 변화

- **M1 마감**: API·MCP를 CLI와 같은 실 파이프라인에 배선, API 키 설정 파일, Docker 스택 검증.
- **M2 한국어 1급**: HWP 5.0 사이드카, 실제 BGE-M3 임베딩·리랭커, OpenSearch Nori 채널, 렌더러 확대, 골든셋으로 측정한 품질 수치.
- **M3 운영**: Temporal 내구 실행, 멀티테넌시·ACL 강제 17지점 전부, 관측성, Helm, 웹훅.

전체는 [마일스톤](docs/11-roadmap/01-milestones.md), 현재 진행은 [진행 보고서](docs/12-appendix/00-progress-report.md).
