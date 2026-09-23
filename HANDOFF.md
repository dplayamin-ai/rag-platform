# HANDOFF — 다른 머신 인수인계

이 저장소는 Windows VDI(Docker·WSL·GPU 없음, `uv 0.12`만 있음)에서 작성됐다. 순수 Python 계층(층 1: 단위
테스트, 계약 왕복, `Qdrant` 로컬 모드, `FakeEmbedder` 등 결정적 가짜, `TestClient` e2e)은 이 VDI에서 이미
실행해 통과시켰다. **Docker·모델 가중치·GPU·외부 네트워크가 필요한 층(2·2b·3)은 이 VDI에서 실행하지
못했다.** 이 문서는 Docker가 있는 Linux/macOS 머신에서 그 나머지를 이어받는 첫 30분 절차다.

배경 문서(순서대로 읽으면 충분하다): [6단계 실행 계획 §8](docs/12-appendix/05-phase6-implementation-kit-plan.md)
(3층 검증 전략의 근거) · [보류 검증 원장](docs/12-appendix/09-deferred-verification-ledger.md)(무엇이
남았는지) · [진행 보고서](docs/12-appendix/00-progress-report.md)(전체 진행 상황과 재개 절차).

## 전제 조건

- Docker Engine + Docker Compose v2(`docker compose` 서브커맨드), Linux 또는 macOS.
- git, 인터넷 접근(패키지 설치, 그리고 층 2b를 다루려면 모델 허브 접근도 필요하다 — 아래 참고).
- 디스크 여유 공간 수 GB(컨테이너 이미지 + 선택적으로 모델 가중치).

## 첫 30분

### 0~5분 — 저장소 확보

```bash
git clone <remote-or-path> rag-platform && cd rag-platform
# 원격이 아직 없다면 VDI에서 받은 zip/번들을 그대로 푼다.
git log --oneline -5   # 베이스라인 커밋과 이후 이력 확인
```

### 5~10분 — uv 설치

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh   # 또는: brew install uv / pipx install uv
uv --version
```

`.github/workflows/ci.yml`의 `UV_VERSION`이 VDI에서 검증한 버전(`0.12.x`)이다. 크게 다른 버전이면 먼저
`uv lock --check`로 잠금 파일과의 정합을 확인한다.

### 10~15분 — 의존성 동기화

```bash
uv python install 3.12 3.13
uv sync --frozen --all-extras --group dev
```

`--frozen`은 `uv.lock`을 그대로 쓰고 갱신하지 않는다. 잠금을 실제로 갱신해야 하면 `--frozen`을 빼고
다시 실행한 뒤 diff를 리뷰하고서 커밋한다(리뷰 없이 커밋하지 않는다).

### 15~20분 — 층 1 재확인(신뢰 재구축)

VDI에서 이미 통과한 검사이지만, 다른 OS·커널에서도 그대로 통과하는지 반드시 다시 확인한다. 하나라도
실패하면 다음 단계로 넘어가지 말고 "실패를 발견했을 때" 절부터 따른다.

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run lint-imports
uv run pytest -q                              # 마커 제외 기본값(pyproject addopts)
node tools/validate-contracts.mjs --root .
node tools/audit-docs.mjs --root .
```

### 20~25분 — 보류 원장 열기

[`docs/12-appendix/09-deferred-verification-ledger.md`](docs/12-appendix/09-deferred-verification-ledger.md)를
연다. 표의 각 행이 VDI가 검증하지 못하고 넘긴 항목 하나다(위치·층·무엇·검증 방법·기대 결과·상태). 층
2(Docker)부터 처리한다. 소스가 바뀐 뒤 표를 다시 만들려면:

```bash
node tools/verify/gen-deferred-ledger.mjs
```

### 25~30분 — 층 2(Docker) 실행

```bash
tools/verify/run-deferred.sh          # Windows + Docker Desktop이면 tools/verify/run-deferred.ps1
```

이 스크립트는 `deploy/compose/compose.lite.yaml`(PostgreSQL·Qdrant·Valkey)을 기동하고(그 파일이 아직
없으면 경고만 내고 계속 진행한다 — 6단계 작업 패키지가 아직 그 파일을 만들지 않았을 수 있다),
`uv run pytest -q -m "needs_docker"`를 실행한 뒤 결과를 `tools/verify/results/deferred-<날짜>.json`에
남기고 compose 스택을 내린다. 30분 시점에서 여기까지가 "확인"이고, 이후는 실패 대응이다.

## 실패를 발견했을 때 수정 규칙

정본 우선순위는 **브리프 > 바이블 > ADR > 개별 문서**([설계 바이블](docs/02-architecture/00-design-bible.md)
§1.1), 계약 모델은 `schemas/*.schema.json`이 정본이고 Pydantic은 생성물이다.

1. **코드가 계약과 다르게 동작하면 코드를 고친다.** 테스트나 스키마를 실패에 맞춰 느슨하게 바꾸지 않는다.
2. **계약·바이블 자체가 실무에서 틀렸다고 판단되면** 바이블 §1.2 변경 절차를 따른다 — ADR을 먼저
   발의하고, 그 근거로 바이블 표를 갱신한 다음, 계약 `schema_version`을 절차대로 올린다. 사람 승인 없이
   바로 major 변경을 반영하지 않는다.
3. `xfail`로 표시된 계약 왕복 실패는 이미 알려진 이슈다(해당 계약 문서 "## 미해결 이슈" 확인). 새로
   발견한 실패만 다룬다.
4. 코드를 고쳤으면 층 1 전체(`ruff`·`mypy`·`lint-imports`·`pytest -q`·두 Node 검증기)를 다시 실행해
   회귀가 없는지 확인한다.
5. 마커 있는 테스트를 실제로 통과시켰으면 소스의 `# DEFERRED:` 주석과 관련 마커를 지우거나 갱신하고
   `node tools/verify/gen-deferred-ledger.mjs`를 다시 실행해 원장을 갱신한다. 원장 표의 상태 열을 손으로
   `검증됨`/`검증 실패`로 남긴다(생성기는 새 항목만 채우고 사람이 남긴 상태를 덮어쓰지 않는다).
6. 계약을 바꾸는 커밋은 트레일러 `Contract-Change: <kebab> <from> -> <to> (<level>)`을 남긴다
   ([CI/CD](docs/10-development/05-ci-cd.md) §4.2 결정; 아직 커밋 린터는 없으므로 사람이 직접 붙인다).

## 이 VDI에서 검증되지 않은 범위(명시)

| 층 | 대상 | VDI 상태 | 이 머신에서 할 일 |
|----|------|----------|----------------|
| 2 Docker | PostgreSQL 원장, Valkey KV, Qdrant 실서버 | 인메모리 대역(`testing.doubles.*`)만 검증 | `tools/verify/run-deferred.sh`/`.ps1` |
| 2b 모델 가중치 | BGE-M3 임베더, 크로스인코더 리랭커, OCR 모델 | `FakeEmbedder` 등 결정적 가짜만 검증, **모델 다운로드는 하지 않았다**(사용자 결정) | 아래 "모델 가중치" 절 참고 |
| 3 GPU | GPU 임베딩/리랭킹 처리량, PaddleOCR GPU 경로 | 모의 응답만 검증 | GPU 머신에서 `uv run pytest -m needs_gpu` |
| 네트워크 | 외부 서비스 실제 호출 | 모의만 검증 | `uv run pytest -m needs_network` |

### 모델 가중치(층 2b)

VDI에서는 사용자 결정으로 모델 가중치를 내려받지 않았다. 이 머신에서 실제 BGE-M3 등을 내려받아
`needs_model` 테스트를 돌릴지는 **이 문서가 대신 정하지 않는다** — 다운로드하기 전에 다시 사용자 승인을
받는다. 승인 없이는 `needs_model` 마커 테스트를 "보류" 상태로 남겨 두는 것이 실패가 아니라 올바른
대응이다.

### CI에서의 대응

`.github/workflows/ci.yml`의 `deferred` 잡은 `workflow_dispatch`로 수동 트리거되며, 이 스크립트와 같은
일을 GitHub Actions의 Docker 서비스 컨테이너(PostgreSQL·Qdrant·Valkey)로 수행한다. 로컬에서 먼저
통과시킨 뒤 그 잡도 한 번 트리거해 재확인하는 것을 권장한다.

## 기록·연락 위치

- **진행 상황의 단일 정본은 [`docs/12-appendix/00-progress-report.md`](docs/12-appendix/00-progress-report.md)**
  (§3 실측 현황, §7 재개 절차). 이 머신에서 검증을 마치면 결과를 이 문서에 추가한다 — 사람이 나중에
  이 파일을 읽고 진행 상황을 파악한다.
- 토큰/비용 집계는 루트 [`PAYMENT.MD`](PAYMENT.MD)(`node tools/usage-report.mjs --out PAYMENT.MD`로
  재생성).
- 이 작업은 사람이 실시간으로 대기하고 있지 않다(자율 진행 합의). 질문이 생기면 멈추지 말고 진행
  보고서나 관련 문서의 "## 미해결 이슈"에 남긴 뒤 계속한다. 유일한 예외는 **모델 가중치 다운로드
  여부**이며, 이것만은 사용자 승인 없이 진행하지 않는다.
- 이 저장소는 git 저장소다(2026-09-23 베이스라인 커밋). 검증 결과는 커밋으로 남긴다. 다른 세션이 동시에
  다른 디렉터리를 편집 중일 수 있으므로, 커밋 전에는 반드시 `git status`·`git log`로 충돌 여부를 확인
  하고 관련 없는 변경까지 함께 커밋하지 않는다.

## 자주 하는 실수

- `uv sync`에서 `--frozen`을 빼면 `uv.lock`이 갱신될 수 있다. 인터넷이 열려 있으면 그 자체는 안전하지만
  diff가 생기므로 리뷰 없이 커밋하지 않는다.
- `deploy/compose/compose.lite.yaml`이 아직 없을 수 있다(6단계 작업 패키지가 아직 도착하지 않은
  경우). 이때 `run-deferred.sh`는 경고만 내고 계속 진행한다 — 정상 동작이며 오류가 아니다.
- `needs_model` 마커 테스트는 모델을 실제로 내려받지 않고는 통과하지 않는다. 실패로 취급해 억지로
  고치려 하지 말고 "모델 가중치" 절의 절차를 따른다.
- pytest 종료 코드 `5`("no tests collected")는 실패가 아니다 — 해당 층에 아직 마커 붙은 테스트가 없다는
  뜻이며, `tools/dev.py test-deferred`와 `run-deferred.sh`/`.ps1` 모두 이를 성공으로 취급한다.
