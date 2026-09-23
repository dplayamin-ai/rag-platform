# 코드 파일 상단 한글 설명 주석 규칙 (Code Header Rule)

적용 대상: 이 저장소의 모든 소스 파일 — `src/**/*.py`, `tests/**/*.py`, `tools/**/*.py`, `tools/**/*.mjs`, `tools/**/*.js`, `sdk/**/*.ts`, 생성기가 만드는 파일 포함. 사용자 지시(2026-09-23): "코드 상단에 코드에 대한 설명 주석을 한글로, 개발자가 이해하기 쉽게".

## 규칙

1. **위치**: 파일 첫 줄부터. Python은 모듈 docstring(`"""..."""`)으로, JS/TS는 `//` 또는 `/** ... */` 블록으로. shebang·인코딩 선언이 있으면 그 바로 아래.
2. **언어**: 본문은 한국어. 식별자(클래스·함수·필드·열거값·경로·명령)는 영문 그대로 백틱으로 표기한다. 기술 용어는 처음 한 번 `한국어(English)` 병기.
3. **분량**: 6~15줄. 파일이 하는 일이 한 줄로 끝나면 짧게, 알고리즘·불변식이 있으면 길게. 본문 코드 주석을 대신하지 않는다(그건 별도).
4. **필수 항목** (순서 고정):
   - **역할**: 이 파일이 무엇을 하는가, 파이프라인·아키텍처의 어디에 놓이는가(한 문장).
   - **설계 근거**: 따르는 정본 절과 결정 — 예 `바이블 §4.2, §6.2 / ADR-0037 / 계약 03-contracts/05`. 계약 타입을 다루면 타입명 명시.
   - **구성**: 공개 클래스·함수 목록을 한 줄씩(`이름 — 하는 일`). 3개 이하면 문장으로.
   - **불변식·주의**: 지켜야 할 규칙(멱등성, 철자 정본, 보안 필터, 금지 사항) 중 이 파일에 해당하는 것.
   - **검증 계층**: `1층(여기서 검증)` / `2층 needs_docker` / `2b needs_model` / `3층 needs_gpu` 중 하나와, 보류된 검증이 있으면 `DEFERRED:` 한 줄.
5. **생성 파일**: 생성기가 헤더를 자동으로 넣는다. 첫 줄에 `GENERATED — 수정 금지. 재생성: <명령>` 를 한국어 설명과 함께 포함한다.
6. **테스트 파일**: 무엇을 검증하는지와 픽스처 출처(예: `docs/03-contracts/05 §예시`)를 적는다.
7. **금지**: 이모지, 영어 전용 헤더, 코드 복사·붙이기식 설명("이 함수는 x를 반환한다"만 있는 것), 변경 이력 나열(git이 담당).
8. **검사**: `ruff`의 `D100`(모듈 docstring 필수)을 켠다. 한국어 여부·필수 항목은 `tools/verify/check-headers.mjs`(6B에서 작성)가 검사한다.

## 예시 — Python

```python
"""RRF 융합기 — 채널별 후보 목록을 Reciprocal Rank Fusion으로 합쳐 `RankedSet(stage=fused)`를 만든다.

설계 근거: 바이블 §8.1 7단계·§3.2 O-01(k=60, 채널 가중 1:1:1, 변형 질의 0.5), ADR-0013.
계약: 입력 `CandidateSet.channel_runs[]`(03-contracts/10), 출력 `RankedSet.results[].score_breakdown`.

구성:
- `RrfFuser` — `Fuser` 프로토콜 구현. `fuse(runs, config) -> list[RankedResult]`
- `contribution(rank, weight, k)` — 단일 런의 기여 점수 `w / (k + rank)`
- `tie_break(results)` — 동점 시 `record_id` 오름차순(§8.1 불변식)

불변식: 각 결과의 `Σ contribution == fused_score`(허용 오차 1e-9). 서버 측 융합(Qdrant prefetch)은 쓰지 않는다 — 점수 분해가 사라진다.
검증 계층: 1층(여기서 검증) — `tests/unit/retrieval/test_rrf.py`, 골든 벡터 `tests/fixtures/fusion/rrf_small.json`.
"""
```

## 예시 — JS/TS 도구

```js
// 계약 검증기 — schemas/*.schema.json과 docs/03-contracts 문서를 대조해 문법·$ref·열거값(바이블 §5.7)·예시 유효성·문서 구조를 검사한다.
// 설계 근거: 계약 개요 03-contracts/00 §검증, 바이블 §1.2(CI 게이트). 외부 의존 없음(ajv 대체, 프록시 환경 고려).
// 구성: main() — 인자 파싱 후 검사 6종 실행; report() — ERROR/WARN/INFO 출력과 --json 저장.
// 주의: 바이블이 정본이므로 스키마 열거값이 다르면 스키마가 틀린 것으로 보고한다.
// 검증 계층: 1층. 실행: node tools/validate-contracts.mjs --root <repo> [--json out.json]
```

## 예시 — 생성 파일 첫 줄

```python
"""GENERATED — 수정 금지. 재생성: `uv run python tools/contracts_gen.py`

`ParsedDocument` 계약의 Pydantic v2 모델 — `schemas/parsed-document.schema.json`(바이블 §5.4)에서 생성했다.
...
"""
```
