---
title: 보류 검증 원장 (Deferred Verification Ledger)
status: active
owner: architecture
version: 1.0.0
last_updated: 2026-09-23
depends_on: ["05-phase6-implementation-kit-plan.md", "../10-development/05-ci-cd.md"]
generated_by: tools/verify/gen-deferred-ledger.mjs
---

# 보류 검증 원장

## 목적

Windows VDI(Docker·WSL·GPU 없음)에서 작성했지만 이 머신에서는 실행 검증할 수 없는 항목을 한 곳에 모은다. 항목은 `src/`·`tests/`의 `# DEFERRED: <무엇을 어디서 어떻게 검증>` 주석과 pytest 속성 마커(`needs_docker`·`needs_model`·`needs_gpu`·`needs_network`)에서 `tools/verify/gen-deferred-ledger.mjs`가 기계 생성하며, 사람이 표를 직접 편집하지 않는다(재생성: `node tools/verify/gen-deferred-ledger.mjs`). Docker가 있는 머신에서 검증을 마친 뒤에는 원본 주석과 이 문서의 상태 열을 함께 갱신하고 재생성한다.

## 범위

`src/**/*.py`·`tests/**/*.py`(`__pycache__` 제외) 전체. 3층 검증 전략(`docs/12-appendix/05-phase6-implementation-kit-plan.md` §8)의 층 2(Docker/Linux)·층 2b(모델 가중치)·층 3(GPU)와, 마커 목록에는 없지만 외부 네트워크가 필요한 항목(`needs_network`)을 포함한다. 층 1(순수 Python·단위 테스트·계약 왕복·Qdrant 로컬 모드·ONNX CPU·FastAPI TestClient)은 이 VDI에서 이미 실행 검증했으므로 이 원장에 없다.

## 1. 요약

| 항목 | 건수 |
|------|-----:|
| 전체 보류 항목 | 3 |
| 층 2 — `needs_docker` | 1 |
| 층 2b — `needs_model` | 0 |
| 층 3 — `needs_gpu` | 0 |
| 네트워크 — `needs_network` | 1 |
| 미분류(마커 언급 없이 `# DEFERRED:`만 있음) | 1 |
| `# DEFERRED:` 주석에서 수집 | 1 |
| pytest 속성 마커에서 수집 | 2 |

## 2. 보류 항목

| 위치 | 층 | 무엇 | 어디서·어떻게 검증 | 기대 결과 | 상태 |
|---|---|---|---|---|---|
| tests/adapters/index/test_qdrant_local.py:401 (test_server_mode_isolation) | 2 (Docker/Linux) | `@pytest.mark.needs_docker` — 인접한 `# DEFERRED:` 주석 없음(코드 규약 위반, 보강 필요) | Docker/Linux 머신에서 compose lite 기동 후 `uv run pytest -m needs_docker` (`tools/verify/run-deferred.sh` 또는 `.ps1`) | 실제 백엔드(PostgreSQL/Valkey/Qdrant 등)에서 인메모리 대역(`testing.doubles.*`)과 동일한 계약 동작을 확인하고 적합성 테스트를 통과한다 | 미검증 |
| tests/adapters/parse/test_hwpx.py:513 (test_public_samples_still_match_origin) | 네트워크 | `@pytest.mark.needs_network` — 인접한 `# DEFERRED:` 주석 없음(코드 규약 위반, 보강 필요) | 외부 네트워크 접근이 허용된 환경에서 `uv run pytest -m needs_network` | 외부 서비스 호출이 성공하고 실패·재시도 경로가 계약대로 동작한다 | 미검증 |
| tests/adapters/parse/test_hwpx.py:516 | 미분류(마커 언급 없음, 수동 분류 필요) | 외부 네트워크 가능 환경(프록시 허용 CI 야간 잡)에서 `uv run python tools/dev.py test-deferred`로 korea.kr 원본을 다시 받아 MANIFEST sha256과 대조한다. 원본 교체·삭제 시 표본 갱신 신호다. | `# DEFERRED:` 주석에 마커(`needs_docker`/`needs_model`/`needs_gpu`/`needs_network`)를 명시한 뒤 재생성 | 분류 후 결정 | 미검증 |

## 결정 사항 요약

- 이 원장의 모든 행은 최초 생성 시 상태 `미검증`으로 시작한다(05-phase6-implementation-kit-plan.md §8 D6-1). 다른 머신에서 `tools/verify/run-deferred.sh`(또는 `.ps1`)를 실행해 통과한 항목만 상태를 `검증됨`으로 바꾸고, 실패한 항목은 원인과 함께 `검증 실패`로 남긴다.
- `needs_model`은 모델 가중치 다운로드가 전제이며, VDI에서는 사용자 결정으로 다운로드하지 않는다. 다른 머신에서도 다운로드 여부는 매번 사용자 결정을 따른다.

## 미해결 이슈

- 미분류 항목(마커 언급이 없는 `# DEFERRED:` 주석)이 있으면 주석에 해당 마커를 명시하고 재생성한다.
- pytest 속성 마커가 있는데 인접한 `# DEFERRED:` 주석이 없는 테스트는 코드 규약(05-phase6-implementation-kit-plan.md §8) 위반이며 주석을 보강해야 한다.

## 참조

- [6단계 실행 계획](05-phase6-implementation-kit-plan.md) §8 · [CI/CD](../10-development/05-ci-cd.md) · [테스트 전략](../10-development/04-testing-strategy.md) · 루트 [HANDOFF.md](../../HANDOFF.md)
